"""python manage.py test apps.accounts.tests_superutilisateur — premier compte créé au démarrage"""
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.accounts.models import User

VARIABLES = {'DJANGO_SUPERUSER_EMAIL': 'proprietaire@sunutribunal.sn',
             'DJANGO_SUPERUSER_PASSWORD': 'Baobab-Encre-2026!',
             'DJANGO_SUPERUSER_NOM': 'Ndiaye'}


class CreerSuperutilisateurTests(TestCase):

    def _lancer(self, variables):
        sortie = StringIO()
        with mock.patch.dict('os.environ', variables, clear=False):
            call_command('creer_superutilisateur', stdout=sortie)
        return sortie.getvalue()

    def test_sans_variables_ne_fait_rien(self):
        with mock.patch.dict('os.environ', {}, clear=True):
            call_command('creer_superutilisateur', stdout=StringIO())
        self.assertFalse(User.objects.exists())

    def test_cree_puis_ne_recree_pas_au_redemarrage(self):
        self.assertIn('créé', self._lancer(VARIABLES))
        u = User.objects.get(email='proprietaire@sunutribunal.sn')
        self.assertTrue(u.is_superuser and u.is_staff)
        self.assertEqual(u.nom, 'Ndiaye')
        self.assertTrue(u.check_password('Baobab-Encre-2026!'))

        # Redémarrage avec un autre mot de passe : le compte existant n'est pas touché
        self.assertIn('déjà présent', self._lancer({**VARIABLES, 'DJANGO_SUPERUSER_PASSWORD': 'Autre-Mdp-2026!'}))
        self.assertEqual(User.objects.count(), 1)
        u.refresh_from_db()
        self.assertTrue(u.check_password('Baobab-Encre-2026!'))

    def test_mot_de_passe_faible_refuse(self):
        with self.assertRaises(CommandError):
            self._lancer({**VARIABLES, 'DJANGO_SUPERUSER_PASSWORD': '12345678'})
        self.assertFalse(User.objects.exists())
