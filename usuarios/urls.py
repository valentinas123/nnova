from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio_publico, name='inicio_publico'),  # incio público
    path('login/', views.login_usuario, name='login'),
    path('registro/', views.registro, name='registro'),
    path('buscar/', views.buscar, name='buscar'),  # search view
    path('solicitar-docente-publico/', views.solicitar_docente, name='solicitar_docente_publico'),
]