"""python manage.py test apps.rdv.tests_tribunaux — tribunaux de base sur une base neuve"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.rdv.models import Tribunal


class ChargerTribunauxTests(TestCase):

    def _lancer(self):
        call_command('charger_tribunaux', stdout=StringIO())

    def test_base_neuve_puis_redemarrage_sans_doublon(self):
        self._lancer()
        self.assertEqual(Tribunal.objects.count(), 5)
        self.assertFalse(Tribunal.objects.filter(latitude=None).exists())   # tous sur la carte
        self._lancer()
        self.assertEqual(Tribunal.objects.count(), 5)

    def test_correction_faite_dans_l_admin_conservee(self):
        self._lancer()
        Tribunal.objects.filter(nom='TGI Dakar - Plateau').update(telephone='+221 33 000 00 00',
                                                                    latitude='14.700000')
        self._lancer()
        t = Tribunal.objects.get(nom='TGI Dakar - Plateau')
        self.assertEqual(t.telephone, '+221 33 000 00 00')
        self.assertEqual(str(t.latitude), '14.700000')
