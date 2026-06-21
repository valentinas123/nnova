from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROLES = (
        ('estudiante', 'Estudiante'),
        ('docente', 'Docente'),
    )

    rol = models.CharField(max_length=20, choices=ROLES, default='estudiante')