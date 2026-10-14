"""
SunuTribunal — Envoi des identifiants provisoires par e-mail
------------------------------------------------------------
Plus personne ne saisit de mot de passe pour un agent : le serveur en génère un,
l'envoie par e-mail, et l'agent doit le changer à sa première connexion.

Configuration (backend/.env) : BREVO_API_KEY (prioritaire, voir brevo.py) ou EMAIL_HOST_USER +
EMAIL_HOST_PASSWORD (Gmail SMTP), DEFAULT_FROM_EMAIL, FRONTEND_URL. Sans aucun des deux,
l'e-mail s'affiche dans le terminal du serveur.
"""
import logging
import smtplib
import socket

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.html import escape

from .brevo import ErreurBrevo
from .models import SecuriteCompte, IdentifiantsProvisoires, generer_mot_de_passe

logger = logging.getLogger(__name__)

OBJET_CREATION = "SunuTribunal — Vos identifiants d'accès à l'espace tribunal"
OBJET_REINITIALISATION = 'SunuTribunal — Réinitialisation de votre mot de passe'

# Charte « Encre & Or » (styles en ligne : seuls compris par toutes les messageries)
ENCRE, OR, IVOIRE, TEXTE, GRIS = '#0E1A2B', '#C9A45C', '#FBF6EC', '#1C2B44', '#6B6457'


def _message_erreur(exc):
    """Erreur d'envoi traduite en phrase lisible pour le greffier en chef."""
    if isinstance(exc, ErreurBrevo):
        return exc.message
    if isinstance(exc, requests.RequestException):
        return "Le service d'e-mail Brevo est injoignable (connexion internet)."
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "Le serveur d'e-mail a refusé la connexion (identifiants Gmail incorrects dans le .env)."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "L'adresse e-mail du destinataire a été refusée par le serveur."
    if isinstance(exc, (socket.timeout, socket.gaierror, ConnectionError, smtplib.SMTPConnectError,
                        smtplib.SMTPServerDisconnected)):
        return "Le serveur d'e-mail est injoignable (connexion internet ou configuration SMTP)."
    return "L'e-mail n'a pas pu être envoyé."


def _contexte(user, mot_de_passe, cree_par):
    lien = (getattr(settings, 'FRONTEND_URL', '') or '').strip().rstrip('/')
    if not lien:
        logger.warning('FRONTEND_URL absent du .env : e-mail envoyé sans lien vers la plateforme')
    return {
        'prenom_nom':  user.full_name or user.email,
        'role':        user.get_role_display(),
        'tribunal':    user.tribunal.nom if user.tribunal_id else 'Non renseignée',
        'createur':    (cree_par.full_name or cree_par.email) if cree_par else "L'administration SunuTribunal",
        'email':       user.email,
        'mot_de_passe': mot_de_passe,
        'lien':        lien,
    }


def _texte(c, reinitialisation):
    intro = ("Votre mot de passe SunuTribunal vient d'être réinitialisé à votre demande ou à celle du greffe."
             if reinitialisation else
             "Un compte vient de vous être créé sur SunuTribunal, la plateforme de gestion des\n"
             "services judiciaires.")
    acces = f"  [ Accéder à SunuTribunal ]  → {c['lien']}\n\n" if c['lien'] else ''
    titre = 'Vos nouveaux identifiants' if reinitialisation else 'Vos identifiants de première connexion'
    return (
        f"Bonjour {c['prenom_nom']},\n\n"
        f"{intro}\n\n"
        f"  • Rôle : {c['role']}\n"
        f"  • Juridiction : {c['tribunal']}\n"
        f"  • {'Réinitialisé' if reinitialisation else 'Compte créé'} par : {c['createur']}\n\n"
        f"{titre} :\n\n"
        f"  Adresse e-mail : {c['email']}\n"
        f"  Mot de passe provisoire : {c['mot_de_passe']}\n\n"
        f"{acces}"
        "Pour des raisons de sécurité :\n"
        "  1. Il vous sera demandé de définir un nouveau mot de passe dès votre première connexion.\n"
        "  2. Ce mot de passe provisoire est personnel : ne le communiquez à personne.\n"
        "  3. Supprimez ce message une fois votre mot de passe modifié.\n\n"
        "Si vous n'êtes pas à l'origine de cette demande ou si vous pensez qu'il s'agit d'une erreur,\n"
        "contactez sans délai le greffe de votre juridiction.\n\n"
        "Cordialement,\n\n"
        "L'équipe SunuTribunal\n"
        f"{c['tribunal']}\n\n"
        "—\n"
        "Ce message a été envoyé automatiquement, merci de ne pas y répondre.\n"
    )


