import React, {useMemo, useState} from 'react';

const FILTROS = [
  {id: 'todos', label: 'Todas'},
  {id: 'por-revisar', label: 'Por revisar'},
  {id: 'revision', label: 'En revisión'},
  {id: 'aceptado', label: 'Aceptadas'},
];

const SOLICITUDES_INICIALES = [
  {
    id: 1,
    estudiante: 'Ana López',
    programa: 'Maestría en Ciencias',
    unidad: 'Ciencias Básicas',
    estado: 'por-revisar',
    prioridad: 'Alta',
    actualizado: 'Hace 2 horas',
    resumen: 'Solicita revisión de documentos y adscripción.',
    observaciones: 'Falta documentación de adscripción y firma del tutor propuesto.',
    notas: ['Revisar historial académico', 'Confirmar formato de cartas de recomendación'],
  },
  {
    id: 2,
    estudiante: 'Carlos Ruiz',
    programa: 'Doctorado en Ingeniería',
    unidad: 'Ingeniería Eléctrica',
    estado: 'revision',
    prioridad: 'Media',
    actualizado: 'Hace 5 horas',
    resumen: 'Expediente completo, requiere validación final.',
    observaciones: 'Se observa coherencia entre el proyecto y la línea de investigación.',
    notas: ['Verificar disponibilidad del comité', 'Programar entrevista final'],
  },
  {
    id: 3,
    estudiante: 'María Vega',
    programa: 'Especialidad en Gestión',
    unidad: 'Administración',
    estado: 'aceptado',
    prioridad: 'Baja',
    actualizado: 'Ayer',
    resumen: 'Aprobada por coordinación, pendiente cierre.',
    observaciones: 'La solicitud ya fue validada; faltan sólo los pasos administrativos.',
    notas: ['Emitir comunicado de aceptación', 'Enviar correo de bienvenida'],
  },
];

function etiquetaEstado(estado) {
  switch (estado) {
    case 'revision': return 'En revisión';
    case 'aceptado': return 'Aceptada';
    case 'por-revisar': return 'Por revisar';
    default: return 'Pendiente';
  }
}

export default function PanelDocente({onLogout}) {
  const [solicitudes, setSolicitudes] = useState(SOLICITUDES_INICIALES);
  const [filtro, setFiltro] = useState('por-revisar');
  const [seleccionadaId, setSeleccionadaId] = useState(SOLICITUDES_INICIALES[0].id);

  const solicitudesFiltradas = useMemo(() => {
    if (filtro === 'todos') return solicitudes;
    return solicitudes.filter((item) => item.estado === filtro);
  }, [filtro, solicitudes]);

  const seleccionada = solicitudesFiltradas.find((item) => item.id === seleccionadaId) || solicitudesFiltradas[0] || null;

  function actualizarEstado(nuevoEstado) {
    if (!seleccionada) return;
    setSolicitudes((prev) => prev.map((item) => item.id === seleccionada.id ? {...item, estado: nuevoEstado} : item));
  }

  const resumen = {
    total: solicitudes.length,
    porRevisar: solicitudes.filter((item) => item.estado === 'por-revisar').length,
    revision: solicitudes.filter((item) => item.estado === 'revision').length,
    aceptado: solicitudes.filter((item) => item.estado === 'aceptado').length,
  };

  return (
    <section className="panel-section" aria-label="Panel del docente">
      <div className="panel-hero">
        <div>
          <p className="panel-kicker">Docente</p>
          <h1>Revisión de solicitudes</h1>
          <p className="panel-sub">Evalúa expedientes, prioriza observaciones y avanza el estado de cada aspirante.</p>
        </div>
        <button type="button" className="btn-outline-danger" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
      </div>

      <div className="coord-stats">
        <div className="admin-stat"><span>{resumen.total}</span><small>Solicitudes totales</small></div>
        <div className="admin-stat"><span>{resumen.porRevisar}</span><small>Por revisar</small></div>
        <div className="admin-stat"><span>{resumen.revision}</span><small>En revisión</small></div>
        <div className="admin-stat"><span>{resumen.aceptado}</span><small>Aceptadas</small></div>
      </div>

      <div className="teacher-panel">
        <aside className="teacher-sidebar">
          <div className="teacher-header">
            <div>
              <p className="panel-kicker">Bandeja</p>
              <h3>Solicitudes por revisar</h3>
              <p>Prioriza expedientes y actualiza el avance de cada caso.</p>
            </div>
            <span className="teacher-badge">{solicitudesFiltradas.length} casos</span>
          </div>

          <div className="teacher-filters" role="tablist" aria-label="Filtros de solicitudes">
            {FILTROS.map((item) => (
              <button type="button" key={item.id} className={filtro === item.id ? 'teacher-filter is-active' : 'teacher-filter'} onClick={() => setFiltro(item.id)}>
                {item.label}
              </button>
            ))}
          </div>

          <div className="teacher-list">
            {solicitudesFiltradas.map((item) => (
              <button type="button" key={item.id} className={seleccionada?.id === item.id ? 'teacher-item is-selected' : 'teacher-item'} onClick={() => setSeleccionadaId(item.id)}>
                <div className="teacher-item-top">
                  <strong>{item.estudiante}</strong>
                  <span className={`estado-badge estado-${item.estado}`}>{etiquetaEstado(item.estado)}</span>
                </div>
                <span className="teacher-item-program">{item.programa}</span>
                <small>{item.unidad} · {item.actualizado}</small>
              </button>
            ))}
          </div>
        </aside>

        <main className="teacher-detail">
          {seleccionada ? (
            <>
              <div className="panel-card teacher-card">
                <div className="teacher-detail-head">
                  <div>
                    <p className="panel-kicker">Expediente</p>
                    <h3>{seleccionada.estudiante}</h3>
                    <p>{seleccionada.programa} · {seleccionada.unidad}</p>
                  </div>
                  <span className={`estado-badge estado-${seleccionada.estado}`}>{etiquetaEstado(seleccionada.estado)}</span>
                </div>

                <div className="teacher-summary-grid">
                  <div>
                    <span>Resumen</span>
                    <p>{seleccionada.resumen}</p>
                  </div>
                  <div>
                    <span>Prioridad</span>
                    <p>{seleccionada.prioridad}</p>
                  </div>
                  <div>
                    <span>Última actualización</span>
                    <p>{seleccionada.actualizado}</p>
                  </div>
                  <div>
                    <span>Observaciones</span>
                    <p>{seleccionada.observaciones}</p>
                  </div>
                </div>

                <div className="teacher-actions">
                  <button type="button" className="qa-btn" onClick={() => actualizarEstado('revision')}>Marcar en revisión</button>
                  <button type="button" className="coord-accept" onClick={() => actualizarEstado('aceptado')}>Aprobar</button>
                  <button type="button" className="btn-outline-danger" onClick={() => actualizarEstado('por-revisar')}>Solicitar cambios</button>
                </div>
              </div>

              <div className="panel-card teacher-notes">
                <h4>Notas para coordinación</h4>
                <p>{seleccionada.observaciones}</p>
                <ul>
                  {seleccionada.notas.map((nota) => <li key={nota}>{nota}</li>)}
                </ul>
              </div>
            </>
          ) : (
            <div className="panel-card teacher-empty">
              <h3>No hay solicitudes en este filtro.</h3>
              <p>Prueba con otro criterio para ver más casos.</p>
            </div>
          )}
        </main>
      </div>
    </section>
  );
}
