"""python manage.py test apps.plaintes.tests_fichiers — accès protégé aux scans"""
import shutil, tempfile
from unittest import mock
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.plaintes.models import PieceJointe
from apps.rdv.models import Tribunal
from sunutribunal.fichiers import lien_signe

MEDIA_TEST = tempfile.mkdtemp()
CONTENU_SCAN = b'\xff\xd8\xff' + b'scan' * 25


@override_settings(MEDIA_ROOT=MEDIA_TEST)
class FichiersProtegesTests(APITestCase):

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEST, ignore_errors=True)

    def setUp(self):
        self.tgi = Tribunal.objects.create(nom='TGI Dakar', adresse='Dakar')
        mk = User.objects.create_user
        self.citoyen = mk('c@test.sn', 'motdepasse123', nom='Diallo')
        self.voisin  = mk('v@test.sn', 'motdepasse123', nom='Ndiaye')
        self.admin_django = mk('chef@test.sn', 'motdepasse123', nom='Sy', role='admin',
                               tribunal=self.tgi, is_staff=True)

    def _deposer(self):
        self.client.force_authenticate(self.citoyen)
        scan = SimpleUploadedFile('scan.jpg', CONTENU_SCAN, content_type='image/jpeg')
        r = self.client.post('/api/plaintes/', {'tribunal': self.tgi.id, 'nature': 'foncier',
                                                'description': 'Litige sur une parcelle.', 'pieces': [scan]},
                             format='multipart')
        self.assertEqual(r.status_code, 201, r.data)
        self.client.force_authenticate(None)
        return r.data

    def _chemin(self, url):
        return urlparse(url).path

    def test_lien_signe_ouvre_le_fichier_sans_jeton_jwt(self):
        piece = self._deposer()['pieces'][0]
        self.assertIn('/api/fichiers/', piece['fichier'])
        self.assertNotIn('/media/', piece['fichier'])

        r = self.client.get(self._chemin(piece['fichier']))   # lien ouvert dans le navigateur, sans connexion
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), CONTENU_SCAN)
        self.assertEqual(r['Content-Type'], 'image/jpeg')
        self.assertTrue(r['Content-Disposition'].startswith('inline'))
        self.assertIn('no-store', r['Cache-Control'])

    def test_autre_citoyen_n_obtient_pas_le_lien(self):
        plainte = self._deposer()
        self.client.force_authenticate(self.voisin)
        self.assertEqual(self.client.get(f"/api/plaintes/{plainte['id']}/").status_code, 404)
        self.assertEqual(self.client.get('/api/plaintes/').data, [])

    def test_media_ferme_au_public_ouvert_a_django_admin(self):
        self._deposer()
        url = '/media/' + PieceJointe.objects.get().fichier.name

        r = self.client.get(url)                       # anonyme : renvoyé vers la connexion de l'admin
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/login/', r['Location'])

        self.client.force_login(self.citoyen)          # citoyen connecté : pas un compte de l'admin
        self.assertEqual(self.client.get(url).status_code, 302)

        self.client.force_login(self.admin_django)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), CONTENU_SCAN)

    def test_lien_modifie_refuse(self):
        url = self._chemin(self._deposer()['pieces'][0]['fichier'])
        jeton = url.rstrip('/').split('/')[-1]
        falsifie = url.replace(jeton, jeton[:-2] + ('AA' if not jeton.endswith('AA') else 'BB'))
        self.assertEqual(self.client.get(falsifie).status_code, 404)
        self.assertEqual(self.client.get('/api/fichiers/plaintes/').status_code, 404)

    def test_lien_expire(self):
        url = self._chemin(self._deposer()['pieces'][0]['fichier'])
        with mock.patch('sunutribunal.fichiers.DUREE_VALIDITE', -1):
            r = self.client.get(url)
        self.assertEqual(r.status_code, 410)
        self.assertIn('expiré', r.content.decode())

    def test_impossible_de_sortir_du_dossier_media(self):
        self.assertEqual(self.client.get(lien_signe('../manage.py')).status_code, 404)
        self.assertEqual(self.client.get(lien_signe('plaintes/pieces/absent.pdf')).status_code, 404)

    def test_fichier_html_telecharge_jamais_affiche(self):
        nom = default_storage.save('registres/courriers/page.html', ContentFile(b'<script>alert(1)</script>'))
        r = self.client.get(lien_signe(nom))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Disposition'].startswith('attachment'))
        self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
