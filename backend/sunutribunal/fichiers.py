"""
SunuTribunal — Accès protégé aux fichiers envoyés (scans, pièces jointes)
--------------------------------------------------------------------------
Les fichiers ne sont pas publics : l'API renvoie à la place un lien signé, valable
DUREE_VALIDITE secondes. Il n'est donné qu'à qui voit déjà le dossier, car les vues
filtrent les plaintes, courriers et archives selon l'utilisateur.
Le lien s'ouvre directement (<a href>, APK) : pas besoin d'en-tête Authorization.
"""
import mimetypes
import os

from django.core import signing
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.db import models
from django.http import FileResponse, Http404, HttpResponse
from django.urls import reverse
from rest_framework import serializers

SEL = 'sunutribunal.fichiers'
DUREE_VALIDITE = 60 * 60   # 1 heure : la page en redemande un à chaque chargement

# Affichés dans le navigateur ; tout le reste est téléchargé (jamais de HTML/SVG exécuté)
TYPES_AFFICHABLES = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp', 'image/gif'}


def lien_signe(nom, request=None):
    """Adresse temporaire du fichier `nom` (chemin dans MEDIA_ROOT)."""
    url = reverse('fichier_protege', args=[signing.dumps(nom, salt=SEL, compress=True)])
    return request.build_absolute_uri(url) if request else url


def telecharger(request, jeton):
    """GET /api/fichiers/<jeton>/ — sert le fichier si le lien est authentique et valide."""
    try:
        nom = signing.loads(jeton, salt=SEL, max_age=DUREE_VALIDITE)
    except signing.SignatureExpired:
        return HttpResponse('Ce lien a expiré. Rechargez la page SunuTribunal pour en obtenir un nouveau.',
                            status=410, content_type='text/plain; charset=utf-8')
    except signing.BadSignature:
        raise Http404
    try:
        fichier = default_storage.open(nom, 'rb')
    except (FileNotFoundError, SuspiciousFileOperation):
        raise Http404

    type_mime = mimetypes.guess_type(nom)[0] or 'application/octet-stream'
    reponse = FileResponse(fichier, content_type=type_mime, filename=os.path.basename(nom),
                           as_attachment=type_mime not in TYPES_AFFICHABLES)
    reponse['Cache-Control'] = 'private, no-store'
    reponse['X-Content-Type-Options'] = 'nosniff'
    reponse['Referrer-Policy'] = 'no-referrer'
    return reponse


class FichierProtege(serializers.FileField):
    """Champ fichier dont l'adresse renvoyée par l'API est un lien signé."""

    def to_representation(self, value):
        if not value:
            return None
        return lien_signe(value.name, self.context.get('request'))


class FichiersProteges:
    """À placer avant ModelSerializer : tous les FileField du modèle deviennent des liens signés."""
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.FileField: FichierProtege,
    }
