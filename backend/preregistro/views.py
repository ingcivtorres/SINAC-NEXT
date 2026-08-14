import logging
from decimal import Decimal
import requests as http
from django.conf import settings
from django.core.mail import send_mail
from django.http import FileResponse
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Aspirante, DocumentoAspirante, SeguimientoSolicitud, Materia, Inscripcion, SolicitudAcademica
from .serializers import (
    AspiranteRegistroSerializer,
    AspiranteDetalleSerializer,
    AspiranteAdminSerializer,
    AspiranteCoordinacionSerializer,
    AspiranteCoordinacionUpdateSerializer,
    InicioSesionSerializer,
    DocumentoAspiranteSerializer,
    SeguimientoSolicitudSerializer,
    MateriaSerializer,
    InscripcionSerializer,
    SolicitudAcademicaSerializer,
)
import csv
from io import TextIOWrapper, BytesIO

logger = logging.getLogger(__name__)

CAMUNDA_URL = getattr(settings, 'CAMUNDA_REST_URL', 'http://camunda:8080/engine-rest')
MAX_DOCUMENTO_BYTES = 10 * 1024 * 1024


def _obtener_tamano_archivo(archivo):
    """Obtiene el tamaño del archivo de forma robusta para uploads de Django."""
    size = getattr(archivo, 'size', None)
    if size is None:
        try:
            size = getattr(archivo.file, 'size', None)
        except Exception:
            size = None
    if size is None:
        try:
            posicion = archivo.tell()
            archivo.seek(0, 2)
            size = archivo.tell()
            archivo.seek(posicion)
        except Exception:
            size = 0
    return int(size or 0)


class InicioSesionView(TokenObtainPairView):
    serializer_class = InicioSesionSerializer


def _enviar_correo_notificacion(aspirante, asunto, mensaje):
    remitente = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@sinac.local'
    destinatario = [aspirante.correo]
    try:
        send_mail(asunto, mensaje, remitente, destinatario, fail_silently=True)
        logger.info('Notificación enviada a %s: %s', aspirante.correo, asunto)
    except Exception as exc:
        logger.warning('No se pudo enviar email de notificación a %s: %s', aspirante.correo, exc)


def _registrar_seguimiento(aspirante, estado, detalle, origen, notificar=False, asunto=None):
    seguimiento = SeguimientoSolicitud.objects.create(
        aspirante=aspirante,
        estado=estado,
        detalle=detalle,
        origen=origen,
    )
    if notificar:
        _enviar_correo_notificacion(aspirante, asunto or 'Actualización de tu solicitud', detalle)
    return seguimiento


