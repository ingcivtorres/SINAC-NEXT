"""Gestión de exámenes en línea: Coordinación los crea; Servicios Escolares los consulta."""
import uuid

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .expediente_central_views import _es_gestion
from .models import Aspirante, ExamenEnLinea, PreguntaExamen
from .servicios_views import es_servicios
from .views import _registrar_seguimiento

TIPOS_GESTIONABLES = ('admision', 'seleccion', 'diagnostico', 'otro')
ROLES_COORDINACION = {'coordinacion', 'coordinador'}
MAX_PREGUNTAS = 200


def _puede_consultar(user):
    return bool(user.is_superuser or _es_gestion(user))


def _puede_crear(user):
    rol = str(getattr(user, 'rol', '') or '').strip().lower()
    return bool(user.is_superuser or rol in ROLES_COORDINACION or (user.is_staff and not es_servicios(user)))


def _denegar(user):
    if not _puede_consultar(user):
        return Response({'detail': 'No tienes permisos para consultar exámenes en línea.'}, status=status.HTTP_403_FORBIDDEN)
    return None


def _item(examen, detalle=False, ver_respuestas=False):
    data = {
        'id': examen.id, 'tipo': examen.tipo, 'tipo_label': examen.get_tipo_display(), 'titulo': examen.titulo,
        'descripcion': examen.descripcion, 'estado': examen.estado, 'estado_label': examen.get_estado_display(),
        'fecha_programada': examen.fecha_programada, 'fecha_inicio': examen.fecha_inicio, 'fecha_fin': examen.fecha_fin,
        'duracion_minutos': examen.duracion_minutos, 'intentos': examen.intentos, 'max_intentos': examen.max_intentos,
        'calificacion': examen.calificacion, 'retroalimentacion': examen.retroalimentacion,
        'total_preguntas': getattr(examen, 'n_preguntas', None) if getattr(examen, 'n_preguntas', None) is not None else examen.preguntas.count(),
        'editable': examen.intentos == 0 and examen.estado == 'programado',
        'aspirante': {
            'id': examen.aspirante_id, 'nombre': examen.aspirante.nombre, 'usuario': examen.aspirante.usuario,
            'correo': examen.aspirante.correo, 'programa': examen.aspirante.programa,
        },
    }
    if detalle:
        data['preguntas'] = [
            {
                'id': p.id, 'orden': p.orden, 'texto': p.texto, 'opciones': p.opciones,
                **({'respuesta_correcta': p.respuesta_correcta} if ver_respuestas else {}),
            }
            for p in examen.preguntas.all()
        ]
        if ver_respuestas:
            respuestas = {r.pregunta_id: r for r in examen.respuestas.all()}
            for pregunta in data['preguntas']:
                r = respuestas.get(pregunta['id'])
                pregunta['respuesta_aspirante'] = r.respuesta if r else None
                pregunta['es_correcta'] = r.es_correcta if r else None
    return data


def _validar_preguntas(raw):
    if not isinstance(raw, list) or not raw:
        return None, 'Agrega al menos una pregunta.'
    if len(raw) > MAX_PREGUNTAS:
        return None, f'Máximo {MAX_PREGUNTAS} preguntas por examen.'
    limpias = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            return None, f'Pregunta {index}: formato inválido.'
        texto = str(item.get('texto') or '').strip()
        correcta = str(item.get('respuesta_correcta') or '').strip()
        opciones = [str(o).strip() for o in (item.get('opciones') or []) if str(o).strip()]
        if not texto:
            return None, f'Pregunta {index}: escribe el enunciado.'
        if not correcta:
            return None, f'Pregunta {index}: indica la respuesta correcta.'
        if len(correcta) > 255 or any(len(o) > 255 for o in opciones):
            return None, f'Pregunta {index}: las respuestas admiten hasta 255 caracteres.'
        if opciones:
            if len(opciones) < 2:
                return None, f'Pregunta {index}: agrega al menos dos opciones o déjalas vacías para respuesta abierta.'
            if len({o.lower() for o in opciones}) != len(opciones):
                return None, f'Pregunta {index}: hay opciones repetidas.'
            if correcta.lower() not in {o.lower() for o in opciones}:
                return None, f'Pregunta {index}: la respuesta correcta debe estar entre las opciones.'
        limpias.append({'orden': index, 'texto': texto, 'opciones': opciones, 'respuesta_correcta': correcta})
    return limpias, None


