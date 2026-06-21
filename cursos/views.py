from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Count, Avg, Q
from django.http import HttpResponse

from usuarios.models import Usuario
from .models import Curso, Inscripcion, Actividad, Entrega

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

import csv
import json
from datetime import datetime
from io import TextIOWrapper

from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

# ===================== ESTUDIANTE =====================

@login_required
@never_cache
def inicio(request):
    # Redirigir docentes y admins a sus paneles propios
    if request.user.is_authenticated and request.user.rol == 'docente':
        return redirect('panel_docente')
    if request.user.is_authenticated and request.user.rol == 'admin':
        return redirect('panel_admin')

    cursos = Curso.objects.all()
    busqueda = request.GET.get('q')

    if busqueda:
        cursos = cursos.filter(nombre__icontains=busqueda)

    inscritos = Inscripcion.objects.filter(
        estudiante=request.user
    ).values_list('curso_id', flat=True)

    context = {
        'cursos': cursos,
        'inscritos': inscritos
    }

    if request.user.rol == 'estudiante':
        inscripciones = Inscripcion.objects.filter(estudiante=request.user).select_related('curso')
        entregas = Entrega.objects.filter(estudiante=request.user).select_related('actividad__curso')
        
        # Calcular promedios
        notas_cursos = [i.nota for i in inscripciones if i.nota is not None]
        promedio_cursos = round(sum(notas_cursos) / len(notas_cursos), 2) if notas_cursos else None
        
        # Actividades pendientes de realizar
        cursos_inscritos_ids = inscripciones.values_list('curso_id', flat=True)
        actividades_pendientes = Actividad.objects.filter(
            curso_id__in=cursos_inscritos_ids
        ).exclude(
            id__in=entregas.values_list('actividad_id', flat=True)
        ).select_related('curso')
        
        notas_entregas = [e.nota for e in entregas if e.nota is not None]
        promedio_entregas = round(sum(notas_entregas) / len(notas_entregas), 2) if notas_entregas else None
        
        entregas_calificadas = entregas.filter(estado='calificado').count()
        entregas_pendientes = entregas.filter(estado='pendiente').count()
        
        context.update({
            'inscripciones_rendimiento': inscripciones,
            'entregas_rendimiento': entregas,
            'actividades_pendientes': actividades_pendientes,
            'promedio_cursos': promedio_cursos,
            'promedio_entregas': promedio_entregas,
            'entregas_calificadas': entregas_calificadas,
            'entregas_pendientes': entregas_pendientes,
            'total_cursos_inscritos': inscripciones.count(),
        })

    return render(request, 'inicio.html', context)


