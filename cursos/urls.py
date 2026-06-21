from django.urls import path
from . import views

urlpatterns = [
    # ================= ESTUDIANTE =================
    path('', views.inicio, name='inicio'),
    path('inscribirse/<int:curso_id>/', views.inscribirse, name='inscribirse'),
    path('mis-cursos/', views.mis_cursos, name='mis_cursos'),
    path('logout/', views.logout_usuario, name='logout'),
    path('cancelar/<int:curso_id>/', views.cancelar_inscripcion, name='cancelar_inscripcion'),
    path('curso/<int:id>/', views.detalle_curso, name='detalle_curso'),
    path('contacto/', views.contacto, name='contacto'),
    path('estudiante/reporte-pdf/', views.pdf_reporte_estudiante, name='pdf_reporte_estudiante'),

    # ================= DOCENTE =================
    path('docente/', views.panel_docente, name='panel_docente'),
    path('crear/', views.crear_curso, name='crear_curso'),
    path('inscritos/<int:curso_id>/', views.ver_inscritos, name='ver_inscritos'),
    path('calificar/<int:inscripcion_id>/', views.calificar, name='calificar'),
    path('editar/<int:curso_id>/', views.editar_curso, name='editar_curso'),
    path('eliminar/<int:curso_id>/', views.eliminar_curso, name='eliminar_curso'),

    # ================= ACTIVIDADES Y ENTREGAS =================
    path('curso/<int:curso_id>/actividad/crear/', views.crear_actividad, name='crear_actividad'),
    path('actividad/<int:actividad_id>/entregar/', views.entregar_actividad, name='entregar_actividad'),
    path('actividad/<int:actividad_id>/entregas/', views.ver_entregas, name='ver_entregas_actividad'),
    path('entrega/<int:entrega_id>/calificar-entrega/', views.calificar_entrega, name='calificar_entrega'),

    # ================= REPORTES CURSOS =================
    path('reportes/cursos/', views.reporte_cursos, name='reporte_cursos'),

    # ================= SOLICITUD DE DOCENTE =================
    path('solicitar-docente/', views.solicitar_docente, name='solicitar_docente'),

    # ================= PDF =================
    path('pdf/curso/<int:curso_id>/', views.pdf_curso, name='pdf_curso'),
    path('pdf/general/', views.pdf_general, name='pdf_general'),

    # ================= ADMIN =================
    path('admin/', views.panel_admin, name='panel_admin'),

    # usuarios
    path('admin/usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('admin/usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('admin/usuarios/editar/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('admin/usuarios/eliminar/<int:usuario_id>/', views.eliminar_usuario, name='eliminar_usuario'),

    # cursos admin ( nuevos nombres)
    path('admin/cursos/', views.admin_cursos, name='admin_cursos'),
    path('admin/cursos/crear/', views.admin_crear_curso, name='admin_crear_curso'),
    path('admin/cursos/editar/<int:curso_id>/', views.admin_editar_curso, name='admin_editar_curso'),
    path('admin/cursos/eliminar/<int:curso_id>/', views.admin_eliminar_curso, name='admin_eliminar_curso'),

    # docente admin
    path('admin/docente/<int:docente_id>/', views.cursos_docente_admin, name='cursos_docente_admin'),

    # estudiante admin
    path('admin/estudiante/<int:estudiante_id>/', views.cursos_estudiante_admin, name='cursos_estudiante_admin'),

    # inscribir
    path('admin/inscribir/', views.inscribir_admin, name='inscribir_admin'),

    # pdf 
    path('admin/pdf-usuarios/', views.pdf_usuarios, name='pdf_usuarios'),
    path('admin/pdf-cursos/', views.pdf_cursos_admin, name='pdf_cursos_admin'),
    path('admin/pdf-general/', views.pdf_general_admin, name='pdf_general_admin'),

    #carga masiva
    path('admin/carga-masiva/', views.carga_masiva_usuarios, name='carga_masiva_usuarios'),
]