def _html(c, reinitialisation):
    e = {k: escape(v) for k, v in c.items()}      # aucune donnée n'est interprétée comme du HTML
    intro = ("Votre mot de passe <strong>SunuTribunal</strong> vient d'être réinitialisé à votre demande "
             "ou à celle du greffe."
             if reinitialisation else
             "Un compte vient de vous être créé sur <strong>SunuTribunal</strong>, la plateforme de gestion "
             "des services judiciaires.")
    titre = 'Vos nouveaux identifiants' if reinitialisation else 'Vos identifiants de première connexion'
    ligne = lambda libelle, valeur: (
        f'<tr><td style="padding:4px 0;color:{GRIS};font-size:14px;width:150px;">{libelle}</td>'
        f'<td style="padding:4px 0;color:{TEXTE};font-size:14px;font-weight:600;">{valeur}</td></tr>')
    bouton = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:28px auto 8px;">'
        f'<tr><td style="background:{ENCRE};border-radius:10px;">'
        f'<a href="{e["lien"]}" target="_blank" style="display:inline-block;padding:14px 32px;'
        f'font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:bold;color:#ffffff;'
        f'text-decoration:none;">Accéder à SunuTribunal</a></td></tr></table>'
        f'<p style="margin:0;text-align:center;font-size:12px;color:{GRIS};">{e["lien"]}</p>'
    ) if c['lien'] else ''
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SunuTribunal</title></head>
<body style="margin:0;padding:0;background:#F7F3EA;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F7F3EA;padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width:600px;background:#ffffff;border:1px solid #E7E1D4;border-radius:14px;overflow:hidden;
              font-family:Arial,Helvetica,sans-serif;color:{TEXTE};">
  <tr><td style="background:{ENCRE};padding:22px 32px;">
    <span style="font-family:Georgia,'Times New Roman',serif;font-size:26px;font-weight:bold;color:#ffffff;">Sunu</span><span
          style="font-family:Georgia,'Times New Roman',serif;font-size:26px;font-weight:bold;color:{OR};">Tribunal</span>
    <div style="font-size:11px;letter-spacing:2px;color:#B4BFD1;margin-top:4px;">JUSTICE DIGITALE · SÉNÉGAL</div>
  </td></tr>
  <tr><td style="padding:32px;">
    <p style="margin:0 0 16px;font-size:16px;">Bonjour <strong>{e['prenom_nom']}</strong>,</p>
    <p style="margin:0 0 20px;font-size:14px;line-height:1.6;">{intro}</p>
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
      {ligne('Rôle', e['role'])}
      {ligne('Juridiction', e['tribunal'])}
      {ligne('Réinitialisé par' if reinitialisation else 'Compte créé par', e['createur'])}
    </table>
    <p style="margin:0 0 10px;font-size:14px;font-weight:bold;">{titre} :</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="background:{IVOIRE};border:1px solid {OR};border-left:4px solid {OR};border-radius:10px;">
      <tr><td style="padding:18px 20px;">
        <div style="font-size:13px;color:{GRIS};">Adresse e-mail</div>
        <div style="font-size:15px;font-weight:600;margin:2px 0 14px;">{e['email']}</div>
        <div style="font-size:13px;color:{GRIS};">Mot de passe provisoire</div>
        <div style="font-family:'Courier New',Courier,monospace;font-size:22px;font-weight:bold;letter-spacing:2px;
                    color:{ENCRE};margin-top:4px;">{e['mot_de_passe']}</div>
      </td></tr>
    </table>
    {bouton}
    <p style="margin:28px 0 8px;font-size:14px;font-weight:bold;">Pour des raisons de sécurité :</p>
    <ol style="margin:0 0 20px;padding-left:20px;font-size:14px;line-height:1.7;">
      <li>Il vous sera demandé de définir un nouveau mot de passe dès votre première connexion.</li>
      <li>Ce mot de passe provisoire est personnel : ne le communiquez à personne.</li>
      <li>Supprimez ce message une fois votre mot de passe modifié.</li>
    </ol>
    <p style="margin:0 0 24px;font-size:13px;line-height:1.6;color:{GRIS};">
      Si vous n'êtes pas à l'origine de cette demande ou si vous pensez qu'il s'agit d'une erreur,
      contactez sans délai le greffe de votre juridiction.</p>
    <p style="margin:0;font-size:14px;line-height:1.6;">Cordialement,<br><br>
      <strong>L'équipe SunuTribunal</strong><br>{e['tribunal']}</p>
  </td></tr>
  <tr><td style="background:#F7F3EA;border-top:1px solid #E7E1D4;padding:14px 32px;font-size:11px;color:{GRIS};
                 text-align:center;">Ce message a été envoyé automatiquement, merci de ne pas y répondre.</td></tr>
