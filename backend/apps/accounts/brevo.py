"""
SunuTribunal — Envoi des e-mails par l'API web de Brevo (HTTPS, port 443)
-------------------------------------------------------------------------
Backend Django utilisé quand BREVO_API_KEY est renseignée dans backend/.env.
Il remplace le SMTP de Gmail (ports 465/587), bloqué par certains réseaux Wi-Fi :
l'API passe par le même port que les pages web, que les réseaux laissent ouvert.

L'expéditeur (DEFAULT_FROM_EMAIL) doit être validé dans Brevo :
Brevo → Senders, domains & dedicated IPs → Senders → Add a sender.
"""
from email.utils import parseaddr

import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

URL_API = 'https://api.brevo.com/v3/smtp/email'


class ErreurBrevo(Exception):
    """Refus de l'API Brevo ; `message` est déjà une phrase lisible pour le greffier en chef."""

    def __init__(self, message, detail=''):
        super().__init__(f'{message} {detail}'.strip())
        self.message = message


class SansServiceEmailBackend(BaseEmailBackend):
    """
    Production sans BREVO_API_KEY ni Gmail : refuse d'envoyer. Le greffier en chef voit l'erreur
    au lieu de « identifiants envoyés », et l'e-mail (avec le mot de passe provisoire) n'est
    jamais écrit dans le journal du serveur, contrairement au backend « console ».
    """

    def send_messages(self, email_messages):
        if email_messages and not self.fail_silently:
            raise ErreurBrevo("Aucun service d'e-mail n'est configuré sur le serveur "
                              "(ajouter BREVO_API_KEY dans ses variables d'environnement).")
        return 0


def _adresse(texte):
    nom, email = parseaddr(texte)
    return {'name': nom, 'email': email} if nom else {'email': email}


class BrevoEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        envoyes = 0
        for message in email_messages:
            try:
                self._envoyer(message)
                envoyes += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return envoyes

    def _envoyer(self, message):
        corps = {
            'sender':      _adresse(message.from_email),
            'to':          [_adresse(a) for a in message.to],
            'subject':     message.subject,
            'textContent': message.body,
        }
        if message.cc:
            corps['cc'] = [_adresse(a) for a in message.cc]
        if message.bcc:
            corps['bcc'] = [_adresse(a) for a in message.bcc]
        for contenu, type_mime in getattr(message, 'alternatives', []):
            if type_mime == 'text/html':
                corps['htmlContent'] = contenu

        reponse = requests.post(
            URL_API, json=corps, timeout=settings.EMAIL_TIMEOUT,
            headers={'api-key': settings.BREVO_API_KEY, 'accept': 'application/json'})
        if reponse.status_code in (200, 201, 202):
            return
        if reponse.status_code in (401, 403):
            raise ErreurBrevo("Brevo a refusé la clé d'API (BREVO_API_KEY incorrecte ou compte non activé).",
                              reponse.text)
        if reponse.status_code == 400 and 'sender' in reponse.text.lower():
            raise ErreurBrevo("L'expéditeur n'est pas validé dans Brevo (Senders → Add a sender).", reponse.text)
        raise ErreurBrevo("Brevo n'a pas pu envoyer l'e-mail.", f'HTTP {reponse.status_code} {reponse.text}')
