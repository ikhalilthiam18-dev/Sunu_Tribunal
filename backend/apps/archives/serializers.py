from rest_framework import serializers
from apps.accounts.models import User
from sunutribunal.fichiers import FichiersProteges
from .models import DossierArchive, PieceArchive, HistoriqueDossier


class PieceArchiveSerializer(FichiersProteges, serializers.ModelSerializer):
    type_label     = serializers.CharField(source='get_type_piece_display', read_only=True)
    ajoute_par_nom = serializers.SerializerMethodField()
    extension      = serializers.CharField(read_only=True)

    class Meta:
        model  = PieceArchive
        fields = ['id', 'nom', 'fichier', 'type_piece', 'type_label', 'taille', 'extension',
                  'ajoute_par_nom', 'created_at']
        read_only_fields = fields

    def get_ajoute_par_nom(self, obj):
        return obj.ajoute_par.full_name if obj.ajoute_par else ''


class HistoriqueSerializer(serializers.ModelSerializer):
    agent_nom = serializers.SerializerMethodField()

    class Meta:
        model  = HistoriqueDossier
        fields = ['id', 'action', 'detail', 'agent_nom', 'date']

    def get_agent_nom(self, obj):
        return obj.agent.full_name if obj.agent else ''


class DossierArchiveSerializer(serializers.ModelSerializer):
    registre_label  = serializers.CharField(source='get_registre_display', read_only=True)
    categorie_label = serializers.CharField(source='get_categorie_display', read_only=True)
    statut_label    = serializers.CharField(source='get_statut_display', read_only=True)
    juge_nom        = serializers.SerializerMethodField()
    plainte_ref     = serializers.CharField(source='plainte.reference', read_only=True, default='')
    emplacement     = serializers.CharField(read_only=True)
    nb_pieces       = serializers.IntegerField(source='pieces.count', read_only=True)
    pieces          = PieceArchiveSerializer(many=True, read_only=True)
    historique      = HistoriqueSerializer(many=True, read_only=True)
    juge            = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='juge'), required=False, allow_null=True)

    class Meta:
        model  = DossierArchive
        fields = ['id', 'numero', 'registre', 'registre_label', 'categorie', 'categorie_label',
                  'intitule', 'demandeur', 'defendeur', 'juge', 'juge_nom', 'plainte', 'plainte_ref',
                  'date_ouverture', 'date_cloture', 'statut', 'statut_label',
                  'salle', 'armoire', 'etagere', 'boite', 'emplacement',
                  'mots_cles', 'observations', 'nb_pieces', 'pieces', 'historique',
                  'created_at', 'updated_at']
        read_only_fields = ['numero', 'date_cloture', 'statut', 'created_at', 'updated_at']

    def get_juge_nom(self, obj):
        return obj.juge.full_name if obj.juge else ''

    def validate(self, data):
        # Le registre ne change plus une fois le numéro attribué
        if self.instance and 'registre' in data and data['registre'] != self.instance.registre:
            raise serializers.ValidationError({'registre': 'Le registre ne peut pas être modifié après numérotation.'})
        return data


class DossierArchiveListSerializer(DossierArchiveSerializer):
    class Meta(DossierArchiveSerializer.Meta):
        fields = [f for f in DossierArchiveSerializer.Meta.fields if f not in ('pieces', 'historique')]
