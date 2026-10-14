from django.db import models
from django.conf import settings
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path, include
from rest_framework.routers import DefaultRouter


class Notification(models.Model):
    TYPES = [
        ('rdv',     'Rendez-vous'),
        ('plainte', 'Plainte'),
        ('sos',     'Alerte SOS'),
        ('message', 'Message tribunal'),
        ('system',  'Système'),
    ]
    destinataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='notifications')
    type_notif   = models.CharField(max_length=20, choices=TYPES, default='system')
    titre        = models.CharField(max_length=200)
    corps        = models.TextField()
    lu           = models.BooleanField(default=False)
    lien         = models.CharField(max_length=200, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SMSLog(models.Model):
    """Journal de tous les SMS (envoyés, échoués ou non configurés) — traçabilité."""
    STATUTS = [
        ('envoye',        'Envoyé'),
        ('echec',         'Échec'),
        ('non_configure', 'SMS non configuré'),
        ('numero_invalide', 'Numéro invalide'),
    ]
    destinataire = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='sms_recus')
    telephone    = models.CharField(max_length=30, blank=True)
    message      = models.TextField()
    statut       = models.CharField(max_length=20, choices=STATUTS)
    sid          = models.CharField(max_length=64, blank=True, help_text='Identifiant du message (Brevo ou Twilio)')
    erreur       = models.TextField(blank=True)
    objet_ref    = models.CharField(max_length=60, blank=True, help_text='Ex : RDV-2026-12345')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SMS envoyé'
        verbose_name_plural = 'Journal des SMS'

    def __str__(self):
        return f'{self.telephone} · {self.get_statut_display()} · {self.objet_ref}'


class SMSLogSerializer(serializers.ModelSerializer):
    statut_label     = serializers.CharField(source='get_statut_display', read_only=True)
    destinataire_nom = serializers.CharField(source='destinataire.full_name', read_only=True, default='')

    class Meta:
        model  = SMSLog
        fields = ['id', 'destinataire_nom', 'telephone', 'message', 'statut', 'statut_label',
                  'sid', 'erreur', 'objet_ref', 'created_at']


class SMSLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Journal des SMS — consultable par le personnel du tribunal."""
    serializer_class = SMSLogSerializer
    pagination_class = None

    def get_permissions(self):
        from apps.accounts.permissions import IsStaffRole
        return [IsStaffRole()]

    def get_queryset(self):
        return SMSLog.objects.select_related('destinataire')[:100]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = '__all__'
        read_only_fields = ['destinataire','created_at']


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class   = None

    def get_queryset(self):
        return Notification.objects.filter(destinataire=self.request.user)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        notif = self.get_object()
        notif.lu = True
        notif.save()
        return Response({'status': 'read'})

    @action(detail=False, methods=['post'])
    def read_all(self, request):
        self.get_queryset().update(lu=True)
        return Response({'status': 'all read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = self.get_queryset().filter(lu=False).count()
        return Response({'count': count})

