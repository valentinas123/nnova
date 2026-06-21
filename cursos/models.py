from django.db import models
from usuarios.models import Usuario

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

class Curso(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, null=True, blank=True)
    # Preserve existing single docente for backward compatibility
    docente = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=True, blank=True)
    # New many‑to‑many relation for multiple docentes
    docentes = models.ManyToManyField(Usuario, related_name='cursos_docentes', blank=True)
    imagen = models.ImageField(upload_to='cursos/', null=True, blank=True)
    limite_estudiantes = models.PositiveIntegerField(default=30, verbose_name="Límite de Estudiantes")
    archivo = models.FileField(upload_to='cursos/materiales/', null=True, blank=True, verbose_name="Archivo del Curso (Opcional)")

    def __str__(self):
        return self.nombre


class Inscripcion(models.Model):
    estudiante = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)

    # 👇 NUEVO (para lo que viene: calificaciones)
    nota = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.estudiante} - {self.curso}"


class Actividad(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='actividades')
    titulo = models.CharField(max_length=200, verbose_name="Título de la Actividad")
    descripcion = models.TextField(verbose_name="Descripción o Instrucciones")
    fecha_limite = models.DateTimeField(verbose_name="Fecha y Hora Límite")
    archivo = models.FileField(upload_to='actividades/', null=True, blank=True, verbose_name="Archivo Adjunto (Opcional)")
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.curso.nombre}"


class Entrega(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente de Calificar'),
        ('calificado', 'Calificado'),
    )
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='entregas')
    estudiante = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol': 'estudiante'})
    archivo = models.FileField(upload_to='entregas/', null=True, blank=True, verbose_name="Archivo Adjunto")
    texto_respuesta = models.TextField(null=True, blank=True, verbose_name="Respuesta de Texto")
    fecha_envio = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='pendiente')
    
    # Datos de calificación
    nota = models.FloatField(null=True, blank=True, verbose_name="Nota Obtenida")
    retroalimentacion = models.TextField(null=True, blank=True, verbose_name="Comentarios del Docente")
    fecha_calificacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('actividad', 'estudiante')

    def __str__(self):
        return f"Entrega: {self.estudiante.username} - {self.actividad.titulo}"