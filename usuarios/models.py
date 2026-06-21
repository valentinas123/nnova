from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROLES = (
        ('admin', 'Administrador'),
        ('docente', 'Docente'),
        ('estudiante', 'Estudiante'),
    )

    rol = models.CharField(
        max_length=20,
        choices=ROLES,
        default='estudiante'
    )