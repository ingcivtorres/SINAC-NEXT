"""Vistas del portal del aspirante: registro, perfil, documentos, apoyos, exámenes y entrevistas."""
import logging
from datetime import datetime, time, timedelta
from decimal import Decimal
from django.http import FileResponse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

from .models import Aspirante, DocumentoAspirante, ExamenEnLinea, EntrevistaVirtual, EvaluacionColegio, RespuestaExamen
from . import camunda
from .serializers import (
    AspiranteRegistroSerializer,
    AspiranteDetalleSerializer,
    PerfilAspiranteSerializer,
    DocumentoAspiranteSerializer,
    SeguimientoSolicitudSerializer,
    ExamenEnLineaSerializer,
    EntrevistaVirtualSerializer,
    EvaluacionColegioSerializer,
)

from .roles import bloquear_si_egresado, es_gestion_academica
from .seguridad import nombre_archivo_seguro, validar_imagen, validar_pdf
from .views import (
    MAX_DOCUMENTO_BYTES,
    _obtener_tamano_archivo,
    _registrar_seguimiento,
    _iniciar_proceso_lida,
    _notificar_documento_lida,
)

logger = logging.getLogger(__name__)


class PreregistroCreateView(generics.CreateAPIView):
    queryset = Aspirante.objects.all()
    serializer_class = AspiranteRegistroSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle]
    throttle_scope = 'registro'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        aspirante = serializer.save()
        _registrar_seguimiento(aspirante, 'pendiente', 'Pre-registro recibido correctamente.', 'Portal Aspirantes')
        camunda_id = _iniciar_proceso_lida(aspirante)
        if camunda_id:
            aspirante.proceso_estado = 'iniciado'
            aspirante.camunda_instance_id = camunda_id
            aspirante.save(update_fields=['proceso_estado', 'camunda_instance_id'])
            _registrar_seguimiento(aspirante, 'iniciado', 'Proceso LIDA iniciado en Camunda.', 'LIDA / Camunda')
        refresh = RefreshToken.for_user(aspirante)
        return Response({
            'mensaje':        'Pre-registro creado correctamente.',
            'business_key':   aspirante.business_key,
            'proceso_estado': aspirante.proceso_estado,
            'camunda_id':     camunda_id,
            'access':         str(refresh.access_token),
            'refresh':        str(refresh),
        }, status=status.HTTP_201_CREATED)


class MiPerfilView(generics.RetrieveUpdateAPIView):
    serializer_class = AspiranteDetalleSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'put', 'head', 'options']
    CAMPOS_EDITABLES = [
        'nombre', 'correo', 'telefono',
        'estado_actual', 'municipio_actual', 'direccion_actual',
        'estado_permanente', 'municipio_permanente', 'direccion_permanente',
        'nombre_familiar', 'parentesco', 'telefono_familiar',
        'ultimo_grado', 'institucion', 'promedio', 'idiomas',
        'publicaciones', 'apoyos', 'experiencia', 'tutor_propuesto', 'comentarios',
    ]

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        aspirante = self.get_object()
        foto = request.FILES.get('profile_photo')
        error_foto = validar_imagen(foto)
        if error_foto:
            return Response({'profile_photo': error_foto}, status=status.HTTP_400_BAD_REQUEST)
        datos = {campo: request.data.get(campo) for campo in self.CAMPOS_EDITABLES if request.data.get(campo) not in (None, '')}
        serializer = AspiranteDetalleSerializer(aspirante, data=datos, partial=True)
        serializer.is_valid(raise_exception=True)
        correo = serializer.validated_data.get('correo')
        if correo and Aspirante.objects.filter(correo__iexact=correo).exclude(pk=aspirante.pk).exists():
            return Response({'correo': 'Ese correo ya está registrado.'}, status=status.HTTP_400_BAD_REQUEST)
        aspirante = serializer.save()
        if foto:
            aspirante.profile_photo = foto
            aspirante.save(update_fields=['profile_photo', 'updated_at'])
        return Response(AspiranteDetalleSerializer(aspirante).data)


