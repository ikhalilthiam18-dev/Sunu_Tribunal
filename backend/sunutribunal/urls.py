from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.views.static import serve
from rest_framework_simplejwt.views import TokenRefreshView
from .views import home_view

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
    # Fichiers envoyés (scans) : servis par Django aussi en production (static() ne marche qu'avec DEBUG)
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]