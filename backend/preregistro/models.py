from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class AspiranteManager(BaseUserManager):
    def create_user(self, usuario, correo, password=None, **extra):
        if not correo:
            raise ValueError('El correo es obligatorio')
        correo = self.normalize_email(correo)
        user = self.model(usuario=usuario, correo=correo, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, usuario, correo, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('is_active', True)
        extra.setdefault('nombre', 'Administrador SINAC')
        extra.setdefault('curp', 'ADMS000000HDF00001')
        extra.setdefault('telefono', '0000000000')
        extra.setdefault('estado_actual', 'Ciudad de México')
        extra.setdefault('municipio_actual', 'Gustavo A. Madero')
        extra.setdefault('direccion_actual', 'Cinvestav')
        extra.setdefault('estado_permanente', 'Ciudad de México')
        extra.setdefault('municipio_permanente', 'Gustavo A. Madero')
        extra.setdefault('direccion_permanente', 'Cinvestav')
        extra.setdefault('nombre_familiar', 'No aplica')
        extra.setdefault('parentesco', 'No aplica')
        extra.setdefault('telefono_familiar', '0000000000')
        extra.setdefault('ultimo_grado', 'No aplica')
        extra.setdefault('institucion', 'Cinvestav')
        extra.setdefault('unidad', 'Administración')
        extra.setdefault('departamento', 'SINAC')
        extra.setdefault('seccion', 'Administración')
        extra.setdefault('programa', 'SINAC NEXT')
        extra.setdefault('business_key', 'ADMIN-SINAC')
        return self.create_user(usuario, correo, password, **extra)


class Aspirante(AbstractBaseUser, PermissionsMixin):
    # Sección 1 – Datos Generales
    usuario    = models.CharField(max_length=20, unique=True)
    matricula  = models.CharField(max_length=30, unique=True, null=True, blank=True)
    nombre     = models.CharField(max_length=180)
    curp       = models.CharField(max_length=18, unique=True)
    correo     = models.EmailField(unique=True)
    telefono   = models.CharField(max_length=20)
    nacimiento = models.DateField(null=True, blank=True)

    # Sección 2 – Domicilio Actual
    estado_actual      = models.CharField(max_length=80)
    municipio_actual   = models.CharField(max_length=80)
    direccion_actual   = models.CharField(max_length=255)

    # Sección 3 – Domicilio Permanente
    estado_permanente    = models.CharField(max_length=80)
    municipio_permanente = models.CharField(max_length=80)
    direccion_permanente = models.CharField(max_length=255)

    # Sección 4 – Familiar
    nombre_familiar   = models.CharField(max_length=180)
    parentesco        = models.CharField(max_length=60)
    telefono_familiar = models.CharField(max_length=20)

    # Sección 5 – Escolaridad
    ultimo_grado = models.CharField(max_length=80)
    institucion  = models.CharField(max_length=180)
    promedio     = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    # Secciones 6–9 – Opcionales
    idiomas      = models.TextField(blank=True)
    publicaciones = models.TextField(blank=True)
    apoyos       = models.TextField(blank=True)
    experiencia  = models.TextField(blank=True)

    # Sección 10 – Cinvestav
    unidad      = models.CharField(max_length=120)
    departamento = models.CharField(max_length=120)
    seccion     = models.CharField(max_length=120)
    programa    = models.CharField(max_length=180)
    modalidad   = models.CharField(
        max_length=20,
        choices=[('Presencial', 'Presencial'), ('Híbrida', 'Híbrida'), ('En línea', 'En línea')],
        default='Presencial',
    )

    # Sección 11 – Adscripción
    tutor_propuesto = models.CharField(max_length=180, blank=True)
    director_tesis = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tesistas_asignados', limit_choices_to={'rol': 'director'},
    )
    comentarios     = models.TextField(blank=True)

    # Fechas y notificaciones
    fecha_examen_admision = models.DateTimeField(null=True, blank=True)
    fecha_entrevista = models.DateTimeField(null=True, blank=True)
    fecha_inicio_curso_propedeutico = models.DateTimeField(null=True, blank=True)
    curso_propedeutico_nota = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    curso_propedeutico_aprobado = models.BooleanField(default=False)
    apoyo_solicitado = models.BooleanField(default=False)
    apoyo_autorizado = models.BooleanField(default=False)
    banco_apoyo = models.CharField(max_length=120, blank=True)
    clabe_interbancaria = models.CharField(max_length=18, blank=True)
    solicitud_apoyo_fecha = models.DateTimeField(null=True, blank=True)

    # LIDA / Camunda
    business_key    = models.CharField(max_length=120, unique=True, blank=True)
    camunda_instance_id = models.CharField(max_length=80, blank=True)
    proceso_estado  = models.CharField(max_length=40, default='pendiente')
    rol            = models.CharField(
        max_length=20,
        choices=[
            ('aspirante', 'Aspirante'),
            ('alumno', 'Alumno'),
            ('docente', 'Docente'),
        ],
        default='aspirante',
    )

    # Profile
    profile_photo = models.ImageField(upload_to='profile_photos/%Y/%m/', null=True, blank=True)

    # Control
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AspiranteManager()

    USERNAME_FIELD  = 'usuario'
    REQUIRED_FIELDS = ['correo', 'nombre', 'curp']

    class Meta:
        verbose_name = 'Aspirante'
        verbose_name_plural = 'Aspirantes'

    def __str__(self):
        return f'{self.usuario} – {self.nombre}'