def _iniciar_proceso_lida(aspirante):
    """Dispara instancia BPMN en Camunda; falla silenciosamente si el motor no está listo."""
    payload = {
        'businessKey': aspirante.business_key,
        'variables': {
            'aspiranteId':  {'value': aspirante.pk,            'type': 'Integer'},
            'correo':       {'value': aspirante.correo,        'type': 'String'},
            'unidad':       {'value': aspirante.unidad,        'type': 'String'},
            'programa':     {'value': aspirante.programa,      'type': 'String'},
            'lidaSource':   {'value': 'PortalAspirantes',      'type': 'String'},
        },
    }
    url = f'{CAMUNDA_URL}/process-definition/key/sinac_preregistro_v1/start'
    try:
        resp = http.post(url, json=payload, timeout=4)
        if resp.status_code == 200:
            logger.info('Camunda: proceso iniciado business_key=%s', aspirante.business_key)
            return resp.json().get('id')          # Camunda instance id
        logger.warning('Camunda respondió %s: %s', resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning('Camunda no disponible: %s', exc)
    return None


def _notificar_documento_lida(documento):
    """Notifica al flujo BPMN sin impedir que el aspirante conserve su archivo."""
    payload = {
        'messageName': 'DocumentoCargado',
        'businessKey': documento.aspirante.business_key,
        'processVariables': {
            'tipoDocumento': {'value': documento.tipo, 'type': 'String'},
            'nombreArchivo': {'value': documento.nombre_original, 'type': 'String'},
            'documentoId': {'value': documento.pk, 'type': 'Integer'},
        },
    }
    try:
        response = http.post(f'{CAMUNDA_URL}/message', json=payload, timeout=4)
        if response.status_code in (200, 204):
            logger.info('LIDA: documento notificado id=%s', documento.pk)
            return True
        logger.warning('LIDA no aceptó documento %s: %s', documento.pk, response.status_code)
    except Exception as exc:
        logger.warning('LIDA no disponible al notificar documento %s: %s', documento.pk, exc)
    return False


class PreregistroCreateView(generics.CreateAPIView):
    queryset = Aspirante.objects.all()
    serializer_class = AspiranteRegistroSerializer
    permission_classes = [permissions.AllowAny]

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

    def get_object(self):
        return self.request.user


class SeguimientoAspiranteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        aspirante = request.user
        seguimientos = aspirante.seguimientos.all()
        return Response({
            'estado_actual': aspirante.proceso_estado,
            'business_key': aspirante.business_key,
            'camunda_instance_id': aspirante.camunda_instance_id or None,
            'eventos': SeguimientoSolicitudSerializer(seguimientos, many=True).data,
        })


class MisMateriasDisponiblesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        materias = Materia.objects.all().order_by('clave')
        return Response([MateriaSerializer(m).data for m in materias])


class MisInscripcionesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        inscripciones = request.user.inscripciones.select_related('materia').order_by('materia__clave')
        return Response(InscripcionSerializer(inscripciones, many=True).data)

    def post(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        materia_id = request.data.get('materia')
        horario = (request.data.get('horario') or '').strip()
        try:
            materia = Materia.objects.get(pk=materia_id)
        except Materia.DoesNotExist:
            return Response({'materia': 'Materia no encontrada.'}, status=status.HTTP_400_BAD_REQUEST)
        inscripcion, created = Inscripcion.objects.get_or_create(
            aspirante=request.user,
            materia=materia,
            defaults={'horario': horario},
        )
        if not created:
            return Response({'detail': 'Ya estás inscrito en esta materia.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(InscripcionSerializer(inscripcion).data, status=status.HTTP_201_CREATED)


class SolicitudAcademicaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        solicitudes = request.user.solicitudes_academicas.all()
        return Response(SolicitudAcademicaSerializer(solicitudes, many=True).data)

    def post(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        tipo = request.data.get('tipo')
        comentario = (request.data.get('comentario') or '').strip()
        if tipo not in dict(SolicitudAcademica.TIPOS).keys():
            return Response({'tipo': 'Selecciona un tipo de solicitud válido.'}, status=status.HTTP_400_BAD_REQUEST)
        solicitud = SolicitudAcademica.objects.create(
            aspirante=request.user,
            tipo=tipo,
            comentario=comentario,
        )
        detalle = f'Solicitud de {solicitud.get_tipo_display()} recibida.'
        _registrar_seguimiento(request.user, 'pendiente', detalle, 'Aspirante', notificar=True, asunto='Nueva solicitud académica')
        return Response(SolicitudAcademicaSerializer(solicitud).data, status=status.HTTP_201_CREATED)


class HorarioDescargaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        inscripciones = request.user.inscripciones.select_related('materia').all()
        content_lines = [
            f'Horario de clases de {request.user.nombre}',
            f'Programa: {request.user.programa}',
            '',
            'Materias inscritas:',
            '------------------',
        ]
        for ins in inscripciones:
            content_lines.append(f'{ins.materia.clave} - {ins.materia.nombre}')
            content_lines.append(f'  Profesor: {ins.materia.profesor or "—"}')
            content_lines.append(f'  Horario: {ins.horario or ins.materia.horario or "Por asignar"}')
            content_lines.append(f'  Estado: {ins.get_estado_display()} / Calificación: {ins.calificacion or "—"}')
            content_lines.append('')
        bio = BytesIO()
        bio.write('\n'.join(content_lines).encode('utf-8'))
        bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'{request.user.usuario}_horario.txt')


class ReinscripcionDescargaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        content = (
            f'Formato de reinscripción\nAlumno: {request.user.nombre}\nCURP: {request.user.curp}\nPrograma: {request.user.programa}\nUnidad: {request.user.unidad}\n\n'
            'Declaro que deseo reinscribirme al programa y acepto los términos académicos.\n'
            'Firma: __________________________\n'
        )
        bio = BytesIO()
        bio.write(content.encode('utf-8'))
        bio.seek(0)
        _registrar_seguimiento(request.user, 'pendiente', 'Se generó una solicitud de reinscripción.', 'Aspirante', notificar=True, asunto='Solicitud de reinscripción')
        return FileResponse(bio, as_attachment=True, filename=f'{request.user.usuario}_reinscripcion.txt')


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

    @staticmethod
    def _aspirante(request):
        return None if request.user.is_staff else request.user

    def get(self, request):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(DocumentoAspiranteSerializer(aspirante.documentos.order_by('tipo'), many=True, context={'request': request}).data)

    def post(self, request):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
        tipo = request.data.get('tipo')
        archivo = request.FILES.get('archivo')
        tipos_validos = {tipo_id for tipo_id, _ in DocumentoAspirante.TIPOS}
        if tipo not in tipos_validos:
            return Response({'tipo': 'Selecciona un tipo de documento válido.'}, status=status.HTTP_400_BAD_REQUEST)
        if not archivo:
            return Response({'archivo': 'Selecciona un archivo PDF.'}, status=status.HTTP_400_BAD_REQUEST)
        if archivo.size > MAX_DOCUMENTO_BYTES:
            return Response({'archivo': 'El archivo no debe exceder 10 MB.'}, status=status.HTTP_400_BAD_REQUEST)
        if not archivo.name.lower().endswith('.pdf'):
            return Response({'archivo': 'Solo se permiten archivos PDF.'}, status=status.HTTP_400_BAD_REQUEST)

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
            documento.save()
        documento.lida_notificado = _notificar_documento_lida(documento)
        documento.save(update_fields=['lida_notificado', 'updated_at'])
        return Response(DocumentoAspiranteSerializer(documento, context={'request': request}).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        aspirante = self._aspirante(request)
        if not aspirante:
            return Response(status=status.HTTP_403_FORBIDDEN)
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
        if not request.user.is_staff and documento.aspirante_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return FileResponse(documento.archivo.open('rb'), as_attachment=True, filename=documento.nombre_original)


class SolicitarApoyoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        aspirante = request.user
        if aspirante.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        nota = aspirante.curso_propedeutico_nota or Decimal('0')
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


class PanelAdministradorView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        aspirantes = Aspirante.objects.filter(is_staff=False).order_by('-created_at')
        return Response({
            'resumen': {
                'total': aspirantes.count(),
                'pendiente': aspirantes.filter(proceso_estado='pendiente').count(),
                'iniciado': aspirantes.filter(proceso_estado='iniciado').count(),
                'revision': aspirantes.filter(proceso_estado='revision').count(),
                'aceptado': aspirantes.filter(proceso_estado='aceptado').count(),
            },
            'aspirantes': AspiranteAdminSerializer(aspirantes, many=True).data,
        })

    def post(self, request):
        """Create a new aspirante (admin only)"""
        nombre = (request.data.get('name') or '').strip()
        correo = (request.data.get('email') or '').strip().lower()
        usuario = (request.data.get('usuario') or nombre.replace(' ', '').lower()[:20]).strip()
        rol = request.data.get('role', 'aspirante').lower()
        programa = request.data.get('area', 'General').strip()

        if not nombre or not correo:
            return Response(
                {'error': 'Nombre y correo son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Aspirante.objects.filter(correo__iexact=correo).exists():
            return Response(
                {'error': 'Ya existe un aspirante con este correo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Aspirante.objects.filter(usuario__iexact=usuario).exists():
            return Response(
                {'error': 'Ya existe un aspirante con este usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.create_user(
                usuario=usuario,
                correo=correo,
                nombre=nombre,
                password='TempPass123!',
                curp='TEMP000000HDF00001',
                rol=rol if rol in ['aspirante', 'alumno', 'docente'] else 'aspirante',
                programa=programa,
                unidad='Administración',
                departamento='SINAC',
                seccion='General',
                estado_actual='Ciudad de México',
                municipio_actual='Gustavo A. Madero',
                direccion_actual='Cinvestav',
                estado_permanente='Ciudad de México',
                municipio_permanente='Gustavo A. Madero',
                direccion_permanente='Cinvestav',
                nombre_familiar='No aplica',
                parentesco='No aplica',
                telefono='0000000000',
                telefono_familiar='0000000000',
                ultimo_grado='No aplica',
                institucion='Cinvestav',
            )
            return Response(AspiranteAdminSerializer(aspirante).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'Error al crear aspirante: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, pk=None):
        """Update an aspirante (admin only)"""
        if not pk and request.data.get('id'):
            pk = request.data['id']

        if not pk:
            return Response(
                {'error': 'Se requiere un ID de usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data:
            aspirante.nombre = request.data['name'].strip()
        if 'email' in request.data:
            email = request.data['email'].strip().lower()
            if Aspirante.objects.exclude(pk=pk).filter(correo__iexact=email).exists():
                return Response(
                    {'error': 'Ya existe un aspirante con este correo.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            aspirante.correo = email
        if 'role' in request.data:
            role = request.data['role'].lower()
            if role in ['aspirante', 'alumno', 'docente']:
                aspirante.rol = role
        if 'area' in request.data:
            aspirante.programa = request.data['area'].strip()

        aspirante.save()
        return Response(AspiranteAdminSerializer(aspirante).data)

    def delete(self, request, pk=None):
        """Delete an aspirante (admin only)"""
        if not pk and request.data.get('id'):
            pk = request.data['id']

        if not pk:
            return Response(
                {'error': 'Se requiere un ID de usuario.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        aspirante.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PanelCoordinacionView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        aspirantes = Aspirante.objects.filter(is_staff=False).order_by('-created_at')
        return Response({
            'resumen': {
                'total': aspirantes.count(),
                'por_revisar': aspirantes.filter(proceso_estado__in=['pendiente', 'iniciado']).count(),
                'revision': aspirantes.filter(proceso_estado='revision').count(),
                'aceptado': aspirantes.filter(proceso_estado='aceptado').count(),
            },
            'aspirantes': AspiranteCoordinacionSerializer(aspirantes, many=True).data,
        })


class EstadoAspiranteCoordinacionView(APIView):
    permission_classes = [permissions.IsAdminUser]
    estados_permitidos = {'revision', 'aceptado', 'rechazado'}

    def patch(self, request, pk):
        estado = request.data.get('proceso_estado')
        if estado not in self.estados_permitidos:
            return Response(
                {'proceso_estado': 'El estado debe ser revisión, aceptado o rechazado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        aspirante.proceso_estado = estado
        aspirante.save(update_fields=['proceso_estado', 'updated_at'])
        if estado == 'revision':
            detalle = 'La solicitud fue marcada en revisión por la Coordinación Académica.'
            asunto = 'Tu solicitud está en revisión'
        elif estado == 'aceptado':
            detalle = 'La solicitud fue aceptada por la Coordinación Académica.'
            asunto = 'Tu solicitud ha sido aceptada'
        else:
            detalle = 'La solicitud fue rechazada. Consulta con la Coordinación Académica para más detalles.'
            asunto = 'Tu solicitud ha sido rechazada'
        _registrar_seguimiento(aspirante, estado, detalle, 'Coordinación Académica')
        return Response(AspiranteCoordinacionSerializer(aspirante).data)


class AspiranteCoordinacionDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_object(self, pk):
        try:
            return Aspirante.objects.prefetch_related('documentos', 'seguimientos').get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return None

    def get(self, request, pk):
        aspirante = self.get_object(pk)
        if not aspirante:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(AspiranteCoordinacionSerializer(aspirante).data)


class MateriasListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        materias = Materia.objects.all().order_by('clave')
        return Response([MateriaSerializer(m).data for m in materias])


class CursosUploadView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        archivo = request.FILES.get('file')
        if not archivo:
            return Response({'file': 'Selecciona un archivo CSV.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            wrapper = TextIOWrapper(archivo.file, encoding='utf-8')
            reader = csv.DictReader(wrapper)
        except Exception:
            return Response({'file': 'No se pudo leer el CSV. Asegúrate de usar UTF-8 y cabeceras: clave,nombre,profesor,horario'}, status=status.HTTP_400_BAD_REQUEST)
        count = 0
        for row in reader:
            clave = (row.get('clave') or row.get('Clave') or '').strip()
            nombre = (row.get('nombre') or row.get('Nombre') or '').strip()
            profesor = (row.get('profesor') or row.get('Profesor') or '').strip()
            horario = (row.get('horario') or row.get('Horario') or '').strip()
            if not clave or not nombre:
                continue
            materia, created = Materia.objects.update_or_create(clave=clave, defaults={'nombre': nombre, 'profesor': profesor, 'horario': horario})
            count += 1
        return Response({'detail': f'{count} materias procesadas.'})


class GenerarCargaView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        # Placeholder: in a real system this would assemble a carga académica export
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        content = 'Carga académica generada en ' + timestamp
        bio = BytesIO()
        bio.write(content.encode('utf-8'))
        bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'carga_academica_{timestamp}.txt')


class CalificacionesDownloadView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'alumno':
            return Response({'detail': 'Las calificaciones solo están disponibles para alumnos.'}, status=status.HTTP_400_BAD_REQUEST)
        # Placeholder: generate a simple text report of calificaciones
        content = f'Historial de calificaciones de {aspirante.nombre}\nCURP: {aspirante.curp}\nPrograma: {aspirante.programa}\n\nNo hay calificaciones reales en esta versión.'
        bio = BytesIO()
        bio.write(content.encode('utf-8'))
        bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'{aspirante.usuario}_calificaciones.txt')


class AdscripcionDownloadView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'alumno':
            return Response({'detail': 'El formato de adscripción solo aplica a alumnos.'}, status=status.HTTP_400_BAD_REQUEST)
        content = f'Formato de adscripción\nNombre: {aspirante.nombre}\nCURP: {aspirante.curp}\nPrograma: {aspirante.programa}\n\nFirma: __________________'
        bio = BytesIO()
        bio.write(content.encode('utf-8'))
        bio.seek(0)
        return FileResponse(bio, as_attachment=True, filename=f'{aspirante.usuario}_adscripcion.txt')


class DarBajaView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol != 'alumno':
            return Response({'detail': 'Solo se pueden dar de baja alumnos.'}, status=status.HTTP_400_BAD_REQUEST)
        aspirante.is_active = False
        aspirante.proceso_estado = 'baja'
        aspirante.save(update_fields=['is_active', 'proceso_estado', 'updated_at'])
        _registrar_seguimiento(aspirante, 'baja', 'El alumno fue dado de baja por Coordinación Académica.', 'Coordinación Académica')
        return Response({'detail': 'Alumno dado de baja.'})


class ConvertirMismaCuentaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        aspirante = request.user
        if aspirante.is_staff:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if aspirante.rol == 'alumno':
            return Response({'detail': 'La cuenta ya está convertida a alumno.', 'rol': 'alumno'})
        aspirante.rol = 'alumno'
        aspirante.save(update_fields=['rol', 'updated_at'])
        _registrar_seguimiento(
            aspirante,
            'aceptado',
            'La cuenta del aspirante fue convertida a alumno desde el panel de seguimiento.',
            'Aspirante',
        )
        return Response({'detail': 'Tu cuenta fue convertida a alumno.', 'rol': aspirante.rol})


class ConvertirAlumnoView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        try:
            aspirante = Aspirante.objects.get(pk=pk, is_staff=False)
        except Aspirante.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if aspirante.rol == 'alumno':
            return Response({'detail': 'El aspirante ya es alumno.', 'rol': 'alumno'})
        aspirante.rol = 'alumno'
        aspirante.save(update_fields=['rol', 'updated_at'])
        _registrar_seguimiento(aspirante, 'aceptado', 'El aspirante fue convertido a alumno por Coordinación Académica.', 'Coordinación Académica')
        return Response({'detail': 'Aspirante convertido a alumno.', 'rol': aspirante.rol})

    def patch(self, request, pk):
        aspirante = self.get_object(pk)
        if not aspirante:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = AspiranteCoordinacionUpdateSerializer(aspirante, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # El formulario envía todos los campos. Conservamos únicamente los que
        # realmente cambiaron para que cada fecha genere una sola notificación.
        cambios = {
            campo: valor
            for campo, valor in serializer.validated_data.items()
            if getattr(aspirante, campo) != valor
        }
        serializer.save()

        if 'proceso_estado' in cambios:
            if aspirante.proceso_estado == 'revision':
                _registrar_seguimiento(aspirante, 'revision', 'La solicitud fue marcada en revisión por la Coordinación Académica.', 'Coordinación Académica')
            elif aspirante.proceso_estado == 'aceptado':
                _registrar_seguimiento(aspirante, 'aceptado', 'Tu solicitud ha sido aceptada. Pronto recibirás fecha y hora para el examen de admisión.', 'Coordinación Académica')

        if 'fecha_examen_admision' in cambios and aspirante.fecha_examen_admision:
            detalle = f'Fecha y hora del examen de admisión programadas para {aspirante.fecha_examen_admision.strftime("%d/%m/%Y %H:%M")}. '
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                detalle,
                'Coordinación Académica',
            )

        if 'fecha_entrevista' in cambios and aspirante.fecha_entrevista:
            detalle = f'Fecha y hora de entrevista programadas para {aspirante.fecha_entrevista.strftime("%d/%m/%Y %H:%M")}. '
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                detalle,
                'Coordinación Académica',
            )

        if 'fecha_inicio_curso_propedeutico' in cambios and aspirante.fecha_inicio_curso_propedeutico:
            detalle = f'Inicio del curso propedéutico programado para {aspirante.fecha_inicio_curso_propedeutico.strftime("%d/%m/%Y %H:%M")}. '
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                detalle,
                'Coordinación Académica',
            )

        if 'curso_propedeutico_aprobado' in cambios and aspirante.curso_propedeutico_aprobado:
            nota = aspirante.curso_propedeutico_nota or Decimal('0')
            if nota >= Decimal('8.00'):
                _registrar_seguimiento(
                    aspirante,
                    'aceptado',
                    'El curso propedéutico fue aprobado con al menos 8. Ahora puedes solicitar apoyo.',
                    'Coordinación Académica',
                )
            else:
                _registrar_seguimiento(
                    aspirante,
                    'aceptado',
                    'El curso propedéutico fue actualizado, pero no alcanzó la calificación mínima de 8 para el apoyo.',
                    'Coordinación Académica',
                )

        if 'apoyo_autorizado' in cambios and aspirante.apoyo_autorizado:
            _registrar_seguimiento(
                aspirante,
                'aceptado',
                'Tu apoyo ha sido autorizado por Coordinación Académica.',
                'Coordinación Académica',
            )

        return Response(AspiranteCoordinacionSerializer(aspirante).data)
