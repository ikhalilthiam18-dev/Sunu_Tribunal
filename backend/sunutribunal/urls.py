from django.contrib import admin
from django.urls import path, re_path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import home_view
from .fichiers import telecharger, media_admin

urlpatterns = [
    path('',              home_view,            name='home'),
    path('admin/',        admin.site.urls),
    path('api/auth/',     include('apps.accounts.urls')),
    path('api/rdv/',      include('apps.rdv.urls')),
    path('api/plaintes/', include('apps.plaintes.urls')),
    path('api/alertes/',  include('apps.alertes.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/chatbot/', include('apps.chatbot.urls')),
    path('api/registres/', include('apps.registres.urls')),
    path('api/archives/',  include('apps.archives.urls')),
    path('api/correspondances/', include('apps.correspondances.urls')),
    path('api/stats/',     include('sunutribunal.stats')),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Fichiers envoyés (scans) : jamais publics. L'API donne des liens signés (sunutribunal/fichiers.py) ;
    # /media/ reste ouvert aux seuls comptes connectés à Django Admin (liens de fichiers de l'admin).
    path('api/fichiers/<str:jeton>/', telecharger, name='fichier_protege'),
    re_path(r'^media/(?P<path>.*)$', media_admin),
]