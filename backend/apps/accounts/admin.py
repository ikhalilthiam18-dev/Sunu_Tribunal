from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from .emails import attribuer_identifiants
from .models import User, STAFF_ROLES, SecuriteCompte, IdentifiantsProvisoires


class SecuriteCompteInline(admin.StackedInline):
    """Débloquer un agent ou lui imposer un nouveau changement de mot de passe."""
    model = SecuriteCompte
    can_delete = False
    extra = 0
    max_num = 1
    verbose_name_plural = 'Sécurité du compte'
    fields = ['doit_changer_mdp', 'echecs_connexion', 'bloque_jusqua', 'derniere_connexion_reussie']
    readonly_fields = ['derniere_connexion_reussie']


class IdentifiantsProvisoiresInline(admin.StackedInline):
    """Historique de l'envoi du mot de passe provisoire (lecture seule)."""
    model = IdentifiantsProvisoires
    fk_name = 'user'
    can_delete = False
    extra = 0
    max_num = 1
    verbose_name_plural = 'Identifiants provisoires'
    fields = readonly_fields = ['cree_par', 'mdp_provisoire_envoye_le', 'mdp_change_le']

    def has_add_permission(self, request, obj=None):
        return False


class AjoutUtilisateurForm(forms.ModelForm):
    """Ajout d'un compte SANS mot de passe : le serveur en génère un et l'envoie par e-mail."""

    class Meta:
        model = User
        fields = ['email', 'nom', 'prenom', 'telephone', 'role', 'tribunal']

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data['email'])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Un compte existe déjà avec cette adresse email.')
        return email

    def clean(self):
        donnees = super().clean()
        if donnees.get('role') in STAFF_ROLES and not donnees.get('tribunal'):
            self.add_error('tribunal', 'Le tribunal est obligatoire pour un compte du personnel.')
        return donnees


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Circuit de création : le superutilisateur crée ici le greffier en chef (rôle « admin ») avec son tribunal ;
    le greffier en chef crée ensuite les autres agents depuis la page Personnel de l'application.
    Aucun mot de passe n'est saisi : un mot de passe provisoire est envoyé par e-mail.
    """
    add_form     = AjoutUtilisateurForm
    list_display = ['email', 'nom', 'role', 'tribunal', 'is_active', 'date_joined']
    list_filter  = ['role', 'tribunal', 'is_verified', 'is_active']
    search_fields= ['email', 'nom']
    ordering     = ['-date_joined']
    inlines      = [SecuriteCompteInline, IdentifiantsProvisoiresInline]
    actions      = ['renvoyer_identifiants']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations', {'fields': ('nom','prenom','telephone','cni','role','tribunal')}),
        ('Statut', {'fields': ('is_verified','is_active','is_staff','is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'telephone', 'role', 'tribunal'),
            'description': "Aucun mot de passe à saisir : un mot de passe provisoire est généré et envoyé "
                           "par e-mail. Il devra être changé à la première connexion.",
        }),
    )

    def get_inlines(self, request, obj):
        return self.inlines if obj else []          # pas d'encadrés sur la page d'ajout

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)
        obj.set_unusable_password()                 # remplacé juste après par le mot de passe provisoire
        obj.is_verified = obj.is_verified or obj.role in STAFF_ROLES
        super().save_model(request, obj, form, change)
        self._annoncer(request, obj, attribuer_identifiants(obj, cree_par=request.user))

    def _annoncer(self, request, user, resultat):
        if resultat['email_envoye']:
            self.message_user(request, f'Identifiants envoyés à {user.email}.', messages.SUCCESS)
        else:
            self.message_user(request, f"Compte enregistré, mais l'e-mail n'a pas pu être envoyé à {user.email} : "
                                       f"{resultat['email_erreur']}", messages.ERROR)

    @admin.action(description='Renvoyer les identifiants (nouveau mot de passe provisoire)')
    def renvoyer_identifiants(self, request, queryset):
        for user in queryset:
            self._annoncer(request, user, attribuer_identifiants(user, cree_par=request.user, reinitialisation=True))
