import logging
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import timedelta
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from .roles import rol_efectivo
from .models import (
    Aspirante, DocumentoAspirante, ExpedienteDigital, FirmaElectronica, SeguimientoSolicitud,
    Materia, Inscripcion, SolicitudAcademica, ExamenEnLinea, EntrevistaVirtual,
    EvaluacionColegio, ProyectoTesis, RevisionAntiplagio, JuradoProyecto, DefensaTesis,
)
from .configuracion_sistema import (
    LOCKOUT_DURATION_MINUTES, get_login_attempt_limit, password_meets_policy,
)
from .seguridad import ImagenFirmadaField, url_media

logger = logging.getLogger(__name__)
# Fallos acumulados desde cualquier origen a partir de los cuales la cuenta se bloquea para todos.
FACTOR_BLOQUEO_GLOBAL = 5


class AspiranteRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)

    class Meta:
        model = Aspirante
        fields = [
            'nombre', 'usuario', 'curp', 'correo', 'telefono', 'nacimiento', 'password',
            'estado_actual', 'municipio_actual', 'direccion_actual',
            'estado_permanente', 'municipio_permanente', 'direccion_permanente',
            'nombre_familiar', 'parentesco', 'telefono_familiar',
            'ultimo_grado', 'institucion', 'promedio',
            'idiomas', 'publicaciones', 'apoyos', 'experiencia',
            'unidad', 'departamento', 'seccion', 'programa', 'modalidad',
            'tutor_propuesto', 'comentarios',
        ]

    def validate_promedio(self, value):
        try:
            return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            raise serializers.ValidationError('Ingresa un número válido para el promedio.')

    def validate(self, attrs):
        usuario = (attrs.get('usuario') or '').strip().upper()
        curp = (attrs.get('curp') or '').strip().upper()
        correo = (attrs.get('correo') or '').strip().lower()
        telefono = (attrs.get('telefono') or '').strip()
        password = attrs.get('password') or ''

        if curp and not re.fullmatch(r'[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]', curp):
            raise serializers.ValidationError({'curp': ['La CURP debe tener un formato válido de 18 caracteres.']})
        if correo and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]{2,}', correo):
            raise serializers.ValidationError({'correo': ['Ingresa un correo electrónico válido.']})
        if telefono and not re.fullmatch(r'[0-9]{10}', telefono):
            raise serializers.ValidationError({'telefono': ['El teléfono debe contener exactamente 10 dígitos.']})
        if usuario:
            if Aspirante.objects.filter(usuario__iexact=usuario).exists():
                raise serializers.ValidationError({'usuario': ['Ya existe un aspirante registrado con este usuario.']})
        if curp:
            if Aspirante.objects.filter(curp__iexact=curp).exists():
                raise serializers.ValidationError({'curp': ['Ya existe un aspirante registrado con este CURP.']})
        if correo:
            if Aspirante.objects.filter(correo__iexact=correo).exists():
                raise serializers.ValidationError({'correo': ['Ya existe un aspirante registrado con este correo.']})
        if not password_meets_policy(password):
            raise serializers.ValidationError({'password': ['La contraseña no cumple la política configurada.']})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        curp     = validated_data.get('curp', 'SINCURP').upper()
        programa = validated_data.get('programa', 'BASE').replace(' ', '').upper()
        business_key = f'PREREG-{curp}-{programa}'
        aspirante = Aspirante.objects.create_user(
            **validated_data,
            password=password,
            business_key=business_key,
        )
        return aspirante


