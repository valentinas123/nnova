import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nnova.settings')
django.setup()

from django.core.management import call_command
from usuarios.models import Usuario

print("🚀 Iniciando setup automático...")

# Migraciones
call_command('migrate', interactive=False)

# Superusuario automático
if not Usuario.objects.filter(username='admin').exists():
    Usuario.objects.create_superuser(
        username='admin',
        email='admin@nnova.edu',
        password='admin1234',
        rol='docente'
    )
    print("✅ Superusuario creado")
else:
    print("⚠️ Admin ya existe")

print("🎉 Setup terminado")