def _validar_config(data, parcial=False):
    cfg, errores = {}, {}
    if 'titulo' in data or not parcial:
        titulo = str(data.get('titulo') or '').strip()
        if not titulo:
            errores['titulo'] = 'Escribe el título del examen.'
        elif len(titulo) > 255:
            errores['titulo'] = 'El título admite hasta 255 caracteres.'
        else:
            cfg['titulo'] = titulo
    if 'descripcion' in data:
        cfg['descripcion'] = str(data.get('descripcion') or '').strip()
    if 'fecha_programada' in data or not parcial:
        valor = data.get('fecha_programada')
        fecha = parse_datetime(str(valor)) if valor else None
        if not fecha:
            errores['fecha_programada'] = 'Indica una fecha y hora válidas.'
        else:
            if timezone.is_naive(fecha):
                fecha = timezone.make_aware(fecha)
            cfg['fecha_programada'] = fecha
    for campo, minimo, maximo, etiqueta in (('duracion_minutos', 5, 480, 'La duración'), ('max_intentos', 1, 5, 'Los intentos')):
        if campo in data or not parcial:
            try:
                numero = int(data.get(campo, 90 if campo == 'duracion_minutos' else 1))
                if not minimo <= numero <= maximo:
                    raise ValueError
                cfg[campo] = numero
            except (TypeError, ValueError):
                errores[campo] = f'{etiqueta} debe ser un entero entre {minimo} y {maximo}.'
    return cfg, errores


class ExamenesGestionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        denegado = _denegar(request.user)
        if denegado:
            return denegado
        qs = ExamenEnLinea.objects.exclude(tipo='predoctoral').select_related('aspirante').annotate(n_preguntas=Count('preguntas'))
        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(titulo__icontains=q) | Q(aspirante__nombre__icontains=q) | Q(aspirante__usuario__icontains=q))
        for campo in ('estado', 'tipo'):
            valor = request.query_params.get(campo, '').strip()
            if valor:
                qs = qs.filter(**{campo: valor})
        qs = qs.order_by('-fecha_programada', '-id')
        base = ExamenEnLinea.objects.exclude(tipo='predoctoral')
        resumen = {estado: base.filter(estado=estado).count() for estado, _ in ExamenEnLinea.ESTADOS_EXAMEN}
        data = [_item(examen) for examen in qs[:300]]
        return Response({
            'examenes': data, 'total': qs.count(), 'resumen': resumen,
            'puede_crear': _puede_crear(request.user),
            'tipos': [{'value': v, 'label': l} for v, l in ExamenEnLinea.TIPOS_EXAMEN if v in TIPOS_GESTIONABLES],
        })

    @transaction.atomic
    def post(self, request):
        if not _puede_crear(request.user):
            return Response({'detail': 'Solo Coordinación Académica puede crear exámenes.'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        tipo = str(data.get('tipo') or '').strip()
        errores = {}
        if tipo not in TIPOS_GESTIONABLES:
            errores['tipo'] = 'Selecciona un tipo de examen válido.'
        cfg, errores_cfg = _validar_config(data)
        errores.update(errores_cfg)
        preguntas, error_preguntas = _validar_preguntas(data.get('preguntas'))
        if error_preguntas:
            errores['preguntas'] = error_preguntas
        ids = data.get('aspirantes')
        if not isinstance(ids, list) or not ids:
            errores['aspirantes'] = 'Selecciona al menos un aspirante.'
        if errores:
            return Response(errores, status=status.HTTP_400_BAD_REQUEST)
        try:
            ids = {int(i) for i in ids}
        except (TypeError, ValueError):
            return Response({'aspirantes': 'Selección de aspirantes inválida.'}, status=status.HTTP_400_BAD_REQUEST)
        aspirantes = list(Aspirante.objects.filter(pk__in=ids, rol='aspirante', is_staff=False, is_active=True))
        if len(aspirantes) != len(ids):
            return Response({'aspirantes': 'Algún aspirante no existe o no está activo.'}, status=status.HTTP_400_BAD_REQUEST)
        creados = []
        for aspirante in aspirantes:
            examen = ExamenEnLinea.objects.create(
                aspirante=aspirante, tipo=tipo, business_key=f'EXAM-{aspirante.pk}-{uuid.uuid4().hex[:10].upper()}',
                descripcion=cfg.get('descripcion', ''), **{k: v for k, v in cfg.items() if k != 'descripcion'},
            )
            PreguntaExamen.objects.bulk_create([PreguntaExamen(examen=examen, **p) for p in preguntas])
            _registrar_seguimiento(aspirante, 'examen_programado', f'Se te asignó el examen "{examen.titulo}".', 'Coordinación Académica', notificar=False)
            creados.append(examen)
        return Response({'creados': len(creados), 'examenes': [_item(e) for e in creados]}, status=status.HTTP_201_CREATED)


class ExamenesGestionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _obtener(self, request, pk):
        denegado = _denegar(request.user)
        if denegado:
            return None, denegado
        try:
            return ExamenEnLinea.objects.select_related('aspirante').exclude(tipo='predoctoral').get(pk=pk), None
        except ExamenEnLinea.DoesNotExist:
            return None, Response({'detail': 'Examen no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk):
        examen, error = self._obtener(request, pk)
        return error or Response(_item(examen, detalle=True, ver_respuestas=_puede_crear(request.user)))

    @transaction.atomic
    def patch(self, request, pk):
        examen, error = self._obtener(request, pk)
        if error:
            return error
        if not _puede_crear(request.user):
            return Response({'detail': 'Solo Coordinación Académica puede modificar exámenes.'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        accion = data.get('accion')
        if accion == 'cancelar':
            if examen.estado in ('aprobado', 'reprobado', 'completado'):
                return Response({'detail': 'Un examen ya calificado no se puede cancelar.'}, status=status.HTTP_409_CONFLICT)
            examen.estado = 'cancelado'
            examen.save(update_fields=['estado', 'updated_at'])
            return Response(_item(examen, detalle=True, ver_respuestas=True))
        if accion == 'otro_intento':
            if examen.estado not in ('reprobado', 'cancelado', 'iniciado'):
                return Response({'detail': 'Solo se puede otorgar otro intento a un examen reprobado, cancelado o interrumpido.'}, status=status.HTTP_409_CONFLICT)
            examen.max_intentos = max(examen.max_intentos, examen.intentos + 1)
            examen.estado = 'programado'
            examen.fecha_inicio = examen.fecha_fin = None
            examen.calificacion = None
            examen.save(update_fields=['max_intentos', 'estado', 'fecha_inicio', 'fecha_fin', 'calificacion', 'updated_at'])
            examen.respuestas.all().delete()
            _registrar_seguimiento(examen.aspirante, 'examen_reabierto', f'Se habilitó un nuevo intento para "{examen.titulo}".', 'Coordinación Académica', notificar=False)
            return Response(_item(examen, detalle=True, ver_respuestas=True))
        if not (examen.intentos == 0 and examen.estado in ('programado', 'cancelado')):
            return Response({'detail': 'El examen ya fue iniciado; no se puede modificar su contenido.'}, status=status.HTTP_409_CONFLICT)
        permitidos = {'titulo', 'descripcion', 'fecha_programada', 'duracion_minutos', 'max_intentos', 'preguntas', 'tipo'}
        desconocidos = set(data) - permitidos - {'accion'}
        if desconocidos:
            return Response({'detail': f'Campos no permitidos: {", ".join(sorted(desconocidos))}.'}, status=status.HTTP_400_BAD_REQUEST)
        cfg, errores = _validar_config(data, parcial=True)
        if 'tipo' in data:
            if data['tipo'] in TIPOS_GESTIONABLES:
                cfg['tipo'] = data['tipo']
            else:
                errores['tipo'] = 'Selecciona un tipo de examen válido.'
        preguntas = None
        if 'preguntas' in data:
            preguntas, error_preguntas = _validar_preguntas(data['preguntas'])
            if error_preguntas:
                errores['preguntas'] = error_preguntas
        if errores:
            return Response(errores, status=status.HTTP_400_BAD_REQUEST)
        for campo, valor in cfg.items():
            setattr(examen, campo, valor)
        if examen.estado == 'cancelado':
            examen.estado = 'programado'
        examen.save()
        if preguntas is not None:
            examen.preguntas.all().delete()
            PreguntaExamen.objects.bulk_create([PreguntaExamen(examen=examen, **p) for p in preguntas])
        return Response(_item(examen, detalle=True, ver_respuestas=True))

    def delete(self, request, pk):
        examen, error = self._obtener(request, pk)
        if error:
            return error
        if not _puede_crear(request.user):
            return Response({'detail': 'Solo Coordinación Académica puede eliminar exámenes.'}, status=status.HTTP_403_FORBIDDEN)
        if examen.intentos > 0:
            return Response({'detail': 'El examen ya fue iniciado; cancélalo en lugar de eliminarlo para conservar el historial.'}, status=status.HTTP_409_CONFLICT)
        examen.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExamenesCandidatosView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not _puede_crear(request.user):
            return Response({'detail': 'No tienes permisos.'}, status=status.HTTP_403_FORBIDDEN)
        qs = Aspirante.objects.filter(rol='aspirante', is_staff=False, is_active=True)
        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(usuario__icontains=q) | Q(correo__icontains=q))
        return Response({'aspirantes': [
            {'id': a.id, 'nombre': a.nombre, 'usuario': a.usuario, 'correo': a.correo, 'programa': a.programa}
            for a in qs.order_by('nombre')[:30]
        ]})