@login_required
def inscribirse(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    if not Inscripcion.objects.filter(estudiante=request.user, curso=curso).exists():
        Inscripcion.objects.create(estudiante=request.user, curso=curso)
        messages.success(request, "Te inscribiste correctamente")

    return redirect('inicio')


@login_required
@never_cache
def mis_cursos(request):
    inscripciones = Inscripcion.objects.filter(estudiante=request.user)
    return render(request, 'mis_cursos.html', {'inscripciones': inscripciones})


@login_required
def cancelar_inscripcion(request, curso_id):
    if request.method == "POST":
        curso = get_object_or_404(Curso, id=curso_id)

        Inscripcion.objects.filter(
            estudiante=request.user,
            curso=curso
        ).delete()

    return redirect('mis_cursos')


def detalle_curso(request, id):
    curso = get_object_or_404(Curso, id=id)

    inscrito = False
    actividades_con_entrega = []
    promedio_curso_estudiante = None
    progreso_curso_estudiante = 0
    total_actividades = 0
    total_entregas_enviadas = 0
    
    if request.user.is_authenticated:
        inscrito = Inscripcion.objects.filter(
            estudiante=request.user,
            curso=curso
        ).exists()

        if inscrito:
            actividades = curso.actividades.all().order_by('-fecha_limite')
            for act in actividades:
                entrega = Entrega.objects.filter(actividad=act, estudiante=request.user).first()
                actividades_con_entrega.append({
                    'actividad': act,
                    'entrega': entrega
                })
            
            entregas_estudiante = Entrega.objects.filter(actividad__curso=curso, estudiante=request.user)
            entregas_calificadas = entregas_estudiante.filter(estado='calificado')
            if entregas_calificadas.exists():
                promedio_curso_estudiante = round(sum([e.nota for e in entregas_calificadas]) / entregas_calificadas.count(), 2)
            
            total_actividades = curso.actividades.count()
            total_entregas_enviadas = entregas_estudiante.count()
            if total_actividades > 0:
                progreso_curso_estudiante = int((total_entregas_enviadas / total_actividades) * 100)

        elif request.user.rol == 'docente' and (curso.docente == request.user or curso.docentes.filter(id=request.user.id).exists()):
            actividades = curso.actividades.all().order_by('-fecha_limite')
            for act in actividades:
                total_entregas = Entrega.objects.filter(actividad=act).count()
                pendientes = Entrega.objects.filter(actividad=act, estado='pendiente').count()
                actividades_con_entrega.append({
                    'actividad': act,
                    'total_entregas': total_entregas,
                    'pendientes': pendientes
                })

    return render(request, 'detalle_curso.html', {
        'curso': curso,
        'inscrito': inscrito,
        'actividades_con_entrega': actividades_con_entrega,
        'promedio_curso_estudiante': promedio_curso_estudiante,
        'progreso_curso_estudiante': progreso_curso_estudiante,
        'total_actividades': total_actividades,
        'total_entregas_enviadas': total_entregas_enviadas,
    })


def logout_usuario(request):
    logout(request)
    return redirect('/')

@login_required
def contacto(request):
    if request.method == 'POST':
        mensaje = request.POST.get('mensaje', '').strip()

        if not mensaje:
            messages.error(request, "El mensaje no puede estar vacío")
            return redirect('contacto')

        try:
            send_mail(
                subject=f"Mensaje de {request.user.username}",
                message=mensaje,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=["valentina10solano@gmail.com"],
                fail_silently=False,
            )
            messages.success(request, "Mensaje enviado correctamente")

        except Exception:
            messages.error(request, "No se pudo enviar el mensaje")

        return redirect('contacto')

    return render(request, 'contacto.html')



# ===================== DOCENTE =====================

@login_required
@never_cache
def panel_docente(request):
    if request.user.rol != 'docente':
        return redirect('inicio')

    # Mostrar cursos donde el usuario está en la relación muchos‑a‑muchos "docentes" o asignado como docente
    cursos = Curso.objects.filter(Q(docentes=request.user) | Q(docente=request.user)).distinct().annotate(
        total_estudiantes=Count('inscripcion'),
        promedio=Avg('inscripcion__nota')
    )

    total_cursos = cursos.count()
    total_estudiantes_global = sum([c.total_estudiantes for c in cursos])
    
    notas_inscripciones = Inscripcion.objects.filter(
        Q(curso__docentes=request.user) | Q(curso__docente=request.user),
        nota__isnull=False
    ).values_list('nota', flat=True)
    promedio_global = round(sum(notas_inscripciones) / len(notas_inscripciones), 2) if notas_inscripciones else None

    # Entregas pendientes para calificar en sus cursos
    entregas_pendientes = Entrega.objects.filter(
        Q(actividad__curso__docentes=request.user) | Q(actividad__curso__docente=request.user),
        estado='pendiente'
    ).select_related('actividad', 'actividad__curso', 'estudiante').order_by('fecha_envio')

    context = {
        'cursos': cursos,
        'total_cursos': total_cursos,
        'total_estudiantes_global': total_estudiantes_global,
        'promedio_global': promedio_global,
        'entregas_pendientes': entregas_pendientes,
    }

    return render(request, 'panel_docente.html', context)


@login_required
def crear_curso(request):
    if request.user.rol != 'docente':
        return redirect('inicio')

    if request.method == 'POST':
        nombre = request.POST['nombre']
        descripcion = request.POST['descripcion']
        imagen = request.FILES.get('imagen')
        archivo = request.FILES.get('archivo')
        # Get selected docentes (multiple)
        docente_ids = request.POST.getlist('docentes')
        # Optional single docente (keep for legacy)
        docente_id = request.POST.get('docente')
        curso = Curso.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            imagen=imagen,
            archivo=archivo,
            materia_id=request.POST.get('materia') if request.POST.get('materia') else None,
        )
        # Assign many-to-many docentes
        if docente_ids:
            curso.docentes.set(docente_ids)
        # Assign legacy single docente if provided
        if docente_id:
            curso.docente_id = docente_id
            curso.save()
        else:
            # El docente que crea el curso queda asignado automáticamente
            curso.docente = request.user
            curso.docentes.add(request.user)
            curso.save()
        messages.success(request, f'Curso "{nombre}" creado correctamente.')
        return redirect('panel_docente')

    return render(request, 'crear_curso.html')


@login_required
def editar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    if request.user != curso.docente and not curso.docentes.filter(id=request.user.id).exists():
        return redirect('panel_docente')

    if request.method == 'POST':
        curso.nombre = request.POST['nombre']
        curso.descripcion = request.POST['descripcion']

        if request.FILES.get('imagen'):
            curso.imagen = request.FILES.get('imagen')
            
        if request.FILES.get('archivo'):
            curso.archivo = request.FILES.get('archivo')

        curso.save()
        return redirect('panel_docente')

    return render(request, 'editar_curso.html', {'curso': curso})


@login_required
def eliminar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)

    if request.user != curso.docente and not curso.docentes.filter(id=request.user.id).exists():
        return redirect('panel_docente')

    if request.method == 'POST':
        if Inscripcion.objects.filter(curso=curso).exists():
            messages.error(request, "No se puede eliminar el curso porque tiene estudiantes inscritos.")
            return redirect('panel_docente')
        curso.delete()
        messages.success(request, "Curso eliminado correctamente")
        return redirect('panel_docente')

    return render(request, 'confirmar_eliminar.html', {'curso': curso})


@login_required
def ver_inscritos(request, curso_id):
    if request.user.rol != 'docente':
        return redirect('inicio')

    curso = get_object_or_404(Curso, id=curso_id)
    inscripciones = Inscripcion.objects.filter(curso=curso).select_related('estudiante')
    return render(request, 'ver_inscritos.html', {'inscripciones': inscripciones, 'curso': curso})


