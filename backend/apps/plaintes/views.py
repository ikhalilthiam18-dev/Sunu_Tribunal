import os

from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .models import Plainte, PieceJointe, MessageDossier, EvenementPlainte
from apps.accounts.models import User, STAFF_ROLES
from apps.accounts.permissions import HasRole
from apps.notifications.services import notifier, notifier_personnel
from sunutribunal.fichiers import FichiersProteges

# Pièces justificatives acceptées (fichiers importés ou photos « Scanner document »)
EXTENSIONS_AUTORISEES = {'.pdf', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.doc', '.docx'}
TAILLE_MAX = 15 * 1024 * 1024  # 15 Mo par fichier

# Qui traite les plaintes côté tribunal
ROLES_GREFFE = ('admin', 'greffier')


# ── Serializers ───────────────────────────────────────
class PieceJointeSerializer(FichiersProteges, serializers.ModelSerializer):
    class Meta:
        model  = PieceJointe
        fields = ['id','nom','fichier','taille','uploaded_at']


class MessageSerializer(serializers.ModelSerializer):
    auteur_nom     = serializers.CharField(source='auteur.full_name', read_only=True)
    est_tribunal   = serializers.SerializerMethodField()

    class Meta:
        model  = MessageDossier
        fields = ['id','contenu','auteur_nom','est_tribunal','created_at']
        read_only_fields = ['auteur_nom','created_at']

    def get_est_tribunal(self, obj):
        return obj.auteur.is_staff_role


class EvenementSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source='get_type_display', read_only=True)
    auteur_nom = serializers.CharField(source='auteur.full_name', read_only=True, default='')

    class Meta:
        model  = EvenementPlainte
        fields = ['id','type','type_label','statut','detail','auteur_nom','created_at']


class PlainteSerializer(serializers.ModelSerializer):
    plaignant_nom = serializers.CharField(source='plaignant.full_name',   read_only=True)
    plaignant_telephone = serializers.CharField(source='plaignant.telephone', read_only=True)
    tribunal_nom  = serializers.CharField(source='tribunal.nom',          read_only=True)
    nature_label  = serializers.CharField(source='get_nature_display',     read_only=True)
    statut_label  = serializers.CharField(source='get_statut_display',     read_only=True)
    juge_nom      = serializers.CharField(source='juge.full_name',         read_only=True, default='')
    pieces        = PieceJointeSerializer(many=True, read_only=True)
    messages      = MessageSerializer(many=True, read_only=True)
    evenements    = EvenementSerializer(many=True, read_only=True)
    nb_pieces     = serializers.IntegerField(source='pieces.count',        read_only=True)
    motif_rejet   = serializers.SerializerMethodField()

    class Meta:
        model  = Plainte
        fields = '__all__'
        read_only_fields = ['reference','plaignant','statut','juge','notes_greffe','created_at','updated_at']

    def get_motif_rejet(self, obj):
        if obj.statut != 'rejected':
            return ''
        rejets = [e for e in obj.evenements.all() if e.type == 'rejet']
        return rejets[-1].detail if rejets else ''


# ── Outils ────────────────────────────────────────────
def lien_citoyen(plainte):
    return f'/citoyen/suivi?ref={plainte.reference}'


def lien_tribunal(plainte):
    return f'/admin/plaintes?ref={plainte.reference}'


def tracer(plainte, user, type_evt, detail=''):
    return EvenementPlainte.objects.create(
        plainte=plainte, type=type_evt, statut=plainte.statut, detail=detail, auteur=user,
    )


def verifier_pieces(fichiers):
    for f in fichiers:
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in EXTENSIONS_AUTORISEES:
            raise serializers.ValidationError({'pieces': f'« {f.name} » : format non accepté (PDF, image ou Word).'})
        if f.size > TAILLE_MAX:
            raise serializers.ValidationError({'pieces': f'« {f.name} » dépasse 15 Mo.'})


def plaintes_visibles(user):
    """Plaintes qu'un utilisateur a le droit de voir (réutilisé par les statistiques)."""
    qs = Plainte.objects.select_related('plaignant', 'tribunal', 'juge')
    if user.is_superuser:
        return qs
    if user.role == 'juge':
        return qs.filter(juge=user)              # le juge ne voit que ses dossiers
    if user.role in ROLES_GREFFE:
        return qs.filter(tribunal=user.tribunal) if user.tribunal_id else qs
    if user.role in STAFF_ROLES:
        return qs.none()                          # accueil, bureau courrier : pas d'accès aux plaintes
    return qs.filter(plaignant=user)


