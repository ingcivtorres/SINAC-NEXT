import React, {useCallback, useEffect, useMemo, useState} from 'react';
import DashboardAnalitico from './DashboardAnalitico';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import MiPerfilAcademico from './MiPerfilAcademico';
import {useTeacherCopy} from './teacherPanelTranslations';
import {TablaHerramientas, TablaPaginacion, useEtiquetasFiltro, useTablaControl} from './TablaControles';
import {alPulsarFondo} from '../a11yModales';

const MENU_ITEMS = [
  {label: 'overview', items: [['overview', '▦']]},
  {label: 'teaching', items: [['cursos', '▤'], ['estudiantes', '♙']]},
  {label: 'evaluation', items: [['calificaciones', '✓'], ['examenes', '✦'], ['entrevistas', '◷']]},
  {label: 'followup', items: [['reportes', '▥'], ['perfil', '●']]},
];

const SESION_EXPIRADA = 'SESION_EXPIRADA';
const CALIFICACION_VACIA = {inscripcion_id: '', calificacion: '', numero_parcial: '1'};
const ENTREVISTA_VACIA = {aspirante_id: '', proposito: 'seguimiento', titulo: 'Entrevista virtual', descripcion: '', fecha_programada: '', duracion_minutos: 30};

function etiquetaEstado(estado, copy) {
  return copy.status[estado] || estado || copy.common.pending;
}

function primerErrorApi(data, fallback) {
  if (!data || typeof data !== 'object') return fallback;
  if (data.error || data.detail) return data.error || data.detail;
  const valor = Object.values(data).find(item => typeof item === 'string' || Array.isArray(item));
  return (Array.isArray(valor) ? valor.join(' ') : valor) || fallback;
}

function deGrupo(inscripciones, materia) {
  return inscripciones.filter(item => (
    String(item.materia) === String(materia.id)
    && String(item.periodo_inscripcion) === String(materia.periodo_inscripcion)
  ));
}

function formatoFecha(valor, locale, opciones = {dateStyle: 'short', timeStyle: 'short'}) {
  return valor ? new Intl.DateTimeFormat(locale, opciones).format(new Date(valor)) : '-';
}

const estadoAcademico = inscripcion => inscripcion.calificacion == null ? 'cursando' : Number(inscripcion.calificacion) < 7 ? 'reprobada' : 'aprobada';

function TablaAlumnosMateria({materia, alumnos, copy, soloCalificaciones = false}) {
  const columnas = soloCalificaciones ? 10 : 9;
  const etiquetas = useEtiquetasFiltro();
  const control = useTablaControl(alumnos, {
    campos: inscripcion => [inscripcion.aspirante?.nombre, inscripcion.aspirante?.usuario, inscripcion.aspirante?.programa],
    filtros: {academico: estadoAcademico, validacion: inscripcion => inscripcion.validacion_servicios || 'pendiente', programa: inscripcion => inscripcion.aspirante?.programa},
  });
  return <section className="docente-materia-section">
    <div className="docente-materia-section-head">
      <div>
        <span className="materia-card-clave">{materia.clave}</span>
        <h4>{materia.nombre}</h4>
        <small>{copy.extra.period}: {materia.periodo_nombre} · {copy.common.schedule}: {materia.horario || '—'} · {alumnos.length} {copy.common.student}{alumnos.length === 1 ? '' : 's'}</small>
        {!materia.calificable && <small> · {copy.extra.closedPeriod}</small>}
      </div>
    </div>
    {alumnos.length > 0 && <div className="docente-materia-tools"><TablaHerramientas control={control} filtros={[
      {clave: 'academico', etiqueta: copy.common.academicStatus, opciones: ['cursando', 'aprobada', 'reprobada'].map(value => ({value, label: copy.status[value]}))},
      ...(soloCalificaciones ? [{clave: 'validacion', etiqueta: copy.extra.validation, opciones: ['pendiente', 'validada', 'observada'].map(value => ({value, label: copy.extra[value] || copy.extra.pendingValidation}))}] : []),
      {clave: 'programa', etiqueta: etiquetas.program},
    ]} /></div>}
    <div className="admin-table-wrap tabla-scroll">
      <table className="admin-table">
        <thead><tr><th>{copy.common.student}</th><th>{copy.common.user}</th><th>{copy.common.program}</th>{soloCalificaciones ? <th>{copy.extra.validation}</th> : <th>{copy.common.status}</th>}<th>{copy.common.partials} 1</th><th>{copy.common.partials} 2</th><th>{copy.common.partials} 3</th><th>{copy.common.final}</th><th>{copy.common.academicStatus}</th>{soloCalificaciones && <th>{copy.grading.lastUpdate}</th>}</tr></thead>
        <tbody>{control.visibles.length ? control.visibles.map(inscripcion => <tr key={inscripcion.id}>
          <td><strong>{inscripcion.aspirante?.nombre || 'N/A'}</strong></td>
          <td>{inscripcion.aspirante?.usuario || 'N/A'}</td>
          <td>{inscripcion.aspirante?.programa || 'N/A'}</td>
          {soloCalificaciones
            ? <td><span className={`estado-badge estado-${inscripcion.validacion_servicios}`}>{copy.extra[inscripcion.validacion_servicios] || copy.extra.pendingValidation}</span></td>
            : <td><span className={`estado-badge estado-${inscripcion.estado}`}>{etiquetaEstado(inscripcion.estado, copy)}</span></td>}
          <td>{inscripcion.parcial_1 ?? '-'}</td><td>{inscripcion.parcial_2 ?? '-'}</td><td>{inscripcion.parcial_3 ?? '-'}</td><td><strong>{inscripcion.calificacion ?? '-'}</strong></td>
          <td><span className={`estado-badge estado-${inscripcion.calificacion == null ? 'cursando' : Number(inscripcion.calificacion) < 7 ? 'reprobada' : 'aprobada'}`}>{inscripcion.calificacion == null ? copy.status.cursando : Number(inscripcion.calificacion) < 7 ? copy.status.reprobada : copy.status.aprobada}</span></td>
          {soloCalificaciones && <td>{formatoFecha(inscripcion.updated_at, copy.locale, {dateStyle: 'medium'})}</td>}
        </tr>) : <tr><td colSpan={columnas} className="docente-empty-cell">{alumnos.length ? copy.filters.noResults : copy.common.noStudents}</td></tr>}</tbody>
      </table>
    </div>
    {alumnos.length > 0 && <div className="docente-materia-tools"><TablaPaginacion control={control} /></div>}
  </section>;
}

