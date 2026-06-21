from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
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
        if '@' in username:
            try:
                user_obj = Usuario.objects.get(email=username)
                if user_obj.check_password(password):
                    user = user_obj
            except Usuario.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.rol == 'admin':
                return redirect('panel_admin')
            elif user.rol == 'docente':
                return redirect('panel_docente')
            else:
                return redirect('inicio')
        else:
            return render(request, 'login.html', {
                'error': 'Nombre de usuario o contraseña incorrectos'
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


def solicitar_docente(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        
        from django.core.mail import EmailMessage
        subject = f"Solicitud de docente: {nombre}"
        body = f"Nombre: {nombre}\nCorreo: {email}\nMensaje:\n{mensaje}"
        
        try:
            email_msg = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.EMAIL_HOST_USER,
                to=['valentina10solano@gmail.com'],
            )
            
            # Adjuntar hoja de vida si existe
            if request.FILES.get('hoja_vida'):
                hoja_vida = request.FILES['hoja_vida']
                email_msg.attach(hoja_vida.name, hoja_vida.read(), hoja_vida.content_type)
                
            email_msg.send(fail_silently=False)
            messages.success(request, 'Tu solicitud y hoja de vida han sido enviadas correctamente.')
        except Exception as e:
            messages.error(request, f'No se pudo enviar la solicitud por correo: {str(e)}')
            
        return redirect('inicio_publico')
    
    return redirect('inicio_publico')