# ── Views ─────────────────────────────────────────────
class PlainteViewSet(viewsets.ModelViewSet):
    serializer_class   = PlainteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['statut', 'nature', 'tribunal', 'juge']
    pagination_class   = None
    # Pas de modification libre : tout changement passe par une action tracée
    http_method_names  = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return plaintes_visibles(self.request.user).prefetch_related(
            'pieces', 'messages__auteur', 'evenements__auteur')

    def create(self, request, *args, **kwargs):
        if request.user.is_staff_role:
            return Response({'detail': 'Le dépôt de plainte est réservé aux citoyens.'}, status=403)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        fichiers = self.request.FILES.getlist('pieces')
        verifier_pieces(fichiers)
        plainte = serializer.save(plaignant=self.request.user)
        for f in fichiers:
            PieceJointe.objects.create(plainte=plainte, fichier=f, nom=f.name[:200], taille=f.size)
        tracer(plainte, self.request.user, 'depot', f'{len(fichiers)} pièce(s) jointe(s)')

        notifier(plainte.plaignant, 'plainte', 'Plainte enregistrée',
                 f'Votre plainte {plainte.reference} a été transmise au greffe du {plainte.tribunal.nom}. '
                 f'Vous serez notifié à chaque étape.', lien_citoyen(plainte))
        notifier_personnel(plainte.tribunal, ROLES_GREFFE, 'plainte', 'Nouvelle plainte déposée',
                           f'{plainte.reference} — {plainte.get_nature_display()} déposée par '
                           f'{plainte.plaignant.full_name} ({len(fichiers)} pièce(s)).', lien_tribunal(plainte))

    @action(detail=False, methods=['get'])
    def my(self, request):
        plaintes = self.get_queryset().filter(plaignant=request.user).order_by('-created_at')
        return Response(self.get_serializer(plaintes, many=True).data)

    def _frais(self, plainte):
        """Relit la plainte (historique à jour) avant de la renvoyer."""
        return self.get_serializer(self.get_queryset().get(pk=plainte.pk)).data

    # ── Décisions du tribunal ─────────────────────────────
    def _peut_decider(self, plainte):
        user = self.request.user
        return user.is_superuser or user.role in ROLES_GREFFE or (user.role == 'juge' and plainte.juge_id == user.id)

    def _changer_statut(self, request, nouveau, depuis, type_evt, titre, corps, detail=''):
        plainte = self.get_object()
        if not self._peut_decider(plainte):
            return Response({'detail': 'Action réservée au greffe ou au juge en charge.'}, status=403)
        if plainte.statut not in depuis:
            return Response({'detail': f'Impossible : la plainte est « {plainte.get_statut_display()} ».'}, status=400)
        plainte.statut = nouveau
        plainte.save(update_fields=['statut', 'updated_at'])
        tracer(plainte, request.user, type_evt, detail)

        notifier(plainte.plaignant, 'plainte', titre, corps.replace('{ref}', plainte.reference), lien_citoyen(plainte))
        # Prévenir l'autre partie du tribunal : le juge si le greffe agit, le greffe si le juge agit
        if request.user.role == 'juge':
            notifier_personnel(plainte.tribunal, ROLES_GREFFE, 'plainte', f'{plainte.reference} : {titre}',
                               f'Décision du juge {request.user.full_name}. {detail}'.strip(), lien_tribunal(plainte))
        elif plainte.juge_id and plainte.juge_id != request.user.id:
            notifier(plainte.juge, 'plainte', f'{plainte.reference} : {titre}',
                     f'Action du greffe ({request.user.full_name}). {detail}'.strip(), lien_tribunal(plainte))
        return Response(self._frais(plainte))

    @action(detail=True, methods=['post'])
    def instruire(self, request, pk=None):
        return self._changer_statut(request, 'progress', ('pending', 'urgent'), 'instruction',
                                    'Dossier en instruction', 'Votre plainte {ref} est désormais en cours d\'instruction.')

    @action(detail=True, methods=['post'])
    def urgent(self, request, pk=None):
        return self._changer_statut(request, 'urgent', ('pending', 'progress'), 'urgent',
                                    'Dossier traité en priorité', 'Votre plainte {ref} est traitée en priorité par le tribunal.')

    @action(detail=True, methods=['post'])
    def traiter(self, request, pk=None):
        commentaire = str(request.data.get('commentaire', '')).strip()[:500]
        corps = 'Votre plainte {ref} a été traitée par le tribunal.'
        if commentaire:
            corps += f' {commentaire}'
        return self._changer_statut(request, 'done', ('progress', 'urgent'), 'traite',
                                    'Dossier traité', corps, commentaire)

    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        motif = str(request.data.get('motif', '')).strip()[:1000]
        if not motif:
            return Response({'detail': 'Le motif du rejet est obligatoire.'}, status=400)
        return self._changer_statut(request, 'rejected', ('pending', 'progress', 'urgent'), 'rejet',
                                    'Plainte rejetée', f'Votre plainte {{ref}} a été rejetée. Motif : {motif}', motif)

    @action(detail=True, methods=['post'], permission_classes=[HasRole(*ROLES_GREFFE)])
    def assigner(self, request, pk=None):
        plainte = self.get_object()
        if plainte.statut in ('done', 'rejected', 'archived'):
            return Response({'detail': 'Ce dossier est clos.'}, status=400)
        juge = User.objects.filter(pk=request.data.get('juge') or 0, role='juge', is_active=True).first()
        if juge is None:
            return Response({'detail': 'Choisissez un juge valide.'}, status=400)
        if juge.tribunal_id and juge.tribunal_id != plainte.tribunal_id:
            return Response({'detail': 'Ce juge n\'est pas rattaché au tribunal de la plainte.'}, status=400)
        plainte.juge = juge
        plainte.save(update_fields=['juge', 'updated_at'])
        tracer(plainte, request.user, 'assignation', f'Juge {juge.full_name}')

        notifier(juge, 'plainte', 'Nouveau dossier assigné',
                 f'Le greffe vous a assigné la plainte {plainte.reference} ({plainte.get_nature_display()}).',
                 lien_tribunal(plainte))
        notifier(plainte.plaignant, 'plainte', 'Dossier confié à un juge',
                 f'Votre plainte {plainte.reference} a été confiée au juge {juge.full_name}.', lien_citoyen(plainte))
        return Response(self._frais(plainte))

    @action(detail=False, methods=['get'], permission_classes=[HasRole(*ROLES_GREFFE)])
    def juges(self, request):
        juges = User.objects.filter(role='juge', is_active=True)
        if request.user.tribunal_id and not request.user.is_superuser:
            juges = juges.filter(tribunal=request.user.tribunal)
        return Response([{'id': j.id, 'nom': j.full_name} for j in juges])

    # ── Messagerie du dossier (dans les deux sens) ─────────
    @action(detail=True, methods=['post'])
    def message(self, request, pk=None):
        plainte = self.get_object()
        contenu = str(request.data.get('message', '')).strip()
        if not contenu:
            return Response({'detail': 'Le message est vide.'}, status=400)
        msg = MessageDossier.objects.create(plainte=plainte, auteur=request.user, contenu=contenu[:5000])
        tracer(plainte, request.user, 'message', contenu[:200])

        extrait = contenu if len(contenu) <= 160 else contenu[:157] + '...'
        if request.user.is_staff_role:
            notifier(plainte.plaignant, 'message', f'Message du tribunal — {plainte.reference}',
                     extrait, lien_citoyen(plainte))
            if plainte.juge_id and plainte.juge_id != request.user.id:
                notifier(plainte.juge, 'message', f'Message du greffe — {plainte.reference}', extrait,
                         lien_tribunal(plainte))
        elif plainte.juge_id:
            notifier(plainte.juge, 'message', f'Message du plaignant — {plainte.reference}', extrait,
                     lien_tribunal(plainte))
        else:
            notifier_personnel(plainte.tribunal, ROLES_GREFFE, 'message',
                               f'Message du plaignant — {plainte.reference}', extrait, lien_tribunal(plainte))
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


# ── URLs ──────────────────────────────────────────────
router = DefaultRouter()
router.register('', PlainteViewSet, basename='plainte')
urlpatterns = [path('', include(router.urls))]
