from rest_framework import serializers
from sunutribunal.fichiers import FichiersProteges
from .models import Courrier, Transmission


class TransmissionSerializer(serializers.ModelSerializer):
    action_label      = serializers.CharField(source='get_action_display', read_only=True)
    origine_label     = serializers.CharField(source='get_service_origine_display', read_only=True)
    destination_label = serializers.CharField(source='get_service_destination_display', read_only=True)
    agent_nom         = serializers.SerializerMethodField()
    courrier_numero   = serializers.CharField(source='courrier.numero', read_only=True)
    courrier_objet    = serializers.CharField(source='courrier.objet', read_only=True)

    class Meta:
        model  = Transmission
        fields = ['id', 'courrier', 'courrier_numero', 'courrier_objet', 'action', 'action_label',
                  'service_origine', 'origine_label', 'service_destination', 'destination_label',
                  'agent_nom', 'commentaire', 'date']
        read_only_fields = fields

    def get_agent_nom(self, obj):
        return obj.agent.full_name if obj.agent else ''


class CourrierSerializer(FichiersProteges, serializers.ModelSerializer):
    sens_label     = serializers.CharField(source='get_sens_display', read_only=True)
    registre_label = serializers.CharField(source='get_registre_display', read_only=True)
    statut_label   = serializers.CharField(source='get_statut_display', read_only=True)
    service_label  = serializers.CharField(source='get_service_actuel_display', read_only=True)
    enregistre_par_nom = serializers.SerializerMethodField()
    transmissions  = TransmissionSerializer(many=True, read_only=True)

    class Meta:
        model  = Courrier
        fields = ['id', 'numero', 'sens', 'sens_label', 'registre', 'registre_label', 'tribunal',
                  'date_courrier', 'date_enregistrement', 'correspondant', 'adresse_correspondant',
                  'reference_externe', 'objet', 'resume', 'nombre_pieces', 'priorite', 'dossier_lie',
                  'service_actuel', 'service_label', 'statut', 'statut_label', 'fichier',
                  'enregistre_par_nom', 'transmissions', 'updated_at']
        read_only_fields = ['numero', 'tribunal', 'date_enregistrement', 'service_actuel',
                            'statut', 'enregistre_par_nom', 'updated_at']

    def get_enregistre_par_nom(self, obj):
        return obj.enregistre_par.full_name if obj.enregistre_par else ''


class CourrierListSerializer(CourrierSerializer):
    """Version légère pour les listes (sans l'historique complet)."""
    class Meta(CourrierSerializer.Meta):
        fields = [f for f in CourrierSerializer.Meta.fields if f != 'transmissions']