class DocumentoAspirante(models.Model):
    TIPOS = [
        ('cv', 'Currículum vitae'),
        ('titulo', 'Título o comprobante de estudios'),
        ('carta_motivacion', 'Carta de motivos'),
        ('carta_recomendacion', 'Carta de recomendación'),
    ]

    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=30, choices=TIPOS)
    archivo = models.FileField(upload_to='aspirantes/%Y/%m/')
    nombre_original = models.CharField(max_length=255)
    tamano = models.PositiveIntegerField()
    lida_notificado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Documento de aspirante'
        verbose_name_plural = 'Documentos de aspirantes'
        constraints = [
            models.UniqueConstraint(fields=['aspirante', 'tipo'], name='documento_unico_por_tipo'),
        ]

    def __str__(self):
        return f'{self.aspirante.usuario} - {self.get_tipo_display()}'


class ExpedienteDigital(models.Model):
    """Expediente creado automáticamente al aceptar una solicitud."""
    aspirante = models.OneToOneField(Aspirante, on_delete=models.CASCADE, related_name='expediente_digital')
    folio = models.CharField(max_length=40, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, default='activo')

    class Meta:
        verbose_name = 'Expediente digital'
        verbose_name_plural = 'Expedientes digitales'

    def __str__(self):
        return f'{self.folio} - {self.aspirante.nombre}'


class FirmaElectronica(models.Model):
    expediente = models.ForeignKey(ExpedienteDigital, on_delete=models.CASCADE, related_name='firmas')
    firmante = models.ForeignKey(Aspirante, on_delete=models.PROTECT, related_name='firmas_realizadas')
    rol_firmante = models.CharField(max_length=40, default='director')
    huella = models.CharField(max_length=64, unique=True)
    firmado_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('expediente', 'firmante', 'rol_firmante')]

    def __str__(self):
        return f'{self.expediente.folio} - {self.firmante.nombre}'


class CargaAcademica(models.Model):
    ESTADOS = [('borrador','Borrador'), ('en_revision','En revisión'), ('aprobada','Aprobada'), ('publicada','Publicada'), ('rechazada','Rechazada')]
    creador = models.ForeignKey(Aspirante, on_delete=models.PROTECT, related_name='cargas_creadas')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    periodo = models.CharField(max_length=30, blank=True)
    camunda_instance_id = models.CharField(max_length=80, blank=True)
    comentario = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SeguimientoSolicitud(models.Model):
    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='seguimientos')
    estado = models.CharField(max_length=40)
    detalle = models.CharField(max_length=255)
    origen = models.CharField(max_length=80)
    leido = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Seguimiento de solicitud'
        verbose_name_plural = 'Seguimientos de solicitudes'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.aspirante.usuario} - {self.estado}'