@login_required
def calificar(request, inscripcion_id):
    inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id)

    if request.method == 'POST':
        inscripcion.nota = request.POST['nota']
        inscripcion.save()
        return redirect('ver_inscritos', curso_id=inscripcion.curso.id)

    return render(request, 'calificar.html', {'inscripcion': inscripcion})


# ===================== PDF =====================

@login_required
def pdf_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    if request.user != curso.docente and not curso.docentes.filter(id=request.user.id).exists():
        return redirect('inicio')

    # Obtener inscripciones y calcular estadísticas
    inscripciones = Inscripcion.objects.filter(curso=curso)
    total_estudiantes = inscripciones.count()
    promedio_curso = inscripciones.aggregate(Avg('nota'))['nota__avg'] or 0.0

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_{curso.nombre}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # --- Construcción del Contenido ---
    elements = []

    # Título y Encabezado
    elements.append(Paragraph(f"REPORTE DETALLADO: {curso.nombre.upper()}", styles['Title']))
    elements.append(Spacer(1, 12))

    # Información General del Curso (Caja de texto)
    elements.append(Paragraph("<b>Descripción:</b>", styles['Normal']))
    elements.append(Paragraph(curso.descripcion or "Sin descripción disponible.", styles['Normal']))
    elements.append(Spacer(1, 15))

    # Estadísticas Rápidas
    stats_data = [
        [f"Total Estudiantes: {total_estudiantes}", f"Promedio del Curso: {promedio_curso:.1f}"]
    ]
    stats_table = Table(stats_data, colWidths=[3*inch, 3*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.darkblue),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 25))

    # Tabla de Estudiantes
    elements.append(Paragraph("<b>Listado de Alumnos</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))

    data = [["ID", "Nombre del Estudiante", "Calificación"]]
    for i, ins in enumerate(inscripciones, 1):
        nota = f"{ins.nota:.1f}" if ins.nota is not None else "N/A"
        data.append([str(i), ins.estudiante.username, nota])

    # Estilo de la Tabla Principal
    tabla = Table(data, colWidths=[0.5*inch, 3.5*inch, 1.5*inch])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')), # Azul oscuro
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(tabla)
    
    # Generar el PDF
    doc.build(elements)
    return response



@login_required
def pdf_general(request):
    # Verificación de rol
    if request.user.rol != 'docente':
        return redirect('inicio')

    # Consulta de datos (Nombre, cantidad de alumnos y promedio)
    cursos = Curso.objects.filter(Q(docente=request.user) | Q(docentes=request.user)).distinct().annotate(
        num_estudiantes=Count('inscripcion'),
        promedio=Avg('inscripcion__nota')
    )

    # Configuración de la respuesta
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_general.pdf"'

    # Creación del documento
    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Título del reporte
    elements.append(Paragraph("REPORTE GENERAL DE CURSOS", styles['Title']))
    elements.append(Spacer(1, 20))

    # Preparación de la tabla
    data = [["Nombre del Curso", "Estudiantes", "Promedio"]]
    
    for curso in cursos:
        promedio_val = f"{curso.promedio:.1f}" if curso.promedio is not None else "N/A"
        data.append([
            curso.nombre, 
            str(curso.num_estudiantes), 
            promedio_val
        ])

    # Estilo de la tabla (Encabezado oscuro y filas alternas)
    tabla = Table(data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    elements.append(tabla)

    # Generación final
    doc.build(elements)
    return response



# ===================== ADMIN =====================

@login_required
@never_cache
def panel_admin(request):
    if request.user.rol != 'admin' and not request.user.is_superuser:
        return redirect('inicio')

    #  estadísticas generales
    total_estudiantes = Usuario.objects.filter(rol='estudiante').count()
    total_docentes = Usuario.objects.filter(rol='docente').count()
    total_admins = Usuario.objects.filter(rol='admin').count()
    total_cursos = Curso.objects.count()
    total_inscripciones = Inscripcion.objects.count()

    #  cursos con estudiantes y promedio
    cursos = Curso.objects.annotate(
        total_estudiantes=Count('inscripcion'),
        promedio=Avg('inscripcion__nota')
    )

    nombres = [c.nombre for c in cursos]
    cantidades = [c.total_estudiantes for c in cursos]
    promedios = [float(c.promedio or 0) for c in cursos]

    return render(request, 'panel_admin.html', {
        'total_estudiantes': total_estudiantes,
        'total_docentes': total_docentes,
        'total_admins': total_admins,
        'total_cursos': total_cursos,
        'total_inscripciones': total_inscripciones,

        'nombres_json': json.dumps(nombres),
        'cantidades_json': json.dumps(cantidades),
        'promedios_json': json.dumps(promedios),
    })


@login_required
@never_cache
def lista_usuarios(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    usuarios = Usuario.objects.all()
    return render(request, 'admin_usuarios.html', {'usuarios': usuarios})


@login_required
def crear_usuario(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        rol = request.POST.get('rol')

        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        from django.contrib.auth.password_validation import validate_password

        # Validar usuario
        if not username:
            messages.error(request, "El nombre de usuario es obligatorio")
            return redirect('crear_usuario')

        if Usuario.objects.filter(username=username).exists():
            messages.error(request, "El nombre de usuario ya existe")
            return redirect('crear_usuario')

        # Validar correo
        if not email:
            messages.error(request, "El correo electrónico es obligatorio")
            return redirect('crear_usuario')

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "El correo electrónico no es válido")
            return redirect('crear_usuario')

        if Usuario.objects.filter(email=email).exists():
            messages.error(request, "Este correo ya está registrado")
            return redirect('crear_usuario')

        # Validar contraseña
        if not password:
            messages.error(request, "La contraseña es obligatoria")
            return redirect('crear_usuario')

        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, e.messages[0])
            return redirect('crear_usuario')

        # Crear usuario
        Usuario.objects.create_user(
            username=username,
            email=email,
            password=password,
            rol=rol
        )

        messages.success(request, "Usuario creado correctamente")
        return redirect('lista_usuarios')

    return render(request, 'crear_usuario.html')


@login_required
def editar_usuario(request, usuario_id):
    if request.user.rol != 'admin':
        return redirect('inicio')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        rol = request.POST.get('rol')
        password = request.POST.get('password')

        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        from django.contrib.auth.password_validation import validate_password

        # VALIDACIÓN
        if not username:
            messages.error(request, "El nombre de usuario no puede estar vacío")
            return render(request, 'editar_usuario.html', {'usuario': usuario})
        
        if Usuario.objects.filter(username=username).exclude(id=usuario.id).exists():
            messages.error(request, "El nombre de usuario ya existe")
            return render(request, 'editar_usuario.html', {'usuario': usuario})

        if not email:
            messages.error(request, "El correo electrónico es obligatorio")
            return render(request, 'editar_usuario.html', {'usuario': usuario})

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "El formato del correo electrónico ingresado no es válido")
            return render(request, 'editar_usuario.html', {'usuario': usuario})

        if Usuario.objects.filter(email=email).exclude(id=usuario.id).exists():
            messages.error(request, "Este correo electrónico ya se encuentra registrado")
            return render(request, 'editar_usuario.html', {'usuario': usuario})

        if password:
            try:
                validate_password(password)
                usuario.password = make_password(password)
            except ValidationError as e:
                messages.error(request, e.messages[0])
                return render(request, 'editar_usuario.html', {'usuario': usuario})

        usuario.username = username
        usuario.email = email
        usuario.rol = rol
        usuario.save()
        messages.success(request, "Usuario actualizado correctamente")
        return redirect('lista_usuarios')

    return render(request, 'editar_usuario.html', {'usuario': usuario})


@login_required
def eliminar_usuario(request, usuario_id):
    if request.user.rol != 'admin':
        return redirect('inicio')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        usuario.delete()
        return redirect('lista_usuarios')

    return render(request, 'eliminar_usuario.html', {'usuario': usuario})


@login_required
def cursos_docente_admin(request, docente_id):
    if request.user.rol != 'admin':
        return redirect('inicio')

    cursos = Curso.objects.filter(Q(docente_id=docente_id) | Q(docentes__id=docente_id)).distinct()
    return render(request, 'admin_cursos_docente.html', {'cursos': cursos})


@login_required
def cursos_estudiante_admin(request, estudiante_id):
    if request.user.rol != 'admin':
        return redirect('inicio')

    estudiante = get_object_or_404(Usuario, id=estudiante_id)
    inscripciones = Inscripcion.objects.filter(estudiante=estudiante)

    return render(request, 'admin_cursos_estudiante.html', {
        'estudiante': estudiante,
        'inscripciones': inscripciones
    })


@login_required
def inscribir_admin(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    if request.method == 'POST':
        Inscripcion.objects.create(
            estudiante_id=request.POST['estudiante'],
            curso_id=request.POST['curso']
        )

        messages.success(request, "Estudiante inscrito correctamente")

        return redirect('panel_admin')

    return render(request, 'inscribir_admin.html', {
        'estudiantes': Usuario.objects.filter(rol='estudiante'),
        'cursos': Curso.objects.all()
    })


@login_required
@never_cache
def admin_cursos(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    #  CONSULTA CON ESTADÍSTICAS
    cursos = Curso.objects.all().annotate(
        total_estudiantes=Count('inscripcion'),
        promedio=Avg('inscripcion__nota')
    )

    #  FILTROS
    nombre = request.GET.get('nombre')
    docente = request.GET.get('docente')
    min_estudiantes = request.GET.get('min')

    if nombre:
        cursos = cursos.filter(nombre__icontains=nombre)

    if docente:
        cursos = cursos.filter(docente__username__icontains=docente)

    if min_estudiantes:
        cursos = cursos.filter(total_estudiantes__gte=min_estudiantes)

    return render(request, 'admin_cursos.html', {
        'cursos': cursos
    })

# ===================== ADMIN CURSOS (CRUD PROPIO) =====================

@login_required
def admin_editar_curso(request, curso_id):
    if request.user.rol != 'admin':
        return redirect('inicio')

    curso = get_object_or_404(Curso, id=curso_id)

    if request.method == 'POST':
        curso.nombre = request.POST['nombre']
        curso.descripcion = request.POST['descripcion']

        if request.FILES.get('imagen'):
            curso.imagen = request.FILES.get('imagen')

        if request.FILES.get('archivo'):
            curso.archivo = request.FILES.get('archivo')

        curso.save()
        messages.success(request, "Curso actualizado correctamente")

        return redirect('admin_cursos')

    return render(request, 'admin_editar_curso.html', {
        'curso': curso
    })


@login_required
def admin_eliminar_curso(request, curso_id):
    if request.user.rol != 'admin':
        return redirect('inicio')

    curso = get_object_or_404(Curso, id=curso_id)

    if request.method == 'POST':
        if Inscripcion.objects.filter(curso=curso).exists():
            messages.error(request, "No se puede eliminar el curso porque tiene estudiantes inscritos.")
            return redirect('admin_cursos')
        curso.delete()
        messages.success(request, "Curso eliminado correctamente")
        return redirect('admin_cursos')

    return render(request, 'admin_eliminar_curso.html', {
        'curso': curso
    })

@login_required
def admin_crear_curso(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    if request.method == 'POST':
        nombre = request.POST['nombre']
        descripcion = request.POST['descripcion']
        docente_id = request.POST['docente']
        imagen = request.FILES.get('imagen')
        archivo = request.FILES.get('archivo')

        Curso.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            imagen=imagen,
            archivo=archivo,
            docente_id=docente_id
        )

        messages.success(request, "Curso creado correctamente")
        return redirect('admin_cursos')

    docentes = Usuario.objects.filter(rol='docente')

    return render(request, 'admin_crear_curso.html', {
        'docentes': docentes
    })

@login_required
def pdf_usuarios(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    usuarios = Usuario.objects.all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_usuarios.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()

    elementos = []

    # Título
    elementos.append(Paragraph("REPORTE DE USUARIOS", styles['Title']))
    elementos.append(Spacer(1, 15))

    data = [["ID", "Usuario", "Correo", "Rol"]]

    for u in usuarios:
        data.append([str(u.id), u.username, u.email, u.rol])

    tabla = Table(data, colWidths=[50, 120, 200, 80])

    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke]),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    return response

@login_required
def pdf_cursos_admin(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    cursos = Curso.objects.all().annotate(
        total_estudiantes=Count('inscripcion'),
        promedio=Avg('inscripcion__nota')
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_cursos.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()

    elementos = []

    elementos.append(Paragraph("REPORTE DE CURSOS", styles['Title']))
    elementos.append(Spacer(1, 15))

    data = [["Curso", "Docente", "Estudiantes", "Promedio"]]

    for c in cursos:
        promedio = f"{c.promedio:.1f}" if c.promedio else "N/A"
        data.append([
            c.nombre,
            c.docente.username if c.docente else "N/A",
            str(c.total_estudiantes),
            promedio
        ])

    tabla = Table(data, colWidths=[150, 120, 80, 80])

    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
    ]))

    elementos.append(tabla)
    doc.build(elementos)

    return response

@login_required
def pdf_general_admin(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    usuarios = Usuario.objects.count()
    cursos = Curso.objects.count()
    inscripciones = Inscripcion.objects.count()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_general.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()

    elementos = []

    # Título
    elementos.append(Paragraph("REPORTE GENERAL DEL SISTEMA", styles['Title']))
    elementos.append(Spacer(1, 20))

    # Estadísticas
    stats = [
        ["Total Usuarios", str(usuarios)],
        ["Total Cursos", str(cursos)],
        ["Total Inscripciones", str(inscripciones)],
    ]

    tabla_stats = Table(stats, colWidths=[200, 100])

    tabla_stats.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
    ]))

    elementos.append(tabla_stats)
    elementos.append(Spacer(1, 25))

    elementos.append(Paragraph("Resumen del sistema generado automáticamente.", styles['Normal']))

    doc.build(elementos)

    return response

