# synchrobi/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from core.views import home_view, perfil, logout_view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Views de autenticação compartilhadas
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('perfil/', perfil, name='perfil'),
    path('logout/', logout_view, name='logout'),

    # Página inicial do SynchroBI
    path('', home_view, name='home'),

    # Portal de gestão - principal do SynchroBI
    path('gestor/', include('gestor.urls', namespace='gestor')),
    
    # APIs REST
    path('api/', include('api.urls', namespace='api')),
]

# Servir mídia durante desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)