class PerfilAspiranteView(APIView):
    """Actualiza datos editables del perfil y la foto mediante multipart/form-data."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    max_photo_size = 5 * 1024 * 1024

    @staticmethod
    def _puede_editar(user):
        rol = str(getattr(user, 'rol', '')).strip().casefold()
        return not user.is_superuser and rol in {
            'aspirante', 'alumno', 'docente', 'director', 'director de tesis', 'coordinacion',
        }

    def get(self, request):
        if not self._puede_editar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(PerfilAspiranteSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        return self._update(request)

    def put(self, request):
        return self._update(request)

    def _update(self, request):
        if not self._puede_editar(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        error_foto = validar_imagen(request.FILES.get('profile_photo'), self.max_photo_size)
        if error_foto:
            return Response({'profile_photo': error_foto}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PerfilAspiranteSerializer(request.user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SeguimientoAspiranteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff or getattr(request.user, 'rol', '') not in {'aspirante', 'alumno'}:
            return Response(status=status.HTTP_403_FORBIDDEN)
        aspirante = request.user
        seguimientos = aspirante.seguimientos.all()[:50]
        return Response({
            'estado_actual': aspirante.proceso_estado,
            'business_key': aspirante.business_key,
            'camunda_instance_id': aspirante.camunda_instance_id or None,
            'eventos': SeguimientoSolicitudSerializer(seguimientos, many=True).data,
            'no_leidas': aspirante.seguimientos.filter(leido=False).count(),
        })


class MisEntrevistasView(APIView):
    """API para que los alumnos vean sus entrevistas virtuales."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Obtener las entrevistas virtuales del alumno."""
        try:
            aspirante = request.user
            if not isinstance(aspirante, Aspirante):
                return Response(
                    {'error': 'Usuario no válido'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Obtener entrevistas del aspirante
            entrevistas = EntrevistaVirtual.objects.filter(
                aspirante=aspirante
            ).order_by('-fecha_programada')

            # Estadísticas
            entrevistas_total = entrevistas.count()
            entrevistas_programadas = entrevistas.filter(estado='programada').count()
            entrevistas_iniciadas = entrevistas.filter(estado='iniciada').count()
            entrevistas_completadas = entrevistas.filter(estado='completada').count()

            datos = EntrevistaVirtualSerializer(entrevistas, many=True).data
            for entrevista in datos:
                entrevista.pop('notas_docente', None)
            return Response({
                'entrevistas': datos,
                'resumen': {
                    'entrevistas_total': entrevistas_total,
                    'entrevistas_programadas': entrevistas_programadas,
                    'entrevistas_iniciadas': entrevistas_iniciadas,
                    'entrevistas_completadas': entrevistas_completadas,
                }
            })
        except Exception:
            logger.exception('Error al consultar las entrevistas del alumno %s', request.user.pk)
            return Response(
                {'error': 'No se pudieron cargar las entrevistas virtuales.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MisExamenesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        examenes = request.user.examenes_en_linea.all().order_by('-fecha_programada')
        data = ExamenEnLineaSerializer(examenes, many=True).data
        for item in data:
            if item['estado'] != 'iniciado':
                item['preguntas'] = []
            item['total_preguntas'] = next((e.preguntas.count() for e in examenes if e.pk == item['id']), 0)
        return Response({'examenes': data, 'total': len(data)})

    def post(self, request):
        bloqueo = bloquear_si_egresado(request.user)
        if bloqueo:
            return bloqueo
        try: examen = request.user.examenes_en_linea.get(pk=request.data.get('id'))
        except ExamenEnLinea.DoesNotExist: return Response({'detail': 'Examen no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if examen.tipo == 'predoctoral': return Response({'detail': 'El examen predoctoral debe ser evaluado por tu Director de Tesis o Coordinación Académica.'}, status=status.HTTP_400_BAD_REQUEST)
        if examen.estado != 'programado': return Response({'detail': 'Este examen no está disponible.'}, status=status.HTTP_400_BAD_REQUEST)
        if examen.fecha_programada and examen.fecha_programada > timezone.now(): return Response({'detail': 'Este examen aún no está disponible. Revisa la fecha programada.'}, status=status.HTTP_400_BAD_REQUEST)
        if examen.intentos >= examen.max_intentos: return Response({'detail': 'Ya no tienes intentos disponibles.'}, status=status.HTTP_400_BAD_REQUEST)
        if not examen.preguntas.exists(): return Response({'detail': 'Este examen todavía no tiene preguntas cargadas.'}, status=status.HTTP_400_BAD_REQUEST)
        examen.estado = 'iniciado'; examen.fecha_inicio = timezone.now(); examen.intentos += 1; examen.save(update_fields=['estado','fecha_inicio','intentos','updated_at'])
        return Response(ExamenEnLineaSerializer(examen).data)

    def put(self, request):
        bloqueo = bloquear_si_egresado(request.user)
        if bloqueo:
            return bloqueo
        try: examen = request.user.examenes_en_linea.get(pk=request.data.get('id'))
        except ExamenEnLinea.DoesNotExist: return Response({'detail': 'Examen no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if examen.tipo == 'predoctoral': return Response({'detail': 'El examen predoctoral debe ser evaluado por tu Director de Tesis o Coordinación Académica.'}, status=status.HTTP_400_BAD_REQUEST)
        if examen.estado != 'iniciado': return Response({'detail': 'El examen no está iniciado.'}, status=status.HTTP_400_BAD_REQUEST)
        limite = (examen.fecha_inicio or timezone.now()) + timedelta(minutes=examen.duracion_minutos + 2)
        tiempo_agotado = timezone.now() > limite
        respuestas = request.data.get('respuestas', {})
        if not isinstance(respuestas, dict): return Response({'detail': 'Formato de respuestas inválido.'}, status=status.HTTP_400_BAD_REQUEST)
        if tiempo_agotado: respuestas = {}
        preguntas = list(examen.preguntas.all()); correctas = 0
        for pregunta in preguntas:
            valor = str(respuestas.get(str(pregunta.id), respuestas.get(pregunta.id, '')))
            correcta = valor.strip().lower() == pregunta.respuesta_correcta.strip().lower()
            RespuestaExamen.objects.update_or_create(pregunta=pregunta, aspirante=request.user, defaults={'examen': examen, 'respuesta': valor, 'es_correcta': correcta})
            correctas += int(correcta)
        examen.calificacion = round((correctas / len(preguntas)) * 10, 2) if preguntas else 0
        examen.estado = 'aprobado' if examen.calificacion >= 8 else 'reprobado'; examen.fecha_fin = timezone.now(); examen.save(update_fields=['calificacion','estado','fecha_fin','updated_at'])
        if examen.business_key:
            camunda.completar_tareas(
                'sinac_examen_v1', 'presentar', business_key=examen.business_key,
                calificacion=float(examen.calificacion), aprobado=examen.estado == 'aprobado',
            )
        return Response(ExamenEnLineaSerializer(examen).data)


def _fecha_evaluacion(valor):
    """Devuelve (fecha, error). Acepta fecha o fecha y hora ISO; vacío equivale a ahora."""
    if valor in (None, ''):
        return timezone.now(), None
    texto = str(valor).strip()
    try:
        fecha = parse_datetime(texto)
        if fecha is None:
            dia = parse_date(texto)
            fecha = datetime.combine(dia, time.min) if dia else None
    except ValueError:
        fecha = None
    if fecha is None:
        return None, Response({'fecha_evaluacion': 'Indica una fecha válida (AAAA-MM-DD).'}, status=status.HTTP_400_BAD_REQUEST)
    if timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha)
    return fecha, None


class EvaluacionColegioView(APIView):
    """El dictamen del Colegio lo registran Coordinación o Administración; el aspirante solo consulta el suyo."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if es_gestion_academica(request.user):
            evaluaciones = EvaluacionColegio.objects.select_related('aspirante').all()
        else:
            evaluaciones = EvaluacionColegio.objects.filter(aspirante=request.user)
        return Response(EvaluacionColegioSerializer(evaluaciones, many=True).data)

    def post(self, request):
        if not es_gestion_academica(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        aspirante_id = request.data.get('aspirante')
        try:
            aspirante = Aspirante.objects.get(pk=aspirante_id)
        except Aspirante.DoesNotExist:
            return Response({'aspirante': 'Aspirante no encontrado.'}, status=status.HTTP_400_BAD_REQUEST)
        if aspirante.rol != 'aspirante':
            return Response({'aspirante': 'La evaluación del Colegio solo aplica a aspirantes.'}, status=status.HTTP_400_BAD_REQUEST)
        estado = request.data.get('estado', 'en_revision')
        dictamen = (request.data.get('dictamen') or '').strip()
        if estado not in dict(EvaluacionColegio.ESTADOS):
            return Response({'estado': 'Selecciona un estado de evaluación válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if estado in ('favorable', 'no_favorable') and not dictamen:
            return Response({'dictamen': 'El dictamen es obligatorio para cerrar la evaluación.'}, status=status.HTTP_400_BAD_REQUEST)
        fecha, error = _fecha_evaluacion(request.data.get('fecha_evaluacion'))
        if error:
            return error
        evaluacion = EvaluacionColegio.objects.create(aspirante=aspirante, evaluador=request.user, estado=estado, dictamen=dictamen, fecha_evaluacion=fecha)
        _registrar_seguimiento(aspirante, 'aceptado' if estado == 'favorable' else 'rechazado' if estado == 'no_favorable' else 'revision', f'El Colegio de Profesores registró un dictamen: {evaluacion.get_estado_display()}.', 'Colegio de Profesores', notificar=True, asunto='Actualización del Colegio de Profesores')
        return Response(EvaluacionColegioSerializer(evaluacion).data, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        try: evaluacion = EvaluacionColegio.objects.get(pk=pk)
        except EvaluacionColegio.DoesNotExist: return Response(status=status.HTTP_404_NOT_FOUND)
        if not es_gestion_academica(request.user): return Response(status=status.HTTP_403_FORBIDDEN)
        estado = request.data.get('estado', evaluacion.estado)
        dictamen = (request.data.get('dictamen', evaluacion.dictamen) or '').strip()
        if estado not in dict(EvaluacionColegio.ESTADOS):
            return Response({'estado': 'Selecciona un estado de evaluación válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if estado in ('favorable', 'no_favorable') and not dictamen:
            return Response({'dictamen': 'El dictamen es obligatorio para cerrar la evaluación.'}, status=status.HTTP_400_BAD_REQUEST)
        evaluacion.estado = estado
        evaluacion.dictamen = dictamen
        if 'fecha_evaluacion' in request.data:
            fecha, error = _fecha_evaluacion(request.data['fecha_evaluacion'])
            if error:
                return error
            evaluacion.fecha_evaluacion = fecha
        evaluacion.evaluador = request.user; evaluacion.save()
        _registrar_seguimiento(evaluacion.aspirante, 'aceptado' if estado == 'favorable' else 'rechazado' if estado == 'no_favorable' else 'revision', f'El dictamen del Colegio fue actualizado a {evaluacion.get_estado_display()}.', 'Colegio de Profesores', notificar=True, asunto='Dictamen actualizado')
        return Response(EvaluacionColegioSerializer(evaluacion).data)


class MarcarNotificacionesLeidasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        aspirante = request.user
        pendientes = aspirante.seguimientos.filter(leido=False)
        count = pendientes.update(leido=True)
        return Response({'updated': count})


class DocumentoAspiranteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    ESTADOS_RESUELTOS = ('aceptado', 'rechazado', 'baja')

    @staticmethod
    def _aspirante(request):
        return None if request.user.is_staff else request.user

    def _bloqueo_edicion(self, aspirante):
        if aspirante.rol != 'aspirante':
            return Response({'detail': 'Solo los aspirantes pueden modificar sus documentos de admisión.'}, status=status.HTTP_403_FORBIDDEN)
        if aspirante.proceso_estado in self.ESTADOS_RESUELTOS:
            return Response(
                {'detail': 'Tu solicitud ya fue resuelta; los documentos no pueden modificarse. Comunícate con Coordinación Académica si necesitas corregir alguno.'},
                status=status.HTTP_409_CONFLICT,
            )
        return None

    def get(self, request):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(DocumentoAspiranteSerializer(aspirante.documentos.order_by('tipo'), many=True, context={'request': request}).data)

    def post(self, request):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
        bloqueo = self._bloqueo_edicion(aspirante)
        if bloqueo:
            return bloqueo
        tipo = request.data.get('tipo')
        archivo = request.FILES.get('archivo')
        tipos_validos = {tipo_id for tipo_id, _ in DocumentoAspirante.TIPOS}
        if tipo not in tipos_validos:
            return Response({'tipo': 'Selecciona un tipo de documento válido.'}, status=status.HTTP_400_BAD_REQUEST)
        error_archivo = validar_pdf(archivo, MAX_DOCUMENTO_BYTES)
        if error_archivo:
            return Response({'archivo': error_archivo}, status=status.HTTP_400_BAD_REQUEST)
        archivo.name = nombre_archivo_seguro(archivo.name, 'documento')

        tamano = _obtener_tamano_archivo(archivo)
        documento, created = DocumentoAspirante.objects.get_or_create(
            aspirante=aspirante,
            tipo=tipo,
            defaults={
                'archivo': archivo,
                'nombre_original': archivo.name,
                'tamano': tamano,
                'lida_notificado': False,
            },
        )
        if not created:
            if documento.archivo:
                documento.archivo.delete(save=False)
            documento.archivo = archivo
            documento.nombre_original = archivo.name
            documento.tamano = tamano
            documento.lida_notificado = False
            documento.revisado = False
            documento.revisado_en = None
            documento.save()
            camunda.completar_tareas('sinac_documentos_v1', 'validar', filtro={'documentoId': documento.pk}, valido=False)
        documento.lida_notificado = _notificar_documento_lida(documento)
        documento.save(update_fields=['lida_notificado', 'updated_at'])
        return Response(DocumentoAspiranteSerializer(documento, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
        bloqueo = self._bloqueo_edicion(aspirante)
        if bloqueo:
            return bloqueo
        try:
            documento = aspirante.documentos.get(pk=pk)
        except DocumentoAspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        documento.archivo.delete(save=False)
        documento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentoDescargaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            documento = DocumentoAspirante.objects.select_related('aspirante').get(pk=pk)
        except DocumentoAspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if documento.aspirante_id != request.user.id:
            from .expediente_central_views import _es_gestion
            director = str(getattr(request.user, 'rol', '')).strip().lower() in ('director', 'director de tesis') and (
                documento.aspirante.director_tesis_id == request.user.id
            )
            if not (_es_gestion(request.user) or director):
                return Response(status=status.HTTP_403_FORBIDDEN)
        if request.query_params.get('inline') == '1':
            return FileResponse(documento.archivo.open('rb'), as_attachment=False, filename=documento.nombre_original, content_type='application/pdf')
        return FileResponse(documento.archivo.open('rb'), as_attachment=True, filename=documento.nombre_original)


def _clabe_valida(clabe):
    pesos = (3, 7, 1)
    suma = sum((int(digito) * pesos[i % 3]) % 10 for i, digito in enumerate(clabe[:17]))
    return (10 - suma % 10) % 10 == int(clabe[17])


class SolicitarApoyoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        aspirante = request.user
        if aspirante.is_staff or aspirante.rol not in ('aspirante', 'alumno'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if aspirante.apoyo_autorizado:
            return Response(
                {'detail': 'Tu apoyo ya fue autorizado; para cambiar los datos bancarios comunícate con Coordinación Académica.'},
                status=status.HTTP_409_CONFLICT,
            )
        nota = Decimal(str(aspirante.curso_propedeutico_nota or '0'))
        if not aspirante.curso_propedeutico_aprobado or nota < Decimal('8.00'):
            return Response(
                {'detail': 'Solo puedes solicitar apoyo después de aprobar el curso propedéutico con al menos 8.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        banco = (request.data.get('banco') or '').strip()
        clabe = ''.join(char for char in (request.data.get('clabe_interbancaria') or '') if char.isdigit())
        if not banco:
            return Response({'banco': 'Captura el nombre del banco.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(clabe) != 18:
            return Response({'clabe_interbancaria': 'La CLABE interbancaria debe tener 18 dígitos.'}, status=status.HTTP_400_BAD_REQUEST)
        if not _clabe_valida(clabe):
            return Response({'clabe_interbancaria': 'La CLABE interbancaria no es válida; revisa los dígitos.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(banco) > 120:
            return Response({'banco': 'El nombre del banco es demasiado largo.'}, status=status.HTTP_400_BAD_REQUEST)

        es_nueva_solicitud = not aspirante.apoyo_solicitado
        aspirante.banco_apoyo = banco
        aspirante.clabe_interbancaria = clabe
        aspirante.apoyo_solicitado = True
        if es_nueva_solicitud:
            aspirante.solicitud_apoyo_fecha = timezone.now()
        aspirante.save(update_fields=['banco_apoyo', 'clabe_interbancaria', 'apoyo_solicitado', 'solicitud_apoyo_fecha', 'updated_at'])
        if es_nueva_solicitud:
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                'El aspirante solicitó apoyo tras aprobar el curso propedéutico.',
                'Aspirante',
            )
        return Response({
            'detail': 'Datos bancarios guardados. Ya puedes imprimir tu solicitud de apoyo.',
            'solicitud': {
                'banco': aspirante.banco_apoyo,
                'clabe_interbancaria': aspirante.clabe_interbancaria,
                'fecha': aspirante.solicitud_apoyo_fecha,
            },
        })