@login_required
def carga_masiva_usuarios(request):
    if request.user.rol != 'admin':
        return redirect('inicio')

    if request.method == 'POST':
        archivo = request.FILES.get('archivo')

        if not archivo:
            messages.error(request, "No seleccionaste ningún archivo")
            return redirect('carga_masiva_usuarios')

        try:
            archivo_csv = TextIOWrapper(archivo.file, encoding='utf-8')
            lector = csv.DictReader(archivo_csv)

            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            from django.contrib.auth.password_validation import validate_password

            creados = 0
            errores = []

            for index, fila in enumerate(lector, start=2):
                username = fila.get('username', '').strip()
                email = fila.get('email', '').strip()
                rol = fila.get('rol', 'estudiante')
                password = fila.get('password', '')

                if not username:
                    errores.append(f"Fila {index}: Nombre de usuario vacío.")
                    continue
                if Usuario.objects.filter(username=username).exists():
                    errores.append(f"Fila {index}: Usuario '{username}' ya existe.")
                    continue

                if not email:
                    errores.append(f"Fila {index}: Correo vacío.")
                    continue
                try:
                    validate_email(email)
                except ValidationError:
                    errores.append(f"Fila {index}: Formato de correo '{email}' inválido.")
                    continue

                if Usuario.objects.filter(email=email).exists():
                    errores.append(f"Fila {index}: Correo '{email}' ya registrado.")
                    continue

                if not password:
                    errores.append(f"Fila {index}: Contraseña vacía.")
                    continue
                try:
                    validate_password(password)
                except ValidationError as e:
                    errores.append(f"Fila {index}: Contraseña para '{username}' no cumple requisitos: {e.messages[0]}")
                    continue

                Usuario.objects.create(
                    username=username,
                    email=email,
                    rol=rol,
                    password=make_password(password)
                )
                creados += 1

            if errores:
                for err in errores[:5]:
                    messages.error(request, err)
                if len(errores) > 5:
                    messages.error(request, f"Y {len(errores) - 5} errores más.")

            if creados > 0:
                messages.success(request, f"{creados} usuarios cargados correctamente.")
            else:
                messages.warning(request, "No se pudo cargar ningún usuario debido a errores de validación.")

        except Exception as e:
            messages.error(request, f"Error al procesar el archivo CSV: {str(e)}")

        return redirect('lista_usuarios')

    return render(request, 'carga_masiva.html')


