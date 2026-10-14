"""
Authentification JWT avec contrôle du mot de passe provisoire.
Tant qu'un compte doit changer son mot de passe (SecuriteCompte.doit_changer_mdp), l'API
répond 403 {"code": "changement_mdp_requis"} partout, sauf pour :
  - consulter son profil (GET /api/auth/me/)
  - changer son mot de passe (POST /api/auth/changer-mot-de-passe/)
La déconnexion se fait côté application (le jeton est simplement effacé) : elle reste possible.
Le blocage est fait côté serveur : un jeton obtenu avec le mot de passe provisoire
ne donne accès à aucune donnée.
"""
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import doit_changer_mdp

CODE_CHANGEMENT_REQUIS = 'changement_mdp_requis'

ROUTES_AUTORISEES = {
    ('GET',  '/api/auth/me/'),
    ('POST', '/api/auth/changer-mot-de-passe/'),
}


class ChangementMotDePasseRequis(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = CODE_CHANGEMENT_REQUIS
    # Le code figure dans la réponse JSON : le frontend s'en sert pour ouvrir la page « Changer le mot de passe »
    default_detail = {'detail': 'Vous devez changer votre mot de passe provisoire avant de continuer.',
                      'code': CODE_CHANGEMENT_REQUIS}


class JWTAuthentificationSecurisee(JWTAuthentication):
    def authenticate(self, request):
        resultat = super().authenticate(request)
        if resultat is None:
            return None
        user, jeton = resultat
        if (request.method, request.path) not in ROUTES_AUTORISEES and doit_changer_mdp(user):
            raise ChangementMotDePasseRequis()
        return user, jeton
