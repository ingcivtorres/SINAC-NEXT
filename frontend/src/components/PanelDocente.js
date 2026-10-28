import React, {useCallback, useEffect, useState} from 'react';
import DashboardAnalitico from './DashboardAnalitico';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import MiPerfilAcademico from './MiPerfilAcademico';
import {useTeacherCopy} from './teacherPanelTranslations';

const MENU_ITEMS = [
  {label: 'overview', items: [['overview', 'Resumen', '▦']]},
  {label: 'teaching', items: [['cursos', 'Mis cursos', '▤'], ['catalogo', 'Elegir materia', '◫'], ['estudiantes', 'Estudiantes', '♙']]},
  {label: 'evaluation', items: [['calificaciones', 'Calificaciones', '✓'], ['examenes', 'Exámenes', '✦'], ['entrevistas', 'Entrevistas', '◷']]},
  {label: 'followup', items: [['solicitudes', 'Solicitudes', '◈'], ['reportes', 'Reportes', '▥'], ['perfil', 'Mi perfil', '●']]},
];

function etiquetaEstado(estado, copy) {
  return copy.status[estado] || estado || copy.common.pending;
}

function TablaAlumnosMateria({materia, inscripciones, copy, soloCalificaciones = false}) {
  const alumnos = inscripciones.filter(inscripcion => String(inscripcion.materia) === String(materia.id));
  return <section className="docente-materia-section">
    <div className="docente-materia-section-head">
      <div><span className="materia-card-clave">{materia.clave}</span><h4>{materia.nombre}</h4><small>{copy.common.schedule}: {materia.horario || copy.common.notAssigned} · {alumnos.length} {copy.common.student}{alumnos.length === 1 ? '' : 's'}</small></div>
    </div>
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead><tr><th>{copy.common.student}</th><th>{copy.common.user}</th><th>{copy.common.program}</th>{!soloCalificaciones && <th>{copy.common.status}</th>}<th>{copy.common.partials} 1</th><th>{copy.common.partials} 2</th><th>{copy.common.partials} 3</th><th>{copy.common.final}</th><th>{copy.common.academicStatus}</th>{soloCalificaciones && <th>{copy.grading.lastUpdate}</th>}</tr></thead>
        <tbody>{alumnos.length ? alumnos.map(inscripcion => <tr key={inscripcion.id}>
          <td><strong>{inscripcion.aspirante?.nombre || 'N/A'}</strong></td>
          <td>{inscripcion.aspirante?.usuario || 'N/A'}</td>
          <td>{inscripcion.aspirante?.programa || 'N/A'}</td>
          {!soloCalificaciones && <td><span className={`estado-badge estado-${inscripcion.estado}`}>{etiquetaEstado(inscripcion.estado, copy)}</span></td>}
          <td>{inscripcion.parcial_1 ?? '-'}</td><td>{inscripcion.parcial_2 ?? '-'}</td><td>{inscripcion.parcial_3 ?? '-'}</td><td><strong>{inscripcion.calificacion ?? '-'}</strong></td>
          <td><span className={`estado-badge estado-${inscripcion.calificacion == null ? 'cursando' : Number(inscripcion.calificacion) < 7 ? 'reprobada' : 'aprobada'}`}>{inscripcion.calificacion == null ? copy.status.cursando : Number(inscripcion.calificacion) < 7 ? copy.status.reprobada : copy.status.aprobada}</span></td>
          {soloCalificaciones && <td>{inscripcion.updated_at ? new Intl.DateTimeFormat(copy.locale, {dateStyle: 'medium'}).format(new Date(inscripcion.updated_at)) : '-'}</td>}
        </tr>) : <tr><td colSpan="9" className="docente-empty-cell">{copy.common.noStudents}</td></tr>}</tbody>
      </table>
    </div>
  </section>;
}

