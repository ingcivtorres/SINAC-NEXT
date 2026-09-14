from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
import re
from .models import Aspirante, DocumentoAspirante, ExpedienteDigital, FirmaElectronica, SeguimientoSolicitud, Materia, Inscripcion, SolicitudAcademica, ExamenEnLinea, EntrevistaVirtual, EvaluacionColegio


class AspiranteRegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Aspirante
        exclude = ['business_key', 'proceso_estado', 'is_active', 'is_staff',
                   'last_login', 'groups', 'user_permissions', 'created_at', 'updated_at']

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
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'[0-9]', password):
            raise serializers.ValidationError({'password': ['La contraseña debe tener 8 caracteres, mayúscula, minúscula y número.']})

        if usuario:
            if Aspirante.objects.filter(usuario__iexact=usuario).exists():
                raise serializers.ValidationError({'usuario': ['Ya existe un aspirante registrado con este usuario.']})
        if curp:
            if Aspirante.objects.filter(curp__iexact=curp).exists():
                raise serializers.ValidationError({'curp': ['Ya existe un aspirante registrado con este CURP.']})
        if correo:
            if Aspirante.objects.filter(correo__iexact=correo).exists():
                raise serializers.ValidationError({'correo': ['Ya existe un aspirante registrado con este correo.']})

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
    materia_profesor = serializers.CharField(source='materia.profesor', read_only=True)
    materia_horario = serializers.CharField(source='materia.horario', read_only=True)
    periodo_nombre = serializers.CharField(source='periodo_inscripcion.nombre', read_only=True, default=None)
    estado_label = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = ['id', 'materia', 'materia_clave', 'materia_nombre', 'materia_creditos', 'materia_profesor', 'materia_horario', 'periodo_inscripcion', 'periodo_nombre', 'aspirante', 'estado', 'estado_label', 'calificacion', 'parcial_1', 'parcial_2', 'parcial_3', 'horario', 'created_at', 'updated_at', 'color']
        read_only_fields = ['id', 'materia_clave', 'materia_nombre', 'materia_creditos', 'materia_profesor', 'materia_horario', 'periodo_inscripcion', 'periodo_nombre', 'estado_label', 'color']

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

    def get_color(self, obj):
        if obj.calificacion is None:
            return 'neutral';
        if obj.calificacion < 7:
            return 'danger';
        if obj.calificacion < 8:
            return 'warning';
        return 'success';


class SolicitudAcademicaSerializer(serializers.ModelSerializer):
    tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = SolicitudAcademica
        fields = ['id', 'tipo', 'tipo_label', 'comentario', 'estado', 'estado_label', 'created_at', 'updated_at']
        read_only_fields = ['id', 'tipo_label', 'estado_label', 'created_at', 'updated_at']


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


class ExpedienteDigitalUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpedienteDigital
        fields = ['estado']

class FirmaElectronicaSerializer(serializers.ModelSerializer):
    firmante_nombre = serializers.CharField(source='firmante.nombre', read_only=True)
    class Meta:
        model = FirmaElectronica
        fields = ['id', 'rol_firmante', 'huella', 'firmado_at', 'firmante_nombre']
        read_only_fields = fields


class AspiranteDetalleSerializer(serializers.ModelSerializer):
    inscripciones = InscripcionSerializer(many=True, read_only=True)
    solicitudes_academicas = SolicitudAcademicaSerializer(many=True, read_only=True)
    expediente_digital = ExpedienteDigitalSerializer(read_only=True)

    class Meta:
        model = Aspirante
        exclude = ['password', 'groups', 'user_permissions', 'last_login']

    def validate(self, attrs):
        if attrs.get('apoyo_solicitado') and not self.instance.curso_propedeutico_aprobado:
            raise serializers.ValidationError({'apoyo_solicitado': 'Solo puedes solicitar apoyo después de aprobar el curso propedéutico con mínimo 8.'})
        return attrs


class PerfilAspiranteSerializer(serializers.ModelSerializer):
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Aspirante
        fields = ['nombre', 'correo', 'telefono', 'matricula', 'profile_photo']

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('El nombre no puede estar vacío.')
        return value

    def validate_correo(self, value):
        if Aspirante.objects.filter(correo__iexact=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError('Ese correo ya está registrado.')
        return value


class AspiranteAdminSerializer(serializers.ModelSerializer):
    profile_photo = serializers.ImageField(read_only=True)
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
                  'lida_notificado', 'updated_at']
        read_only_fields = fields


class SeguimientoSolicitudSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeguimientoSolicitud
        fields = ['id', 'estado', 'detalle', 'origen', 'created_at', 'leido']


class AspiranteCoordinacionSerializer(serializers.ModelSerializer):
    profile_photo = serializers.ImageField(read_only=True)
    director_tesis_nombre = serializers.CharField(source='director_tesis.nombre', read_only=True, allow_null=True)
    documentos = DocumentoAspiranteSerializer(many=True, read_only=True)
    seguimientos = SeguimientoSolicitudSerializer(many=True, read_only=True)
    expediente_digital = ExpedienteDigitalSerializer(read_only=True)

    class Meta:
        model = Aspirante
        fields = ['id', 'nombre', 'usuario', 'matricula', 'correo', 'telefono', 'profile_photo', 'curp', 'rol',
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
        fields = ['programa', 'unidad', 'departamento', 'seccion', 'modalidad',
                  'tutor_propuesto', 'director_tesis', 'ultimo_grado', 'institucion', 'promedio',
                  'idiomas', 'publicaciones', 'apoyos', 'comentarios', 'proceso_estado',
                  'fecha_examen_admision', 'fecha_entrevista', 'fecha_inicio_curso_propedeutico',
                  'curso_propedeutico_nota', 'curso_propedeutico_aprobado',
                  'apoyo_solicitado', 'apoyo_autorizado', 'banco_apoyo', 'clabe_interbancaria']


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
        if user.is_superuser:
            return 'admin'
        if str(getattr(user, 'rol', '')).strip().lower() in ('admin', 'administrador'):
            return 'admin'
        if user.is_staff:
            return 'coordinacion'
        if str(getattr(user, 'rol', '')).strip().lower() in ('director', 'director de tesis'):
            return 'director'
        if str(getattr(user, 'rol', '')).strip().lower() in ('servicios', 'servicios_escolares', 'servicios escolares'):
            return 'servicios'
        if getattr(user, 'rol', None) == 'docente':
            return 'docente'
        if getattr(user, 'rol', None) == 'alumno':
            return 'alumno'
        if getattr(user, 'rol', None) == 'director':
            return 'director'
        return 'aspirante'

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
            raise AuthenticationFailed('No active account found with the given credentials.')
        if not user.check_password(password):
            raise AuthenticationFailed('No active account found with the given credentials.')

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
    class Meta:
        model = Materia
        fields = ['id', 'clave', 'nombre', 'creditos', 'profesor', 'horario']
        read_only_fields = ['id']

    def validate_creditos(self, value):
        if value not in (4, 5, 7):
            raise serializers.ValidationError('Los créditos permitidos son 4, 5 o 7.')
        return value


class ExamenEnLineaSerializer(serializers.ModelSerializer):
    tipo_label = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    color = serializers.SerializerMethodField()
    preguntas = serializers.SerializerMethodField()

    def get_preguntas(self, obj):
        return [{'id': p.id, 'texto': p.texto, 'opciones': p.opciones, 'orden': p.orden} for p in obj.preguntas.all()]

    class Meta:
        model = ExamenEnLinea
        fields = ['id', 'tipo', 'tipo_label', 'titulo', 'descripcion', 'business_key',
                  'camunda_instance_id', 'fecha_programada', 'fecha_inicio', 'fecha_fin',
                  'duracion_minutos', 'estado', 'estado_label', 'calificacion', 'intentos',
                  'max_intentos', 'retroalimentacion', 'color', 'preguntas', 'created_at', 'updated_at']
        read_only_fields = ['id', 'tipo_label', 'estado_label', 'color', 'created_at', 'updated_at']

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


class EntrevistaVirtualSerializer(serializers.ModelSerializer):
    proposito_label = serializers.CharField(source='get_proposito_display', read_only=True)
    estado_label = serializers.CharField(source='get_estado_display', read_only=True)
    color = serializers.SerializerMethodField()
    tiempo_restante = serializers.SerializerMethodField()

    class Meta:
        model = EntrevistaVirtual
        fields = ['id', 'proposito', 'proposito_label', 'titulo', 'descripcion',
                  'fecha_programada', 'fecha_inicio', 'fecha_fin', 'duracion_minutos',
                  'jitsi_room_id', 'jitsi_room_link', 'estado', 'estado_label',
                  'recording_link', 'notas_docente', 'retroalimentacion', 'color',
                  'tiempo_restante', 'created_at', 'updated_at']
        read_only_fields = ['id', 'proposito_label', 'estado_label', 'color', 'tiempo_restante',
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