# ===================== ACTIVIDADES Y ENTREGAS =====================

from django.utils import timezone

@login_required
def crear_actividad(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    
    es_docente = curso.docente == request.user or curso.docentes.filter(id=request.user.id).exists()
    if request.user.rol != 'docente' or not es_docente:
        messages.error(request, "No tienes permiso para crear actividades en este curso.")
        return redirect('panel_docente')

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_limite_str = request.POST.get('fecha_limite')
        archivo = request.FILES.get('archivo')

        if not titulo or not descripcion or not fecha_limite_str:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'crear_actividad.html', {'curso': curso})

        try:
            # Parsear fecha
            fecha_limite = datetime.fromisoformat(fecha_limite_str)
            if timezone.is_naive(fecha_limite):
                fecha_limite = timezone.make_aware(fecha_limite)
            
            Actividad.objects.create(
                curso=curso,
                titulo=titulo,
                descripcion=descripcion,
                fecha_limite=fecha_limite,
                archivo=archivo
            )
            messages.success(request, "Actividad creada correctamente.")
            return redirect('detalle_curso', id=curso.id)
        except Exception as e:
            messages.error(request, f"Error al crear actividad: {str(e)}")

    return render(request, 'crear_actividad.html', {'curso': curso})


@login_required
def entregar_actividad(request, actividad_id):
    actividad = get_object_or_404(Actividad, id=actividad_id)
    
    # Validar rol y que esté inscrito
    if request.user.rol != 'estudiante':
        messages.error(request, "Solo los estudiantes pueden entregar tareas.")
        return redirect('inicio')

    inscrito = Inscripcion.objects.filter(estudiante=request.user, curso=actividad.curso).exists()
    if not inscrito:
        messages.error(request, "No estás inscrito en este curso.")
        return redirect('inicio')

    # Si ya tiene una entrega calificada
    entrega_existente = Entrega.objects.filter(actividad=actividad, estudiante=request.user).first()
    if entrega_existente and entrega_existente.estado == 'calificado':
        messages.warning(request, "Esta entrega ya fue calificada y no se puede modificar.")
        return redirect('detalle_curso', id=actividad.curso.id)

    if request.method == 'POST':
        archivo = request.FILES.get('archivo')
        texto_respuesta = request.POST.get('texto_respuesta', '').strip()

        if not archivo and not texto_respuesta:
            messages.error(request, "Debes subir un archivo o escribir una respuesta.")
            return render(request, 'entregar_actividad.html', {'actividad': actividad, 'entrega': entrega_existente})

        if not entrega_existente:
            entrega_existente = Entrega(actividad=actividad, estudiante=request.user)

        if archivo:
            entrega_existente.archivo = archivo
        if texto_respuesta:
            entrega_existente.texto_respuesta = texto_respuesta

        entrega_existente.estado = 'pendiente'
        entrega_existente.fecha_envio = timezone.now()
        entrega_existente.save()

        messages.success(request, "Tarea entregada correctamente.")
        return redirect('detalle_curso', id=actividad.curso.id)

    return render(request, 'entregar_actividad.html', {'actividad': actividad, 'entrega': entrega_existente})


