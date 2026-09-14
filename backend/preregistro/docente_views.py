"""Panel de docentes y endpoints para gestión de calificaciones y cursos."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
import requests
from django.conf import settings
from .models import Aspirante, Materia, Inscripcion, SolicitudAcademica, ExamenEnLinea, EntrevistaVirtual
from .serializers import MateriaSerializer, InscripcionSerializer, SolicitudAcademicaSerializer, ExamenEnLineaSerializer, EntrevistaVirtualSerializer


class PanelDocenteView(APIView):
    """Panel del docente: obtiene sus cursos, estudiantes e inscripciones."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Obtiene información del panel del docente."""
        docente = request.user
        
        # Verificar que sea docente
        if str(getattr(docente, 'rol', '')).lower() not in ('docente', 'teacher'):
            return Response(
                {'error': 'No tienes permisos de docente.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Obtener cursos del docente (materias donde es profesor)
        nombre_docente = (docente.nombre or '').strip()
        materias = Materia.objects.filter(profesor__iexact=nombre_docente).order_by('clave') if nombre_docente else Materia.objects.none()
        
        # Obtener inscripciones en esos cursos
        inscripciones = Inscripcion.objects.filter(
            materia__in=materias
        ).select_related('aspirante', 'materia').order_by('-created_at')

        # Las solicitudes y evaluaciones del panel deben pertenecer a los
        # estudiantes inscritos en las materias del docente, no a todo el
        # padrón institucional.
        estudiante_ids = inscripciones.values_list('aspirante_id', flat=True)
        solicitudes_query = SolicitudAcademica.objects.filter(
            aspirante_id__in=estudiante_ids
        ).order_by('-created_at')
        
        solicitudes = solicitudes_query[:10]

        # Obtener exámenes en línea del docente
        examenes = ExamenEnLinea.objects.filter(
            aspirante_id__in=estudiante_ids
        ).order_by('-fecha_programada')

        # Obtener entrevistas virtuales de estudiantes del docente
        aspirantes = Aspirante.objects.filter(
            id__in=inscripciones.values_list('aspirante_id', flat=True)
        )
        entrevistas = EntrevistaVirtual.objects.filter(
            aspirante__in=aspirantes
        ).order_by('-fecha_programada')

        return Response({
            'docente': {
                'id': docente.id,
                'nombre': docente.nombre,
                'usuario': docente.usuario,
                'programa': docente.programa,
                'unidad': docente.unidad,
            },
            'materias': MateriaSerializer(materias, many=True).data,
            'inscripciones': InscripcionSerializer(inscripciones, many=True).data,
            'solicitudes': SolicitudAcademicaSerializer(solicitudes, many=True).data,
            'examenes': ExamenEnLineaSerializer(examenes, many=True).data,
            'entrevistas': EntrevistaVirtualSerializer(entrevistas, many=True).data,
            'resumen': {
                'total_materias': materias.count(),
                'total_inscripciones': inscripciones.count(),
                'inscripciones_aprobadas': inscripciones.filter(estado='aprobada').count(),
                'inscripciones_reprobadas': inscripciones.filter(estado='reprobada').count(),
                'solicitudes_pendientes': solicitudes_query.filter(estado='pendiente').count(),
                'examenes_total': examenes.count(),
                'examenes_programados': examenes.filter(estado='programado').count(),
                'examenes_completados': examenes.filter(estado__in=['aprobado', 'reprobado']).count(),
                'entrevistas_total': entrevistas.count(),
                'entrevistas_programadas': entrevistas.filter(estado='programada').count(),
                'entrevistas_iniciadas': entrevistas.filter(estado='iniciada').count(),
                'entrevistas_completadas': entrevistas.filter(estado='completada').count(),
            }
        })


class DocenteCatalogoMateriasView(APIView):
    """Permite al docente elegir una materia del catálogo y proponer su horario."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.rol != 'docente':
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(MateriaSerializer(Materia.objects.all().order_by('clave'), many=True).data)

    def patch(self, request, pk):
        if request.user.rol != 'docente':
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            materia = Materia.objects.get(pk=pk)
        except Materia.DoesNotExist:
            return Response({'detail': 'Materia no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if materia.profesor and materia.profesor.lower() != request.user.nombre.lower():
            return Response({'detail': 'Esta materia ya fue asignada a otro docente.'}, status=status.HTTP_409_CONFLICT)
        materia.profesor = request.user.nombre
        materia.horario = (request.data.get('horario') or '').strip()
        materia.save(update_fields=['profesor', 'horario'])
        return Response(MateriaSerializer(materia).data)


class DocenteMateriaView(APIView):
    """Obtiene detalles de una materia específica del docente."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Obtiene estudiantes inscritos en una materia."""
        docente = request.user
        if docente.rol != 'docente':
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            materia = Materia.objects.get(pk=pk, profesor__iexact=docente.nombre)
        except Materia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        inscripciones = Inscripcion.objects.filter(materia=materia).select_related('aspirante')
        
        return Response({
            'materia': MateriaSerializer(materia).data,
            'inscripciones': InscripcionSerializer(inscripciones, many=True).data,
            'estadisticas': {
                'total': inscripciones.count(),
                'cursando': inscripciones.filter(estado='cursando').count(),
                'aprobada': inscripciones.filter(estado='aprobada').count(),
                'reprobada': inscripciones.filter(estado='reprobada').count(),
            }
        })


class CalificacionesView(APIView):
    """Permite al docente registrar o actualizar calificaciones."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Registra o actualiza calificaciones de estudiantes."""
        docente = request.user
        if docente.rol != 'docente':
            return Response(status=status.HTTP_403_FORBIDDEN)

        inscripcion_id = request.data.get('inscripcion_id')
        calificacion = request.data.get('calificacion')
        parcial = request.data.get('parcial')

        if not inscripcion_id or (calificacion is None and parcial is None):
            return Response(
                {'error': 'Se requiere inscripcion_id y calificacion.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            inscripcion = Inscripcion.objects.select_related('materia').get(pk=inscripcion_id)
            if inscripcion.materia.profesor.lower() != docente.nombre.lower():
                return Response(status=status.HTTP_403_FORBIDDEN)
        except Inscripcion.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if parcial is not None:
            try:
                numero = int(request.data.get('numero_parcial', 1))
                valor = float(parcial)
            except (TypeError, ValueError):
                return Response({'error': 'La calificación parcial no es válida.'}, status=status.HTTP_400_BAD_REQUEST)
            if numero not in (1, 2, 3):
                return Response({'error': 'El parcial debe ser 1, 2 o 3.'}, status=status.HTTP_400_BAD_REQUEST)
            if not 0 <= valor <= 10:
                return Response({'error': 'La calificación debe estar entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            setattr(inscripcion, f'parcial_{numero}', valor)
            # Los parciales no sustituyen la calificación final. La materia
            # permanece cursando hasta que se capture explícitamente la final.
            if inscripcion.calificacion is None:
                inscripcion.estado = 'cursando'
        else:
            try:
                calificacion = float(calificacion)
            except (TypeError, ValueError):
                return Response({'error': 'La calificación final no es válida.'}, status=status.HTTP_400_BAD_REQUEST)
            if not 0 <= calificacion <= 10:
                return Response({'error': 'La calificación debe estar entre 0 y 10.'}, status=status.HTTP_400_BAD_REQUEST)
            inscripcion.calificacion = calificacion
            # Solo la final determina aprobación o reprobación.
            inscripcion.estado = 'reprobada' if calificacion < 7 else 'aprobada'

        inscripcion.save()
        return Response(InscripcionSerializer(inscripcion).data)

    def put(self, request, pk):
        """Actualiza calificación de una inscripción específica."""
        docente = request.user
        if docente.rol != 'docente':
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            inscripcion = Inscripcion.objects.select_related('materia').get(pk=pk)
            if inscripcion.materia.profesor.lower() != docente.nombre.lower():
                return Response(status=status.HTTP_403_FORBIDDEN)
        except Inscripcion.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if 'calificacion' in request.data:
            try:
                calificacion = float(request.data['calificacion'])
                if not (0 <= calificacion <= 10):
                    raise ValueError('La calificación debe estar entre 0 y 10.')
                inscripcion.calificacion = calificacion
                
                # Actualizar estado basado en calificación
                if calificacion < 7:
                    inscripcion.estado = 'reprobada'
                else:
                    inscripcion.estado = 'aprobada'
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if 'horario' in request.data:
            inscripcion.horario = request.data['horario']

        inscripcion.save()
        return Response(InscripcionSerializer(inscripcion).data)


class ActasCalificacionesView(APIView):
    """Genera actas de calificaciones para descarga."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, materia_id):
        """Genera un acta de calificaciones de una materia."""
        docente = request.user
        if docente.rol != 'docente':
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            materia = Materia.objects.get(pk=materia_id, profesor__iexact=docente.nombre)
        except Materia.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        inscripciones = Inscripcion.objects.filter(materia=materia).select_related('aspirante')
        
        # Preparar datos para el acta
        acta_data = {
            'materia': {
                'clave': materia.clave,
                'nombre': materia.nombre,
                'profesor': materia.profesor,
                'horario': materia.horario,
            },
            'calificaciones': []
        }

        for inscripcion in inscripciones:
            acta_data['calificaciones'].append({
                'estudiante': inscripcion.aspirante.nombre,
                'usuario': inscripcion.aspirante.usuario,
                'calificacion': inscripcion.calificacion,
                'estado': inscripcion.estado,
                'programa': inscripcion.aspirante.programa,
            })

        return Response(acta_data)


class DocenteExamenView(APIView):
    """Lista y actualiza exámenes en línea."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Lista todos los exámenes en línea asociados al docente."""
        docente = request.user
        if docente.rol != 'docente':
            return Response(
                {'error': 'No tienes permisos de docente.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Obtener exámenes de los estudiantes inscritos en las materias del docente
        materias = Materia.objects.filter(profesor__iexact=docente.nombre)
        inscripciones = Inscripcion.objects.filter(materia__in=materias)
        aspirantes = inscripciones.values_list('aspirante_id', flat=True).distinct()
        
        examenes = ExamenEnLinea.objects.filter(
            aspirante_id__in=aspirantes
        ).select_related('aspirante').order_by('-fecha_programada')

        return Response({
            'total': examenes.count(),
            'examenes': ExamenEnLineaSerializer(examenes, many=True).data,
            'resumen': {
                'programados': examenes.filter(estado='programado').count(),
                'iniciados': examenes.filter(estado='iniciado').count(),
                'completados': examenes.filter(estado='completado').count(),
                'aprobados': examenes.filter(estado='aprobado').count(),
                'reprobados': examenes.filter(estado='reprobado').count(),
                'cancelados': examenes.filter(estado='cancelado').count(),
            }
        })

    def put(self, request, pk):
        """Actualiza el estado de un examen."""
        docente = request.user
        if docente.rol != 'docente':
            return Response(
                {'error': 'No tienes permisos de docente.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            examen = ExamenEnLinea.objects.get(pk=pk)
        except ExamenEnLinea.DoesNotExist:
            return Response(
                {'error': 'Examen no encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verificar que el docente tenga permiso (puede ser profesor de alguna materia del estudiante)
        materias = Materia.objects.filter(profesor__iexact=docente.nombre)
        inscripciones = Inscripcion.objects.filter(
            aspirante=examen.aspirante,
            materia__in=materias
        )
        if not inscripciones.exists():
            return Response(
                {'error': 'No tienes permiso para actualizar este examen.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Actualizar campos permitidos
        if 'estado' in request.data:
            estado = request.data.get('estado')
            valid_estados = ['programado', 'iniciado', 'completado', 'aprobado', 'reprobado', 'cancelado']
            if estado not in valid_estados:
                return Response(
                    {'error': f'Estado inválido. Debe ser uno de: {", ".join(valid_estados)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            examen.estado = estado

        if 'calificacion' in request.data:
            try:
                calificacion = float(request.data.get('calificacion'))
                if not (0 <= calificacion <= 10):
                    raise ValueError('La calificación debe estar entre 0 y 10.')
                examen.calificacion = calificacion
            except (ValueError, TypeError) as e:
                return Response(
                    {'error': f'Calificación inválida: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if 'retroalimentacion' in request.data:
            examen.retroalimentacion = request.data.get('retroalimentacion')

        if 'fecha_inicio' in request.data:
            examen.fecha_inicio = request.data.get('fecha_inicio')

        if 'fecha_fin' in request.data:
            examen.fecha_fin = request.data.get('fecha_fin')

        examen.save()
        return Response(ExamenEnLineaSerializer(examen).data)


class DocenteExamenDetailView(APIView):
    """Obtiene detalle de un examen específico."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Obtiene detalle de un examen."""
        docente = request.user
        if docente.rol != 'docente':
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            examen = ExamenEnLinea.objects.select_related('aspirante').get(pk=pk)
        except ExamenEnLinea.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Verificar permiso
        materias = Materia.objects.filter(profesor__iexact=docente.nombre)
        inscripciones = Inscripcion.objects.filter(
            aspirante=examen.aspirante,
            materia__in=materias
        )
        if not inscripciones.exists():
            return Response(status=status.HTTP_403_FORBIDDEN)

        return Response(ExamenEnLineaSerializer(examen).data)


class DocenteEntrevistaView(APIView):
    """API para gestión de entrevistas virtuales por docentes."""
    
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Obtener lista de entrevistas de los estudiantes del docente."""
        try:
            docente = request.user
            if not isinstance(docente, Aspirante):
                return Response(
                    {'error': 'Usuario no válido'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            # Obtener materias donde es profesor
            materias = Materia.objects.filter(profesor__icontains=docente.nombre)
            
            # Obtener todas las inscripciones (estudiantes) en esas materias
            inscripciones = Inscripcion.objects.filter(materia__in=materias)
            aspirantes = Aspirante.objects.filter(
                id__in=inscripciones.values_list('aspirante_id', flat=True)
            )
            
            # Obtener entrevistas para esos estudiantes
            entrevistas = EntrevistaVirtual.objects.filter(
                aspirante__in=aspirantes
            ).order_by('-fecha_programada')
            
            # Estadísticas
            entrevistas_total = entrevistas.count()
            entrevistas_programadas = entrevistas.filter(estado='programada').count()
            entrevistas_iniciadas = entrevistas.filter(estado='iniciada').count()
            entrevistas_completadas = entrevistas.filter(estado='completada').count()
            
            serializer = EntrevistaVirtualSerializer(entrevistas, many=True)
            return Response({
                'entrevistas': serializer.data,
                'resumen': {
                    'entrevistas_total': entrevistas_total,
                    'entrevistas_programadas': entrevistas_programadas,
                    'entrevistas_iniciadas': entrevistas_iniciadas,
                    'entrevistas_completadas': entrevistas_completadas,
                }
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """Crear nueva entrevista virtual."""
        try:
            docente = request.user
            if not isinstance(docente, Aspirante):
                return Response(
                    {'error': 'Usuario no válido'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            aspirante_id = request.data.get('aspirante_id')
            if not aspirante_id:
                return Response(
                    {'error': 'aspirante_id es requerido'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            try:
                aspirante = Aspirante.objects.get(id=aspirante_id)
            except Aspirante.DoesNotExist:
                return Response(
                    {'error': 'Aspirante no encontrado'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            
            # Verificar que el docente tenga relación con el estudiante
            materias = Materia.objects.filter(profesor__icontains=docente.nombre)
            inscripciones = Inscripcion.objects.filter(
                materia__in=materias,
                aspirante=aspirante
            )
            if not inscripciones.exists():
                return Response(
                    {'error': 'No tienes permiso para crear entrevista para este estudiante'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            # Generar Jitsi room ID
            import uuid
            jitsi_room_id = str(uuid.uuid4())[:8]
            jitsi_room_link = f"https://meet.jitsi.si/sinac-{jitsi_room_id}"
            
            # Crear entrevista
            entrevista_data = request.data.copy()
            entrevista_data['jitsi_room_id'] = jitsi_room_id
            entrevista_data['jitsi_room_link'] = jitsi_room_link
            entrevista_data['aspirante'] = aspirante.id
            entrevista_data['estado'] = 'programada'  # Estado inicial
            
            serializer = EntrevistaVirtualSerializer(data=entrevista_data)
            if serializer.is_valid():
                entrevista = serializer.save(aspirante=aspirante)
                base = getattr(settings, 'CAMUNDA_REST_URL', '')
                if base:
                    try:
                        r = requests.post(f'{base}/process-definition/key/sinac_entrevista_v1/start', json={'businessKey': f'entrevista-{entrevista.id}', 'variables': {'entrevistaId': {'value': entrevista.id, 'type': 'Integer'}, 'aspiranteId': {'value': aspirante.id, 'type': 'Integer'}}}, timeout=6)
                        if r.ok:
                            entrevista.camunda_instance_id = r.json().get('id', ''); entrevista.save(update_fields=['camunda_instance_id','updated_at'])
                    except requests.RequestException:
                        pass
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        """Actualizar entrevista existente."""
        try:
            entrevista = EntrevistaVirtual.objects.get(id=pk)
        except EntrevistaVirtual.DoesNotExist:
            return Response(
                {'error': 'Entrevista no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Verificar permisos
        docente = request.user
        materias = Materia.objects.filter(profesor__icontains=docente.nombre)
        inscripciones = Inscripcion.objects.filter(
            materia__in=materias,
            aspirante=entrevista.aspirante
        )
        if not inscripciones.exists():
            return Response(
                {'error': 'No tienes permiso para actualizar esta entrevista'},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        # Actualizar campos permitidos
        if 'estado' in request.data:
            estado = request.data.get('estado')
            valid_estados = ['programada', 'iniciada', 'completada', 'cancelada']
            if estado not in valid_estados:
                return Response(
                    {'error': f'Estado inválido. Debe ser uno de: {", ".join(valid_estados)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            entrevista.estado = estado
        
        if 'notas_docente' in request.data:
            entrevista.notas_docente = request.data.get('notas_docente')
        
        if 'retroalimentacion' in request.data:
            entrevista.retroalimentacion = request.data.get('retroalimentacion')
        
        if 'recording_link' in request.data:
            entrevista.recording_link = request.data.get('recording_link')
        
        if 'fecha_inicio' in request.data:
            entrevista.fecha_inicio = request.data.get('fecha_inicio')
        
        if 'fecha_fin' in request.data:
            entrevista.fecha_fin = request.data.get('fecha_fin')
        
        try:
            entrevista.save()
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        return Response(EntrevistaVirtualSerializer(entrevista).data)


class DocenteEntrevistaDetailView(APIView):
    """API para detalle de entrevista virtual."""
    
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Obtener detalle de una entrevista."""
        try:
            entrevista = EntrevistaVirtual.objects.get(id=pk)
        except EntrevistaVirtual.DoesNotExist:
            return Response(
                {'error': 'Entrevista no encontrada'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Verificar permisos
        docente = request.user
        materias = Materia.objects.filter(profesor__icontains=docente.nombre)
        inscripciones = Inscripcion.objects.filter(
            materia__in=materias,
            aspirante=entrevista.aspirante
        )
        if not inscripciones.exists():
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        return Response(EntrevistaVirtualSerializer(entrevista).data)
