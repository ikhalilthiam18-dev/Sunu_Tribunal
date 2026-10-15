import os
from rest_framework import serializers
from sunutribunal.fichiers import FichiersProteges
from .models import CourrierCitoyen

EXTENSIONS_AUTORISEES = {'.pdf', '.jpg', '.jpeg', '.png', '.webp'}
TAILLE_MAX = 10 * 1024 * 1024  # 10 Mo


class CourrierCitoyenSerializer(FichiersProteges, serializers.ModelSerializer):
    citoyen_nom       = serializers.CharField(source='citoyen.full_name', read_only=True)
    citoyen_email     = serializers.CharField(source='citoyen.email', read_only=True)
    tribunal_nom      = serializers.CharField(source='tribunal.nom', read_only=True, default='')
    destinataire_label = serializers.CharField(source='get_destinataire_service_display', read_only=True)
    juge_nom          = serializers.CharField(source='juge.full_name', read_only=True, default='')
    auteur_nom        = serializers.SerializerMethodField()
    piece_nom         = serializers.SerializerMethodField()
    numero_registre   = serializers.CharField(source='courrier_registre.numero', read_only=True, default='')

    class Meta:
        model  = CourrierCitoyen
        fields = ['id', 'citoyen', 'citoyen_nom', 'citoyen_email', 'tribunal', 'tribunal_nom',
                  'sens', 'destinataire_service', 'destinataire_label', 'juge', 'juge_nom',
                  'sujet', 'message', 'dossier_ref', 'piece_jointe', 'piece_nom',
                  'auteur_nom', 'parent', 'lu', 'lu_at', 'numero_registre', 'created_at']
        read_only_fields = ['sens', 'juge', 'lu', 'lu_at', 'created_at']
        extra_kwargs = {'citoyen': {'required': False}}

    def get_auteur_nom(self, obj):
        if obj.sens == 'entrant':
            return obj.citoyen.full_name
        # Côté citoyen, le courrier vient « du greffe » ; l'agent est précisé entre parenthèses
        service = obj.tribunal.nom if obj.tribunal else 'Tribunal'
        return f'Greffe {service}' + (f' ({obj.auteur.full_name})' if obj.auteur else '')

    def get_piece_nom(self, obj):
        return os.path.basename(obj.piece_jointe.name) if obj.piece_jointe else ''

    def validate_piece_jointe(self, f):
        if not f:
            return f
        if os.path.splitext(f.name)[1].lower() not in EXTENSIONS_AUTORISEES:
            raise serializers.ValidationError('Format accepté : PDF ou image.')
        if f.size > TAILLE_MAX:
            raise serializers.ValidationError('La pièce jointe dépasse 10 Mo.')
        return f

    def validate_sujet(self, v):
        if not v.strip():
            raise serializers.ValidationError('Le sujet est obligatoire.')
        return v.strip()

    def validate_message(self, v):
        if not v.strip():
            raise serializers.ValidationError('Le message est obligatoire.')
        return v.strip()