export default function PanelDocente({session, onLogout}) {
  const copy = useTeacherCopy();
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [activeSection, setActiveSection] = useState('overview');
  const [cursoSeleccionado, setCursoSeleccionado] = useState(null);
  const [showCalificacionForm, setShowCalificacionForm] = useState(false);
  const [calificacionForm, setCalificacionForm] = useState({inscripcion_id: '', calificacion: '', parcial: '', numero_parcial: '1'});
  const [examenCalificar, setExamenCalificar] = useState(null);
  const [examenCalificacionForm, setExamenCalificacionForm] = useState({calificacion: '', retroalimentacion: ''});
  const [guardandoExamen, setGuardandoExamen] = useState(false);
  const [materiaCalificacionId, setMateriaCalificacionId] = useState('');
  const [materiaEstudiantesFiltro, setMateriaEstudiantesFiltro] = useState('');
  const [materiaCalificacionesFiltro, setMateriaCalificacionesFiltro] = useState('');
  const [examenesFiltro, setExamenesFiltro] = useState({aspiranteId: '', tipo: '', estado: ''});
  const [entrevistasFiltro, setEntrevistasFiltro] = useState({aspiranteId: '', proposito: '', estado: ''});
  const [solicitudesFiltro, setSolicitudesFiltro] = useState({aspiranteId: '', tipo: '', estado: ''});
  const [materiaReporteFiltro, setMateriaReporteFiltro] = useState('');
  const [catalogo, setCatalogo] = useState([]);
  const [horarios, setHorarios] = useState({});
  const [salones, setSalones] = useState({});
  const [periodo, setPeriodo] = useState(null);
  const [cargandoPeriodo, setCargandoPeriodo] = useState(false);
  const totalEstudiantes = new Set((datos?.inscripciones || []).map(item => item.aspirante?.id).filter(Boolean)).size;
  const [mostrarEntrevistaForm, setMostrarEntrevistaForm] = useState(false);
  const [entrevistaGuardando, setEntrevistaGuardando] = useState(false);
  const [entrevistaForm, setEntrevistaForm] = useState({
    aspirante_id: '',
    proposito: 'seguimiento',
    titulo: 'Entrevista virtual',
    descripcion: '',
    fecha_programada: '',
    duracion_minutos: 30,
  });
  const materiasEstudiantesFiltradas = (datos?.materias || []).filter(
    materia => !materiaEstudiantesFiltro || String(materia.id) === materiaEstudiantesFiltro,
  );
  const materiasCalificacionesFiltradas = (datos?.materias || []).filter(
    materia => !materiaCalificacionesFiltro || String(materia.id) === materiaCalificacionesFiltro,
  );
  const inscripcionesFiltradasCalificacion = (datos?.inscripciones || []).filter(
    inscripcion => !materiaCalificacionId || String(inscripcion.materia) === materiaCalificacionId,
  );
  const examenesFiltrados = (datos?.examenes || []).filter(examen => (
    (!examenesFiltro.aspiranteId || String(examen.aspirante?.id) === examenesFiltro.aspiranteId)
    && (!examenesFiltro.tipo || examen.tipo === examenesFiltro.tipo)
    && (!examenesFiltro.estado || examen.estado === examenesFiltro.estado)
  ));
  const entrevistasFiltradas = (datos?.entrevistas || []).filter(entrevista => (
    (!entrevistasFiltro.aspiranteId || String(entrevista.aspirante?.id) === entrevistasFiltro.aspiranteId)
    && (!entrevistasFiltro.proposito || entrevista.proposito === entrevistasFiltro.proposito)
    && (!entrevistasFiltro.estado || entrevista.estado === entrevistasFiltro.estado)
  ));
  const solicitudesFiltradas = (datos?.solicitudes || []).filter(solicitud => (
    (!solicitudesFiltro.aspiranteId || String(solicitud.aspirante?.id) === solicitudesFiltro.aspiranteId)
    && (!solicitudesFiltro.tipo || solicitud.tipo === solicitudesFiltro.tipo)
    && (!solicitudesFiltro.estado || solicitud.estado === solicitudesFiltro.estado)
  ));
  const estudiantesDocente = Array.from(new Map(
    (datos?.inscripciones || [])
      .filter(item => item.aspirante?.id)
      .map(item => [String(item.aspirante.id), item.aspirante]),
  ).values());
  const solicitudesTipos = Array.from(new Map(
    (datos?.solicitudes || []).map(item => [item.tipo, item.tipo_label || item.tipo]),
  ).entries());
  const examenesTipos = Array.from(new Map(
    (datos?.examenes || []).map(item => [item.tipo, item.tipo_label || item.tipo]),
  ).entries());
  const entrevistasPropositos = Array.from(new Map(
    (datos?.entrevistas || []).map(item => [item.proposito, item.proposito_label || item.proposito]),
  ).entries());
  const reporteInscripciones = (datos?.inscripciones || []).filter(
    item => !materiaReporteFiltro || String(item.materia) === materiaReporteFiltro,
  );
  const reporteEstudianteIds = new Set(reporteInscripciones.map(item => item.aspirante?.id).filter(Boolean));
  const reporteExamenes = (datos?.examenes || []).filter(examen => (
    !materiaReporteFiltro || reporteEstudianteIds.has(examen.aspirante?.id)
  ));
  const reporteEntrevistas = (datos?.entrevistas || []).filter(entrevista => (
    !materiaReporteFiltro || reporteEstudianteIds.has(entrevista.aspirante?.id)
  ));
  const reporteAprobados = reporteInscripciones.filter(item => item.estado === 'aprobada').length;
  const reporteReprobados = reporteInscripciones.filter(item => item.estado === 'reprobada').length;
  const inscripcionesFiltradasExportacion = (datos?.inscripciones || []).filter(
    item => !materiaCalificacionesFiltro || String(item.materia) === materiaCalificacionesFiltro,
  );
  async function leerJson(response, mensaje) { const tipo=response.headers.get('content-type')||''; if (!response.ok || !tipo.includes('application/json')) throw new Error(mensaje); return response.json(); }
  const cargarPanel = useCallback(async (signal) => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/docente/panel/', {
        headers: {Authorization: `Bearer ${session.access}`},
        signal,
      });
      if (response.status === 401) {
        onLogout(copy.messages.expired);
        return;
      }
      if (response.status === 403) {
        throw new Error(copy.messages.permission);
      }
      if (!response.ok) {
        let detail = '';
        try { const body = await response.json(); detail = body.error || body.detail || ''; } catch (ignore) { /* respuesta no JSON */ }
        throw new Error(detail || `${copy.messages.loadError} (HTTP ${response.status}).`);
      }
      setDatos(await leerJson(response, copy.messages.loadError));
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || copy.messages.loadError);
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [copy, onLogout, session.access]);

  useEffect(() => {
    const controller = new AbortController();
    cargarPanel(controller.signal);
    return () => controller.abort();
  }, [cargarPanel]);

  useEffect(() => {
    if (activeSection !== 'catalogo') return;
    fetch('/api/docente/catalogo-materias/', {headers: {Authorization: `Bearer ${session.access}`}})
        .then(response => response.ok ? response.json() : Promise.reject(new Error(copy.messages.noCatalog)))
      .then(setCatalogo).catch(err => setError(err.message));
      }, [activeSection, copy, session.access]);
  useEffect(() => {
    if (activeSection !== 'catalogo') return undefined;
    const controller = new AbortController();
    setCargandoPeriodo(true);
    fetch('/api/periodos-inscripcion/', {
      headers: {Authorization: `Bearer ${session.access}`},
      signal: controller.signal,
    })
      .then(async response => {
        if (response.status === 401) {
          onLogout(copy.messages.expired);
          return null;
        }
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || copy.messages.periodError);
        return body;
      })
      .then(setPeriodo)
      .catch(err => {
        if (err.name !== 'AbortError') setError(err.message || copy.messages.periodError);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCargandoPeriodo(false);
      });
    return () => controller.abort();
  }, [activeSection, copy.messages.expired, copy.messages.periodError, onLogout, session.access]);

  async function seleccionarMateria(materia) {
    const horario = (horarios[materia.id] || '').trim();
    const salon = salones[materia.id] || materia.salon || '';
    if (!horario) { setError(copy.courses.scheduleMissing); return; }
    if (!salon) { setError(copy.courses.roomMissing); return; }
    try {
      const response = await fetch(`/api/docente/catalogo-materias/${materia.id}/`, {method: 'PATCH', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({horario, salon})});
      if (response.status === 401) { onLogout(copy.messages.expired); return; }
      if (!response.ok) { const body = await response.json().catch(() => ({})); setError(body.detail || copy.courses.assignError); return; }
      setError(''); setCatalogo(items => items.map(item => item.id === materia.id ? {...item, profesor: datos?.docente?.nombre || copy.brand, horario, salon} : item));
    } catch { setError(copy.courses.connectionError); return; }
    cargarPanel(new AbortController().signal);
  }

  const handleCalificacionChange = (event) => {
    const {name, value} = event.target;
    setCalificacionForm((prev) => ({...prev, [name]: value}));
  };

  const handleCalificacionSubmit = async (event) => {
    event.preventDefault();
    if (!materiaCalificacionId || !calificacionForm.inscripcion_id || !calificacionForm.calificacion) {
      setError(copy.grading.studentRequired);
      return;
    }
    const inscripcionSeleccionada = inscripcionesFiltradasCalificacion.find(
      inscripcion => String(inscripcion.id) === String(calificacionForm.inscripcion_id),
    );
    if (!inscripcionSeleccionada) {
      setError(copy.grading.studentRequired);
      return;
    }

    try {
      const response = await fetch('/api/docente/calificaciones/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(calificacionForm.numero_parcial === 'final' ? {inscripcion_id: calificacionForm.inscripcion_id, calificacion: calificacionForm.calificacion} : {inscripcion_id: calificacionForm.inscripcion_id, parcial: calificacionForm.calificacion, numero_parcial: calificacionForm.numero_parcial}),
      });

      const contentType = response.headers.get('content-type') || '';
      const data = contentType.includes('application/json') ? await response.json().catch(() => null) : null;
      if (!response.ok) {
        const errData = data || {};
        setError(errData.error || copy.grading.saveError);
        return;
      }
      if (!data || data.id == null) {
        throw new Error(copy.grading.saveError);
      }

      setDatos(actual => actual ? {
        ...actual,
        inscripciones: actual.inscripciones.map(inscripcion => (
          String(inscripcion.id) === String(data.id) ? data : inscripcion
        )),
      } : actual);
      setShowCalificacionForm(false);
      setCalificacionForm({inscripcion_id: '', calificacion: '', parcial: '', numero_parcial: '1'});
      setError('');
      await cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || copy.grading.saveError);
    }
  };

  function abrirFormularioCalificacion() {
    setMateriaCalificacionId('');
    setCalificacionForm({inscripcion_id: '', calificacion: '', parcial: '', numero_parcial: '1'});
    setError('');
    setShowCalificacionForm(true);
  }

  function cerrarFormularioCalificacion() {
    setShowCalificacionForm(false);
    setMateriaCalificacionId('');
    setCalificacionForm({inscripcion_id: '', calificacion: '', parcial: '', numero_parcial: '1'});
  }

  async function programarEntrevista(event) {
    event.preventDefault();
    if (!entrevistaForm.aspirante_id || !entrevistaForm.fecha_programada) {
      setError(copy.interviews.studentDateRequired);
      return;
    }
    setEntrevistaGuardando(true);
    setError('');
    try {
      const response = await fetch('/api/docente/entrevistas/', {
        method: 'POST',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({
          ...entrevistaForm,
          aspirante_id: Number(entrevistaForm.aspirante_id),
          duracion_minutos: Number(entrevistaForm.duracion_minutos) || 30,
          fecha_programada: new Date(entrevistaForm.fecha_programada).toISOString(),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(body.error || body.detail || copy.interviews.scheduleError);
      }
      setMostrarEntrevistaForm(false);
      setEntrevistaForm({aspirante_id: '', proposito: 'seguimiento', titulo: 'Entrevista virtual', descripcion: '', fecha_programada: '', duracion_minutos: 30});
      await cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || copy.interviews.scheduleError);
    } finally {
      setEntrevistaGuardando(false);
    }
  }

  async function actualizarEntrevista(id, cambios) {
    setError('');
    try {
      const response = await fetch(`/api/docente/entrevistas/${id}/`, {
        method: 'PUT',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify(cambios),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.error || body.detail || copy.interviews.updateError);
      await cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || copy.interviews.updateError);
    }
  }

  async function actualizarExamen(id, cambios) {
    setError('');
    try {
      const response = await fetch(`/api/docente/examenes/${id}/`, {
        method: 'PUT',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify(cambios),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.error || body.detail || copy.exams.updateError);
      await cargarPanel(new AbortController().signal);
      return true;
    } catch (err) {
      setError(err.message || copy.exams.updateError);
      return false;
    }
  }

  function calificarExamen(examen) {
    setExamenCalificar(examen);
    setExamenCalificacionForm({
      calificacion: examen.calificacion ?? '',
      retroalimentacion: examen.retroalimentacion || '',
    });
    setError('');
  }

  async function guardarCalificacionExamen(event) {
    event.preventDefault();
    const calificacion = Number(examenCalificacionForm.calificacion);
    if (!Number.isFinite(calificacion) || calificacion < 0 || calificacion > 10) {
      setError(copy.exams.gradeRange);
      return;
    }
    setGuardandoExamen(true);
    try {
      const actualizado = await actualizarExamen(examenCalificar.id, {
        calificacion,
        retroalimentacion: examenCalificacionForm.retroalimentacion,
      });
      if (actualizado) setExamenCalificar(null);
    } finally {
      setGuardandoExamen(false);
    }
  }

  function cambiarEstadoEntrevista(entrevista, estado) {
    let notas = entrevista.notas_docente || '';
    if (estado === 'completada') {
      const captura = window.prompt(copy.interviews.notesPrompt, notas);
      if (captura === null) return;
      notas = captura;
    }
    actualizarEntrevista(entrevista.id, {estado, notas_docente: notas});
  }

  function exportarCalificaciones() {
    if (!inscripcionesFiltradasExportacion.length) {
      setError(copy.grading.courseLoad);
      return;
    }
    const encabezados = copy.grading.exportHeaders;
    const escapar = valor => `"${String(valor ?? '').replace(/"/g, '""')}"`;
    const filas = inscripcionesFiltradasExportacion.map(item => [
      item.aspirante?.nombre,
      item.aspirante?.usuario,
      item.materia_clave,
      item.aspirante?.programa,
      item.parcial_1,
      item.parcial_2,
      item.parcial_3,
      item.calificacion,
      etiquetaEstado(item.estado, copy),
    ]);
    const contenido = [encabezados, ...filas].map(fila => fila.map(escapar).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([`\ufeff${contenido}`], {type: 'text/csv;charset=utf-8'}));
    const enlace = document.createElement('a');
    enlace.href = url;
    const materia = datos.materias.find(item => String(item.id) === materiaCalificacionesFiltro);
    const claveArchivo = materia?.clave.replace(/[<>:"/\\|?*]/g, '-');
    enlace.download = materia ? `calificaciones_${claveArchivo}.csv` : 'calificaciones_docente.csv';
    enlace.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    setError('');
  }

  return (
    <section className="admin-dashboard docente-dashboard" aria-label={copy.panel}>
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
            <div className="admin-brand-mark docente-brand-mark">{datos?.docente?.profile_photo ? <img style={{width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'inherit'}} src={fotoUrl(datos.docente.profile_photo)} alt={copy.brand} /> : 'D'}</div>
          <div>
            <p className="panel-kicker">{copy.operations}</p>
            <h2>{copy.brand}</h2>
            <small>{copy.brandSubtitle}</small>
          </div>
        </div>

        <nav className="admin-menu" aria-label={copy.panel}>
          {MENU_ITEMS.map(group => <div className="docente-nav-group" key={group.label}><p>{copy.groups[group.label]}</p>{group.items.map(([id, , icon]) => <button key={id} type="button" className={`admin-menu-item ${activeSection === id ? 'is-active' : ''}`} onClick={() => setActiveSection(id)}><i aria-hidden="true">{icon}</i><span>{copy.menu[id]}</span><small>{id === 'cursos' && (datos?.resumen?.total_materias || 0)}{id === 'estudiantes' && totalEstudiantes}{id === 'calificaciones' && (datos?.resumen?.total_inscripciones || 0)}{id === 'examenes' && (datos?.resumen?.examenes_total || 0)}{id === 'solicitudes' && (datos?.resumen?.solicitudes_pendientes || 0)}</small></button>)}</div>)}
        </nav>

        <div className="admin-side-card">
          <p>{copy.reports.kicker}</p>
          <strong>{datos?.resumen?.total_materias || 0}</strong>
          <span>{copy.overview.assigned}</span>
        </div>

        <button type="button" className="admin-logout" onClick={() => onLogout(copy.logout)}>{copy.logout}</button>
      </aside>

      <main className="admin-main-panel">
        <header className="admin-topbar">
          <div>
            <p className="panel-kicker">{copy.kicker}</p>
            <h1>{copy.panel}</h1>
          </div>
          <div className="admin-top-actions">
            <button type="button" className="btn-primary" disabled={!datos?.inscripciones?.length} onClick={abrirFormularioCalificacion}>+ {copy.common.registerGrade}</button>
          </div>
        </header>

        {error && <div className="api-error" role="alert">{error}</div>}
        {cargando && !datos && <div className="panel-card">{copy.loading}</div>}

        {activeSection !== 'overview' && !datos && cargando && (
          <div className="panel-card">{copy.loadingData}</div>
        )}

        {activeSection === 'overview' && datos && (
          <>
            <div className="admin-stat-grid">
              <div className="admin-stat-card accent">
                <span>{copy.overview.courses}</span>
                <strong>{datos.resumen.total_materias}</strong>
                <small>{copy.overview.assigned}</small>
              </div>
              <div className="admin-stat-card">
                <span>{copy.overview.students}</span>
                <strong>{totalEstudiantes}</strong>
                <small>{copy.reports.totalStudents}</small>
              </div>
              <div className="admin-stat-card">
                <span>{copy.overview.passed}</span>
                <strong>{datos.resumen.inscripciones_aprobadas}</strong>
                <small>{copy.common.academicStatus}</small>
              </div>
              <div className="admin-stat-card">
                <span>{copy.overview.exams}</span>
                <strong>{datos.resumen.examenes_total}</strong>
                <small>{copy.overview.online}</small>
              </div>
              <div className="admin-stat-card">
                <span>{copy.overview.interviews}</span>
                <strong>{datos.resumen.entrevistas_total || 0}</strong>
                <small>{copy.reports.allInterviews}</small>
              </div>
              <div className="admin-stat-card">
                <span>{copy.overview.requests}</span>
                <strong>{datos.resumen.solicitudes_pendientes}</strong>
                <small>{copy.overview.toReview}</small>
              </div>
            </div>

            <div className="admin-grid-layout">
              <div className="admin-card admin-card-wide">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">{copy.overview.courseKicker}</p>
                    <h3>{copy.overview.mySubjects}</h3>
                  </div>
                </div>
                {datos.materias.length ? (
                  <div className="materias-grid">
                    {datos.materias.map((materia) => (
                      <button key={materia.id} type="button" className="materia-card docente-course-link" onClick={() => {setCursoSeleccionado(materia); setActiveSection('cursos');}}>
                        <h4>{materia.clave}</h4>
                        <p>{materia.nombre}</p>
                        <small>{copy.common.schedule}: {materia.horario || '—'}</small>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="empty-state">{copy.common.noSubjects}</p>
                )}
              </div>

              <div className="admin-card">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">{copy.overview.activity}</p>
                    <h3>{copy.overview.recent}</h3>
                  </div>
                </div>
                <ul className="activity-list">
                  {datos.solicitudes.slice(0, 3).map((solicitud) => (
                    <li key={solicitud.id}>
                      <strong>{solicitud.tipo_label || solicitud.tipo}</strong>
                      <span>{etiquetaEstado(solicitud.estado, copy)}</span>
                      <button type="button" className="icon-btn" onClick={() => {
                        setSolicitudesFiltro({
                          aspiranteId: solicitud.aspirante?.id ? String(solicitud.aspirante.id) : '',
                          tipo: solicitud.tipo || '',
                          estado: solicitud.estado || '',
                        });
                        setActiveSection('solicitudes');
                      }}>{copy.common.view}</button>
                    </li>
                  ))}
                  {datos.solicitudes.length === 0 && <li><strong>{copy.common.noRequests}</strong><span>{copy.common.allResolved}</span></li>}
                </ul>
              </div>
            </div>
          </>
        )}

        {activeSection === 'cursos' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">{copy.courses.kicker}</p>
                <h3>{cursoSeleccionado ? cursoSeleccionado.nombre : copy.courses.mySubjects}</h3>
              </div>
            </div>

            {cursoSeleccionado ? (
              <>
                <div className="curso-detalles">
                  <div><strong>{copy.courses.key}:</strong> {cursoSeleccionado.clave}</div>
                  <div><strong>{copy.courses.schedule}:</strong> {cursoSeleccionado.horario || '—'}</div>
                  <button type="button" className="btn-secondary" onClick={() => setCursoSeleccionado(null)}>← {copy.courses.back}</button>
                </div>
                <h4 style={{marginTop: '20px'}}>{copy.courses.enrolled}</h4>
                <div className="admin-table-wrap">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>{copy.common.student}</th>
                        <th>{copy.common.user}</th>
                        <th>{copy.common.program}</th>
                        <th>{copy.common.status}</th>
                          <th>{copy.common.partials} 1</th><th>{copy.common.partials} 2</th><th>{copy.common.partials} 3</th><th>{copy.common.final}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {datos.inscripciones.filter((i) => i.materia === cursoSeleccionado.id).map((inscripcion) => (
                        <tr key={inscripcion.id}>
                          <td><strong>{inscripcion.aspirante.nombre || 'N/A'}</strong></td>
                          <td>{inscripcion.aspirante.usuario || 'N/A'}</td>
                          <td>{inscripcion.aspirante.programa || 'N/A'}</td>
                          <td><span className={`estado-badge estado-${inscripcion.estado}`}>{etiquetaEstado(inscripcion.estado, copy)}</span></td>
                          <td>{inscripcion.parcial_1 ?? '-'}</td><td>{inscripcion.parcial_2 ?? '-'}</td><td>{inscripcion.parcial_3 ?? '-'}</td><td><strong>{inscripcion.calificacion ?? '-'}</strong></td>
                        </tr>
                      ))}
        </tbody>
      </table>
                </div>
              </>
            ) : (
              <div className="materias-grid">
                {datos.materias.map((materia) => (
                  <div key={materia.id} className="materia-card" onClick={() => setCursoSeleccionado(materia)}>
                    <h4>{materia.clave}</h4>
                    <p>{materia.nombre}</p>
                    <small>{copy.common.schedule}: {materia.horario || '—'}</small>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSection === 'catalogo' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">{copy.courses.selectTitle}</p>
                <h3>{copy.courses.choose}</h3>
              </div>
            </div>
            <p className="panel-sub">{copy.courses.intro}</p>
            <p className="panel-sub">
              <strong>{copy.courses.currentPeriod}:</strong>{' '}
              {cargandoPeriodo ? copy.courses.loadingPeriod : periodo?.nombre || copy.courses.periodNotConfigured}
            </p>
            <div className="materias-grid">
              {catalogo.map(materia => {
                const propia = materia.profesor && materia.profesor.toLowerCase() === datos.docente.nombre.toLowerCase();
                const ocupada = Boolean(materia.profesor) && !propia;
                return (
                  <div key={materia.id} className={`materia-card ${propia ? 'is-selected' : ''}`}>
                    <span className="materia-card-clave">{materia.clave}</span>
                    <strong className="materia-card-nombre">{materia.nombre}</strong>
                    <small>{copy.courses.professor}: {materia.profesor || copy.courses.available} · {materia.inscritos || 0} {copy.courses.of} {materia.capacidad || 42} {copy.courses.students}</small>
                    <input className="calificacion-form-input" disabled={ocupada} placeholder={copy.courses.schedulePlaceholder} value={horarios[materia.id] ?? materia.horario ?? ''} onChange={event => setHorarios(previous => ({...previous, [materia.id]: event.target.value}))}/>
                    <select className="calificacion-form-input" disabled={ocupada} value={salones[materia.id] ?? materia.salon ?? ''} onChange={event => setSalones(previous => ({...previous, [materia.id]: event.target.value}))}>
                      <option value="">{copy.courses.selectRoom}</option>
                      <option value="salon_1">{copy.courses.roomOne}</option>
                      <option value="laboratorio_harold">{copy.courses.roomLab}</option>
                      <option value="sala_juntas">{copy.courses.meetingRoom}</option>
                    </select>
                    <button type="button" className="btn-primary" disabled={ocupada} onClick={() => seleccionarMateria(materia)}>
                      {ocupada ? copy.courses.assignedElsewhere : propia ? copy.courses.updateSchedule : copy.courses.selectSubject}
                    </button>
                  </div>
                );
              })}
            </div>
            {!catalogo.length && <p className="empty-state">{copy.courses.catalogEmpty}</p>}
          </div>
        )}

        {activeSection === 'estudiantes' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div><p className="panel-kicker">{copy.courses.kicker}</p><h3>{copy.menu.estudiantes}</h3><p className="panel-sub">{copy.courses.intro}</p></div>
            </div>
            <div className="docente-filter-bar">
              <label><span>{copy.filters.subject}</span>
                <select value={materiaEstudiantesFiltro} onChange={event => setMateriaEstudiantesFiltro(event.target.value)}>
                  <option value="">{copy.filters.allSubjects}</option>
                  {datos.materias.map(materia => <option key={materia.id} value={materia.id}>{materia.clave} - {materia.nombre}</option>)}
                </select>
              </label>
            </div>
            <div className="docente-materias-sections">{materiasEstudiantesFiltradas.length ? materiasEstudiantesFiltradas.map(materia => <TablaAlumnosMateria key={materia.id} materia={materia} inscripciones={datos.inscripciones} copy={copy} />) : <p className="empty-state">{copy.common.noSubjects}</p>}</div>
          </div>
        )}

        {activeSection === 'calificaciones' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div><p className="panel-kicker">{copy.grading.kicker}</p><h3>{copy.grading.title}</h3><p className="panel-sub">{copy.grading.intro}</p></div>
              <button type="button" className="btn-secondary" disabled={!inscripcionesFiltradasExportacion.length} onClick={exportarCalificaciones}>{copy.common.export}</button>
            </div>
            <div className="docente-filter-bar">
              <label><span>{copy.filters.subject}</span>
                <select value={materiaCalificacionesFiltro} onChange={event => setMateriaCalificacionesFiltro(event.target.value)}>
                  <option value="">{copy.filters.allSubjects}</option>
                  {datos.materias.map(materia => <option key={materia.id} value={materia.id}>{materia.clave} - {materia.nombre}</option>)}
                </select>
              </label>
            </div>
            <div className="docente-materias-sections">{materiasCalificacionesFiltradas.length ? materiasCalificacionesFiltradas.map(materia => <TablaAlumnosMateria key={materia.id} materia={materia} inscripciones={datos.inscripciones} copy={copy} soloCalificaciones />) : <p className="empty-state">{copy.common.noSubjects}</p>}</div>
          </div>
        )}

        {activeSection === 'examenes' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">{copy.exams.kicker}</p>
                <h3>{copy.exams.title}</h3>
              </div>
            </div>

            <div className="docente-filter-bar">
              <label><span>{copy.filters.student}</span>
                <select value={examenesFiltro.aspiranteId} onChange={event => setExamenesFiltro(previous => ({...previous, aspiranteId: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {estudiantesDocente.map(estudiante => <option key={estudiante.id} value={estudiante.id}>{estudiante.nombre} ({estudiante.usuario})</option>)}
                </select>
              </label>
              <label><span>{copy.filters.type}</span>
                <select value={examenesFiltro.tipo} onChange={event => setExamenesFiltro(previous => ({...previous, tipo: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {examenesTipos.map(([tipo, label]) => <option key={tipo} value={tipo}>{label}</option>)}
                </select>
              </label>
              <label><span>{copy.filters.status}</span>
                <select value={examenesFiltro.estado} onChange={event => setExamenesFiltro(previous => ({...previous, estado: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {['programado', 'iniciado', 'completado', 'aprobado', 'reprobado', 'cancelado'].map(estado => <option key={estado} value={estado}>{etiquetaEstado(estado, copy)}</option>)}
                </select>
              </label>
            </div>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{copy.exams.student}</th>
                    <th>{copy.exams.type}</th>
                    <th>{copy.exams.scheduled}</th>
                    <th>{copy.exams.status}</th>
                    <th>{copy.exams.grade}</th>
                    <th>{copy.exams.attempts}</th>
                    <th>{copy.exams.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {examenesFiltrados.length > 0 ? (
                    examenesFiltrados.map((examen) => (
                      <tr key={examen.id}>
                        <td><strong>{examen.aspirante?.nombre || 'N/A'}</strong></td>
                        <td>{examen.tipo_label || examen.tipo}</td>
                        <td>{examen.fecha_programada ? new Intl.DateTimeFormat(copy.locale, {dateStyle: 'short', timeStyle: 'short'}).format(new Date(examen.fecha_programada)) : '-'}</td>
                        <td><span className={`estado-badge estado-${examen.estado}`}>{etiquetaEstado(examen.estado, copy)}</span></td>
                        <td><strong>{examen.calificacion !== null ? examen.calificacion : '-'}</strong></td>
                        <td>{examen.intentos}/{examen.max_intentos}</td>
                        <td><div className="table-action-group">{examen.tipo !== 'predoctoral' && ['aprobado', 'reprobado'].includes(examen.estado) && <button type="button" className="link-btn" onClick={() => calificarExamen(examen)}>{copy.exams.gradeAction}</button>}</div></td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan="7" style={{textAlign: 'center', padding: '20px'}}>{datos.examenes?.length ? copy.filters.noResults : copy.exams.none}</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSection === 'entrevistas' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">{copy.interviews.kicker}</p>
                <h3>{copy.interviews.title}</h3>
              </div>
              <button type="button" className="btn-primary" onClick={() => setMostrarEntrevistaForm(value => !value)}>
                {mostrarEntrevistaForm ? copy.interviews.closeForm : `+ ${copy.interviews.schedule}`}
              </button>
            </div>

            {mostrarEntrevistaForm && (
              <form className="entrevista-form" onSubmit={programarEntrevista}>
                <div className="entrevista-form-grid">
                  <label>{copy.interviews.student}
                    <select value={entrevistaForm.aspirante_id} onChange={event => setEntrevistaForm({...entrevistaForm, aspirante_id: event.target.value})} required>
                      <option value="">{copy.interviews.selectStudent}</option>
                      {Array.from(new Map((datos.inscripciones || []).filter(item => item.aspirante?.id).map(item => [item.aspirante.id, item.aspirante])).values()).map(estudiante => (
                        <option key={estudiante.id} value={estudiante.id}>{estudiante.nombre} ({estudiante.usuario})</option>
                      ))}
                    </select>
                  </label>
                  <label>{copy.interviews.purpose}
                    <select value={entrevistaForm.proposito} onChange={event => setEntrevistaForm({...entrevistaForm, proposito: event.target.value})}>
                      <option value="admision">{copy.interviews.purposeOptions.admision}</option>
                      <option value="seguimiento">{copy.interviews.purposeOptions.seguimiento}</option>
                      <option value="tutoria">{copy.interviews.purposeOptions.tutoria}</option>
                      <option value="orientacion">{copy.interviews.purposeOptions.orientacion}</option>
                      <option value="otro">{copy.interviews.purposeOptions.otro}</option>
                    </select>
                  </label>
                  <label>{copy.interviews.titleField}
                    <input value={entrevistaForm.titulo} onChange={event => setEntrevistaForm({...entrevistaForm, titulo: event.target.value})} maxLength="255" required />
                  </label>
                  <label>{copy.interviews.date}
                    <input type="datetime-local" value={entrevistaForm.fecha_programada} onChange={event => setEntrevistaForm({...entrevistaForm, fecha_programada: event.target.value})} required />
                  </label>
                  <label>{copy.interviews.duration}
                    <input type="number" min="15" max="240" step="15" value={entrevistaForm.duracion_minutos} onChange={event => setEntrevistaForm({...entrevistaForm, duracion_minutos: event.target.value})} />
                  </label>
                  <label className="entrevista-form-wide">{copy.interviews.description}
                    <textarea rows="2" value={entrevistaForm.descripcion} onChange={event => setEntrevistaForm({...entrevistaForm, descripcion: event.target.value})} placeholder={copy.interviews.descriptionPlaceholder}/>
                  </label>
                </div>
                <div className="entrevista-form-actions">
                  <button type="submit" className="btn-primary" disabled={entrevistaGuardando}>{entrevistaGuardando ? copy.interviews.saving : copy.interviews.save}</button>
                  <span className="form-hint">{copy.interviews.jitsi}</span>
                </div>
              </form>
            )}

            <div className="docente-filter-bar">
              <label><span>{copy.filters.student}</span>
                <select value={entrevistasFiltro.aspiranteId} onChange={event => setEntrevistasFiltro(previous => ({...previous, aspiranteId: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {estudiantesDocente.map(estudiante => <option key={estudiante.id} value={estudiante.id}>{estudiante.nombre} ({estudiante.usuario})</option>)}
                </select>
              </label>
              <label><span>{copy.filters.purpose}</span>
                <select value={entrevistasFiltro.proposito} onChange={event => setEntrevistasFiltro(previous => ({...previous, proposito: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {entrevistasPropositos.map(([proposito, label]) => <option key={proposito} value={proposito}>{label}</option>)}
                </select>
              </label>
              <label><span>{copy.filters.status}</span>
                <select value={entrevistasFiltro.estado} onChange={event => setEntrevistasFiltro(previous => ({...previous, estado: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {['programada', 'iniciada', 'completada', 'cancelada'].map(estado => <option key={estado} value={estado}>{etiquetaEstado(estado, copy)}</option>)}
                </select>
              </label>
            </div>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{copy.interviews.student}</th>
                    <th>{copy.interviews.purpose}</th>
                    <th>{copy.interviews.scheduled}</th>
                    <th>{copy.common.status}</th>
                    <th>{copy.interviews.jitsiCol}</th>
                    <th>{copy.interviews.notes}</th>
                    <th>{copy.common.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {entrevistasFiltradas.length > 0 ? (
                    entrevistasFiltradas.map((entrevista) => (
                      <tr key={entrevista.id}>
                        <td><strong>{entrevista.aspirante?.nombre || 'N/A'}</strong></td>
                        <td>{entrevista.proposito_label || entrevista.proposito}</td>
                        <td>{entrevista.fecha_programada ? new Intl.DateTimeFormat(copy.locale, {dateStyle: 'short', timeStyle: 'short'}).format(new Date(entrevista.fecha_programada)) : '-'}</td>
                        <td><span className={`estado-badge estado-${entrevista.estado}`}>{etiquetaEstado(entrevista.estado, copy)}</span></td>
                        <td>{entrevista.jitsi_room_link && ['iniciada', 'completada'].includes(entrevista.estado) ? <a href={entrevista.jitsi_room_link} target="_blank" rel="noopener noreferrer" style={{color: '#0066cc'}}>{copy.interviews.join}</a> : (entrevista.estado === 'programada' ? copy.interviews.available : '-')}</td>
                        <td><small>{entrevista.notas_docente ? entrevista.notas_docente.substring(0, 50) + (entrevista.notas_docente.length > 50 ? '…' : '') : '-'}</small></td>
                        <td>
                          <div className="table-action-group">
                            {entrevista.estado === 'programada' && <button type="button" className="link-btn" onClick={() => cambiarEstadoEntrevista(entrevista, 'iniciada')}>{copy.interviews.start}</button>}
                            {entrevista.estado === 'iniciada' && <button type="button" className="link-btn" onClick={() => cambiarEstadoEntrevista(entrevista, 'completada')}>{copy.interviews.finish}</button>}
                            {['programada', 'iniciada'].includes(entrevista.estado) && <button type="button" className="link-btn danger" onClick={() => cambiarEstadoEntrevista(entrevista, 'cancelada')}>{copy.interviews.cancel}</button>}
                            {['completada', 'cancelada'].includes(entrevista.estado) && <span className="form-hint">{copy.interviews.noActions}</span>}
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan="7" style={{textAlign: 'center', padding: '20px'}}>{datos.entrevistas?.length ? copy.filters.noResults : copy.interviews.none}</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSection === 'solicitudes' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">{copy.requests.kicker}</p>
                <h3>{copy.requests.title}</h3>
              </div>
            </div>

            <div className="docente-filter-bar">
              <label><span>{copy.filters.student}</span>
                <select value={solicitudesFiltro.aspiranteId} onChange={event => setSolicitudesFiltro(previous => ({...previous, aspiranteId: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {Array.from(new Map((datos.solicitudes || []).filter(item => item.aspirante?.id).map(item => [String(item.aspirante.id), item.aspirante])).values()).map(estudiante => (
                    <option key={estudiante.id} value={estudiante.id}>{estudiante.nombre} ({estudiante.usuario})</option>
                  ))}
                </select>
              </label>
              <label><span>{copy.filters.type}</span>
                <select value={solicitudesFiltro.tipo} onChange={event => setSolicitudesFiltro(previous => ({...previous, tipo: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {solicitudesTipos.map(([tipo, label]) => <option key={tipo} value={tipo}>{label}</option>)}
                </select>
              </label>
              <label><span>{copy.filters.status}</span>
                <select value={solicitudesFiltro.estado} onChange={event => setSolicitudesFiltro(previous => ({...previous, estado: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {['pendiente', 'aceptado', 'rechazado'].map(estado => <option key={estado} value={estado}>{etiquetaEstado(estado, copy)}</option>)}
                </select>
              </label>
            </div>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{copy.requests.student}</th>
                    <th>{copy.requests.type}</th>
                    <th>{copy.requests.comment}</th>
                    <th>{copy.requests.status}</th>
                    <th>{copy.requests.date}</th>
                  </tr>
                </thead>
                <tbody>
                  {solicitudesFiltradas.map((solicitud) => (
                    <tr key={solicitud.id}>
                      <td><strong>{solicitud.aspirante?.nombre || 'N/A'}</strong></td>
                      <td>{solicitud.tipo_label || solicitud.tipo}</td>
                      <td>{solicitud.comentario || '-'}</td>
                      <td><span className={`estado-badge estado-${solicitud.estado}`}>{etiquetaEstado(solicitud.estado, copy)}</span></td>
                      <td>{new Intl.DateTimeFormat(copy.locale, {dateStyle: 'medium'}).format(new Date(solicitud.created_at))}</td>
                    </tr>
                  ))}
                  {!solicitudesFiltradas.length && <tr><td colSpan="5" style={{textAlign: 'center', padding: '20px'}}>{datos.solicitudes?.length ? copy.filters.noResults : copy.common.noRequests}</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSection === 'perfil' && datos && (
          <section className="docente-profile-layout">
            <header className="docente-profile-hero">
              <div className="docente-profile-avatar">
                {datos.docente.profile_photo
                  ? <img src={fotoUrl(datos.docente.profile_photo)} alt={datos.docente.nombre || copy.brand}/>
                  : <span>{(datos.docente.nombre || copy.brand).charAt(0).toUpperCase()}</span>}
              </div>
              <div className="docente-profile-identity">
                <p className="panel-kicker">{copy.menu.perfil}</p>
                <h2>{datos.docente.nombre}</h2>
                <p>{copy.brandSubtitle}</p>
              </div>
              <div className="docente-profile-details">
                <div><span>{copy.common.user}</span><strong>{datos.docente.usuario || '—'}</strong></div>
                <div><span>{copy.common.program}</span><strong>{datos.docente.programa || '—'}</strong></div>
                <div><span>{copy.reports.unit}</span><strong>{datos.docente.unidad || '—'}</strong></div>
              </div>
            </header>
            <div className="docente-profile-sections">
              <MiPerfilAcademico session={session} docenteId={datos.docente.id} onLogout={onLogout} />
              <PerfilAspirante perfil={{...datos.docente, telefono: datos.docente.telefono || ''}} session={session} onActualizado={(actualizado) => setDatos(actual => ({...actual, docente: {...actual.docente, ...actualizado}}))} />
            </div>
          </section>
        )}

        {activeSection === 'reportes' && datos && (
          <section className="docente-report-layout">
            <header className="docente-report-heading">
              <div><p className="panel-kicker">{copy.reports.kicker}</p><h2>{copy.reports.title}</h2><p>{copy.reports.description}</p></div>
            </header>
            <div className="admin-card docente-report-filter">
              <div className="docente-filter-bar">
                <label><span>{copy.filters.subject}</span>
                  <select value={materiaReporteFiltro} onChange={event => setMateriaReporteFiltro(event.target.value)}>
                    <option value="">{copy.filters.allSubjects}</option>
                    {datos.materias.map(materia => <option key={materia.id} value={materia.id}>{materia.clave} - {materia.nombre}</option>)}
                  </select>
                </label>
              </div>
              <p className="docente-report-filter-note">{copy.filters.cohortNote}</p>
            </div>
            <DashboardAnalitico title={copy.reports.analytics} description={copy.reports.description} metrics={[{label:copy.reports.courses, value:materiaReporteFiltro ? 1 : datos.resumen.total_materias}, {label:copy.reports.students, value:reporteEstudianteIds.size}, {label:copy.reports.exams, value:reporteExamenes.length}, {label:copy.reports.interviews, value:reporteEntrevistas.length}]} distribution={[{label:copy.reports.passed, value:reporteAprobados}, {label:copy.reports.failed, value:reporteReprobados}]} />
            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">{copy.reports.kicker}</p>
                  <h3>{copy.reports.title}</h3>
                </div>
              </div>
              <div className="report-list">
                <div><span>{copy.reports.totalStudents}</span><strong>{reporteEstudianteIds.size}</strong></div>
                <div><span>{copy.reports.passed}</span><strong>{reporteAprobados}</strong></div>
                <div><span>{copy.reports.failed}</span><strong>{reporteReprobados}</strong></div>
              </div>
            </div>

            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">{copy.reports.kicker}</p>
                  <h3>{copy.brand}</h3>
                </div>
              </div>
              <div className="docente-report-identity">
                <div><strong>{copy.courses.name}:</strong> {datos.docente.nombre}</div>
                <div><strong>{copy.common.user}:</strong> {datos.docente.usuario}</div>
                <div><strong>{copy.common.program}:</strong> {datos.docente.programa}</div>
                <div><strong>{copy.reports.unit}:</strong> {datos.docente.unidad}</div>
              </div>
            </div>
          </section>
        )}
      </main>

      {showCalificacionForm && (
        <div className="modal-backdrop" onClick={cerrarFormularioCalificacion}>
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="docente-grade-title" onClick={(event) => event.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="panel-kicker">{copy.menu.calificaciones}</p>
                <h3 id="docente-grade-title">{copy.grading.registration}</h3>
              </div>
              <button type="button" className="close-btn" aria-label={copy.grading.cancel} onClick={cerrarFormularioCalificacion}>×</button>
            </div>

            <form onSubmit={handleCalificacionSubmit} className="modal-form">
              <label>{copy.filters.subject}
                <select value={materiaCalificacionId} onChange={event => {setMateriaCalificacionId(event.target.value); setCalificacionForm(previous => ({...previous, inscripcion_id: ''}));}} required>
                  <option value="">{copy.filters.selectSubject}</option>
                  {datos?.materias?.map(materia => <option key={materia.id} value={materia.id}>{materia.clave} - {materia.nombre}</option>)}
                </select>
              </label>
              <label>{copy.grading.number}<select name="numero_parcial" value={calificacionForm.numero_parcial} onChange={handleCalificacionChange}><option value="1">{copy.common.partials} 1</option><option value="2">{copy.common.partials} 2</option><option value="3">{copy.common.partials} 3</option><option value="final">{copy.grading.final}</option></select></label>
              <div className="form-grid">
                <label>
                  {copy.interviews.student}
                  <select name="inscripcion_id" value={calificacionForm.inscripcion_id} onChange={handleCalificacionChange} disabled={!materiaCalificacionId} required>
                    <option value="">{copy.common.selectStudent}</option>
                    {inscripcionesFiltradasCalificacion.map((inscripcion) => (
                      <option key={inscripcion.id} value={inscripcion.id}>
                        {inscripcion.aspirante?.nombre || inscripcion.aspirante?.usuario} ({inscripcion.aspirante?.usuario})
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  {copy.common.grade} (0-10)
                  <input
                    type="number"
                    name="calificacion"
                    value={calificacionForm.calificacion}
                    onChange={handleCalificacionChange}
                    placeholder="8.5"
                    min="0"
                    max="10"
                    step="0.1"
                  />
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={cerrarFormularioCalificacion}>{copy.grading.cancel}</button>
                <button type="submit" className="btn-primary">{copy.common.registerGrade}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {examenCalificar && (
        <div className="modal-backdrop" onClick={() => !guardandoExamen && setExamenCalificar(null)}>
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="docente-exam-grade-title" onClick={event => event.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="panel-kicker">{copy.exams.title}</p>
                <h3 id="docente-exam-grade-title">{copy.exams.gradeAction}</h3>
                <p className="panel-sub">{examenCalificar.aspirante?.nombre} · {examenCalificar.tipo_label || examenCalificar.tipo}</p>
              </div>
              <button type="button" className="close-btn" aria-label={copy.grading.cancel} disabled={guardandoExamen} onClick={() => setExamenCalificar(null)}>×</button>
            </div>
            <form className="modal-form" onSubmit={guardarCalificacionExamen}>
              <label>{copy.common.grade} (0-10)
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.01"
                  required
                  value={examenCalificacionForm.calificacion}
                  onChange={event => setExamenCalificacionForm(previous => ({...previous, calificacion: event.target.value}))}
                />
              </label>
              <label>{copy.filters.feedback}
                <textarea
                  rows="3"
                  value={examenCalificacionForm.retroalimentacion}
                  onChange={event => setExamenCalificacionForm(previous => ({...previous, retroalimentacion: event.target.value}))}
                />
              </label>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" disabled={guardandoExamen} onClick={() => setExamenCalificar(null)}>{copy.grading.cancel}</button>
                <button type="submit" className="btn-primary" disabled={guardandoExamen}>{guardandoExamen ? copy.interviews.saving : copy.common.registerGrade}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