class Materia(models.Model):
    clave = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=200)
    # Valor oficial de créditos de la materia. El catálogo inicial utiliza
    # únicamente 4, 5 o 7 créditos.
    creditos = models.PositiveSmallIntegerField(
        default=4,
        choices=[(4, '4 créditos'), (5, '5 créditos'), (7, '7 créditos')],
    )
    profesor = models.CharField(max_length=180, blank=True)
    horario = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'

    def __str__(self):
        return f'{self.clave} - {self.nombre}'

class PeriodoInscripcion(models.Model):
    nombre = models.CharField(max_length=40, unique=True)
    apertura = models.DateTimeField()
    cierre = models.DateTimeField()
    activo = models.BooleanField(default=False)
    def __str__(self): return self.nombre


class AuditoriaSistema(models.Model):
    """Bitácora de cambios administrativos para trazabilidad institucional."""
    actor = models.ForeignKey(Aspirante, on_delete=models.SET_NULL, null=True, blank=True, related_name='auditorias_realizadas')
    accion = models.CharField(max_length=80)
    modelo = models.CharField(max_length=80)
    objeto_id = models.CharField(max_length=80, blank=True)
    datos_anteriores = models.JSONField(default=dict, blank=True)
    datos_nuevos = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ConfiguracionSistema(models.Model):
    """Parámetros institucionales editables por el administrador."""
    clave = models.CharField(max_length=80, unique=True)
    valor = models.TextField(blank=True)
    descripcion = models.CharField(max_length=255, blank=True)
    actualizado_por = models.ForeignKey(Aspirante, on_delete=models.SET_NULL, null=True, blank=True, related_name='configuraciones_actualizadas')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.clave


class Inscripcion(models.Model):
    ESTADOS = [
        ('cursando', 'Cursando'),
        ('aprobada', 'Aprobada'),
        ('reprobada', 'Reprobada'),
    ]

    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='inscripciones')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='inscripciones')
    periodo_inscripcion = models.ForeignKey(
        PeriodoInscripcion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inscripciones',
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='cursando')
    calificacion = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    parcial_1 = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    parcial_2 = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    parcial_3 = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    horario = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        unique_together = [('aspirante', 'materia')]

    def __str__(self):
        return f'{self.aspirante.usuario} - {self.materia.clave} ({self.estado})'

    def estado_academico(self):
        if self.calificacion is None:
            return 'pendiente'
        if self.calificacion < 7:
            return 'reprobada'
        if self.calificacion < 8:
            return 'aprobada_siete'
        return 'aprobada_ocho'


class SolicitudAcademica(models.Model):
    TIPOS = [
        ('historial', 'Historial académico'),
        ('reinscripcion', 'Reinscripción'),
        ('ajuste_materias', 'Ajuste de materias'),
    ]
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
    ]

    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='solicitudes_academicas')
    tipo = models.CharField(max_length=40, choices=TIPOS)
    comentario = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Solicitud académica'
        verbose_name_plural = 'Solicitudes académicas'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.aspirante.usuario} - {self.get_tipo_display()} ({self.estado})'


