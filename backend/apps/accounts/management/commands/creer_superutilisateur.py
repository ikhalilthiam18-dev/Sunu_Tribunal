"""
python manage.py creer_superutilisateur

Crée le superutilisateur à partir des variables d'environnement, s'il n'existe pas encore.
Lancé à chaque démarrage par start.sh : sert sur les hébergeurs sans terminal (Render gratuit).
  DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_NOM (facultatif)
Sans ces variables, la commande ne fait rien.
"""
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Crée le superutilisateur décrit par DJANGO_SUPERUSER_EMAIL / _PASSWORD s'il n'existe pas."

    def handle(self, *args, **options):
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        mot_de_passe = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')
        if not email or not mot_de_passe:
            return

        if User.objects.filter(email__iexact=email).exists():
            self.stdout.write(f'Superutilisateur déjà présent : {email}')
            return

        try:
            validate_password(mot_de_passe)
        except ValidationError as e:
            raise CommandError('DJANGO_SUPERUSER_PASSWORD refusé : ' + ' '.join(e.messages))

        User.objects.create_superuser(email, mot_de_passe,
                                      nom=os.environ.get('DJANGO_SUPERUSER_NOM', 'Administrateur'))
        self.stdout.write(f'Superutilisateur créé : {email}')