@login_required
def ver_entregas(request, actividad_id):
    actividad = get_object_or_404(Actividad, id=actividad_id)
    
    es_docente = actividad.curso.docente == request.user or actividad.curso.docentes.filter(id=request.user.id).exists()
    if request.user.rol != 'docente' or not es_docente:
        messages.error(request, "No tienes permiso para ver estas entregas.")
        return redirect('panel_docente')

    entregas = actividad.entregas.select_related('estudiante').all()
    return render(request, 'ver_entregas.html', {'actividad': actividad, 'entregas': entregas})


@login_required
def calificar_entrega(request, entrega_id):
    entrega = get_object_or_404(Entrega, id=entrega_id)
    
    es_docente = entrega.actividad.curso.docente == request.user or entrega.actividad.curso.docentes.filter(id=request.user.id).exists()
    if request.user.rol != 'docente' or not es_docente:
        messages.error(request, "No tienes permiso para calificar esta entrega.")
        return redirect('panel_docente')

    if request.method == 'POST':
        nota_str = request.POST.get('nota')
        retro = request.POST.get('retroalimentacion', '').strip()

        try:
            nota = float(nota_str)
            if not (0.0 <= nota <= 5.0):
                raise ValueError("La nota debe estar en el rango de 0.0 a 5.0")

            entrega.nota = nota
            entrega.retroalimentacion = retro
            entrega.estado = 'calificado'
            entrega.fecha_calificacion = timezone.now()
            entrega.save()

            # --- Sincronizar promedio en Inscripcion ---
            curso = entrega.actividad.curso
            entregas_calificadas = Entrega.objects.filter(
                actividad__curso=curso,
                estudiante=entrega.estudiante,
                estado='calificado'
            )
            if entregas_calificadas.exists():
                promedio = sum([e.nota for e in entregas_calificadas]) / entregas_calificadas.count()
                # Redondear a un decimal
                promedio = round(promedio, 2)
                Inscripcion.objects.filter(estudiante=entrega.estudiante, curso=curso).update(nota=promedio)

            messages.success(request, "Calificación registrada correctamente.")
            return redirect('ver_entregas_actividad', actividad_id=entrega.actividad.id)
        except ValueError as e:
            messages.error(request, f"Nota inválida: {str(e)}")

    return render(request, 'calificar_entrega.html', {'entrega': entrega})


