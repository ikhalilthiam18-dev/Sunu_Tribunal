"""
python manage.py charger_tribunaux

Ajoute les tribunaux de base (carte, prise de rendez-vous) s'ils n'existent pas encore.
Lancé à chaque démarrage par start.sh : une base neuve (Neon, VPS) a ainsi sa carte.
Ne modifie jamais un tribunal existant (même nom) : les corrections faites dans
Django Admin sont conservées.

Téléphone et e-mail volontairement absents : à saisir dans Django Admin une fois vérifiés.
Coordonnées approximatives : à affiner dans Django Admin si besoin.
"""
from django.core.management.base import BaseCommand

from apps.rdv.models import Tribunal

TRIBUNAUX = [
    {'nom': 'TGI Dakar - Plateau', 'adresse': 'Avenue Leopold Sedar Senghor, Dakar',
     'latitude': '14.697900', 'longitude': '-17.438000', 'heures_ouverture': 'Lun-Ven 08h-17h'},
    {'nom': 'Tribunal de Commerce de Dakar', 'adresse': 'Rue Carnot, Dakar Plateau',
     'latitude': '14.693800', 'longitude': '-17.440000', 'heures_ouverture': 'Lun-Ven 08h-17h'},
    {'nom': 'Tribunal Regional de Pikine', 'adresse': 'Route de Pikine, Dakar',
     'latitude': '14.752200', 'longitude': '-17.392000', 'heures_ouverture': 'Lun-Ven 08h-16h'},
    {'nom': 'Tribunal Regional de Saint-Louis', 'adresse': 'Centre-ville, Saint-Louis',
     'latitude': '16.017900', 'longitude': '-16.489700', 'heures_ouverture': 'Lun-Ven 08h-17h'},
    {'nom': 'Tribunal Regional de Thies', 'adresse': 'Quartier Randoulene, Thies',
     'latitude': '14.791700', 'longitude': '-16.926100', 'heures_ouverture': 'Lun-Ven 08h-17h'},
]


class Command(BaseCommand):
    help = "Ajoute les tribunaux de base manquants (sans toucher aux existants)."

    def handle(self, *args, **options):
        ajoutes = 0
        for donnees in TRIBUNAUX:
            _, cree = Tribunal.objects.get_or_create(nom=donnees['nom'], defaults=donnees)
            ajoutes += cree
        if ajoutes:
            self.stdout.write(f'Tribunaux ajoutés : {ajoutes}')