export default function PanelDocente({session, onLogout}) {
  const copy = useTeacherCopy();
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [cargando, setCargando] = useState(true);
  const [activeSection, setActiveSection] = useState('overview');
  const [cursoSeleccionado, setCursoSeleccionado] = useState(null);
  const [showCalificacionForm, setShowCalificacionForm] = useState(false);
  const [calificacionForm, setCalificacionForm] = useState(CALIFICACION_VACIA);
  const [asignacionCalificacionId, setAsignacionCalificacionId] = useState('');
  const [guardandoCalificacion, setGuardandoCalificacion] = useState(false);
  const [examenCalificar, setExamenCalificar] = useState(null);
  const [examenCalificacionForm, setExamenCalificacionForm] = useState({calificacion: '', retroalimentacion: ''});
  const [guardandoExamen, setGuardandoExamen] = useState(false);
  const [asignacionEstudiantesFiltro, setAsignacionEstudiantesFiltro] = useState('');
  const [asignacionCalificacionesFiltro, setAsignacionCalificacionesFiltro] = useState('');
  const [asignacionReporteFiltro, setAsignacionReporteFiltro] = useState('');
  const [examenesFiltro, setExamenesFiltro] = useState({aspiranteId: '', tipo: '', estado: ''});
  const [entrevistasFiltro, setEntrevistasFiltro] = useState({aspiranteId: '', proposito: '', estado: ''});
  const [mostrarEntrevistaForm, setMostrarEntrevistaForm] = useState(false);
  const [entrevistaGuardando, setEntrevistaGuardando] = useState(false);
  const [entrevistaForm, setEntrevistaForm] = useState(ENTREVISTA_VACIA);
  const [entrevistaFinalizar, setEntrevistaFinalizar] = useState(null);

  const materias = useMemo(() => datos?.materias || [], [datos]);
  const inscripciones = useMemo(() => datos?.inscripciones || [], [datos]);
  const periodoEnCurso = datos?.periodo_en_curso || null;
  const buscarAsignacion = id => materias.find(item => String(item.asignacion_id) === String(id));
  const puedeCalificar = useCallback(inscripcion => Boolean(
    periodoEnCurso
    && String(inscripcion.periodo_inscripcion) === String(periodoEnCurso.id)
    && inscripcion.validacion_servicios === 'validada'
  ), [periodoEnCurso]);

  const estudiantesDocente = useMemo(() => Array.from(new Map(
    inscripciones.filter(item => item.aspirante?.id).map(item => [String(item.aspirante.id), item.aspirante]),
  ).values()), [inscripciones]);
  const asignacionesCalificables = materias.filter(materia => materia.calificable && deGrupo(inscripciones, materia).some(puedeCalificar));
  const asignacionCalificacion = buscarAsignacion(asignacionCalificacionId);
  const alumnosCalificables = asignacionCalificacion ? deGrupo(inscripciones, asignacionCalificacion).filter(puedeCalificar) : [];

  const materiasEstudiantes = materias.filter(materia => !asignacionEstudiantesFiltro || String(materia.asignacion_id) === asignacionEstudiantesFiltro);
  const materiasCalificaciones = materias.filter(materia => !asignacionCalificacionesFiltro || String(materia.asignacion_id) === asignacionCalificacionesFiltro);
  const inscripcionesExportacion = materiasCalificaciones.flatMap(materia => deGrupo(inscripciones, materia));

  const examenes = useMemo(() => datos?.examenes || [], [datos]);
  const examenesFiltrados = examenes.filter(examen => (
    (!examenesFiltro.aspiranteId || String(examen.aspirante?.id) === examenesFiltro.aspiranteId)
    && (!examenesFiltro.tipo || examen.tipo === examenesFiltro.tipo)
    && (!examenesFiltro.estado || examen.estado === examenesFiltro.estado)
  ));
  const examenesAspirantes = Array.from(new Map(examenes.filter(item => item.aspirante?.id).map(item => [String(item.aspirante.id), item.aspirante])).values());
  const examenesTipos = Array.from(new Map(examenes.map(item => [item.tipo, item.tipo_label || item.tipo])).entries());

  const entrevistas = useMemo(() => datos?.entrevistas || [], [datos]);
  const entrevistasFiltradas = entrevistas.filter(entrevista => (
    (!entrevistasFiltro.aspiranteId || String(entrevista.aspirante?.id) === entrevistasFiltro.aspiranteId)
    && (!entrevistasFiltro.proposito || entrevista.proposito === entrevistasFiltro.proposito)
    && (!entrevistasFiltro.estado || entrevista.estado === entrevistasFiltro.estado)
  ));
  const entrevistasAspirantes = Array.from(new Map(entrevistas.filter(item => item.aspirante?.id).map(item => [String(item.aspirante.id), item.aspirante])).values());
  const entrevistasPropositos = Array.from(new Map(entrevistas.map(item => [item.proposito, item.proposito_label || item.proposito])).entries());
  const proximasEntrevistas = entrevistas.filter(item => item.estado === 'programada').slice(0, 3);
  const examenesTabla = useTablaControl(examenesFiltrados, {campos: examen => [examen.aspirante?.nombre, examen.aspirante?.usuario, examen.titulo, examen.tipo_label]});
  const entrevistasTabla = useTablaControl(entrevistasFiltradas, {campos: entrevista => [entrevista.aspirante?.nombre, entrevista.aspirante?.usuario, entrevista.titulo, entrevista.proposito_label, entrevista.notas_docente]});

  const asignacionReporte = buscarAsignacion(asignacionReporteFiltro);
  const reporteInscripciones = asignacionReporte ? deGrupo(inscripciones, asignacionReporte) : inscripciones;
  const reporteEstudianteIds = new Set(reporteInscripciones.map(item => item.aspirante?.id).filter(Boolean));
  const reporteEntrevistas = entrevistas.filter(entrevista => !asignacionReporte || reporteEstudianteIds.has(entrevista.aspirante?.id));
  const reporteExamenes = examenes.filter(examen => !asignacionReporte || reporteEstudianteIds.has(examen.aspirante?.id));
  const reporteAprobados = reporteInscripciones.filter(item => item.estado === 'aprobada').length;
  const reporteReprobados = reporteInscripciones.filter(item => item.estado === 'reprobada').length;

  const solicitar = useCallback(async (url, {method = 'GET', body, signal} = {}, fallback = copy.messages.loadError) => {
    const response = await fetch(url, {
      method,
      signal,
      headers: {Authorization: `Bearer ${session.access}`, ...(body ? {'Content-Type': 'application/json'} : {})},
      body: body ? JSON.stringify(body) : undefined,
    });
    if (response.status === 401) {
      onLogout(copy.messages.expired);
      throw new Error(SESION_EXPIRADA);
    }
    const data = await response.json().catch(() => null);
    if (response.status === 403 && !data) throw new Error(copy.messages.permission);
    if (!response.ok) throw new Error(primerErrorApi(data, `${fallback} (HTTP ${response.status}).`));
    return data;
  }, [copy.messages.expired, copy.messages.loadError, copy.messages.permission, onLogout, session.access]);

  const mostrarError = useCallback((err, fallback) => {
    if (err.name === 'AbortError' || err.message === SESION_EXPIRADA) return;
    setMensaje('');
    setError(err.message || fallback);
  }, []);

  const cargarPanel = useCallback(async (signal) => {
    setCargando(true);
    try {
      setDatos(await solicitar('/api/docente/panel/', {signal}, copy.messages.loadError));
      setError('');
    } catch (err) {
      mostrarError(err, copy.messages.loadError);
    } finally {
      if (!signal?.aborted) setCargando(false);
    }
  }, [copy.messages.loadError, mostrarError, solicitar]);

  useEffect(() => {
    const controller = new AbortController();
    cargarPanel(controller.signal);
    return () => controller.abort();
  }, [cargarPanel]);

  useEffect(() => {
    setMensaje('');
    setError('');
  }, [activeSection]);

  function exito(texto) {
    setError('');
    setMensaje(texto);
  }

  function abrirFormularioCalificacion() {
    setAsignacionCalificacionId('');
    setCalificacionForm(CALIFICACION_VACIA);
    setError('');
    setShowCalificacionForm(true);
  }

  function cerrarFormularioCalificacion() {
    if (guardandoCalificacion) return;
    setShowCalificacionForm(false);
    setAsignacionCalificacionId('');
    setCalificacionForm(CALIFICACION_VACIA);
  }

  async function guardarCalificacion(event) {
    event.preventDefault();
    const inscripcion = alumnosCalificables.find(item => String(item.id) === String(calificacionForm.inscripcion_id));
    if (!inscripcion || calificacionForm.calificacion === '') {
      setError(copy.grading.studentRequired);
      return;
    }
    const cuerpo = calificacionForm.numero_parcial === 'final'
      ? {inscripcion_id: inscripcion.id, calificacion: calificacionForm.calificacion}
      : {inscripcion_id: inscripcion.id, parcial: calificacionForm.calificacion, numero_parcial: calificacionForm.numero_parcial};
    setGuardandoCalificacion(true);
    try {
      const actualizada = await solicitar('/api/docente/calificaciones/', {method: 'POST', body: cuerpo}, copy.grading.saveError);
      setDatos(actual => actual ? {...actual, inscripciones: actual.inscripciones.map(item => String(item.id) === String(actualizada.id) ? actualizada : item)} : actual);
      setShowCalificacionForm(false);
      setCalificacionForm(CALIFICACION_VACIA);
      exito(copy.extra.gradeSaved);
      cargarPanel();
    } catch (err) {
      mostrarError(err, copy.grading.saveError);
    } finally {
      setGuardandoCalificacion(false);
    }
  }

  async function programarEntrevista(event) {
    event.preventDefault();
    if (!entrevistaForm.aspirante_id || !entrevistaForm.fecha_programada) {
      setError(copy.interviews.studentDateRequired);
      return;
    }
    setEntrevistaGuardando(true);
    try {
      await solicitar('/api/docente/entrevistas/', {
        method: 'POST',
        body: {
          ...entrevistaForm,
          aspirante_id: Number(entrevistaForm.aspirante_id),
          duracion_minutos: Number(entrevistaForm.duracion_minutos) || 30,
          fecha_programada: new Date(entrevistaForm.fecha_programada).toISOString(),
        },
      }, copy.interviews.scheduleError);
      setMostrarEntrevistaForm(false);
      setEntrevistaForm(ENTREVISTA_VACIA);
      exito(copy.extra.interviewScheduled);
      await cargarPanel();
    } catch (err) {
      mostrarError(err, copy.interviews.scheduleError);
    } finally {
      setEntrevistaGuardando(false);
    }
  }

  async function actualizarEntrevista(id, cambios) {
    try {
      await solicitar(`/api/docente/entrevistas/${id}/`, {method: 'PUT', body: cambios}, copy.interviews.updateError);
      exito(copy.extra.interviewUpdated);
      await cargarPanel();
      return true;
    } catch (err) {
      mostrarError(err, copy.interviews.updateError);
      return false;
    }
  }

  async function confirmarFinalizarEntrevista(event) {
    event.preventDefault();
    const {entrevista, notas} = entrevistaFinalizar;
    const actualizada = await actualizarEntrevista(entrevista.id, {estado: 'completada', notas_docente: notas});
    if (actualizada) setEntrevistaFinalizar(null);
  }

  function calificarExamen(examen) {
    setExamenCalificar(examen);
    setExamenCalificacionForm({calificacion: examen.calificacion ?? '', retroalimentacion: examen.retroalimentacion || ''});
    setError('');
  }

  async function guardarCalificacionExamen(event) {
    event.preventDefault();
    const calificacion = Number(examenCalificacionForm.calificacion);
    if (examenCalificacionForm.calificacion === '' || !Number.isFinite(calificacion) || calificacion < 0 || calificacion > 10) {
      setError(copy.exams.gradeRange);
      return;
    }
    setGuardandoExamen(true);
    try {
      await solicitar(`/api/docente/examenes/${examenCalificar.id}/`, {
        method: 'PUT',
        body: {calificacion, retroalimentacion: examenCalificacionForm.retroalimentacion},
      }, copy.exams.updateError);
      setExamenCalificar(null);
      exito(copy.extra.examSaved);
      await cargarPanel();
    } catch (err) {
      mostrarError(err, copy.exams.updateError);
    } finally {
      setGuardandoExamen(false);
    }
  }

  function exportarCalificaciones() {
    if (!inscripcionesExportacion.length) {
      setError(copy.grading.courseLoad);
      return;
    }
    const escapar = valor => `"${String(valor ?? '').replace(/"/g, '""')}"`;
    const filas = inscripcionesExportacion.map(item => [
      item.aspirante?.nombre, item.aspirante?.usuario, item.materia_clave, item.aspirante?.programa,
      item.parcial_1, item.parcial_2, item.parcial_3, item.calificacion, etiquetaEstado(item.estado, copy),
    ]);
    const contenido = [copy.grading.exportHeaders, ...filas].map(fila => fila.map(escapar).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([`\ufeff${contenido}`], {type: 'text/csv;charset=utf-8'}));
    const enlace = document.createElement('a');
    const materia = buscarAsignacion(asignacionCalificacionesFiltro);
    const limpiar = texto => String(texto || '').replace(/[<>:"/\\|?*\s]/g, '-');
    enlace.href = url;
    enlace.download = materia ? `calificaciones_${limpiar(materia.clave)}_${limpiar(materia.periodo_nombre)}.csv` : 'calificaciones_docente.csv';
    enlace.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    setError('');
  }

  const opcionesAsignacion = materias.map(materia => <option key={materia.asignacion_id} value={materia.asignacion_id}>{materia.clave} - {materia.nombre} ({materia.periodo_nombre})</option>);
  const contadores = {
    cursos: datos?.resumen?.total_materias || 0,
    estudiantes: datos?.resumen?.total_estudiantes || 0,
    calificaciones: datos?.resumen?.total_inscripciones || 0,
    examenes: datos?.resumen?.examenes_total || 0,
    entrevistas: datos?.resumen?.entrevistas_programadas || 0,
  };

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
          {MENU_ITEMS.map(group => <div className="docente-nav-group" key={group.label}><p>{copy.groups[group.label]}</p>{group.items.map(([id, icon]) => <button key={id} type="button" className={`admin-menu-item ${activeSection === id ? 'is-active' : ''}`} onClick={() => setActiveSection(id)}><i aria-hidden="true">{icon}</i><span>{copy.menu[id]}</span><small>{contadores[id] ?? ''}</small></button>)}</div>)}
        </nav>

        <div className="admin-side-card">
          <p>{copy.extra.currentPeriod}</p>
          <strong>{periodoEnCurso?.nombre || copy.extra.noPeriod}</strong>
          <span>{contadores.cursos} {copy.overview.assigned.toLowerCase()}</span>
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
            <button type="button" className="btn-secondary" disabled={cargando} onClick={() => cargarPanel()}>{copy.refresh}</button>
            <button type="button" className="btn-primary" disabled={!asignacionesCalificables.length} title={asignacionesCalificables.length ? undefined : copy.extra.noGradable} onClick={abrirFormularioCalificacion}>+ {copy.common.registerGrade}</button>
          </div>
        </header>

        {error && <div className="api-error" role="alert">{error}</div>}
        {mensaje && <div className="api-success" role="status">{mensaje}</div>}
        {cargando && !datos && <div className="panel-card">{copy.loading}</div>}

        {activeSection === 'overview' && datos && (
          <>
            <div className="admin-stat-grid">
              <div className="admin-stat-card accent"><span>{copy.overview.courses}</span><strong>{datos.resumen.total_materias}</strong><small>{copy.overview.assigned}</small></div>
              <div className="admin-stat-card"><span>{copy.overview.students}</span><strong>{datos.resumen.total_estudiantes}</strong><small>{copy.reports.totalStudents}</small></div>
              <div className="admin-stat-card"><span>{copy.overview.passed}</span><strong>{datos.resumen.inscripciones_aprobadas}</strong><small>{copy.common.academicStatus}</small></div>
              <div className="admin-stat-card"><span>{copy.overview.exams}</span><strong>{datos.resumen.examenes_total}</strong><small>{copy.overview.online}</small></div>
              <div className="admin-stat-card"><span>{copy.overview.interviews}</span><strong>{datos.resumen.entrevistas_total}</strong><small>{copy.reports.allInterviews}</small></div>
            </div>

            <div className="admin-grid-layout">
              <div className="admin-card admin-card-wide">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">{copy.overview.courseKicker}</p>
                    <h3>{copy.overview.mySubjects}</h3>
                    <p className="panel-sub">{copy.extra.coursesIntro}</p>
                  </div>
                </div>
                {materias.length ? (
                  <div className="materias-grid">
                    {materias.map(materia => (
                      <button key={materia.asignacion_id} type="button" className="materia-card docente-course-link" onClick={() => {setCursoSeleccionado(materia); setActiveSection('cursos');}}>
                        <h4>{materia.clave}</h4>
                        <p>{materia.nombre}</p>
                        <small>{materia.periodo_nombre} · {copy.common.schedule}: {materia.horario || '—'}</small>
                      </button>
                    ))}
                  </div>
                ) : <p className="empty-state">{copy.common.noSubjects}</p>}
              </div>

              <div className="admin-card">
                <div className="admin-card-head"><div><p className="panel-kicker">{copy.overview.activity}</p><h3>{copy.extra.upcoming}</h3></div></div>
                <ul className="activity-list">
                  {proximasEntrevistas.map(entrevista => (
                    <li key={entrevista.id}>
                      <strong>{entrevista.aspirante?.nombre || entrevista.titulo}</strong>
                      <span>{formatoFecha(entrevista.fecha_programada, copy.locale)}</span>
                      <button type="button" className="icon-btn" onClick={() => setActiveSection('entrevistas')}>{copy.common.view}</button>
                    </li>
                  ))}
                  {!proximasEntrevistas.length && <li><strong>{copy.extra.noUpcoming}</strong></li>}
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
                {!cursoSeleccionado && <p className="panel-sub">{copy.extra.coursesIntro}</p>}
              </div>
            </div>

            {cursoSeleccionado ? (
              <>
                <div className="curso-detalles">
                  <div><strong>{copy.courses.key}:</strong> {cursoSeleccionado.clave}</div>
                  <div><strong>{copy.extra.period}:</strong> {cursoSeleccionado.periodo_nombre}</div>
                  <div><strong>{copy.courses.schedule}:</strong> {cursoSeleccionado.horario || '—'}</div>
                  <div><strong>{copy.extra.room}:</strong> {cursoSeleccionado.salon_label || '—'}</div>
                  <div><strong>{copy.extra.capacity}:</strong> {cursoSeleccionado.inscritos}/{cursoSeleccionado.capacidad}</div>
                  <button type="button" className="btn-secondary" onClick={() => setCursoSeleccionado(null)}>← {copy.courses.back}</button>
                </div>
                <TablaAlumnosMateria materia={cursoSeleccionado} alumnos={deGrupo(inscripciones, cursoSeleccionado)} copy={copy} />
              </>
            ) : materias.length ? (
              <div className="materias-grid">
                {materias.map(materia => (
                  <button key={materia.asignacion_id} type="button" className="materia-card docente-course-link" onClick={() => setCursoSeleccionado(materia)}>
                    <h4>{materia.clave}</h4>
                    <p>{materia.nombre}</p>
                    <small>{materia.periodo_nombre} · {copy.common.schedule}: {materia.horario || '—'} · {materia.inscritos}/{materia.capacidad}</small>
                  </button>
                ))}
              </div>
            ) : <p className="empty-state">{copy.common.noSubjects}</p>}
          </div>
        )}

        {activeSection === 'estudiantes' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div><p className="panel-kicker">{copy.courses.kicker}</p><h3>{copy.menu.estudiantes}</h3><p className="panel-sub">{copy.extra.coursesIntro}</p></div>
            </div>
            <div className="docente-filter-bar">
              <label><span>{copy.filters.subject}</span>
                <select value={asignacionEstudiantesFiltro} onChange={event => setAsignacionEstudiantesFiltro(event.target.value)}>
                  <option value="">{copy.filters.allSubjects}</option>
                  {opcionesAsignacion}
                </select>
              </label>
            </div>
            <div className="docente-materias-sections">{materiasEstudiantes.length ? materiasEstudiantes.map(materia => <TablaAlumnosMateria key={materia.asignacion_id} materia={materia} alumnos={deGrupo(inscripciones, materia)} copy={copy} />) : <p className="empty-state">{copy.common.noSubjects}</p>}</div>
          </div>
        )}

        {activeSection === 'calificaciones' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div><p className="panel-kicker">{copy.grading.kicker}</p><h3>{copy.grading.title}</h3><p className="panel-sub">{copy.grading.intro} {copy.extra.gradableHint}</p></div>
              <button type="button" className="btn-secondary" disabled={!inscripcionesExportacion.length} onClick={exportarCalificaciones}>{copy.common.export}</button>
            </div>
            <div className="docente-filter-bar">
              <label><span>{copy.filters.subject}</span>
                <select value={asignacionCalificacionesFiltro} onChange={event => setAsignacionCalificacionesFiltro(event.target.value)}>
                  <option value="">{copy.filters.allSubjects}</option>
                  {opcionesAsignacion}
                </select>
              </label>
            </div>
            <div className="docente-materias-sections">{materiasCalificaciones.length ? materiasCalificaciones.map(materia => <TablaAlumnosMateria key={materia.asignacion_id} materia={materia} alumnos={deGrupo(inscripciones, materia)} copy={copy} soloCalificaciones />) : <p className="empty-state">{copy.common.noSubjects}</p>}</div>
          </div>
        )}

        {activeSection === 'examenes' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div><p className="panel-kicker">{copy.exams.kicker}</p><h3>{copy.exams.title}</h3><p className="panel-sub">{copy.extra.examsIntro}</p></div>
            </div>

            <div className="docente-filter-bar">
              <label><span>{copy.filters.student}</span>
                <select value={examenesFiltro.aspiranteId} onChange={event => setExamenesFiltro(previous => ({...previous, aspiranteId: event.target.value}))}>
                  <option value="">{copy.filters.all}</option>
                  {examenesAspirantes.map(estudiante => <option key={estudiante.id} value={estudiante.id}>{estudiante.nombre} ({estudiante.usuario})</option>)}
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
            <TablaHerramientas control={examenesTabla} />
            <div className="admin-table-wrap tabla-scroll">
              <table className="admin-table">
                <thead><tr><th>{copy.exams.student}</th><th>{copy.exams.type}</th><th>{copy.exams.scheduled}</th><th>{copy.exams.status}</th><th>{copy.exams.grade}</th><th>{copy.exams.attempts}</th><th>{copy.exams.actions}</th></tr></thead>
                <tbody>
                  {examenesTabla.visibles.length ? examenesTabla.visibles.map(examen => (
                    <tr key={examen.id}>
                      <td><strong>{examen.aspirante?.nombre || 'N/A'}</strong></td>
                      <td>{examen.tipo_label || examen.tipo}</td>
                      <td>{formatoFecha(examen.fecha_programada, copy.locale)}</td>
                      <td><span className={`estado-badge estado-${examen.estado}`}>{etiquetaEstado(examen.estado, copy)}</span></td>
                      <td><strong>{examen.calificacion ?? '-'}</strong></td>
                      <td>{examen.intentos}/{examen.max_intentos}</td>
                      <td><div className="table-action-group">{['aprobado', 'reprobado'].includes(examen.estado) && <button type="button" className="link-btn" onClick={() => calificarExamen(examen)}>{copy.exams.gradeAction}</button>}</div></td>
                    </tr>
                  )) : <tr><td colSpan="7" className="docente-empty-cell">{examenes.length ? copy.filters.noResults : copy.exams.none}</td></tr>}
                </tbody>
              </table>
            </div>
            <TablaPaginacion control={examenesTabla} />
          </div>
        )}

        {activeSection === 'entrevistas' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div><p className="panel-kicker">{copy.interviews.kicker}</p><h3>{copy.interviews.title}</h3></div>
              <button type="button" className="btn-primary" disabled={!estudiantesDocente.length} onClick={() => setMostrarEntrevistaForm(value => !value)}>
                {mostrarEntrevistaForm ? copy.interviews.closeForm : `+ ${copy.interviews.schedule}`}
              </button>
            </div>

            {mostrarEntrevistaForm && (
              <form className="entrevista-form" onSubmit={programarEntrevista}>
                <div className="entrevista-form-grid">
                  <label>{copy.interviews.student}
                    <select value={entrevistaForm.aspirante_id} onChange={event => setEntrevistaForm({...entrevistaForm, aspirante_id: event.target.value})} required>
                      <option value="">{copy.interviews.selectStudent}</option>
                      {estudiantesDocente.map(estudiante => <option key={estudiante.id} value={estudiante.id}>{estudiante.nombre} ({estudiante.usuario})</option>)}
                    </select>
                  </label>
                  <label>{copy.interviews.purpose}
                    <select value={entrevistaForm.proposito} onChange={event => setEntrevistaForm({...entrevistaForm, proposito: event.target.value})}>
                      {['seguimiento', 'tutoria', 'orientacion', 'otro'].map(proposito => <option key={proposito} value={proposito}>{copy.interviews.purposeOptions[proposito]}</option>)}
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
                  {entrevistasAspirantes.map(estudiante => <option key={estudiante.id} value={estudiante.id}>{estudiante.nombre} ({estudiante.usuario})</option>)}
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
            <TablaHerramientas control={entrevistasTabla} />
            <div className="admin-table-wrap tabla-scroll">
              <table className="admin-table">
                <thead><tr><th>{copy.interviews.student}</th><th>{copy.interviews.purpose}</th><th>{copy.interviews.scheduled}</th><th>{copy.common.status}</th><th>{copy.interviews.jitsiCol}</th><th>{copy.interviews.notes}</th><th>{copy.common.actions}</th></tr></thead>
                <tbody>
                  {entrevistasTabla.visibles.length ? entrevistasTabla.visibles.map(entrevista => (
                    <tr key={entrevista.id}>
                      <td><strong>{entrevista.aspirante?.nombre || 'N/A'}</strong></td>
                      <td>{entrevista.proposito_label || entrevista.proposito}</td>
                      <td>{formatoFecha(entrevista.fecha_programada, copy.locale)}</td>
                      <td><span className={`estado-badge estado-${entrevista.estado}`}>{etiquetaEstado(entrevista.estado, copy)}</span></td>
                      <td>{entrevista.jitsi_room_link && ['iniciada', 'completada'].includes(entrevista.estado) ? <a href={entrevista.jitsi_room_link} target="_blank" rel="noopener noreferrer">{copy.interviews.join}</a> : (entrevista.estado === 'programada' ? copy.interviews.available : '-')}</td>
                      <td><small>{entrevista.notas_docente ? entrevista.notas_docente.substring(0, 50) + (entrevista.notas_docente.length > 50 ? '…' : '') : '-'}</small></td>
                      <td>
                        <div className="table-action-group">
                          {entrevista.estado === 'programada' && <button type="button" className="link-btn" onClick={() => actualizarEntrevista(entrevista.id, {estado: 'iniciada'})}>{copy.interviews.start}</button>}
                          {entrevista.estado === 'iniciada' && <button type="button" className="link-btn" onClick={() => setEntrevistaFinalizar({entrevista, notas: entrevista.notas_docente || ''})}>{copy.interviews.finish}</button>}
                          {['programada', 'iniciada'].includes(entrevista.estado) && <button type="button" className="link-btn danger" onClick={() => actualizarEntrevista(entrevista.id, {estado: 'cancelada'})}>{copy.interviews.cancel}</button>}
                          {['completada', 'cancelada'].includes(entrevista.estado) && <span className="form-hint">{copy.interviews.noActions}</span>}
                        </div>
                      </td>
                    </tr>
                  )) : <tr><td colSpan="7" className="docente-empty-cell">{entrevistas.length ? copy.filters.noResults : copy.interviews.none}</td></tr>}
                </tbody>
              </table>
            </div>
            <TablaPaginacion control={entrevistasTabla} />
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
                  <select value={asignacionReporteFiltro} onChange={event => setAsignacionReporteFiltro(event.target.value)}>
                    <option value="">{copy.filters.allSubjects}</option>
                    {opcionesAsignacion}
                  </select>
                </label>
              </div>
              <p className="docente-report-filter-note">{copy.filters.cohortNote}</p>
            </div>
            <DashboardAnalitico title={copy.reports.analytics} description={copy.reports.description} metrics={[{label: copy.reports.courses, value: asignacionReporte ? 1 : datos.resumen.total_materias}, {label: copy.reports.students, value: reporteEstudianteIds.size}, {label: copy.reports.exams, value: reporteExamenes.length}, {label: copy.reports.interviews, value: reporteEntrevistas.length}]} distribution={[{label: copy.reports.passed, value: reporteAprobados}, {label: copy.reports.failed, value: reporteReprobados}]} />
            <div className="admin-card">
              <div className="admin-card-head"><div><p className="panel-kicker">{copy.reports.kicker}</p><h3>{copy.reports.title}</h3></div></div>
              <div className="report-list">
                <div><span>{copy.reports.totalStudents}</span><strong>{reporteEstudianteIds.size}</strong></div>
                <div><span>{copy.reports.passed}</span><strong>{reporteAprobados}</strong></div>
                <div><span>{copy.reports.failed}</span><strong>{reporteReprobados}</strong></div>
              </div>
            </div>
            <div className="admin-card">
              <div className="admin-card-head"><div><p className="panel-kicker">{copy.reports.kicker}</p><h3>{copy.brand}</h3></div></div>
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
        <div className="modal-backdrop" role="presentation" onClick={alPulsarFondo(cerrarFormularioCalificacion)}>
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="docente-grade-title">
            <div className="modal-head">
              <div>
                <p className="panel-kicker">{copy.menu.calificaciones}</p>
                <h3 id="docente-grade-title">{copy.grading.registration}</h3>
                <p className="panel-sub">{copy.extra.currentPeriod}: {periodoEnCurso?.nombre || copy.extra.noPeriod}. {copy.extra.gradableHint}</p>
              </div>
              <button type="button" className="close-btn" aria-label={copy.grading.cancel} disabled={guardandoCalificacion} onClick={cerrarFormularioCalificacion}>×</button>
            </div>

            <form onSubmit={guardarCalificacion} className="modal-form">
              <label>{copy.filters.subject}
                <select value={asignacionCalificacionId} onChange={event => {setAsignacionCalificacionId(event.target.value); setCalificacionForm(previous => ({...previous, inscripcion_id: ''}));}} required>
                  <option value="">{copy.filters.selectSubject}</option>
                  {asignacionesCalificables.map(materia => <option key={materia.asignacion_id} value={materia.asignacion_id}>{materia.clave} - {materia.nombre}</option>)}
                </select>
              </label>
              <label>{copy.grading.number}
                <select value={calificacionForm.numero_parcial} onChange={event => setCalificacionForm(previous => ({...previous, numero_parcial: event.target.value}))}>
                  <option value="1">{copy.common.partials} 1</option><option value="2">{copy.common.partials} 2</option><option value="3">{copy.common.partials} 3</option><option value="final">{copy.grading.final}</option>
                </select>
              </label>
              <div className="form-grid">
                <label>{copy.interviews.student}
                  <select value={calificacionForm.inscripcion_id} onChange={event => setCalificacionForm(previous => ({...previous, inscripcion_id: event.target.value}))} disabled={!asignacionCalificacion} required>
                    <option value="">{copy.common.selectStudent}</option>
                    {alumnosCalificables.map(inscripcion => <option key={inscripcion.id} value={inscripcion.id}>{inscripcion.aspirante?.nombre || inscripcion.aspirante?.usuario} ({inscripcion.aspirante?.usuario})</option>)}
                  </select>
                </label>
                <label>{copy.common.grade} (0-10)
                  <input type="number" value={calificacionForm.calificacion} onChange={event => setCalificacionForm(previous => ({...previous, calificacion: event.target.value}))} placeholder="8.5" min="0" max="10" step="0.01" required />
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" disabled={guardandoCalificacion} onClick={cerrarFormularioCalificacion}>{copy.grading.cancel}</button>
                <button type="submit" className="btn-primary" disabled={guardandoCalificacion}>{guardandoCalificacion ? copy.interviews.saving : copy.common.registerGrade}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {examenCalificar && (
        <div className="modal-backdrop" role="presentation" onClick={alPulsarFondo(() => !guardandoExamen && setExamenCalificar(null))}>
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="docente-exam-grade-title">
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
                <input type="number" min="0" max="10" step="0.01" required value={examenCalificacionForm.calificacion} onChange={event => setExamenCalificacionForm(previous => ({...previous, calificacion: event.target.value}))} />
              </label>
              <label>{copy.filters.feedback}
                <textarea rows="3" value={examenCalificacionForm.retroalimentacion} onChange={event => setExamenCalificacionForm(previous => ({...previous, retroalimentacion: event.target.value}))} />
              </label>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" disabled={guardandoExamen} onClick={() => setExamenCalificar(null)}>{copy.grading.cancel}</button>
                <button type="submit" className="btn-primary" disabled={guardandoExamen}>{guardandoExamen ? copy.interviews.saving : copy.common.registerGrade}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {entrevistaFinalizar && (
        <div className="modal-backdrop" role="presentation" onClick={alPulsarFondo(() => setEntrevistaFinalizar(null))}>
          <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="docente-interview-finish-title">
            <div className="modal-head">
              <div>
                <p className="panel-kicker">{copy.interviews.title}</p>
                <h3 id="docente-interview-finish-title">{copy.extra.finishTitle}</h3>
                <p className="panel-sub">{entrevistaFinalizar.entrevista.aspirante?.nombre} · {entrevistaFinalizar.entrevista.titulo}</p>
              </div>
              <button type="button" className="close-btn" aria-label={copy.extra.close} onClick={() => setEntrevistaFinalizar(null)}>×</button>
            </div>
            <form className="modal-form" onSubmit={confirmarFinalizarEntrevista}>
              <label>{copy.extra.notesLabel}
                <textarea rows="4" autoFocus value={entrevistaFinalizar.notas} onChange={event => setEntrevistaFinalizar(previous => ({...previous, notas: event.target.value}))} />
              </label>
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setEntrevistaFinalizar(null)}>{copy.grading.cancel}</button>
                <button type="submit" className="btn-primary">{copy.extra.confirmFinish}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