class ExamenEnLinea(models.Model):
    TIPOS_EXAMEN = [
        ('admision', 'Examen de Admisión'),
        ('seleccion', 'Examen de Selección'),
        ('diagnostico', 'Examen de Diagnóstico'),
        ('otro', 'Otro'),
    ]
    
    ESTADOS_EXAMEN = [
        ('programado', 'Programado'),
        ('iniciado', 'Iniciado'),
        ('completado', 'Completado'),
        ('aprobado', 'Aprobado'),
        ('reprobado', 'Reprobado'),
        ('cancelado', 'Cancelado'),
    ]

    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='examenes_en_linea')
    tipo = models.CharField(max_length=20, choices=TIPOS_EXAMEN)
    titulo = models.CharField(max_length=255, default='Examen en línea')
    descripcion = models.TextField(blank=True)
    
    # LIDA Integration
    business_key = models.CharField(max_length=120, unique=True, blank=True)
    camunda_instance_id = models.CharField(max_length=80, blank=True)
    
    # Fechas
    fecha_programada = models.DateTimeField(null=True, blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    duracion_minutos = models.PositiveIntegerField(default=90)
    
    # Estado y resultados
    estado = models.CharField(max_length=20, choices=ESTADOS_EXAMEN, default='programado')
    calificacion = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    intentos = models.PositiveIntegerField(default=0)
    max_intentos = models.PositiveIntegerField(default=3)
    retroalimentacion = models.TextField(blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Examen en línea'
        verbose_name_plural = 'Exámenes en línea'
        ordering = ['-fecha_programada']

    def __str__(self):
        return f'{self.aspirante.usuario} - {self.get_tipo_display()} ({self.estado})'


class PreguntaExamen(models.Model):
    examen = models.ForeignKey(ExamenEnLinea, on_delete=models.CASCADE, related_name='preguntas')
    texto = models.TextField()
    opciones = models.JSONField(default=list)
    respuesta_correcta = models.CharField(max_length=255)
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['orden', 'id']


class RespuestaExamen(models.Model):
    examen = models.ForeignKey(ExamenEnLinea, on_delete=models.CASCADE, related_name='respuestas')
    pregunta = models.ForeignKey(PreguntaExamen, on_delete=models.CASCADE, related_name='respuestas')
    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='respuestas_examen')
    respuesta = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = [('pregunta', 'aspirante')]


class EntrevistaVirtual(models.Model):
    PROPOSITO_ENTREVISTA = [
        ('admision', 'Entrevista de Admisión'),
        ('seguimiento', 'Seguimiento de progreso'),
        ('tutoria', 'Tutoría académica'),
        ('orientacion', 'Orientación vocacional'),
        ('otro', 'Otro'),
    ]
    
    ESTADOS_ENTREVISTA = [
        ('programada', 'Programada'),
        ('iniciada', 'Iniciada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='entrevistas_virtuales')
    proposito = models.CharField(max_length=20, choices=PROPOSITO_ENTREVISTA)
    titulo = models.CharField(max_length=255, default='Entrevista virtual')
    descripcion = models.TextField(blank=True)
    
    # Fechas y duración
    fecha_programada = models.DateTimeField(null=True, blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    duracion_minutos = models.PositiveIntegerField(default=30)
    
    # Videoconferencia (Jitsi)
    jitsi_room_id = models.CharField(max_length=120, unique=True, blank=True)
    jitsi_room_link = models.URLField(blank=True)
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADOS_ENTREVISTA, default='programada')
    
    # Grabación y contenido
    recording_link = models.URLField(blank=True, help_text='URL de la grabación si está disponible')
    notas_docente = models.TextField(blank=True, help_text='Notas del docente durante la entrevista')
    retroalimentacion = models.TextField(blank=True, help_text='Retroalimentación para el estudiante')
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entrevista virtual'
        verbose_name_plural = 'Entrevistas virtuales'
        ordering = ['-fecha_programada']

    def __str__(self):
        return f'{self.aspirante.usuario} - {self.get_proposito_display()} ({self.estado})'


class EvaluacionColegio(models.Model):
    ESTADOS = [('pendiente', 'Pendiente'), ('en_revision', 'En revisión'), ('favorable', 'Favorable'), ('no_favorable', 'No favorable')]
    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='evaluaciones_colegio')
    evaluador = models.ForeignKey(Aspirante, on_delete=models.SET_NULL, null=True, blank=True, related_name='evaluaciones_realizadas')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    dictamen = models.TextField(blank=True)
    fecha_evaluacion = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