# ===================== REPORTE CURSOS =====================

@login_required
@never_cache
def reporte_cursos(request):
    if request.user.rol not in ['admin', 'docente']:
        return redirect('inicio')

    # Cargar listas para filtros
    docentes = Usuario.objects.filter(rol='docente')
    cursos_list = Curso.objects.all()

    # Si es un docente, solo puede filtrar sobre sus propios cursos
    if request.user.rol == 'docente':
        cursos_list = cursos_list.filter(Q(docente=request.user) | Q(docentes=request.user)).distinct()

    # Capturar parámetros
    curso_id = request.GET.get('curso')
    docente_id = request.GET.get('docente')
    estado = request.GET.get('estado')

    # Query inicial
    inscripciones = Inscripcion.objects.select_related('curso', 'estudiante', 'curso__docente').all()

    # Si es docente, limitar a sus cursos inscritos
    if request.user.rol == 'docente':
        inscripciones = inscripciones.filter(Q(curso__docente=request.user) | Q(curso__docentes=request.user)).distinct()

    # Construir filtros combinados (Multicriterio)
    filtros = Q()

    if curso_id:
        filtros &= Q(curso_id=curso_id)

    if docente_id and request.user.rol == 'admin': # Solo admin filtra por cualquier docente
        filtros &= (Q(curso__docente_id=docente_id) | Q(curso__docentes__id=docente_id))

    if estado:
        if estado == 'aprobado':
            filtros &= Q(nota__gte=3.0)
        elif estado == 'reprobado':
            filtros &= Q(nota__lt=3.0)
        elif estado == 'pendiente':
            filtros &= Q(nota__isnull=True)

    # Aplicar filtros
    resultados = inscripciones.filter(filtros)

    # --- EXPORTAR A PDF (ReportLab) ---
    if 'exportar_pdf' in request.GET:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_cursos.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter)
        styles = getSampleStyleSheet()
        elementos = []

        # Título
        elementos.append(Paragraph("REPORTE ACADÉMICO DE CURSOS", styles['Title']))
        elementos.append(Spacer(1, 15))

        # Texto Informativo de los Filtros
        filtros_aplicados = []
        if curso_id:
            c = Curso.objects.filter(id=curso_id).first()
            if c: filtros_aplicados.append(f"Curso: {c.nombre}")
        if docente_id and request.user.rol == 'admin':
            d = Usuario.objects.filter(id=docente_id).first()
            if d: filtros_aplicados.append(f"Docente: {d.username}")
        if estado:
            filtros_aplicados.append(f"Estado de Nota: {estado.capitalize()}")
        
        filtro_txt = "Filtros aplicados: " + (", ".join(filtros_aplicados) if filtros_aplicados else "Ninguno (Todos)")
        elementos.append(Paragraph(f"<b>{filtro_txt}</b>", styles['Normal']))
        elementos.append(Spacer(1, 15))

        # Datos de la Tabla
        data = [["Curso", "Estudiante", "Docente", "Nota Final"]]
        for ins in resultados:
            nota_str = f"{ins.nota:.1f}" if ins.nota is not None else "Sin calificar"
            data.append([
                ins.curso.nombre,
                ins.estudiante.username,
                ins.curso.docente.username,
                nota_str
            ])

        tabla = Table(data, colWidths=[2.2*inch, 1.8*inch, 1.8*inch, 1.2*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke]),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))

        elementos.append(tabla)
        doc.build(elementos)
        return response

    return render(request, 'reporte_cursos.html', {
        'docentes': docentes,
        'cursos_list': cursos_list,
        'resultados': resultados,
        'curso_id': curso_id,
        'docente_id': docente_id,
        'estado': estado
    })


