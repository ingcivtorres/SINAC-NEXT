from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.urls import reverse
from .models import Aspirante, DocumentoAspirante, SeguimientoSolicitud, Materia, Inscripcion, SolicitudAcademica


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
    materia_clave = serializers.CharField(source='materia.clave', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    materia_profesor = serializers.CharField(source='materia.profesor', read_only=True)
    materia_horario = serializers.CharField(source='materia.horario', read_only=True)
    estado_label = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = ['id', 'materia', 'materia_clave', 'materia_nombre', 'materia_profesor', 'materia_horario', 'estado', 'estado_label', 'calificacion', 'horario', 'created_at', 'updated_at', 'color']
        read_only_fields = ['id', 'materia_clave', 'materia_nombre', 'materia_profesor', 'materia_horario', 'estado_label', 'color']

    def get_estado_label(self, obj):
        if obj.calificacion is None:
            return 'Cursando'
        if obj.calificacion < 7:
            return 'Reprobada'
        if obj.calificacion < 8:
            return 'Aprobada con seguimiento'
        return 'Aprobada'

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


class AspiranteDetalleSerializer(serializers.ModelSerializer):
    inscripciones = InscripcionSerializer(many=True, read_only=True)
    solicitudes_academicas = SolicitudAcademicaSerializer(many=True, read_only=True)

    class Meta:
        model = Aspirante
        exclude = ['password', 'groups', 'user_permissions', 'last_login']

    def validate(self, attrs):
        if attrs.get('apoyo_solicitado') and not self.instance.curso_propedeutico_aprobado:
            raise serializers.ValidationError({'apoyo_solicitado': 'Solo puedes solicitar apoyo después de aprobar el curso propedéutico con mínimo 8.'})
        return attrs


class AspiranteAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aspirante
        fields = ['id', 'nombre', 'usuario', 'correo', 'programa', 'unidad',
                  'modalidad', 'proceso_estado', 'created_at']


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
    documentos = DocumentoAspiranteSerializer(many=True, read_only=True)
    seguimientos = SeguimientoSolicitudSerializer(many=True, read_only=True)

    class Meta:
        model = Aspirante
        fields = ['id', 'nombre', 'usuario', 'correo', 'telefono', 'curp', 'rol',
                  'programa', 'unidad', 'departamento', 'seccion', 'modalidad',
                  'ultimo_grado', 'institucion', 'promedio', 'tutor_propuesto',
                  'apoyos', 'comentarios', 'idiomas', 'publicaciones', 'experiencia',
                  'proceso_estado', 'fecha_examen_admision', 'fecha_entrevista',
                  'fecha_inicio_curso_propedeutico', 'curso_propedeutico_nota',
                  'curso_propedeutico_aprobado', 'apoyo_solicitado', 'apoyo_autorizado',
                  'banco_apoyo', 'clabe_interbancaria', 'solicitud_apoyo_fecha',
                  'created_at', 'documentos', 'seguimientos']


class AspiranteCoordinacionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aspirante
        fields = ['programa', 'unidad', 'departamento', 'seccion', 'modalidad',
                  'tutor_propuesto', 'ultimo_grado', 'institucion', 'promedio',
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
        if user.is_staff:
            return 'coordinacion'
        if getattr(user, 'rol', None) == 'docente':
            return 'docente'
        if getattr(user, 'rol', None) == 'alumno':
            return 'alumno'
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
        fields = ['id', 'clave', 'nombre', 'profesor', 'horario']
        read_only_fields = ['id']
