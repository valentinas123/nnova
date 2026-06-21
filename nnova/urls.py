from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),  # Sistema de autenticación
    path('app/', include('cursos.urls')), # Sistema interno de cursos
    
    # Ruta estándar para servir archivos multimedia en Railway (Producción)
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
]