</table>
</td></tr></table>
</body></html>"""


def envoyer_identifiants(user, mot_de_passe, cree_par, reinitialisation=False):
    """
    Envoie l'e-mail (HTML + texte brut). Ne lève jamais d'exception :
    renvoie (True, '') ou (False, message lisible) ; l'erreur technique est journalisée.
    """
    c = _contexte(user, mot_de_passe, cree_par)
    message = EmailMultiAlternatives(
        subject=OBJET_REINITIALISATION if reinitialisation else OBJET_CREATION,
        body=_texte(c, reinitialisation),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(_html(c, reinitialisation), 'text/html')
    try:
        message.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Échec de l'envoi des identifiants à %s", user.email)
        return False, _message_erreur(exc)
    IdentifiantsProvisoires.objects.update_or_create(
        user=user, defaults={'mdp_provisoire_envoye_le': timezone.now()})
    return True, ''


def attribuer_identifiants(user, cree_par, reinitialisation=False):
    """
    Génère un mot de passe provisoire, l'envoie par e-mail, puis — seulement si l'envoi a réussi —
    l'enregistre (haché) et impose son changement à la prochaine connexion.
    Si l'e-mail échoue, le mot de passe actuel reste valable : personne ne se retrouve avec
    un mot de passe que nul ne connaît. (Un compte neuf garde un mot de passe inutilisable
    jusqu'à un envoi réussi via « Renvoyer les identifiants ».)
    Renvoie {'email_envoye': bool, 'email_erreur': str} — jamais le mot de passe.
    """
    suivi, cree = IdentifiantsProvisoires.objects.get_or_create(user=user, defaults={'cree_par': cree_par})
    if not reinitialisation:
        SecuriteCompte.exiger_changement(user)     # compte neuf : changement exigé dès la 1re connexion

    mot_de_passe = generer_mot_de_passe()
    envoye, erreur = envoyer_identifiants(user, mot_de_passe, cree_par, reinitialisation=reinitialisation)
    if not envoye:
        return {'email_envoye': False, 'email_erreur': erreur}

    user.set_password(mot_de_passe)
    user.save(update_fields=['password'])
    SecuriteCompte.exiger_changement(user)
    if not cree and reinitialisation:
        suivi.mdp_change_le = None
        suivi.save(update_fields=['mdp_change_le'])
    return {'email_envoye': True, 'email_erreur': ''}
