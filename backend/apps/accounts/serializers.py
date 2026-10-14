from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, SecuriteCompte, doit_changer_mdp

# Rôles que le greffier en chef peut attribuer depuis la page Personnel.
# Le rôle « admin » (greffier en chef) se crée uniquement dans Django Admin, par le superutilisateur.
ROLES_CREABLES_PAR_LE_CHEF = ('juge', 'greffier', 'accueil', 'courrier')

# Protection contre les essais de mot de passe
MAX_ECHECS     = 5
DUREE_BLOCAGE  = timedelta(minutes=15)
MSG_ECHEC      = 'Email ou mot de passe incorrect.'
MSG_BLOQUE     = 'Trop de tentatives. Réessayez dans 15 minutes.'


class UserSerializer(serializers.ModelSerializer):
    tribunal_nom     = serializers.CharField(source='tribunal.nom', read_only=True, default='')
    doit_changer_mdp = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id','email','nom','prenom','telephone','cni','role','tribunal','tribunal_nom',
                  'is_verified','date_joined','doit_changer_mdp']
        # Le rôle ne peut JAMAIS être modifié par l'utilisateur lui-même (/api/auth/me/)
        read_only_fields = ['id','email','role','tribunal','date_joined','is_verified']

    def get_doit_changer_mdp(self, obj):
        return doit_changer_mdp(obj)


class RegisterSerializer(serializers.ModelSerializer):
    """Inscription publique : réservée aux citoyens (le rôle est forcé côté serveur)."""
    password  = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['email','nom','prenom','telephone','cni','password','password2']
        # L'unicité de l'email est vérifiée dans validate_email (message en français clair)
        extra_kwargs = {'email': {'validators': []}}

    def validate_email(self, email):
        email = User.objects.normalize_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Un compte existe déjà avec cette adresse email.')
        return email

    def validate(self, data):
        if data['password'] != data.pop('password2'):
            raise serializers.ValidationError({'password': 'Les mots de passe ne correspondent pas.'})
        # Mêmes règles que le changement de mot de passe (validateurs Django, messages en français) :
        # 8 caractères minimum, pas un mot de passe courant, pas trop proche de l'email ou du nom
        futur = User(email=data.get('email', ''), nom=data.get('nom', ''), prenom=data.get('prenom', ''))
        try:
            validate_password(data['password'], futur)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data

    def create(self, validated_data):
        # Toute donnée "role" envoyée par le client est ignorée
        validated_data['role'] = 'citoyen'
        return User.objects.create_user(**validated_data)


class StaffUserSerializer(serializers.ModelSerializer):
    """
    Création / gestion des comptes du personnel judiciaire (greffier en chef uniquement).
    Aucun mot de passe n'est saisi : le serveur génère un mot de passe provisoire et l'envoie
    par e-mail (voir apps/accounts/emails.py). Le tribunal est forcé à celui du créateur.
    """
    role = serializers.ChoiceField(choices=[r for r in User.ROLES if r[0] in ROLES_CREABLES_PAR_LE_CHEF])
    tribunal_nom = serializers.CharField(source='tribunal.nom', read_only=True, default='')
    doit_changer_mdp = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id','email','nom','prenom','telephone','role','tribunal','tribunal_nom',
                  'is_active','date_joined','doit_changer_mdp']
        read_only_fields = ['id','date_joined']

    def get_doit_changer_mdp(self, obj):
        return doit_changer_mdp(obj)

    def validate_email(self, email):
        email = User.objects.normalize_email(email)
        doublon = User.objects.filter(email__iexact=email)
        if self.instance:
            doublon = doublon.exclude(pk=self.instance.pk)
        if doublon.exists():
            raise serializers.ValidationError('Un compte existe déjà avec cette adresse email.')
        return email

    def _tribunal_impose(self, validated_data):
        """Le compte est rattaché au tribunal du greffier en chef (seul un superutilisateur choisit)."""
        createur = self.context['request'].user
        if createur.tribunal_id and not createur.is_superuser:
            validated_data['tribunal'] = createur.tribunal
        return validated_data

    def create(self, validated_data):
        validated_data = self._tribunal_impose(validated_data)
        # Mot de passe inutilisable en attendant le mot de passe provisoire (attribué juste après par la vue)
        return User.objects.create_user(password=None, is_verified=True, **validated_data)

    def update(self, instance, validated_data):
        validated_data = self._tribunal_impose(validated_data)
        return super().update(instance, validated_data)


class CustomTokenSerializer(TokenObtainPairSerializer):
    """
    Connexion unique (citoyens et personnel) : le rôle est renvoyé dans `user`,
    la redirection se fait côté frontend.
    - un seul message d'échec, qui ne dit jamais si l'email existe ;
    - blocage 15 minutes après 5 échecs (compte existant ou non : même comportement).
    """
    default_error_messages = {'no_active_account': MSG_ECHEC}

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['nom']  = user.nom
        token['role'] = user.role
        return token

    def validate(self, attrs):
        email = str(attrs.get(self.username_field, '')).strip().lower()
        compte = User.objects.filter(email__iexact=email).first()
        securite = SecuriteCompte.de(compte) if compte else None
        cle = f'connexion-echecs:{email}'

        if (securite and securite.est_bloque) or (not compte and cache.get(cle + ':bloque')):
            raise AuthenticationFailed(MSG_BLOQUE, code='trop_de_tentatives')

        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            if securite:
                securite.echecs_connexion += 1
                bloque = securite.echecs_connexion >= MAX_ECHECS
                if bloque:
                    securite.bloque_jusqua = timezone.now() + DUREE_BLOCAGE
                    securite.echecs_connexion = 0
                securite.save(update_fields=['echecs_connexion', 'bloque_jusqua'])
            else:
                # Email inconnu : même compteur, en cache, pour ne pas révéler que le compte n'existe pas
                echecs = cache.get(cle, 0) + 1
                bloque = echecs >= MAX_ECHECS
                if bloque:
                    cache.set(cle + ':bloque', True, DUREE_BLOCAGE.total_seconds())
                    cache.delete(cle)
                else:
                    cache.set(cle, echecs, DUREE_BLOCAGE.total_seconds())
            raise AuthenticationFailed(MSG_BLOQUE if bloque else MSG_ECHEC,
                                       code='trop_de_tentatives' if bloque else 'identifiants_invalides')

        securite = SecuriteCompte.de(self.user)
        securite.echecs_connexion = 0
        securite.bloque_jusqua = None
        securite.derniere_connexion_reussie = timezone.now()
        securite.save(update_fields=['echecs_connexion', 'bloque_jusqua', 'derniere_connexion_reussie'])

        data['user'] = UserSerializer(self.user).data
        data['doit_changer_mdp'] = securite.doit_changer_mdp
        return data


class ChangerMotDePasseSerializer(serializers.Serializer):
    ancien_mdp   = serializers.CharField(write_only=True)
    nouveau_mdp  = serializers.CharField(write_only=True)
    confirmation = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['ancien_mdp']):
            raise serializers.ValidationError({'ancien_mdp': 'Mot de passe actuel incorrect.'})
        if data['nouveau_mdp'] != data['confirmation']:
            raise serializers.ValidationError({'confirmation': 'Les deux mots de passe ne correspondent pas.'})
        if data['nouveau_mdp'] == data['ancien_mdp']:
            raise serializers.ValidationError({'nouveau_mdp': "Le nouveau mot de passe doit être différent de l'ancien."})
        try:
            # 8 caractères minimum, pas un mot de passe courant, pas trop proche de l'email ou du nom
            validate_password(data['nouveau_mdp'], user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'nouveau_mdp': list(e.messages)})
        return data
