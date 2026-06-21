from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib import messages
from .models import Usuario


def inicio_publico(request):
    return render(request, 'landing.html')


def buscar(request):
    query = request.GET.get('q', '').strip()
    return render(request, 'landing.html', {'query': query})


def login_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')

        user = None

        # login por email o username
        if '@' in username:
            try:
                user_obj = Usuario.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except Usuario.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=username, password=password)

        if user is not None:

            if not user.is_active:
                return render(request, 'login.html', {
                    'error': 'Tu cuenta está desactivada.'
                })

            login(request, user)

            # 🔥 DEBUG IMPORTANTE (para ver qué rol tienes realmente)
            print("ROL DEL USUARIO:", user.rol)

            # 🔥 REDIRECCIÓN POR ROL
            if user.rol == 'admin' or user.is_superuser:
                return redirect('panel_admin')
            elif user.rol == 'docente':
                return redirect('panel_docente')
            else:
                return redirect('inicio')

        return render(request, 'login.html', {
            'error': 'Credenciales incorrectas'
        })

    return render(request, 'login.html')



def registro(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        rol = 'estudiante'

        if not username:
            return render(request, 'registro.html', {'error': 'El nombre de usuario es obligatorio.', 'ocultar_nav': True})
        if Usuario.objects.filter(username=username).exists():
            return render(request, 'registro.html', {'error': 'El nombre de usuario ya existe.', 'ocultar_nav': True})

        if not email:
            return render(request, 'registro.html', {'error': 'El correo electrónico es obligatorio.', 'ocultar_nav': True})
        
        try:
            validate_email(email)
        except ValidationError:
            return render(request, 'registro.html', {'error': 'El formato del correo electrónico ingresado no es válido.', 'ocultar_nav': True})

        if Usuario.objects.filter(email=email).exists():
            return render(request, 'registro.html', {'error': 'Este correo electrónico ya se encuentra registrado.', 'ocultar_nav': True})

        if not password:
            return render(request, 'registro.html', {'error': 'La contraseña es obligatoria.', 'ocultar_nav': True})

        try:
            validate_password(password)
        except ValidationError as e:
            return render(request, 'registro.html', {'error': e.messages[0], 'ocultar_nav': True})

        # Crear el usuario y loguearlo
        user = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password,
            rol=rol
        )
        login(request, user)
        messages.success(request, "Cuenta creada exitosamente. ¡Bienvenido/a!")
        return redirect('inicio')

    return render(request, 'registro.html')


@login_required
def solicitar_docente(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        archivo = request.FILES.get('hoja_vida')

        if not nombre or not email:
            messages.error(request, "Nombre y correo son obligatorios")
            return redirect('solicitar_docente')

        try:
            email_msg = EmailMessage(
                subject=f"Solicitud de docente: {nombre}",
                body=f"""
Nombre: {nombre}
Correo: {email}

Mensaje:
{mensaje}
""",
                from_email=settings.EMAIL_HOST_USER,
                to=["valentina10solano@gmail.com"],
            )

            # adjunto seguro
            if archivo:
                email_msg.attach(
                    archivo.name,
                    archivo.read(),
                    archivo.content_type
                )

            email_msg.send(fail_silently=False)

            messages.success(request, "Solicitud enviada correctamente")

        except Exception:
            messages.error(request, "Error al enviar la solicitud")

        return redirect('inicio')

    return render(request, 'solicitar_docente.html')