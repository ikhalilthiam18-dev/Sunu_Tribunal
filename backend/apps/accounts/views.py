from django.utils import timezone
from rest_framework import generics, status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import PermissionDenied
from .emails import attribuer_identifiants
from .models import User, STAFF_ROLES, SecuriteCompte, IdentifiantsProvisoires
from .permissions import IsChefGreffe
from .serializers import (UserSerializer, RegisterSerializer, CustomTokenSerializer, StaffUserSerializer,
                          ChangerMotDePasseSerializer)


def message_envoi(user, resultat, action='Compte créé'):
    """Phrase affichée au greffier en chef après création ou renvoi des identifiants."""
    if resultat['email_envoye']:
        return f'{action}. Les identifiants ont été envoyés à {user.email}.'
    return (f"{action}, mais l'e-mail n'a pas pu être envoyé à {user.email} : {resultat['email_erreur']} "
            "Utilisez « Renvoyer les identifiants » une fois le problème réglé.")


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class   = CustomTokenSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class   = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'message': 'Compte créé avec succès.', 'user': UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class   = UserSerializer

    def get_object(self):
        return self.request.user


class ChangerMotDePasseView(APIView):
    """
    POST /api/auth/changer-mot-de-passe/  {ancien_mdp, nouveau_mdp, confirmation}
    Obligatoire à la 1re connexion d'un compte du personnel (mot de passe provisoire),
    disponible pour tous les utilisateurs depuis le menu.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangerMotDePasseSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['nouveau_mdp'])
        user.save(update_fields=['password'])
        SecuriteCompte.objects.update_or_create(user=user, defaults={'doit_changer_mdp': False})
        IdentifiantsProvisoires.objects.filter(user=user).update(mdp_change_le=timezone.now())
        return Response({'message': 'Mot de passe modifié.', 'user': UserSerializer(user).data})


class UpdateFCMTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('fcm_token')
        if token:
            request.user.fcm_token = token
            request.user.save(update_fields=['fcm_token'])
        return Response({'status': 'ok'})


class StaffUserViewSet(mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    """
    Gestion du personnel judiciaire (module AdminUtilisateurs).
    GET    /api/auth/staff/                → liste du personnel (du tribunal du chef)
    POST   /api/auth/staff/                → créer un compte (juge / greffier / accueil / courrier) :
                                             mot de passe provisoire généré et envoyé par e-mail
    PATCH  /api/auth/staff/<id>/           → modifier / activer / désactiver
    POST   /api/auth/staff/<id>/renvoyer/  → nouveau mot de passe provisoire, renvoyé par e-mail
    Réservé au greffier en chef (role 'admin') et au superutilisateur.
    Les comptes « greffier en chef » se créent et se modifient uniquement dans Django Admin.
    """
    serializer_class   = StaffUserSerializer
    permission_classes = [IsChefGreffe]
    pagination_class   = None

    def get_queryset(self):
        qs = User.objects.filter(role__in=STAFF_ROLES).order_by('-date_joined')
        user = self.request.user
        if user.tribunal_id and not user.is_superuser:
            qs = qs.filter(tribunal=user.tribunal)
        return qs

    def perform_update(self, serializer):
        cible, moi = serializer.instance, self.request.user
        if cible == moi:
            # Empêche le greffier en chef de se désactiver ou de changer son propre rôle
            if serializer.validated_data.get('is_active') is False:
                raise ValidationError({'detail': 'Vous ne pouvez pas désactiver votre propre compte.'})
            if 'role' in serializer.validated_data and serializer.validated_data['role'] != cible.role:
                raise ValidationError({'role': 'Vous ne pouvez pas changer votre propre rôle.'})
        elif cible.role == 'admin' and not moi.is_superuser:
            # Un autre compte « greffier en chef » ne se modifie que par le superutilisateur (Django Admin)
            raise PermissionDenied("Ce compte se gère uniquement dans l'administration Django.")
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        resultat = attribuer_identifiants(user, cree_par=request.user)
        # Le mot de passe provisoire n'est JAMAIS renvoyé au navigateur : seulement par e-mail
        return Response({**self.get_serializer(user).data, **resultat,
                         'message': message_envoi(user, resultat)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def renvoyer(self, request, pk=None):
        """Nouveau mot de passe provisoire (changement obligatoire à la connexion), renvoyé par e-mail."""
        cible = self.get_object()          # limité au tribunal du chef : un autre tribunal → 404
        if cible == request.user:
            return Response({'detail': 'Pour votre propre compte, utilisez « Changer le mot de passe ».'},
                            status=status.HTTP_400_BAD_REQUEST)
        if cible.role == 'admin' and not request.user.is_superuser:
            raise PermissionDenied("Ce compte se gère uniquement dans l'administration Django.")
        resultat = attribuer_identifiants(cible, cree_par=request.user, reinitialisation=True)
        return Response({**resultat, 'message': message_envoi(cible, resultat, 'Nouveau mot de passe provisoire généré')})
