from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),    # Sistema de autenticación
    path('app/', include('cursos.urls')),   # Sistema interno de cursos
]

# Corrección para que funcione en producción (Railway) con DEBUG = False
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
