"""
SunuTribunal — Envoi de SMS réels (téléphone Android, Brevo ou Twilio)
----------------------------------------------------------------------
Configuration dans backend/.env, au choix (ordre de priorité) :
  • Téléphone Android, GRATUIT (application « SMS Gateway for Android », https://sms-gate.app) :
    le serveur demande au téléphone d'envoyer le SMS avec sa carte SIM (coût : celui du forfait).
    SMSGATE_LOGIN=...  SMSGATE_PASSWORD=...   (affichés dans l'application, mode « Cloud server »)
    Le téléphone doit rester allumé, connecté à internet, avec l'application ouverte en arrière-plan.
  • Brevo (payant : crédits SMS) :
    BREVO_API_KEY=xkeysib-...            (la même clé que pour les e-mails)
    BREVO_SMS_SENDER=SunuTrib            (11 caractères max, lettres/chiffres, sans espace)
    Il faut des crédits SMS : Brevo → Campaigns → SMS → acheter des crédits.
  • Twilio :
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    TWILIO_FROM_NUMBER=+1xxxxxxxxxx      (le compte d'essai refuse les textes libres)

Chaque tentative est enregistrée dans le journal (modèle SMSLog),
même en cas d'échec : l'action métier (valider un RDV…) n'est jamais bloquée.
"""
import logging
import re
import unicodedata

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def normaliser_telephone(numero: str) -> str | None:
    """
    Convertit un numéro sénégalais au format international E.164.
      77 123 45 67      → +221771234567
      00221771234567    → +221771234567
      221771234567      → +221771234567
      +33612345678      → +33612345678  (numéros étrangers acceptés)
    Retourne None si le numéro est invalide.
    """
    if not numero:
        return None
    n = re.sub(r'[\s.\-()/]', '', str(numero))
    if n.startswith('00'):
        n = '+' + n[2:]
    if re.fullmatch(r'[73]\d{8}', n):          # 9 chiffres sénégalais (mobile 7x, fixe 33)
        n = '+221' + n
    elif re.fullmatch(r'221[73]\d{8}', n):
        n = '+' + n
    if re.fullmatch(r'\+\d{8,15}', n):
        return n
    return None


def sans_accents(texte: str) -> str:
    """Les SMS sans accents tiennent en 160 caractères (au lieu de 70) : moins chers."""
    t = unicodedata.normalize('NFKD', texte)
    return ''.join(c for c in t if not unicodedata.combining(c)).replace('’', "'")


class SMSErreur(Exception):
    """Refus du fournisseur SMS ; `str(e)` est déjà une phrase lisible pour l'agent."""


# Codes couleur ANSI (ex. « \x1b[31m ») que la bibliothèque Twilio met dans ses messages
_ANSI = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')


def _nettoyer(texte) -> str:
    return ' '.join(_ANSI.sub('', str(texte)).split())


def message_lisible(exc) -> str:
    """
    Phrase courte en français pour l'écran et le journal des SMS.
    Le détail technique complet n'est écrit que dans le journal du serveur.
    """
    if isinstance(exc, SMSErreur):
        return str(exc)
    if isinstance(exc, (requests.RequestException, ConnectionError, TimeoutError)):
        return 'Service SMS injoignable (connexion internet).'
    try:
        from twilio.base.exceptions import TwilioRestException
    except ImportError:                              # bibliothèque Twilio absente
        TwilioRestException = ()
    if TwilioRestException and isinstance(exc, TwilioRestException):
        texte = _nettoyer(getattr(exc, 'msg', '') or exc).lower()
        code = getattr(exc, 'code', None)
        if 'template' in texte:
            return ("Compte Twilio d'essai : seuls les modèles de SMS prédéfinis sont autorisés. "
                    "Utilisez la passerelle SMS gratuite par téléphone Android (SMSGATE_LOGIN dans le .env).")
        if code == 21608 or 'unverified' in texte:
            return ("Numéro non vérifié dans le compte Twilio d'essai "
                    "(Twilio → Phone Numbers → Verified Caller IDs).")
        if code == 20003 or exc.status == 401:
            return 'Identifiants Twilio refusés (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN).'
        if code in (21408, 21612):
            return "Twilio n'autorise pas l'envoi vers ce pays (Messaging → Geo permissions)."
        if code in (21211, 21614):
            return 'Numéro de téléphone refusé par Twilio.'
        return f'Twilio a refusé le SMS (code {code}).' if code else 'Twilio a refusé le SMS.'
    # Autre erreur : première phrase, sans codes couleur, longueur limitée
    return _nettoyer(exc).split(' More information')[0][:200] or "Le SMS n'a pas pu être envoyé."


def twilio_configure() -> bool:
    return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER)


