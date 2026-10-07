from datetime import timedelta

from django.utils import timezone

from .models import Aspirante, PeriodoInscripcion, SeguimientoSolicitud


ALERTA_DIAS_VENCIMIENTO = 7


def _crear_alerta(aspirante, estado, detalle, origen='Alertas automatizadas', detalle_estable=None):
    alertas_existentes = SeguimientoSolicitud.objects.filter(aspirante=aspirante, estado=estado)
    if detalle_estable:
        alertas_existentes = alertas_existentes.filter(detalle__startswith=detalle_estable)
    else:
        alertas_existentes = alertas_existentes.filter(detalle=detalle)
    if alertas_existentes.exists():
        return False
    SeguimientoSolicitud.objects.create(
        aspirante=aspirante,
        estado=estado,
        detalle=detalle,
        origen=origen,
    )
    return True


def generar_alertas_automatizadas(dias_vencimiento=ALERTA_DIAS_VENCIMIENTO):
    """Registra alertas idempotentes para que pueda ejecutarse de forma periódica."""
    ahora = timezone.now()
    limite = ahora + timedelta(days=dias_vencimiento)
    resultado = {'bajas': 0, 'vencimientos': 0, 'becas': 0}

    for alumno in Aspirante.objects.filter(rol='alumno', proceso_estado='baja', is_staff=False):
        detalle = 'Alerta institucional: tu cuenta académica se encuentra en estado de baja. Contacta a Servicios Escolares para orientación.'
        resultado['bajas'] += _crear_alerta(alumno, 'alerta_baja', detalle)

    periodos = PeriodoInscripcion.objects.filter(activo=True, cierre__gte=ahora, cierre__lte=limite)
    alumnos_activos = Aspirante.objects.filter(rol='alumno', is_active=True, is_staff=False).exclude(proceso_estado='baja')
    for periodo in periodos:
        dias = max(0, (periodo.cierre.date() - ahora.date()).days)
        detalle = f'Alerta de vencimiento [{periodo.pk}]: el periodo de inscripción "{periodo.nombre}" cierra en {dias} día(s).'
        for alumno in alumnos_activos:
            resultado['vencimientos'] += _crear_alerta(
                alumno,
                'alerta_vencimiento',
                detalle,
                detalle_estable=f'Alerta de vencimiento [{periodo.pk}]:',
            )

    solicitudes = Aspirante.objects.filter(apoyo_solicitado=True, is_staff=False)
    for aspirante in solicitudes:
        if aspirante.apoyo_autorizado:
            detalle = 'Alerta de beca: tu apoyo académico fue autorizado. Consulta Coordinación Académica para los siguientes pasos.'
            estado = 'alerta_beca_autorizada'
        else:
            detalle = 'Alerta de beca: tu solicitud de apoyo académico está pendiente de revisión.'
            estado = 'alerta_beca_revision'
        resultado['becas'] += _crear_alerta(aspirante, estado, detalle)

    resultado['total'] = sum(resultado.values())
    return resultado