class InscripcionSerializer(serializers.ModelSerializer):
    aspirante = serializers.SerializerMethodField()
    materia = serializers.PrimaryKeyRelatedField(read_only=True)
    materia_clave = serializers.CharField(source='materia.clave', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    materia_creditos = serializers.IntegerField(source='materia.creditos', read_only=True)
    materia_profesor = serializers.CharField(source='profesor_asignado', read_only=True)
    materia_horario = serializers.CharField(source='horario_asignado', read_only=True)
    materia_salon = serializers.CharField(source='salon_asignado', read_only=True)
    materia_capacidad = serializers.SerializerMethodField()
    materia_inscritos = serializers.SerializerMethodField()
    periodo_nombre = serializers.CharField(source='periodo_inscripcion.nombre', read_only=True, default=None)
    estado_label = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = ['id', 'materia', 'materia_clave', 'materia_nombre', 'materia_creditos', 'materia_profesor', 'materia_horario', 'materia_salon', 'materia_capacidad', 'materia_inscritos', 'periodo_inscripcion', 'periodo_nombre', 'aspirante', 'estado', 'validacion_servicios', 'estado_label', 'calificacion', 'parcial_1', 'parcial_2', 'parcial_3', 'horario', 'extemporanea', 'motivo_extemporanea', 'registrada_por', 'created_at', 'updated_at', 'color']
        read_only_fields = ['id', 'materia_clave', 'materia_nombre', 'materia_creditos', 'materia_profesor', 'materia_horario', 'materia_salon', 'materia_capacidad', 'materia_inscritos', 'periodo_inscripcion', 'periodo_nombre', 'aspirante', 'estado', 'validacion_servicios', 'estado_label', 'calificacion', 'parcial_1', 'parcial_2', 'parcial_3', 'extemporanea', 'motivo_extemporanea', 'registrada_por', 'created_at', 'updated_at', 'color']

    def get_estado_label(self, obj):
        if obj.calificacion is None:
            return 'Cursando'
        if obj.calificacion < 7:
            return 'Reprobada'
        if obj.calificacion < 8:
            return 'Aprobada con seguimiento'
        return 'Aprobada'

    def get_aspirante(self, obj):
        return {'id': obj.aspirante_id, 'nombre': obj.aspirante.nombre, 'usuario': obj.aspirante.usuario, 'programa': obj.aspirante.programa}

    def get_materia_capacidad(self, obj):
        detalle = obj.detalle_carga
        return detalle.capacidad if detalle else obj.materia.capacidad

    def get_materia_inscritos(self, obj):
        if not obj.periodo_inscripcion_id:
            return obj.materia.inscripciones.filter(periodo_inscripcion__isnull=True).count()
        return obj.materia.inscripciones.filter(periodo_inscripcion_id=obj.periodo_inscripcion_id).count()

    def get_color(self, obj):
        if obj.calificacion is None:
            return 'neutral';
        if obj.calificacion < 7:
            return 'danger';
        if obj.calificacion < 8:
            return 'warning';
        return 'success';


class SolicitudAcademicaSerializer(serializers.ModelSerializer):
    aspirante = serializers.SerializerMethodField()
    tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    resuelta_por_nombre = serializers.CharField(source='resuelta_por.nombre', read_only=True, default=None)

    class Meta:
        model = SolicitudAcademica
        fields = ['id', 'aspirante', 'tipo', 'tipo_label', 'comentario', 'estado', 'estado_label', 'respuesta_revision', 'resuelta_por_nombre', 'created_at', 'updated_at']
        read_only_fields = ['id', 'aspirante', 'tipo_label', 'estado_label', 'respuesta_revision', 'resuelta_por_nombre', 'created_at', 'updated_at']

    def get_aspirante(self, obj):
        return {
            'id': obj.aspirante_id,
            'nombre': obj.aspirante.nombre,
            'usuario': obj.aspirante.usuario,
        }


class ExpedienteDigitalSerializer(serializers.ModelSerializer):
    aspirante_nombre = serializers.CharField(source='aspirante.nombre', read_only=True)
    usuario = serializers.CharField(source='aspirante.usuario', read_only=True)
    matricula = serializers.CharField(source='aspirante.matricula', read_only=True)
    programa = serializers.CharField(source='aspirante.programa', read_only=True)
    departamento = serializers.CharField(source='aspirante.departamento', read_only=True)
    proceso_estado = serializers.CharField(source='aspirante.proceso_estado', read_only=True)

    class Meta:
        model = ExpedienteDigital
        fields = ['id', 'folio', 'fecha_creacion', 'estado', 'aspirante_nombre', 'usuario', 'matricula', 'programa', 'departamento', 'proceso_estado']
        read_only_fields = fields


class FirmaElectronicaSerializer(serializers.ModelSerializer):
    firmante_nombre = serializers.CharField(source='firmante.nombre', read_only=True)
    class Meta:
        model = FirmaElectronica
        fields = ['id', 'rol_firmante', 'huella', 'firmado_at', 'firmante_nombre']
        read_only_fields = fields


class ProyectoTesisSerializer(serializers.ModelSerializer):
    alumno_nombre = serializers.CharField(source='alumno.nombre', read_only=True)
    alumno_matricula = serializers.CharField(source='alumno.matricula', read_only=True)
    alumno_programa = serializers.CharField(source='alumno.programa', read_only=True)
    director_nombre = serializers.CharField(source='director.nombre', read_only=True, allow_null=True)
    director_usuario = serializers.CharField(source='director.usuario', read_only=True, allow_null=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    jurados = serializers.SerializerMethodField()
    defensa = serializers.SerializerMethodField()
    revisiones_antiplagio = serializers.SerializerMethodField()

    class Meta:
        model = ProyectoTesis
        fields = [
            'id', 'alumno', 'alumno_nombre', 'alumno_matricula', 'alumno_programa',
            'director', 'director_nombre', 'director_usuario', 'titulo', 'resumen',
            'linea_investigacion', 'objetivos', 'metodologia', 'comentarios_revision',
            'avance_porcentaje', 'estado', 'estado_label', 'fecha_presentacion', 'jurados', 'defensa',
            'revisiones_antiplagio', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'alumno_nombre', 'alumno_matricula', 'alumno_programa',
            'director_nombre', 'director_usuario', 'estado_label', 'jurados', 'defensa',
            'revisiones_antiplagio', 'created_at', 'updated_at',
        ]

    def get_revisiones_antiplagio(self, obj):
        return [
            {
                'id': revision.id,
                'proveedor': revision.proveedor,
                'nombre_original': revision.nombre_original,
                'porcentaje_similitud': float(revision.porcentaje_similitud),
                'estado': revision.estado,
                'observaciones': revision.observaciones,
                'created_at': revision.created_at,
            }
            for revision in obj.revisiones_antiplagio.all()[:5]
        ]

    def validate_titulo(self, value):
        value = (value or '').strip()
        if len(value) < 10:
            raise serializers.ValidationError('El título debe tener al menos 10 caracteres.')
        return value

    def validate_resumen(self, value):
        value = (value or '').strip()
        if len(value) < 30:
            raise serializers.ValidationError('El resumen debe tener al menos 30 caracteres.')
        return value

    def validate_director(self, value):
        if value is not None and (str(getattr(value, 'rol', '')).lower() not in {'director', 'director de tesis'} or value.is_staff):
            raise serializers.ValidationError('El director seleccionado debe tener el rol Director de Tesis.')
        return value

    def get_jurados(self, obj):
        jurados = obj.jurados.select_related('jurado').all()
        return JuradoProyectoSerializer(jurados, many=True).data

    def get_defensa(self, obj):
        defensa = getattr(obj, 'defensa_tesis', None)
        if not defensa:
            return None
        return DefensaTesisSerializer(defensa).data


class JuradoProyectoSerializer(serializers.ModelSerializer):
    jurado_nombre = serializers.CharField(source='jurado.nombre', read_only=True)
    jurado_correo = serializers.CharField(source='jurado.correo', read_only=True)
    jurado_usuario = serializers.CharField(source='jurado.usuario', read_only=True)
    rol_label = serializers.CharField(source='get_rol_display', read_only=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = JuradoProyecto
        fields = [
            'id', 'proyecto', 'jurado', 'jurado_nombre', 'jurado_correo', 'jurado_usuario',
            'rol', 'rol_label', 'orden', 'estado', 'estado_label', 'observaciones', 'fecha_confirmacion', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'jurado_nombre', 'jurado_correo', 'jurado_usuario', 'rol_label', 'estado_label', 'created_at', 'updated_at']


class DefensaTesisSerializer(serializers.ModelSerializer):
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    modalidad_label = serializers.CharField(source='get_modalidad_display', read_only=True)

    class Meta:
        model = DefensaTesis
        fields = ['id', 'proyecto', 'fecha', 'lugar', 'modalidad', 'modalidad_label', 'enlace_virtual', 'estado', 'estado_label', 'observaciones', 'calificacion_final', 'acta_url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'modalidad_label', 'estado_label', 'created_at', 'updated_at']


class RevisionAntiplagioSerializer(serializers.ModelSerializer):
    proyecto = serializers.PrimaryKeyRelatedField(read_only=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = RevisionAntiplagio
        fields = ['id', 'proyecto', 'proveedor', 'nombre_original', 'porcentaje_similitud', 'estado', 'estado_label', 'observaciones', 'resultados', 'archivo_url', 'created_at', 'updated_at']

    def get_archivo_url(self, obj):
        return url_media(obj.archivo)


class AspiranteDetalleSerializer(serializers.ModelSerializer):
    inscripciones = InscripcionSerializer(many=True, read_only=True)
    solicitudes_academicas = SolicitudAcademicaSerializer(many=True, read_only=True)
    expediente_digital = ExpedienteDigitalSerializer(read_only=True)
    profile_photo = ImagenFirmadaField(read_only=True)

    class Meta:
        model = Aspirante
        exclude = ['password', 'groups', 'user_permissions', 'last_login', 'login_failed_attempts', 'login_locked_until']
        read_only_fields = [
            'usuario', 'matricula', 'curp', 'rol', 'is_active', 'is_staff', 'is_superuser',
            'business_key', 'camunda_instance_id', 'proceso_estado', 'director_tesis',
            'numero_periodo_actual', 'fecha_examen_admision', 'fecha_entrevista',
            'fecha_inicio_curso_propedeutico', 'curso_propedeutico_nota', 'curso_propedeutico_aprobado',
            'apoyo_autorizado', 'profile_photo', 'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        if attrs.get('apoyo_solicitado') and not self.instance.curso_propedeutico_aprobado:
            raise serializers.ValidationError({'apoyo_solicitado': 'Solo puedes solicitar apoyo después de aprobar el curso propedéutico con mínimo 8.'})
        return attrs


class PerfilAspiranteSerializer(serializers.ModelSerializer):
    profile_photo = ImagenFirmadaField(required=False, allow_null=True)

    class Meta:
        model = Aspirante
        fields = ['nombre', 'correo', 'telefono', 'matricula', 'profile_photo']
        read_only_fields = ['matricula']

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('El nombre no puede estar vacío.')
        return value

    def validate_telefono(self, value):
        value = value.strip()
        digitos = sum(caracter.isdigit() for caracter in value)
        if not re.fullmatch(r'[\d\s()+-]+', value) or not 10 <= digitos <= 15:
            raise serializers.ValidationError('Captura un teléfono válido de 10 a 15 dígitos.')
        return value

    def validate_correo(self, value):
        if Aspirante.objects.filter(correo__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('Ese correo ya está registrado.')
        return value


class AspiranteAdminSerializer(serializers.ModelSerializer):
    profile_photo = ImagenFirmadaField(read_only=True)
    class Meta:
        model = Aspirante
        fields = ['id', 'nombre', 'usuario', 'matricula', 'correo', 'profile_photo', 'rol', 'programa', 'unidad',
                  'modalidad', 'proceso_estado', 'is_active', 'created_at']


class DocumentoAspiranteSerializer(serializers.ModelSerializer):
    tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
    archivo = serializers.SerializerMethodField()

    def get_archivo(self, obj):
        return reverse('documento-descarga', args=[obj.pk])

    class Meta:
        model = DocumentoAspirante
        fields = ['id', 'tipo', 'tipo_label', 'archivo', 'nombre_original', 'tamano',
                  'lida_notificado', 'revisado', 'revisado_en', 'updated_at']
        read_only_fields = fields


class SeguimientoSolicitudSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeguimientoSolicitud
        fields = ['id', 'estado', 'detalle', 'origen', 'created_at', 'leido']


class AspiranteCoordinacionSerializer(serializers.ModelSerializer):
    profile_photo = ImagenFirmadaField(read_only=True)
    director_tesis_nombre = serializers.CharField(source='director_tesis.nombre', read_only=True, allow_null=True)
    documentos = DocumentoAspiranteSerializer(many=True, read_only=True)
    seguimientos = SeguimientoSolicitudSerializer(many=True, read_only=True)
    expediente_digital = ExpedienteDigitalSerializer(read_only=True)

    class Meta:
        model = Aspirante
        fields = ['id', 'nombre', 'usuario', 'matricula', 'numero_periodo_actual', 'correo', 'telefono', 'profile_photo', 'curp', 'rol',
                  'programa', 'unidad', 'departamento', 'seccion', 'modalidad',
                  'ultimo_grado', 'institucion', 'promedio', 'tutor_propuesto', 'director_tesis', 'director_tesis_nombre',
                  'apoyos', 'comentarios', 'idiomas', 'publicaciones', 'experiencia',
                  'proceso_estado', 'fecha_examen_admision', 'fecha_entrevista',
                  'fecha_inicio_curso_propedeutico', 'curso_propedeutico_nota',
                  'curso_propedeutico_aprobado', 'apoyo_solicitado', 'apoyo_autorizado',
                  'banco_apoyo', 'clabe_interbancaria', 'solicitud_apoyo_fecha',
                  'created_at', 'documentos', 'seguimientos', 'expediente_digital']


class AspiranteCoordinacionUpdateSerializer(serializers.ModelSerializer):
    def validate_director_tesis(self, value):
        if value is not None and (value.rol != 'director' or value.is_staff):
            raise serializers.ValidationError('El usuario seleccionado no tiene rol de Director de Tesis.')
        if self.instance is not None and value is not None and value.pk == self.instance.pk:
            raise serializers.ValidationError('Un alumno no puede ser su propio director de tesis.')
        return value

    class Meta:
        model = Aspirante
        fields = ['programa', 'unidad', 'departamento', 'seccion', 'modalidad', 'numero_periodo_actual',
                  'tutor_propuesto', 'director_tesis', 'ultimo_grado', 'institucion', 'promedio',
                  'idiomas', 'publicaciones', 'apoyos', 'comentarios', 'proceso_estado',
                  'fecha_examen_admision', 'fecha_entrevista', 'fecha_inicio_curso_propedeutico',
                  'curso_propedeutico_nota', 'curso_propedeutico_aprobado',
                  'apoyo_solicitado', 'apoyo_autorizado', 'banco_apoyo', 'clabe_interbancaria']

    def validate_numero_periodo_actual(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError('El número de semestre o cuatrimestre debe ser mayor que cero.')
        return value


class InicioSesionSerializer(TokenObtainPairSerializer):
    """Incluye el rol calculado en servidor para que el frontend no lo infiera."""
    usuario = serializers.CharField(write_only=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['rol'] = cls.obtener_rol(user)
        return token

    @staticmethod
    def obtener_rol(user):
        return rol_efectivo(user)

    def _origen(self):
        request = self.context.get('request')
        return AnonRateThrottle().get_ident(request) if request else 'desconocido'

    @staticmethod
    def get_user_by_identifier(identifier):
        value = (identifier or '').strip()
        if not value:
            return None
        return Aspirante.objects.filter(
            Q(usuario__iexact=value) | Q(correo__iexact=value)
        ).order_by('id').first()

    def validate(self, attrs):
        identifier = (attrs.get('usuario') or '').strip()
        password = attrs.get('password')

        if not identifier or not password:
            raise AuthenticationFailed('Credenciales inválidas.')

        user = self.get_user_by_identifier(identifier)
        if user is None or not user.is_active:
            raise AuthenticationFailed('Credenciales inválidas.')

        invalid_credentials = False
        now = timezone.now()
        limite = get_login_attempt_limit()
        clave_origen = f'login_fallos:{user.pk}:{self._origen()}'
        with transaction.atomic():
            user = Aspirante.objects.select_for_update().filter(pk=user.pk).first()
            bloqueada = bool(user and user.login_locked_until and user.login_locked_until > now)
            if user is None or not user.is_active:
                invalid_credentials = True
            elif bloqueada and (cache.get(clave_origen) or user.login_failed_attempts >= limite * FACTOR_BLOQUEO_GLOBAL):
                invalid_credentials = True
            else:
                had_login_failures = bool(user.login_failed_attempts or user.login_locked_until)
                if user.login_locked_until and not bloqueada:
                    user.login_failed_attempts = 0
                    user.login_locked_until = None
                if not user.check_password(password):
                    user.login_failed_attempts += 1
                    cache.set(clave_origen, (cache.get(clave_origen) or 0) + 1, LOCKOUT_DURATION_MINUTES * 60)
                    if user.login_failed_attempts >= limite and not bloqueada:
                        user.login_locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                        logger.warning('Cuenta %s bloqueada temporalmente por intentos fallidos.', user.pk)
                    user.save(update_fields=['login_failed_attempts', 'login_locked_until', 'updated_at'])
                    invalid_credentials = True
                elif had_login_failures:
                    user.login_failed_attempts = 0
                    user.login_locked_until = None
                    user.save(update_fields=['login_failed_attempts', 'login_locked_until', 'updated_at'])
                    cache.delete(clave_origen)

        if invalid_credentials:
            raise AuthenticationFailed('Credenciales inválidas.')

        self.user = user
        refresh = RefreshToken.for_user(user)
        refresh['rol'] = self.obtener_rol(user)

        role = self.obtener_rol(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'role': role,
            'rol': role,
        }


class MateriaSerializer(serializers.ModelSerializer):
    salon_label = serializers.CharField(source='get_salon_display', read_only=True)
    inscritos = serializers.IntegerField(source='inscripciones.count', read_only=True)

    class Meta:
        model = Materia
        fields = ['id', 'clave', 'nombre', 'categoria', 'lgacs', 'creditos', 'profesor', 'horario', 'salon', 'salon_label', 'capacidad', 'inscritos']
        read_only_fields = ['id']

    def validate_creditos(self, value):
        if value not in (4, 5, 7):
            raise serializers.ValidationError('Los créditos permitidos son 4, 5 o 7.')
        return value


class ExamenEnLineaSerializer(serializers.ModelSerializer):
    aspirante = serializers.SerializerMethodField()
    tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    color = serializers.SerializerMethodField()
    preguntas = serializers.SerializerMethodField()

    def get_aspirante(self, obj):
        return {
            'id': obj.aspirante_id,
            'nombre': obj.aspirante.nombre,
            'usuario': obj.aspirante.usuario,
        }

    def get_preguntas(self, obj):
        return [{'id': p.id, 'texto': p.texto, 'opciones': p.opciones, 'orden': p.orden} for p in obj.preguntas.all()]

    class Meta:
        model = ExamenEnLinea
        fields = ['id', 'aspirante', 'tipo', 'tipo_label', 'titulo', 'descripcion', 'business_key',
                  'camunda_instance_id', 'fecha_programada', 'fecha_inicio', 'fecha_fin',
                  'duracion_minutos', 'estado', 'estado_label', 'calificacion', 'intentos',
                  'max_intentos', 'retroalimentacion', 'evaluador', 'color', 'preguntas', 'created_at', 'updated_at']
        read_only_fields = ['id', 'tipo_label', 'estado_label', 'evaluador', 'color', 'created_at', 'updated_at']

    def get_color(self, obj):
        """Return color badge based on exam state and score."""
        if obj.estado == 'programado':
            return 'info'
        if obj.estado in ['aprobado']:
            return 'success'
        if obj.estado in ['reprobado']:
            return 'danger'
        if obj.estado in ['iniciado', 'completado']:
            return 'warning'
        if obj.estado == 'cancelado':
            return 'secondary'
        return 'neutral'


class CalificacionExamenDocenteSerializer(serializers.Serializer):
    calificacion = serializers.DecimalField(
        max_digits=4, decimal_places=2, min_value=Decimal('0'), max_value=Decimal('10'),
    )
    retroalimentacion = serializers.CharField(required=False, allow_blank=True)


class EntrevistaVirtualSerializer(serializers.ModelSerializer):
    aspirante = serializers.SerializerMethodField()
    proposito_label = serializers.CharField(source='get_proposito_display', read_only=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    color = serializers.SerializerMethodField()
    tiempo_restante = serializers.SerializerMethodField()

    class Meta:
        model = EntrevistaVirtual
        fields = ['id', 'aspirante', 'docente', 'proposito', 'proposito_label', 'titulo', 'descripcion',
                  'fecha_programada', 'fecha_inicio', 'fecha_fin', 'duracion_minutos',
                  'jitsi_room_id', 'jitsi_room_link', 'estado', 'estado_label',
                  'recording_link', 'notas_docente', 'retroalimentacion', 'color',
                  'tiempo_restante', 'created_at', 'updated_at']
        read_only_fields = ['id', 'docente', 'proposito_label', 'estado_label', 'color', 'tiempo_restante',
                           'jitsi_room_id', 'jitsi_room_link', 'created_at', 'updated_at']

    def get_color(self, obj):
        """Return color badge based on interview state."""
        if obj.estado == 'programada':
            return 'info'
        if obj.estado == 'iniciada':
            return 'warning'
        if obj.estado == 'completada':
            return 'success'
        if obj.estado == 'cancelada':
            return 'secondary'
        return 'neutral'

    def get_aspirante(self, obj):
        return {
            'id': obj.aspirante_id,
            'nombre': obj.aspirante.nombre,
            'usuario': obj.aspirante.usuario,
            'programa': obj.aspirante.programa,
        }

    def get_tiempo_restante(self, obj):
        """Calculate remaining time until interview starts."""
        if obj.estado == 'programada' and obj.fecha_programada:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            delta = obj.fecha_programada.replace(tzinfo=timezone.utc) - now
            if delta.total_seconds() > 0:
                return int(delta.total_seconds() / 60)  # minutes
        return 0
class EvaluacionColegioSerializer(serializers.ModelSerializer):
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    aspirante_nombre = serializers.CharField(source='aspirante.nombre', read_only=True)
    aspirante_usuario = serializers.CharField(source='aspirante.usuario', read_only=True)
    evaluador_nombre = serializers.CharField(source='evaluador.nombre', read_only=True, default=None)
    class Meta:
        model = EvaluacionColegio
        fields = ['id', 'aspirante', 'aspirante_nombre', 'aspirante_usuario', 'evaluador', 'evaluador_nombre', 'estado', 'estado_label', 'dictamen', 'fecha_evaluacion', 'created_at', 'updated_at']
        read_only_fields = ['id', 'estado_label', 'created_at', 'updated_at']