def brevo_sms_configure() -> bool:
    return bool(settings.BREVO_API_KEY and settings.BREVO_SMS_SENDER)


def smsgate_configure() -> bool:
    return bool(getattr(settings, 'SMSGATE_LOGIN', '') and getattr(settings, 'SMSGATE_PASSWORD', ''))


def _envoyer_smsgate(numero: str, message: str) -> str:
    """
    Envoie par votre téléphone Android (API « SMS Gateway for Android »).
    Le serveur dépose le SMS ; le téléphone l'envoie avec sa carte SIM dès qu'il est en ligne.
    """
    reponse = requests.post(
        settings.SMSGATE_URL, timeout=20,
        auth=(settings.SMSGATE_LOGIN, settings.SMSGATE_PASSWORD),
        json={'message': message, 'phoneNumbers': [numero]})
    if reponse.status_code in (200, 201, 202):
        try:
            return str(reponse.json().get('id', ''))
        except ValueError:
            return ''
    logger.error('Passerelle SMS refusée : HTTP %s %s', reponse.status_code, reponse.text[:500])
    if reponse.status_code == 401:
        raise SMSErreur('Identifiants de la passerelle SMS refusés (SMSGATE_LOGIN / SMSGATE_PASSWORD).')
    raise SMSErreur(f"La passerelle SMS du téléphone a refusé l'envoi (erreur {reponse.status_code}).")


URL_BREVO_SMS = 'https://api.brevo.com/v3/transactionalSMS/sms'


def _envoyer_brevo(numero: str, message: str) -> str:
    """Envoie par l'API Brevo (HTTPS) ; retourne l'identifiant du message, lève Exception sinon."""
    reponse = requests.post(
        URL_BREVO_SMS, timeout=20,
        headers={'api-key': settings.BREVO_API_KEY, 'accept': 'application/json'},
        json={'sender': settings.BREVO_SMS_SENDER, 'recipient': numero.lstrip('+'),
              'content': message, 'type': 'transactional'})
    if reponse.status_code in (200, 201):
        return str(reponse.json().get('messageId', ''))
    logger.error('Brevo SMS refusé : HTTP %s %s', reponse.status_code, reponse.text[:500])
    if reponse.status_code in (401, 403):
        raise SMSErreur("Brevo a refusé la clé d'API (BREVO_API_KEY).")
    if 'credit' in reponse.text.lower():
        raise SMSErreur('Crédits SMS Brevo insuffisants (Brevo → SMS → acheter des crédits).')
    raise SMSErreur(f"Brevo n'a pas pu envoyer le SMS (erreur {reponse.status_code}).")


def _envoyer_twilio(numero: str, message: str) -> str:
    from twilio.rest import Client
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    msg = client.messages.create(body=message, from_=settings.TWILIO_FROM_NUMBER, to=numero)
    return getattr(msg, 'sid', '') or ''


def envoyer_sms(telephone: str, message: str, destinataire=None, objet_ref: str = ''):
    """
    Envoie un SMS et l'inscrit au journal.
    Retourne l'objet SMSLog (champ .statut : envoye / echec / non_configure / numero_invalide).
    """
    from .models import SMSLog

    message = sans_accents(message)[:600]
    numero = normaliser_telephone(telephone)
    log = SMSLog(destinataire=destinataire, telephone=numero or (telephone or ''),
                 message=message, objet_ref=objet_ref)

    if not numero:
        log.statut = 'numero_invalide'
        log.erreur = 'Numéro de téléphone absent ou invalide.'
    elif not (smsgate_configure() or brevo_sms_configure() or twilio_configure()):
        log.statut = 'non_configure'
        log.erreur = ('Aucun fournisseur SMS : renseigner SMSGATE_LOGIN + SMSGATE_PASSWORD (téléphone Android, '
                      'gratuit), BREVO_API_KEY + BREVO_SMS_SENDER, ou les identifiants TWILIO_* dans .env')
    else:
        # Priorité : téléphone Android (gratuit) > Brevo > Twilio
        fournisseur, envoi = ((('Passerelle Android', _envoyer_smsgate) if smsgate_configure() else None)
                              or (('Brevo', _envoyer_brevo) if brevo_sms_configure() else None)
                              or ('Twilio', _envoyer_twilio))
        try:
            log.sid = envoi(numero, message)[:64]
            log.statut = 'envoye'
        except Exception as e:  # erreur réseau, crédit épuisé, compte d'essai Twilio…
            log.statut = 'echec'
            # Phrase lisible pour l'écran et le journal SMS ; détail complet dans le journal du serveur
            log.erreur = message_lisible(e)[:1000]
            logger.error('SMS %s en échec vers %s : %s', fournisseur, numero, _nettoyer(e))

    log.save()
    return log
