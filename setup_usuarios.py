"""
Script para crear/restaurar usuarios del sistema nnova.
Se ejecuta automáticamente en el Procfile de Railway.
Es idempotente: no duplica usuarios, solo los crea si no existen o actualiza sus datos.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nnova.settings')
django.setup()

from usuarios.models import Usuario

# Definir usuarios base del sistema
# IMPORTANTE: Cada dict se consume una sola vez, no mutar
USUARIOS = [
    {
        'username': 'admin',
        'password': 'AdminPass123',
        'rol': 'admin',
        'is_staff': True,
        'is_superuser': True,
        'email': 'admin@nnova.com',
        'first_name': 'Administrador',
        'last_name': '',
    },
    {
        'username': 'docente1',
        'password': 'DocentePass123',
        'rol': 'docente',
        'is_staff': False,
        'is_superuser': False,
        'email': 'docente1@nnova.com',
        'first_name': 'Docente',
        'last_name': 'Uno',
    },
    {
        'username': 'docente2',
        'password': 'DocentePass123',
        'rol': 'docente',
        'is_staff': False,
        'is_superuser': False,
        'email': 'docente2@nnova.com',
        'first_name': 'Docente',
        'last_name': 'Dos',
    },
    {
        'username': 'estudiante1',
        'password': 'EstudiantePass123',
        'rol': 'estudiante',
        'is_staff': False,
        'is_superuser': False,
        'email': 'estudiante1@nnova.com',
        'first_name': 'Estudiante',
        'last_name': 'Uno',
    },
    {
        'username': 'estudiante2',
        'password': 'EstudiantePass123',
        'rol': 'estudiante',
        'is_staff': False,
        'is_superuser': False,
        'email': 'estudiante2@nnova.com',
        'first_name': 'Estudiante',
        'last_name': 'Dos',
    },
]

print("[setup_usuarios] Verificando usuarios del sistema...")
print(f"[setup_usuarios] Base de datos: {django.conf.settings.DATABASES['default']['ENGINE']}")

for user_data in USUARIOS:
    # Copiar el dict para no mutar el original
    data = dict(user_data)
    password = data.pop('password')
    username = data['username']

    try:
        usuario, created = Usuario.objects.get_or_create(
            username=username,
            defaults=data
        )

        if created:
            # Usuario recién creado: establecer contraseña hasheada
            usuario.set_password(password)
            usuario.save()
            print(f"  [CREADO] {username} | rol={usuario.rol}")
        else:
            # Usuario ya existía: actualizar campos y contraseña
            for campo, valor in data.items():
                setattr(usuario, campo, valor)
            usuario.set_password(password)
            usuario.save()
            print(f"  [OK] {username} | rol={usuario.rol}")

    except Exception as e:
        print(f"  [ERROR] {username}: {e}", file=sys.stderr)

print("[setup_usuarios] Listo.")

# Reparar cursos huérfanos (sin docente asignado)
from cursos.models import Curso, Materia, Inscripcion
from django.db.models import Count

docente1 = Usuario.objects.filter(username='docente1').first()
if docente1:
    orphan_courses = Curso.objects.filter(docente__isnull=True).annotate(
        doc_count=Count('docentes')
    ).filter(doc_count=0)
    fixed = 0
    for curso in orphan_courses:
        curso.docente = docente1
        curso.save()
        curso.docentes.add(docente1)
        fixed += 1
    if fixed:
        print(f"[setup_usuarios] Reparados {fixed} curso(s) sin docente asignado.")

    # Crear curso de ejemplo si la plataforma está vacía
    if not Curso.objects.exists():
        materia, _ = Materia.objects.get_or_create(
            nombre='Programación',
            defaults={'descripcion': 'Cursos de desarrollo de software'}
        )
        curso = Curso.objects.create(
            nombre='Introducción a Python',
            descripcion='Aprende los fundamentos de Python desde cero.',
            materia=materia,
            docente=docente1,
        )
        curso.docentes.add(docente1)
        print(f"[setup_usuarios] Curso de ejemplo creado: {curso.nombre}")