@login_required
def solicitar_docente(request):
    if request.method == 'POST':
        asunto = f"Solicitud de Rol Docente - {request.user.username}"
        mensaje = f"Hola Administrador,\n\nEl estudiante '{request.user.username}' (Correo: {request.user.email}) ha solicitado cambiar su rol a 'Docente' en la plataforma Nnova Learning para poder impartir cursos.\n\nPor favor, valide e ingrese al panel de administración para actualizar su perfil si corresponde.\n\nAtentamente,\nPlataforma Nnova Learning."
        
        try:
            send_mail(
                subject=asunto,
                message=mensaje,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=['valentina10solano@gmail.com'],
                fail_silently=False,
            )
            messages.success(request, "Tu solicitud para ser docente ha sido enviada correctamente al administrador.")
        except Exception as e:
            messages.error(request, f"Ocurrió un error al enviar tu solicitud: {str(e)}")
            
        return redirect('inicio')
        
    return redirect('inicio')


@login_required
def pdf_reporte_estudiante(request):
    estudiante = request.user
    
    if request.user.rol in ['docente', 'admin']:
        estudiante_id = request.GET.get('estudiante_id')
        if estudiante_id:
            estudiante = get_object_or_404(Usuario, id=estudiante_id, rol='estudiante')
            
            # Si es docente, validar que el estudiante esté inscrito en al menos uno de sus cursos
            if request.user.rol == 'docente':
                es_su_estudiante = Inscripcion.objects.filter(
                    estudiante=estudiante,
                    curso__docente=request.user
                ).exists() or Inscripcion.objects.filter(
                    estudiante=estudiante,
                    curso__docentes=request.user
                ).exists()
                
                if not es_su_estudiante:
                    messages.error(request, "No tienes permiso para ver el reporte de este estudiante.")
                    return redirect('panel_docente')
        else:
            messages.error(request, "Debe especificar un estudiante para generar el reporte.")
            if request.user.rol == 'admin':
                return redirect('panel_admin')
            return redirect('panel_docente')
    elif request.user.rol != 'estudiante':
        return redirect('inicio')

    inscripciones = Inscripcion.objects.filter(estudiante=estudiante).select_related('curso', 'curso__docente')
    entregas = Entrega.objects.filter(estudiante=estudiante).select_related('actividad__curso')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_academico_{estudiante.username}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title & Header
    elements.append(Paragraph(f"REPORTE ACADÉMICO: {estudiante.username.upper()}", styles['Title']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Estudiante:</b> {estudiante.username} ({estudiante.email or 'N/A'})", styles['Normal']))
    elements.append(Paragraph(f"<b>Fecha de Generación:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # General Metrics Table
    notas_cursos = [i.nota for i in inscripciones if i.nota is not None]
    promedio_cursos = round(sum(notas_cursos) / len(notas_cursos), 2) if notas_cursos else 0.0
    
    total_entregas = entregas.count()
    calificadas = entregas.filter(estado='calificado').count()
    pendientes = entregas.filter(estado='pendiente').count()

    stats_data = [
        ["Promedio General", "Cursos Inscritos", "Tareas Entregadas", "Calificadas / Pendientes"],
        [f"{promedio_cursos:.2f}", str(inscripciones.count()), str(total_entregas), f"{calificadas} / {pendientes}"]
    ]
    stats_table = Table(stats_data, colWidths=[1.8*inch, 1.8*inch, 1.5*inch, 1.9*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5b4ff5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 25))

    # Details of Courses
    elements.append(Paragraph("<b>Detalle por Curso</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))

    course_data = [["Curso", "Docente", "Nota Final", "Estado"]]
    for ins in inscripciones:
        docente_str = ins.curso.docente.username if ins.curso.docente else "N/A"
        nota_str = f"{ins.nota:.2f}" if ins.nota is not None else "Pendiente"
        estado_str = "Aprobado" if (ins.nota is not None and ins.nota >= 3.0) else ("Reprobado" if ins.nota is not None else "En progreso")
        course_data.append([ins.curso.nombre, docente_str, nota_str, estado_str])

    course_table = Table(course_data, colWidths=[2.5*inch, 2.0*inch, 1.2*inch, 1.3*inch])
    course_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(course_table)
    elements.append(Spacer(1, 25))

    # Details of Graded Activities
    elements.append(Paragraph("<b>Reporte de Actividades Entregadas</b>", styles['Heading2']))
    elements.append(Spacer(1, 10))

    act_data = [["Actividad", "Curso", "Fecha Envío", "Nota", "Retroalimentación"]]
    for ent in entregas:
        fecha_str = ent.fecha_envio.strftime('%d/%m/%Y') if ent.fecha_envio else "N/A"
        nota_str = f"{ent.nota:.1f}" if ent.nota is not None else "Pendiente"
        retro_str = ent.retroalimentacion or "-"
        # Wrap long text using Paragraph
        retro_para = Paragraph(retro_str, styles['Normal'])
        act_data.append([ent.actividad.titulo, ent.actividad.curso.nombre, fecha_str, nota_str, retro_para])

    act_table = Table(act_data, colWidths=[1.8*inch, 1.5*inch, 1.1*inch, 0.8*inch, 1.8*inch])
    act_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(act_table)

    doc.build(elements)
    return response