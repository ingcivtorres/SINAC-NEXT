import React, {useCallback, useEffect, useMemo, useState} from 'react';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import ExamenesEnLinea from './ExamenesEnLinea';
import {useStudentCopy} from './studentPanelTranslations';
import thesisWorkflowTranslations from './tesisWorkflowTranslations';
import './PanelAlumno.css';
import './PanelAlumnoFixes.css';

const MENU = [
  {label: 'space', items: [['resumen', 'Resumen', '\u2302'], ['perfil', 'Mi perfil', '\u263A']]},
  {label: 'academic', items: [['materias', 'Materias e inscripciones', '\u25A6'], ['calificaciones', 'Calificaciones y avance', '\u2713'], ['horario', 'Horario', '\u25F7']]},
  {label: 'communication', items: [['solicitudes', 'Solicitudes académicas', '\u2709'], ['entrevistas', 'Entrevistas virtuales', '\u25C9']]},
  {label: 'thesisDocs', items: [['tesis', 'Proyecto de tesis', '\u25C7'], ['predoctoral', 'Examen predoctoral', '\u2736'], ['diploma', 'Diploma digital', '\u25C8'], ['tramites', 'Documentos y trámites', '\u25A4']]},
];

function InfoRow({label, value}) { return <div className="info-row"><span>{label}</span><strong>{value || '-'}</strong></div>; }
function Badge({children, tone = 'neutral'}) { return <span className={`badge badge--${tone}`}>{children}</span>; }
function etiquetaEstado(estado, copy) {
  const key = String(estado || '').toLowerCase();
  const aliases = {revision:'en_revision', aprobado:'approved', aprobada:'aprobada', aceptado:'aprobada'};
  return copy.extra.apiStatus[key] || copy.extra.apiStatus[aliases[key]] || copy.status[key] || copy.common.pending;
}
function estadoMateria(materia, copy) {
  if (materia.calificacion === null || materia.calificacion === undefined || materia.calificacion === '') {
    return {key: 'cursando', label: copy.status.cursando, tone: 'neutral', aviso: ''};
  }
  const nota = Number(materia.calificacion);
  if (!Number.isFinite(nota) || nota < 7) {
    return {key: 'reprobada', label: copy.status.reprobada, tone: 'danger', aviso: copy.status.recovery};
  }
  if (nota < 8) {
    return {key: 'aprobada-seguimiento', label: copy.status.approvedFollowup, tone: 'warning', aviso: copy.status.improve};
  }
  return {key: 'aprobada', label: copy.status.aprobada, tone: 'success', aviso: ''};
}
function MateriaRow({materia}) {
  const copy = useStudentCopy();
  const estado = estadoMateria(materia, copy);
  return <article className="subject-row"><div><strong>{materia.materia_clave}</strong> {materia.materia_nombre}<p>{materia.materia_profesor || copy.grade.professorMissing} · {copy.common.credits}: {materia.materia_creditos ?? '-'} · {copy.common.period}: {materia.periodo_nombre || copy.grade.periodMissing}</p></div><div className="subject-meta"><Badge tone={estado.tone}>{estado.label}</Badge><div className="subject-grades"><span>{copy.common.partials}: {[materia.parcial_1, materia.parcial_2, materia.parcial_3].map(n => n ?? '-').join(' · ')}</span><strong>{copy.common.final}: {materia.calificacion ?? copy.common.pending}</strong>{estado.aviso && <small className={`calificacion-aviso calificacion-aviso--${estado.tone}`}>{estado.aviso}</small>}</div></div></article>;
}
function AvanceCurricular({inscripciones, plan = []}) {
  const copy = useStudentCopy();
  const inscripcionesPorMateria = new Map(inscripciones.map(item => [Number(item.materia), item]));
  const idsPlan = new Set(plan.map(item => Number(item.materia)));
  const materiasPlan = plan.map(item => {
    const inscripcion = inscripcionesPorMateria.get(Number(item.materia));
    const materia = {
      ...inscripcion,
      id: item.materia,
      materia: item.materia,
      materia_clave: item.clave,
      materia_nombre: item.nombre,
      materia_creditos: item.creditos,
      periodo_sugerido: item.periodo_sugerido,
      obligatoria: item.obligatoria,
    };
    return {
      materia,
      periodo: `${copy.common.period} ${item.periodo_sugerido}`,
      estado: inscripcion ? estadoMateria(materia, copy) : {
        key: 'por-cursar',
        label: item.obligatoria ? copy.status.toTake : copy.status.elective,
        tone: 'info',
        aviso: '',
      },
    };
  });
  const materiasFueraPlan = inscripciones
    .filter(item => !idsPlan.has(Number(item.materia)))
    .map(materia => ({materia, periodo: copy.status.outsidePlan, estado: estadoMateria(materia, copy)}));
  const estados = [...materiasPlan, ...materiasFueraPlan];
  const itemsAvance = plan.length ? materiasPlan : estados;
  const aprobadas = itemsAvance.filter(item => ['aprobada', 'aprobada-seguimiento'].includes(item.estado.key));
  const reprobadas = itemsAvance.filter(item => item.estado.key === 'reprobada');
  const enCurso = itemsAvance.filter(item => item.estado.key === 'cursando');
  const porCursar = itemsAvance.filter(item => item.estado.key === 'por-cursar');
  const creditosObligatorios = plan.filter(item => item.obligatoria);
  const creditosRegistrados = plan.length
    ? creditosObligatorios.reduce((total, item) => total + (Number(item.creditos) || 0), 0)
    : inscripciones.reduce((total, item) => total + (Number(item.materia_creditos) || 0), 0);
  const creditosAprobados = plan.length
    ? materiasPlan.filter(item => item.materia.obligatoria && ['aprobada', 'aprobada-seguimiento'].includes(item.estado.key)).reduce((total, item) => total + (Number(item.materia.materia_creditos) || 0), 0)
    : aprobadas.reduce((total, item) => total + (Number(item.materia.materia_creditos) || 0), 0);
  const porcentaje = creditosRegistrados ? Math.round((creditosAprobados / creditosRegistrados) * 100) : 0;
  const periodos = Array.from(new Set(estados.map(item => item.periodo)));
  const grupos = periodos.map(periodo => ({periodo, materias: estados.filter(item => item.periodo === periodo)}));

  return <div className="avance-curricular">
    <div className="avance-curricular-head"><div><p className="panel-kicker">{copy.grade.kicker}</p><h3>{copy.grade.progress}</h3><p>{copy.grade.detail}</p></div><strong className="avance-percent">{porcentaje}%</strong></div>
    {!plan.length && <p className="api-error">{copy.grade.configured}</p>}
    <div className="avance-progress" aria-label={`Avance curricular: ${porcentaje}%`}><span style={{width: `${porcentaje}%`}} /></div>
    <div className="avance-metrics"><div><strong>{aprobadas.length}</strong><span>{copy.grade.passed}</span></div><div><strong>{enCurso.length}</strong><span>{copy.grade.inProgress}</span></div><div><strong>{porCursar.length}</strong><span>{copy.grade.toTake}</span></div><div><strong>{reprobadas.length}</strong><span>{copy.grade.retake}</span></div></div>
    <div className="reticula-periodos">{grupos.map(grupo => <section key={grupo.periodo} className="reticula-periodo"><h4>{grupo.periodo}</h4><div className="reticula-grid">{grupo.materias.map(({materia, estado}) => <article key={materia.id} className={`reticula-materia reticula-materia--${estado.key}`}><div><strong>{materia.materia_clave}</strong><span>{materia.materia_nombre}</span></div><Badge tone={estado.tone}>{estado.label}</Badge><small>{materia.materia_creditos ?? 0} {copy.grade.credits} · {copy.common.final}: {materia.calificacion ?? copy.common.pending}</small></article>)}</div></section>)}</div>
    {!estados.length && <div className="avance-empty"><strong>{copy.grade.emptyTitle}</strong><span>{copy.grade.emptyText}</span></div>}
  </div>;
}
function formatoFecha(value, locale, pending) { return value ? new Intl.DateTimeFormat(locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value)) : pending; }
function JuradoDefensaAlumno({proyecto, session}) {
  const copy = useStudentCopy();
  const defensa = proyecto.defensa;
  const diplomaDisponible = defensa && ['realizada', 'revisada'].includes(defensa.estado) && defensa.calificacion_final != null && Number(defensa.calificacion_final) >= 7;
  async function descargarDiploma() {
    const response = await fetch(`/api/proyectos-tesis/${proyecto.id}/diploma/`, {headers: {Authorization: `Bearer ${session.access}`}});
    if (!response.ok) return;
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `diploma-${proyecto.id}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  }
  return <div className="tesis-follow-up">
    <div className="tesis-follow-up-section"><strong>{copy.jury.assigned}</strong>{proyecto.jurados?.length ? <div className="tesis-jury-list">{proyecto.jurados.map(jurado => <span key={jurado.id}><b>{jurado.rol_label || jurado.rol}</b> {jurado.jurado_nombre} <small>{etiquetaEstado(jurado.estado, copy)}</small></span>)}</div> : <p className="form-hint">{copy.jury.notAssigned}</p>}</div>
    <div className="tesis-follow-up-section"><strong>{copy.jury.defense}</strong>{defensa ? <div className="tesis-defense-summary"><span><b>{etiquetaEstado(defensa.estado, copy)}</b> - {defensa.modalidad_label || defensa.modalidad}</span><small>{formatoFecha(defensa.fecha, copy.locale, copy.communication.datePending)}{defensa.lugar ? ` - ${defensa.lugar}` : ''}</small>{defensa.enlace_virtual && ['virtual', 'hibrida'].includes(defensa.modalidad) && <a className="btn-primary" href={defensa.enlace_virtual} target="_blank" rel="noopener noreferrer">{copy.jury.enterDefense}</a>}{defensa.calificacion_final != null && <small>{copy.common.final}: <b>{defensa.calificacion_final}</b></small>}{diplomaDisponible && <button type="button" className="btn-secondary" onClick={descargarDiploma}>{copy.jury.downloadDiploma}</button>}</div> : <p className="form-hint">{copy.jury.notScheduled}</p>}</div>
  </div>;
}
function EtapaTesisEnAvance({flujo, onOpenThesis, onOpenCourses}) {
  const copy = useStudentCopy();
  const text = thesisWorkflowTranslations[copy.locale.split('-')[0]]?.student || thesisWorkflowTranslations.es.student;
  const elegibilidad = flujo?.elegibilidad;
  const solicitud = flujo?.solicitud;
  const etapa = elegibilidad?.resumen?.etapa;
  const message = solicitud?.estado === 'aprobada'
    ? text.matched
    : etapa === 'por_iniciar'
      ? text.upcoming
      : etapa === 'iniciada'
        ? text.start
        : text.firstYear;
  const matched = solicitud?.estado === 'aprobada';
  return <section className="panel-card tesis-stage-progress">
    <div className="alumno-section-title"><div><p className="panel-kicker">{copy.thesis.kicker}</p><h3>{text.title}</h3></div><Badge tone={matched ? 'success' : etapa === 'por_iniciar' ? 'warning' : 'info'}>{matched ? text.matchConfirmed : elegibilidad?.configuracion ? `${text.currentTerm} ${elegibilidad.resumen?.periodo_actual || '—'}` : copy.common.pending}</Badge></div>
    <p>{message}</p>
    <div className="coord-action-row">
      {matched
        ? <button type="button" className="btn-primary" onClick={onOpenCourses}>{text.openCourses}</button>
        : <button type="button" className="btn-secondary" onClick={onOpenThesis}>{text.openThesis}</button>}
    </div>
  </section>;
}

function EstadoInicioTesis({flujo, form, setForm, onSolicitar, onResponder, cargando = false}) {
  const copy = useStudentCopy();
  const t = copy.thesis;
  const text = thesisWorkflowTranslations[copy.locale.split('-')[0]]?.student || thesisWorkflowTranslations.es.student;
  const elegibilidad = flujo?.elegibilidad;
  const solicitud = flujo?.solicitud;
  const resumen = elegibilidad?.resumen || {};
  if (!elegibilidad) return <div className="panel-card"><h3>{t.lockTitle}</h3><p>{cargando ? t.checking : t.planUnavailable}</p></div>;
  const canSubmit = elegibilidad.elegible && (!solicitud || ['rechazada', 'cancelada'].includes(solicitud.estado));
  return <div className="tesis-view">
    <div className="panel-card">
      <div className="alumno-section-title"><div><p className="panel-kicker">{t.kicker}</p><h3>{t.validation}</h3></div><Badge tone={elegibilidad.elegible ? 'success' : 'warning'}>{elegibilidad.elegible ? t.completed : t.missing}</Badge></div>
        {elegibilidad.configuracion && <><p>{elegibilidad.configuracion.grado_label} · {elegibilidad.configuracion.duracion_anios} {t.years} · {elegibilidad.configuracion.periodos_requeridos} {t.periods}.</p><div className="avance-metrics"><div><strong>{resumen.periodo_actual || '—'}</strong><span>{text.currentTerm}</span></div><div><strong>{resumen.periodo_inicio_tesis}</strong><span>{text.startTerm}</span></div><div><strong>{resumen.periodos_por_anio}</strong><span>{text.termsPerYear}</span></div></div></>}
      {!elegibilidad.elegible && <div className="api-error"><strong>{t.notReady}</strong><ul>{elegibilidad.motivos.map(motivo => <li key={motivo}>{motivo}</li>)}</ul></div>}
    </div>
    {canSubmit && <div className="panel-card"><h3>{t.startTitle}</h3><p>{t.startText}</p><form className="tesis-form" onSubmit={onSolicitar}><label>{text.directorChoice}<select value={form.director_sugerido} onChange={event => setForm({...form, director_sugerido:event.target.value})}><option value="">{text.noPreference}</option>{(flujo.directores || []).map(director => <option key={director.id} value={director.id}>{director.nombre} · {director.departamento || director.programa}</option>)}</select></label><label>{t.line}<input value={form.linea_investigacion} onChange={event => setForm({...form, linea_investigacion:event.target.value})} placeholder={t.linePlaceholder}/></label><label>{t.justification}<textarea required minLength="20" rows="4" value={form.justificacion} onChange={event => setForm({...form, justificacion:event.target.value})} placeholder={t.justificationPlaceholder}/></label><button className="btn-primary" type="submit">{t.sendCoord}</button></form></div>}
    {solicitud && <div className="panel-card"><h3>{t.startTitle}</h3><Badge tone={solicitud.estado === 'rechazada' || solicitud.estado === 'cancelada' ? 'danger' : solicitud.estado === 'aprobada' ? 'success' : 'info'}>{etiquetaEstado(solicitud.estado, copy)}</Badge><p><strong>{t.line}:</strong> {solicitud.linea_investigacion || '—'}</p><p><strong>{text.topic}:</strong> {solicitud.justificacion || '—'}</p>{solicitud.director_asignado && <p><strong>{text.assignedDirector}:</strong> {solicitud.director_asignado.nombre}</p>}{solicitud.estado === 'pendiente' && <p>{text.waitingCoordination}</p>}{solicitud.estado === 'pendiente_director' && <p>{text.waitingDirector}</p>}{solicitud.estado === 'pendiente_alumno' && <><p>{text.waitingStudent}</p><div className="coord-action-row"><button type="button" className="btn-primary" onClick={() => onResponder('aprobada')}>{text.confirm}</button><button type="button" className="btn-secondary" onClick={() => onResponder('rechazada')}>{text.reject}</button></div></>}{solicitud.estado === 'aprobada' && <p>{text.matchConfirmed}</p>}{['rechazada', 'cancelada'].includes(solicitud.estado) && <p>{text.matchRejected}</p>}{solicitud.observaciones && <p><strong>{t.comments}:</strong> {solicitud.observaciones}</p>}</div>}
  </div>;
}

export default function PanelAlumno({session, onLogout}) {
  const copy = useStudentCopy();
  const [perfil, setPerfil] = useState(null), [inscripciones, setInscripciones] = useState([]), [materias, setMaterias] = useState([]), [solicitudes, setSolicitudes] = useState([]), [notificaciones, setNotificaciones] = useState([]), [entrevistas, setEntrevistas] = useState([]), [examenes, setExamenes] = useState([]), [proyectosTesis, setProyectosTesis] = useState([]), [inscribiendo, setInscribiendo] = useState(false);
  const [materiasSeleccionadas, setMateriasSeleccionadas] = useState([]);
  const [antiplagioForm, setAntiplagioForm] = useState({archivo: null, proveedor: 'turnitin'});
  const [revisionAntiplagio, setRevisionAntiplagio] = useState(null);
  const [subiendoAntiplagio, setSubiendoAntiplagio] = useState(false);
  const [seccion, setSeccion] = useState('resumen'), [error, setError] = useState(''), [loading, setLoading] = useState(true), [message, setMessage] = useState('');
  const [modalInscripcion, setModalInscripcion] = useState(null);
  const [periodoInscripcion, setPeriodoInscripcion] = useState(null);
  const [solicitudAcademicaForm, setSolicitudAcademicaForm] = useState({tipo: '', comentario: ''});
  const [enviandoSolicitudAcademica, setEnviandoSolicitudAcademica] = useState(false);
  const [proyectoForm, setProyectoForm] = useState({titulo:'', resumen:'', linea_investigacion:'', objetivos:'', metodologia:''});
  const [flujoTesis, setFlujoTesis] = useState(null);
  const [solicitudTesisForm, setSolicitudTesisForm] = useState({director_sugerido:'', linea_investigacion:'', justificacion:''});
  const apiHeaders = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);
  const cargarDatos = useCallback(async signal => {
    setLoading(true); setError('');
    try {
      const rs = await Promise.all(['me/', 'inscripciones/', 'materias/', 'solicitudes-academicas/', 'entrevistas/', 'examenes/', 'seguimiento/'].map(path => fetch(`/api/preregistro/${path}`, {headers: apiHeaders, signal})));
      if (rs.some(r => r.status === 401)) { onLogout(copy.messages.expired); return; }
      if (rs.some(r => !r.ok)) throw new Error(copy.messages.loadError);
      setPerfil(await rs[0].json()); setInscripciones(await rs[1].json()); setMaterias(await rs[2].json()); setSolicitudes(await rs[3].json());
      const data = await rs[4].json(); setEntrevistas(data.entrevistas || []); const examenesData = await rs[5].json(); setExamenes(examenesData.examenes || []);
      const seguimiento = await rs[6].json(); setNotificaciones(seguimiento.eventos || []);
      const proyectosResponse = await fetch('/api/proyectos-tesis/', {headers: apiHeaders, signal});
      if (proyectosResponse.status === 401) { onLogout(copy.messages.expired); return; }
      if (!proyectosResponse.ok) throw new Error(copy.messages.projectsError);
      setProyectosTesis(await proyectosResponse.json());
      const flujoResponse = await fetch('/api/tesis/flujo/', {headers: apiHeaders, signal});
      if (flujoResponse.ok) setFlujoTesis(await flujoResponse.json());
    } catch (err) { if (err.name !== 'AbortError') setError(err.message || copy.messages.loadError); }
    finally { if (!signal.aborted) setLoading(false); }
  }, [apiHeaders, copy, onLogout]);
  useEffect(() => { const c = new AbortController(); cargarDatos(c.signal); return () => c.abort(); }, [cargarDatos]);
  useEffect(() => { fetch('/api/periodos-inscripcion/', {headers: apiHeaders}).then(r=>r.ok?r.json():null).then(setPeriodoInscripcion).catch(()=>{}); }, [apiHeaders]);
  async function marcarNotificacionesLeidas() {
    try {
      const response = await fetch('/api/preregistro/notificaciones/marcar-leidas/', {method: 'POST', headers: apiHeaders});
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (!response.ok) throw new Error(copy.notifications.markError);
      setNotificaciones(items => items.map(item => ({...item, leido: true})));
    } catch (err) {
      setError(err.message || copy.notifications.markError);
    }
  }
  async function crearSolicitudAcademica(event) {
    event.preventDefault();
    const comentario = solicitudAcademicaForm.comentario.trim();
    if (!solicitudAcademicaForm.tipo || comentario.length < 10) {
      setError(copy.requests.requiredFields);
      return;
    }
    setError('');
    setMessage('');
    setEnviandoSolicitudAcademica(true);
    try {
      const response = await fetch('/api/preregistro/solicitudes-academicas/', {
        method: 'POST',
        headers: {...apiHeaders, 'Content-Type': 'application/json'},
        body: JSON.stringify({...solicitudAcademicaForm, comentario}),
      });
      if (response.status === 401) return onLogout(copy.messages.expired);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || data.comentario || data.tipo || copy.requests.submitError);
      setSolicitudes(items => [data, ...items]);
      setSolicitudAcademicaForm({tipo: '', comentario: ''});
      setMessage(copy.requests.created);
    } catch (err) {
      setError(err.message || copy.requests.submitError);
    } finally {
      setEnviandoSolicitudAcademica(false);
    }
  }
  const promedio = useMemo(() => { const a = inscripciones.map(i => Number(i.calificacion)).filter(n => !Number.isNaN(n)); return a.length ? (a.reduce((x, n) => x + n, 0) / a.length).toFixed(2) : null; }, [inscripciones]);
  const descargar = useCallback(async (ruta, nombre) => { try { const r = await fetch(ruta, {headers: apiHeaders}); if (!r.ok) throw new Error(copy.messages.downloadError); const url = URL.createObjectURL(await r.blob()); const a = document.createElement('a'); a.href = url; a.download = nombre; a.click(); URL.revokeObjectURL(url); setMessage(`${nombre}: ${copy.docs.pdf}`); } catch (e) { setError(e.message); } }, [apiHeaders, copy]);
  async function inscribirMateriasSeleccionadas() {
    if (inscribiendo) return;
    if (!periodoInscripcion?.activo) {
      setError(copy.enrollment.activeClosed);
      setModalInscripcion({kind: 'error', message: copy.enrollment.activeClosed});
      return;
    }
    const inscripcionesPeriodo = inscripciones.filter(item => item.periodo_nombre === periodoInscripcion.nombre).length;
    const faltan = Math.max(0, 4 - inscripcionesPeriodo);
    if (materiasSeleccionadas.length !== faltan) {
      const detalle = copy.enrollment.exactCount.replace('{count}', faltan);
      setError(detalle);
      setModalInscripcion({kind: 'error', message: detalle});
      return;
    }
    setModalInscripcion({kind: 'processing'});
    setInscribiendo(true); setError(''); setMessage('');
    try {
      const r = await fetch('/api/preregistro/inscripciones/', {method: 'POST', headers: {...apiHeaders, 'Content-Type': 'application/json'}, body: JSON.stringify({materias: materiasSeleccionadas})});
      if (r.status === 401) { onLogout(copy.messages.expired); return; }
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        const detail = data.detail || data.materias || Object.values(data).flat().find(value => typeof value === 'string');
        throw new Error(typeof detail === 'string' ? detail : copy.messages.courseLoadError);
      }
      if (!Array.isArray(data)) throw new Error(copy.messages.courseLoadError);
      setInscripciones(items => [...items, ...data]);
      setMateriasSeleccionadas([]);
      setMessage(copy.enrollment.registered.replace('{period}', periodoInscripcion.nombre));
      setModalInscripcion({kind: 'success', message: copy.enrollment.registered.replace('{period}', periodoInscripcion.nombre)});
    } catch (e) {
      const detalle = e.message || copy.messages.courseLoadError;
      setError(detalle);
      setModalInscripcion({kind: 'error', message: detalle});
    } finally { setInscribiendo(false); }
  }
  function prepararInscripcion() {
    if (!periodoInscripcion?.activo) {
      setError(copy.enrollment.activeClosed);
      setModalInscripcion({kind: 'error', message: copy.enrollment.activeClosed});
      return;
    }
    const actuales = inscripciones.filter(item => item.periodo_nombre === periodoInscripcion.nombre).length;
    const faltan = Math.max(0, 4 - actuales);
    if (materiasSeleccionadas.length !== faltan) {
      const detalle = copy.enrollment.exactCount.replace('{count}', faltan);
      setError(detalle);
      setModalInscripcion({kind: 'error', message: detalle});
      return;
    }
    const detalle = copy.enrollment.confirm.replace('{count}', materiasSeleccionadas.length).replace('{period}', periodoInscripcion.nombre);
    setError('');
    setModalInscripcion({kind: 'confirm', message: detalle});
  }
  async function guardarProyecto(event, enviarRevision = false) {
    event.preventDefault();
    setError('');
    const payload = {...proyectoForm, ...(enviarRevision ? {enviar_revision: true} : {})};
    const editando = Boolean(proyectoForm.id);
    const response = await fetch(editando ? `/api/proyectos-tesis/${proyectoForm.id}/` : '/api/proyectos-tesis/', {method: editando ? 'PATCH' : 'POST', headers: {...apiHeaders, 'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) return setError(data.detail || data.titulo?.[0] || data.resumen?.[0] || copy.thesis.saveError);
    setProyectosTesis(items => editando ? items.map(item => item.id === data.id ? data : item) : [data, ...items]);
    setProyectoForm({titulo:'', resumen:'', linea_investigacion:'', objetivos:'', metodologia:''});
    setMessage(enviarRevision ? copy.thesis.sentReview : copy.thesis.draftSaved);
  }
  async function solicitarDireccionTesis(event) {
    event.preventDefault(); setError('');
    const response = await fetch('/api/tesis/flujo/', {method:'POST', headers:{...apiHeaders, 'Content-Type':'application/json'}, body:JSON.stringify(solicitudTesisForm)});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) return setError(data.detail || copy.messages.thesisRequestError);
    setFlujoTesis(actual => ({...actual, solicitud:data})); setSolicitudTesisForm({director_sugerido:'', linea_investigacion:'', justificacion:''}); setMessage(copy.thesis.sentDirection);
  }
  async function responderMatchTesis(estado) {
    const solicitud = flujoTesis?.solicitud;
    if (!solicitud) return;
    setError('');
    try {
      const response = await fetch(`/api/tesis/solicitudes/${solicitud.id}/`, {
        method: 'PATCH',
        headers: {...apiHeaders, 'Content-Type': 'application/json'},
        body: JSON.stringify({estado}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || copy.messages.thesisRequestError);
      setFlujoTesis(actual => ({...actual, solicitud:data}));
      const text = thesisWorkflowTranslations[copy.locale.split('-')[0]]?.student || thesisWorkflowTranslations.es.student;
      setMessage(data.estado === 'aprobada' ? text.matchConfirmed : text.matchRejected);
    } catch (error) {
      setError(error.message || copy.messages.thesisRequestError);
    }
  }
  async function subirRevisionAntiplagio(event) {
    event.preventDefault();
    setError('');
    if (!antiplagioForm.archivo) {
      setError(copy.plagiarism.missingFile);
      return;
    }
    setSubiendoAntiplagio(true);
    try {
      const proyectoActivo = proyectosTesis.find(item => item.estado && ['borrador', 'en_revision', 'observado'].includes(item.estado));
      if (!proyectoActivo) {
        throw new Error(copy.plagiarism.activeProject);
      }
      const formData = new FormData();
      formData.append('archivo', antiplagioForm.archivo);
      formData.append('proveedor', antiplagioForm.proveedor);
      const response = await fetch(`/api/proyectos-tesis/${proyectoActivo.id}/revision-antiplagio/`, {
        method: 'POST',
        headers: {Authorization: `Bearer ${session.access}`},
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || data.archivo?.[0] || data.archivo || copy.plagiarism.sendError);
      setRevisionAntiplagio(data);
      setAntiplagioForm({archivo: null, proveedor: 'turnitin'});
      setMessage(`${copy.plagiarism.complete}: ${data.porcentaje_similitud}% ${copy.plagiarism.similarity} (${data.estado}).`);
      const proyectoActualizado = await fetch(`/api/proyectos-tesis/${proyectoActivo.id}/`, {headers: apiHeaders});
      if (proyectoActualizado.ok) {
        const proyectoData = await proyectoActualizado.json();
        setProyectosTesis(items => items.map(item => item.id === proyectoData.id ? proyectoData : item));
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSubiendoAntiplagio(false);
    }
  }
  const contenido = () => {
    if (seccion === 'tesis' && (!flujoTesis || !flujoTesis.elegibilidad?.elegible || flujoTesis.solicitud?.estado !== 'aprobada')) return <EstadoInicioTesis flujo={flujoTesis} form={solicitudTesisForm} setForm={setSolicitudTesisForm} onSolicitar={solicitarDireccionTesis} onResponder={responderMatchTesis} cargando={loading}/>;
    if (seccion === 'diploma') return <div className="panel-card"><div className="alumno-section-title"><div><p className="panel-kicker">{copy.diploma.kicker}</p><h3>{copy.diploma.title}</h3></div><Badge tone="info">{copy.diploma.defense}</Badge></div><p>{copy.diploma.intro}</p>{proyectosTesis.length ? <div className="tesis-list">{proyectosTesis.map(proyecto => <article key={proyecto.id}><div><strong>{proyecto.titulo}</strong><small>{proyecto.defensa ? etiquetaEstado(proyecto.defensa.estado, copy) : copy.diploma.pending}</small><JuradoDefensaAlumno proyecto={proyecto} session={session}/></div></article>)}</div> : <p>{copy.diploma.noProjects}</p>}</div>;
    if (seccion === 'predoctoral') {
      const examenesPredoctorales = examenes.filter(examen => examen.tipo === 'predoctoral');
      return <div className="panel-card"><div className="alumno-section-title"><div><p className="panel-kicker">{copy.predoctoral.kicker}</p><h3>{copy.predoctoral.title}</h3></div><Badge tone="info">{copy.predoctoral.academic}</Badge></div><p>{copy.predoctoral.intro}</p>{examenesPredoctorales.length ? <div className="request-list">{examenesPredoctorales.map(examen => <article key={examen.id}><strong>{examen.titulo}</strong><p>{examen.descripcion || copy.predoctoral.evaluation}</p><p><strong>{copy.common.date}:</strong> {formatoFecha(examen.fecha_programada, copy.locale, copy.communication.datePending)} · <strong>{copy.common.duration}:</strong> {examen.duracion_minutos || 120} {copy.common.minutes}</p><Badge tone={examen.color || 'neutral'}>{etiquetaEstado(examen.estado, copy)}</Badge>{examen.calificacion !== null && examen.calificacion !== undefined && <p>{copy.common.result}: <strong>{examen.calificacion}</strong></p>}{examen.retroalimentacion && <p><strong>{copy.common.feedback}:</strong> {examen.retroalimentacion}</p>}</article>)}</div> : <p>{copy.predoctoral.noExam}</p>}</div>;
    }
    if (seccion === 'examenes') return <ExamenesEnLinea session={session} examenes={examenes} onChange={setExamenes} />;
    if (seccion === 'resumen') return <div className="alumno-dashboard-grid">
      <section className="alumno-dashboard-hero">
        <div className="alumno-dashboard-identity">
          <span className="alumno-dashboard-avatar">
            {(perfil.nombre || 'A').charAt(0).toUpperCase()}
            {perfil.profile_photo && <img src={fotoUrl(perfil.profile_photo)} alt="" onError={event => {event.currentTarget.style.display = 'none';}}/>}
          </span>
          <div className="alumno-dashboard-greeting">
            <p className="panel-kicker">{copy.panel}</p>
            <h3>{copy.summary.welcome}, {perfil.nombre || copy.summary.student}</h3>
            <p>{copy.summary.user}: <strong>{perfil.usuario || perfil.correo || '-'}</strong></p>
          </div>
        </div>
        <Badge tone="info">{etiquetaEstado(perfil.proceso_estado, copy)}</Badge>
        <div className="alumno-dashboard-profile" aria-label={copy.summary.program}>
          <InfoRow label={copy.summary.program} value={perfil.programa}/>
          <InfoRow label={copy.summary.unit} value={perfil.unidad}/>
          <InfoRow label={copy.summary.modality} value={perfil.modalidad}/>
        </div>
      </section>
      <section className="alumno-stats" aria-label={copy.summary.quick}>
        <article className="alumno-stat-card alumno-stat-card--courses"><span aria-hidden="true">▤</span><strong>{inscripciones.length}</strong><small>{copy.summary.registered}</small></article>
        <article className="alumno-stat-card alumno-stat-card--average"><span aria-hidden="true">◉</span><strong>{promedio || '-'}</strong><small>{copy.summary.average}</small></article>
        <article className="alumno-stat-card alumno-stat-card--requests"><span aria-hidden="true">✉</span><strong>{solicitudes.length}</strong><small>{copy.summary.requests}</small></article>
        <article className="alumno-stat-card alumno-stat-card--interviews"><span aria-hidden="true">◷</span><strong>{entrevistas.length}</strong><small>{copy.summary.interviews}</small></article>
      </section>
      <section className="panel-card alumno-dashboard-actions">
        <div className="alumno-dashboard-section-heading"><p className="panel-kicker">{copy.panel}</p><h3>{copy.summary.quick}</h3></div>
        <div className="alumno-dashboard-action-grid">
          <button type="button" onClick={() => setSeccion('horario')}><span aria-hidden="true">▦</span><strong>{copy.summary.schedule}</strong><span aria-hidden="true">↗</span></button>
          <button type="button" onClick={() => setSeccion('solicitudes')}><span aria-hidden="true">✉</span><strong>{copy.summary.viewRequests}</strong><span aria-hidden="true">↗</span></button>
          <button type="button" onClick={() => setSeccion('tramites')}><span aria-hidden="true">⇩</span><strong>{copy.summary.downloadDocs}</strong><span aria-hidden="true">↗</span></button>
        </div>
      </section>
    </div>;
    if (seccion === 'materias') { const inscritas = new Set(inscripciones.filter(i => i.periodo_nombre === periodoInscripcion?.nombre).map(i => Number(i.materia))); const periodoActivo = Boolean(periodoInscripcion?.activo); const periodoActualInscripciones = inscripciones.filter(i => i.periodo_nombre === periodoInscripcion?.nombre).length; const faltan = Math.max(0, 4 - periodoActualInscripciones); const seleccionadas = new Set(materiasSeleccionadas); const fecha = valor => valor ? new Date(valor).toLocaleDateString(copy.locale) : '-'; const alternarMateria = id => setMateriasSeleccionadas(actual => actual.includes(id) ? actual.filter(item => item !== id) : actual.length < faltan ? [...actual, id] : actual); return <div className="alumno-materias-view"><div className="panel-card"><h3>{copy.summary.courses}</h3><p>{copy.enrollment.exact}</p><div className={`inscripcion-periodo ${periodoActivo ? 'is-open' : 'is-closed'}`}><strong>{periodoActivo ? `${copy.enrollment.open}: ${periodoInscripcion.nombre}` : copy.enrollment.closed}</strong><span>{periodoInscripcion ? `${fecha(periodoInscripcion.apertura)} - ${fecha(periodoInscripcion.cierre)}` : copy.enrollment.notEnabled}</span></div>{periodoActivo && <p className="form-hint">{copy.enrollment.load}: {periodoActualInscripciones} / 4 · {copy.enrollment.selected}: {materiasSeleccionadas.length} / {faltan}</p>}{materias.length > 0 && periodoActivo ? <><div className="materias-grid">{materias.map(m => { const yaInscrita = inscritas.has(Number(m.id)); const seleccionada = seleccionadas.has(m.id); return <article className={`materia-card ${yaInscrita || seleccionada ? 'is-selected' : ''}`} key={m.id}><span className="materia-card-clave">{m.clave}</span><strong className="materia-card-nombre">{m.nombre}</strong>{m.categoria === 'seminario' && <Badge tone="info">{thesisWorkflowTranslations[copy.locale.split('-')[0]]?.seminar || thesisWorkflowTranslations.es.seminar}</Badge>}<small><strong>{copy.docs.schoolYear}: {periodoInscripcion.nombre}</strong><br/>{copy.common.period}: {m.periodo_sugerido}<br/>{copy.common.teacher}: {m.profesor || copy.common.notAssigned}<br/>{copy.docs.schedule}: {m.horario || copy.common.toDefine}<br/>{copy.common.roomPending}: {m.salon_label || copy.common.roomPending}<br/>{copy.common.enrolled}: {m.inscritos || 0} / {m.capacidad || 42}</small>{yaInscrita ? <Badge tone="success">{copy.enrollment.already}</Badge> : <button type="button" className="btn-primary" disabled={inscribiendo || faltan === 0 || (!seleccionada && materiasSeleccionadas.length >= faltan)} onClick={() => alternarMateria(m.id)}>{seleccionada ? copy.enrollment.selectedLabel : copy.enrollment.select}</button>}</article>; })}</div><button type="button" className="btn-primary" disabled={inscribiendo || faltan === 0 || materiasSeleccionadas.length !== faltan} onClick={prepararInscripcion}>{inscribiendo ? copy.enrollment.submitting : faltan === 0 ? `${copy.enrollment.load} (4/4)` : `${copy.enrollment.submit}: ${faltan}`}</button></> : <p>{periodoActivo ? copy.enrollment.noAvailableCourses : copy.enrollment.activeClosed}</p>}</div><div className="panel-card"><h3>{copy.summary.registered}</h3>{inscripciones.length ? <div className="subject-list">{inscripciones.map(m => <MateriaRow key={m.id} materia={m}/>)}</div> : <p>{copy.common.noCourses}</p>}</div></div>; }
    if (seccion === 'calificaciones') return <div className="panel-card"><div className="alumno-section-title"><div><p className="panel-kicker">{copy.grade.kicker}</p><h3>{copy.grade.title}</h3></div></div><AvanceCurricular inscripciones={inscripciones} plan={flujoTesis?.elegibilidad?.configuracion?.materias_plan || []}/><EtapaTesisEnAvance flujo={flujoTesis} onOpenThesis={() => setSeccion('tesis')} onOpenCourses={() => setSeccion('materias')}/><div className="subject-list">{inscripciones.length ? inscripciones.map(m => <MateriaRow key={m.id} materia={m}/>) : <p>{copy.common.noCourses}</p>}</div></div>;
    if (seccion === 'horario' || seccion === 'tramites') {
      const inscripcionesConPeriodo = inscripciones.filter(materia => materia.periodo_inscripcion && materia.periodo_nombre);
      const periodoActualId = periodoInscripcion?.activo ? periodoInscripcion.id : null;
      const periodoHorario = periodoActualId
        ? inscripcionesConPeriodo.find(materia => String(materia.periodo_inscripcion) === String(periodoActualId)) || null
        : inscripcionesConPeriodo.reduce((reciente, item) => !reciente || new Date(item.created_at) > new Date(reciente.created_at) ? item : reciente, null);
      const horarioPeriodoId = periodoActualId || periodoHorario?.periodo_inscripcion || periodoInscripcion?.id;
      const cicloEscolar = periodoActualId
        ? periodoInscripcion.nombre
        : periodoHorario?.periodo_nombre || periodoInscripcion?.nombre || '—';
      const horarioUrl = horarioPeriodoId
        ? `/api/preregistro/horario/download/?periodo=${horarioPeriodoId}`
        : '/api/preregistro/horario/download/';
      const documentos = [
        {tipo: 'constancia', grupo: 'oficiales', titulo: copy.docs.schoolCertificate, descripcion: copy.docs.schoolCertificateDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/constancia/` : null},
        {tipo: 'calificaciones', grupo: 'oficiales', titulo: copy.docs.gradesCertificate, descripcion: copy.docs.gradesCertificateDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/calificaciones/` : null},
        {tipo: 'historial', grupo: 'oficiales', titulo: copy.docs.transcript, descripcion: copy.docs.transcriptDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/historial/` : null},
        {tipo: 'inscripcion', grupo: 'oficiales', titulo: copy.docs.enrollmentCertificate, descripcion: copy.docs.enrollmentCertificateDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/inscripcion/` : null},
        {tipo: 'egreso', grupo: 'oficiales', titulo: copy.docs.graduation, descripcion: copy.docs.graduationDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/egreso/` : null},
        {tipo: 'horario', grupo: 'inscripcion', titulo: copy.docs.schedule, descripcion: copy.docs.scheduleDesc, ruta: horarioUrl},
        {tipo: 'boleta', grupo: 'inscripcion', titulo: copy.docs.enrollmentSlip, descripcion: copy.docs.enrollmentSlipDesc, ruta: '/api/preregistro/boleta-inscripcion/download/'},
        {tipo: 'reinscripcion', grupo: 'inscripcion', titulo: copy.docs.reenrollmentSlip, descripcion: copy.docs.reenrollmentSlipDesc, ruta: '/api/preregistro/reinscripcion/download/'},
      ];
      if (seccion === 'horario') {
        const inscripcionesHorario = horarioPeriodoId
          ? inscripciones.filter(materia => String(materia.periodo_inscripcion) === String(horarioPeriodoId))
          : inscripciones;
        const descargasHorario = [
          {id: 'horario', titulo: copy.docs.schedulePdf, nombre: 'horario.pdf', ruta: horarioUrl, icono: '▦'},
          {id: 'boleta', titulo: copy.docs.enrollmentPdf, nombre: 'boleta_inscripcion.pdf', ruta: '/api/preregistro/boleta-inscripcion/download/', icono: '▤'},
          {id: 'reinscripcion', titulo: copy.docs.reenrollmentPdf, nombre: 'reinscripcion.pdf', ruta: '/api/preregistro/reinscripcion/download/', icono: '↻'},
        ];
        return <div className="alumno-schedule-view">
          <section className="alumno-schedule-summary panel-card">
            <div className="alumno-schedule-summary-copy">
              <p className="panel-kicker">{copy.docs.scheduleAndReenroll}</p>
              <h3>{copy.docs.schoolYear}: {cicloEscolar}</h3>
              <p>{copy.docs.intro}</p>
            </div>
            <div className="alumno-schedule-count"><strong>{inscripcionesHorario.length}</strong><span>{copy.docs.courseCount}</span></div>
          </section>
          <section className="panel-card alumno-schedule-downloads">
            <div className="alumno-schedule-section-head"><div><p className="panel-kicker">{copy.docs.downloads}</p><h3>{copy.docs.documentsAndProcedures}</h3></div></div>
            <div className="alumno-schedule-download-grid">{descargasHorario.map(documento => <article className="alumno-schedule-download" key={documento.id}>
              <span aria-hidden="true">{documento.icono}</span>
              <div><strong>{documento.titulo}</strong><small>{copy.docs.schoolYear}: {cicloEscolar}</small></div>
              <button type="button" className="btn-secondary" onClick={() => descargar(documento.ruta, documento.nombre)}>{copy.docs.pdf}</button>
            </article>)}</div>
          </section>
          <section className="panel-card alumno-schedule-courses">
            <div className="alumno-schedule-section-head"><div><p className="panel-kicker">{copy.docs.scheduleDetails}</p><h3>{copy.docs.courseList}</h3></div><Badge tone="info">{inscripcionesHorario.length} {copy.docs.courseCount}</Badge></div>
            {inscripcionesHorario.length ? <div className="alumno-schedule-course-list">{inscripcionesHorario.map(materia => <article className="alumno-schedule-course" key={materia.id}>
              <div className="alumno-schedule-course-title"><span>{materia.materia_clave || '—'}</span><strong>{materia.materia_nombre || copy.common.course}</strong></div>
              <div className="alumno-schedule-course-detail"><span>{copy.common.teacher}<strong>{materia.materia_profesor || copy.grade.professorMissing}</strong></span><span>{copy.docs.timeLabel}<strong>{materia.materia_horario || materia.horario || copy.common.toDefine}</strong></span><span>{copy.docs.roomLabel}<strong>{materia.materia_salon || materia.salon || copy.common.roomPending}</strong></span></div>
            </article>)}</div> : <div className="alumno-schedule-empty"><span aria-hidden="true">▦</span><strong>{copy.docs.noScheduleCourses}</strong><p>{copy.common.noCourses}</p></div>}
          </section>
        </div>;
      }
      const documentosDisponibles = documentos.filter(doc => doc.ruta);
      const gruposDocumentos = [
        {id: 'oficiales', titulo: copy.docs.officialDocuments, icono: '▤'},
        {id: 'inscripcion', titulo: copy.docs.enrollmentDocuments, icono: '▦'},
      ];
      return <div className="alumno-procedures-view">
        <section className="alumno-schedule-summary panel-card">
          <div className="alumno-schedule-summary-copy">
            <p className="panel-kicker">{copy.docs.documentsAndProcedures}</p>
            <h3>{copy.docs.documentsAndProcedures}</h3>
            <p>{copy.docs.intro}</p>
          </div>
          <div className="alumno-schedule-count"><strong>{documentosDisponibles.length}</strong><span>{copy.docs.documentCount}</span></div>
        </section>
        {gruposDocumentos.map(grupo => {
          const items = documentosDisponibles.filter(documento => documento.grupo === grupo.id);
          if (!items.length) return null;
          return <section className="panel-card alumno-procedure-group" key={grupo.id}>
            <div className="alumno-schedule-section-head">
              <div><p className="panel-kicker">{copy.docs.downloads}</p><h3>{grupo.titulo}</h3></div>
              <Badge tone="info">{items.length}</Badge>
            </div>
            <div className="alumno-procedure-grid">{items.map(documento => <article className="alumno-procedure-card" key={documento.tipo}>
              <span className="alumno-procedure-icon" aria-hidden="true">{grupo.icono}</span>
              <div className="alumno-procedure-copy"><strong>{documento.titulo}</strong><p>{documento.descripcion}</p></div>
              <button type="button" className="btn-secondary" onClick={() => descargar(documento.ruta, `${documento.tipo}.pdf`)}>{copy.docs.documentOpen}</button>
            </article>)}</div>
          </section>;
        })}
      </div>;
    }
    if (seccion === 'solicitudes') return <div className="alumno-academic-requests">
      <section className="panel-card alumno-request-form-card">
        <div className="alumno-section-title"><div><p className="panel-kicker">{copy.requests.title}</p><h3>{copy.requests.formTitle}</h3><p>{copy.requests.intro}</p><p className="alumno-request-routing">{copy.requests.routing}</p></div></div>
        <form className="alumno-request-form" onSubmit={crearSolicitudAcademica}>
          <label><span>{copy.requests.type}</span><select required value={solicitudAcademicaForm.tipo} onChange={event => setSolicitudAcademicaForm(form => ({...form, tipo: event.target.value}))}>
            <option value="">{copy.requests.selectType}</option>
            {Object.entries(copy.requests.types).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select></label>
          <label><span>{copy.requests.comment}</span><textarea required minLength="10" maxLength="2000" rows="4" value={solicitudAcademicaForm.comentario} onChange={event => setSolicitudAcademicaForm(form => ({...form, comentario: event.target.value}))} placeholder={copy.requests.commentPlaceholder}/><small>{copy.requests.commentHint} · {solicitudAcademicaForm.comentario.length}/2000</small></label>
          <button type="submit" className="btn-primary" disabled={enviandoSolicitudAcademica}>{enviandoSolicitudAcademica ? copy.requests.submitting : copy.requests.submit}</button>
        </form>
      </section>
      <section className="panel-card alumno-request-history">
        <div className="alumno-section-title"><div><p className="panel-kicker">{copy.requests.title}</p><h3>{copy.requests.history}</h3></div><Badge tone="info">{solicitudes.length}</Badge></div>
        {solicitudes.length ? <div className="alumno-request-list">{solicitudes.map(item => {
          const statusLabel = copy.requests[item.estado] || etiquetaEstado(item.estado, copy);
          return <article className={`alumno-request-item alumno-request-item--${item.estado}`} key={item.id}>
            <div className="alumno-request-item-heading"><div><strong>{copy.requests.types[item.tipo] || item.tipo_label}</strong><small>{copy.requests.requestedOn}: {formatoFecha(item.created_at, copy.locale, '—')}</small></div><Badge tone={item.estado === 'aceptado' ? 'success' : item.estado === 'rechazado' ? 'danger' : 'warning'}>{statusLabel}</Badge></div>
            <p>{item.comentario || '—'}</p>
            {item.respuesta_revision ? <div className="alumno-request-response"><strong>{copy.requests.reviewerResponse}</strong><p>{item.respuesta_revision}</p>{item.resuelta_por_nombre && <small>{copy.requests.reviewedBy}: {item.resuelta_por_nombre}</small>}</div> : item.estado === 'pendiente' && <p className="alumno-request-pending">{copy.requests.emptyResponse}</p>}
          </article>;
        })}</div> : <div className="alumno-request-empty"><span aria-hidden="true">✉</span><strong>{copy.requests.noRequests}</strong></div>}
      </section>
    </div>;
    if (seccion === 'entrevistas') return <div className="panel-card entrevistas-alumno-card"><div className="alumno-section-title"><div><p className="panel-kicker">{copy.communication.kicker}</p><h3>{copy.communication.title}</h3></div><Badge tone="info">{entrevistas.length} {entrevistas.length === 1 ? copy.communication.countOne : copy.communication.countMany}</Badge></div>{entrevistas.length ? <div className="entrevistas-alumno-list">{entrevistas.map(i => <article className="entrevista-alumno-item" key={i.id}><div className="entrevista-alumno-main"><div className="entrevista-alumno-heading"><strong>{i.titulo || copy.communication.virtualInterview}</strong><Badge tone={i.color || 'neutral'}>{etiquetaEstado(i.estado, copy)}</Badge></div><p>{i.proposito_label || i.proposito}</p>{i.descripcion && <small>{i.descripcion}</small>}<div className="interview-meta"><span><strong>{copy.common.date}:</strong> {formatoFecha(i.fecha_programada, copy.locale, copy.communication.datePending)}</span><span><strong>{copy.common.duration}:</strong> {i.duracion_minutos || 30} {copy.common.minutes}</span></div>{i.retroalimentacion && <div className="entrevista-feedback"><strong>{copy.communication.teacherFeedback}</strong><p>{i.retroalimentacion}</p></div>}</div><div className="entrevista-alumno-actions">{i.estado === 'iniciada' && i.jitsi_room_link ? <a className="btn-primary" href={i.jitsi_room_link} target="_blank" rel="noopener noreferrer">{copy.communication.join}</a> : i.estado === 'programada' ? <span className="form-hint">{copy.communication.availableWhenStarted}</span> : i.estado === 'completada' ? <span className="form-hint">{copy.communication.completed}</span> : <span className="form-hint">{copy.communication.cancelled}</span>}</div></article>)}</div> : <div className="empty-state"><strong>{copy.communication.noScheduled}</strong><p>{copy.communication.emptyText}</p></div>}</div>;
    if (seccion === 'tesis') return <div className="tesis-view">
      <div className="panel-card">
        <div className="alumno-section-title"><div><p className="panel-kicker">{copy.thesis.thesisKicker}</p><h3>{copy.thesis.projectTitle}</h3></div><span className="badge badge--info">{copy.thesis.lida}</span></div>
        <p>{copy.thesis.projectIntro}</p>
        <form className="tesis-form" onSubmit={event => guardarProyecto(event, false)}>
          <label>{copy.thesis.title}<input required minLength="10" value={proyectoForm.titulo} onChange={event => setProyectoForm({...proyectoForm, titulo:event.target.value})} placeholder={copy.thesis.titlePlaceholder}/></label>
          <label>{copy.thesis.line}<input value={proyectoForm.linea_investigacion} onChange={event => setProyectoForm({...proyectoForm, linea_investigacion:event.target.value})} placeholder={copy.thesis.linePlaceholder}/></label>
          <label>{copy.thesis.summary}<textarea required minLength="30" rows="4" value={proyectoForm.resumen} onChange={event => setProyectoForm({...proyectoForm, resumen:event.target.value})} placeholder={copy.thesis.summaryPlaceholder}/></label>
          <label>{copy.thesis.objectives}<textarea rows="3" value={proyectoForm.objetivos} onChange={event => setProyectoForm({...proyectoForm, objetivos:event.target.value})} placeholder={copy.thesis.objectivesPlaceholder}/></label>
          <label>{copy.thesis.methodology}<textarea rows="3" value={proyectoForm.metodologia} onChange={event => setProyectoForm({...proyectoForm, metodologia:event.target.value})} placeholder={copy.thesis.methodologyPlaceholder}/></label>
          <div className="tesis-form-actions"><button type="submit" className="btn-secondary">{copy.thesis.saveDraft}</button><button type="button" className="btn-primary" onClick={event => guardarProyecto(event, true)}>{copy.thesis.sendReview}</button>{proyectoForm.id && <button type="button" className="link-btn" onClick={() => setProyectoForm({titulo:'', resumen:'', linea_investigacion:'', objetivos:'', metodologia:''})}>{copy.extra.thesis.clear}</button>}</div>
        </form>
        {proyectosTesis.length ? <div className="tesis-list">{proyectosTesis.map(proyecto => <article key={proyecto.id}><div><strong>{proyecto.titulo}</strong><small>{etiquetaEstado(proyecto.estado, copy)} · {proyecto.director_nombre || copy.common.notAssigned}</small><p>{proyecto.resumen}</p></div><div className="tesis-list-actions"><button type="button" className="btn-secondary" onClick={() => setProyectoForm({...proyecto})}>{copy.extra.thesis.edit}</button></div></article>)}</div> : <p>{copy.diploma.noProjects}</p>}
      </div>
      <div className="panel-card">
        <div className="alumno-section-title"><div><p className="panel-kicker">{copy.extra.plagiarism.kicker}</p><h3>{copy.extra.plagiarism.title}</h3></div><Badge tone={revisionAntiplagio ? (revisionAntiplagio.estado === 'rechazado' ? 'danger' : revisionAntiplagio.estado === 'observado' ? 'warning' : 'success') : 'neutral'}>{revisionAntiplagio ? etiquetaEstado(revisionAntiplagio.estado, copy) : copy.extra.plagiarism.none}</Badge></div>
        <p>{copy.extra.plagiarism.intro}</p>
        <form className="tesis-form" onSubmit={subirRevisionAntiplagio}><label>{copy.extra.plagiarism.provider}<select value={antiplagioForm.proveedor} onChange={event => setAntiplagioForm({...antiplagioForm, proveedor: event.target.value})}><option value="turnitin">Turnitin</option><option value="copyleaks">Copyleaks</option><option value="manual">{copy.extra.plagiarism.manual}</option></select></label><label>{copy.extra.plagiarism.file}<input type="file" accept="application/pdf" onChange={event => setAntiplagioForm({...antiplagioForm, archivo: event.target.files?.[0] || null})}/></label><div className="tesis-form-actions"><button type="submit" className="btn-primary" disabled={subiendoAntiplagio}>{subiendoAntiplagio ? copy.extra.plagiarism.submitting : copy.extra.plagiarism.submit}</button></div></form>
        {revisionAntiplagio && <div className="request-list"><article><strong>{copy.common.result}: {revisionAntiplagio.porcentaje_similitud}% {copy.plagiarism.similarity}</strong><p>{revisionAntiplagio.observaciones || copy.extra.plagiarism.noObservations}</p><p><strong>{copy.extra.plagiarism.provider}:</strong> {revisionAntiplagio.proveedor} · <strong>{copy.common.status}:</strong> {etiquetaEstado(revisionAntiplagio.estado, copy)}</p></article></div>}
      </div>
    </div>;
    return <div><PerfilAspirante perfil={perfil} session={session} onActualizado={data => { setPerfil(actual => ({...actual, ...data})); setMessage(copy.extra.profileSaved); }}/><div className="panel-card alumno-profile-summary"><h3>{copy.grade.title}</h3><div className="info-grid"><InfoRow label={copy.summary.program} value={perfil.programa}/><InfoRow label={copy.summary.unit} value={perfil.unidad}/><InfoRow label={copy.common.grade} value={perfil.promedio ? Number(perfil.promedio).toFixed(2) : '-'}/><InfoRow label={copy.summary.average} value={promedio || '—'}/></div></div></div>;
  };
  const titulo = copy.menu[seccion];
  return <>
  {modalInscripcion && <div className="modal-backdrop alumno-inscripcion-backdrop" role="presentation" onClick={() => { if (!inscribiendo) setModalInscripcion(null); }}>
    <div className="modal-card alumno-inscripcion-modal" role="dialog" aria-modal="true" aria-labelledby="alumno-inscripcion-title" onClick={event => event.stopPropagation()}>
      <span className={`alumno-inscripcion-icon alumno-inscripcion-icon--${modalInscripcion.kind}`} aria-hidden="true">
        {modalInscripcion.kind === 'success' ? '✓' : modalInscripcion.kind === 'error' ? '!' : modalInscripcion.kind === 'processing' ? '…' : '▣'}
      </span>
      <h3 id="alumno-inscripcion-title">{copy.enrollment[`${modalInscripcion.kind}Title`] || copy.enrollment.confirmTitle}</h3>
      {modalInscripcion.kind === 'processing'
        ? <p>{copy.enrollment.submitting}</p>
        : <p>{modalInscripcion.message}</p>}
      {modalInscripcion.kind === 'confirm' && <ul className="alumno-inscripcion-selected">
        {materias.filter(item => materiasSeleccionadas.includes(item.id)).map(item => <li key={item.id}><strong>{item.clave}</strong> · {item.nombre}</li>)}
      </ul>}
      <div className="modal-actions">
        {modalInscripcion.kind === 'confirm' && <button type="button" className="btn-secondary" onClick={() => setModalInscripcion(null)}>{copy.enrollment.cancel}</button>}
        {modalInscripcion.kind !== 'processing' && <button type="button" className="btn-primary" autoFocus onClick={modalInscripcion.kind === 'confirm' ? inscribirMateriasSeleccionadas : () => setModalInscripcion(null)}>
          {modalInscripcion.kind === 'confirm' ? copy.enrollment.confirmAction : copy.enrollment.close}
        </button>}
      </div>
    </div>
  </div>}
  <section className="panel-section" aria-label={copy.panel}>
    <div className="panel-hero"><div><p className="panel-kicker">{copy.summary.student}</p><h1>{copy.panel}</h1><p className="panel-sub">{copy.extra.intro}</p></div><button className="btn-secondary" onClick={() => cargarDatos(new AbortController().signal)}>{copy.refresh}</button></div>
    {message && <div className="api-success">{message}</div>}
    {error && <div className="api-error">{error}<button className="link-btn" onClick={() => cargarDatos(new AbortController().signal)}>{copy.common.retry}</button></div>}
    {loading && !perfil && <div className="panel-card">{copy.loadingData}</div>}
    {perfil && <div className="alumno-layout">
      <aside className="alumno-sidebar"><div className="alumno-sidebar-user"><span className="alumno-avatar" style={{position:'relative',overflow:'hidden'}}>{(perfil.nombre || 'A').charAt(0).toUpperCase()}{perfil.profile_photo && <img src={fotoUrl(perfil.profile_photo)} alt="" style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover'}} onError={event => {event.currentTarget.style.display = 'none';}}/>}</span><div><strong>{perfil.nombre || copy.summary.student}</strong><small>{perfil.programa || copy.summary.program}</small></div></div>
        <nav className="alumno-nav" aria-label={copy.panel}>{MENU.map(group => <div className="alumno-nav-group" key={group.label}><p>{copy.groups[group.label]}</p>{group.items.map(([id, , icon]) => <button type="button" key={id} className={`alumno-nav-item ${seccion === id ? 'is-active' : ''}`} onClick={() => setSeccion(id)}><span className="alumno-nav-icon">{icon}</span><span>{copy.menu[id]}</span>{id === 'materias' && <b>{inscripciones.length}</b>}{id === 'solicitudes' && <b>{solicitudes.length}</b>}{id === 'entrevistas' && <b>{entrevistas.length}</b>}</button>)}</div>)}</nav>
        <button className="sidebar-logout" onClick={() => onLogout(copy.logout)}>{copy.logout}</button>
      </aside>
      <div className="alumno-content">
        <div className="alumno-section-header"><div><p className="panel-kicker">{copy.panel}</p><h2>{titulo}</h2></div>{loading && <span className="panel-sub">{copy.loading}</span>}</div>
        {notificaciones.some(item => !item.leido) && <section className="panel-card alumno-notifications" aria-label={copy.notifications.title}>
          <div className="alumno-section-title"><h3>{copy.notifications.title}</h3><button type="button" className="btn-secondary" onClick={marcarNotificacionesLeidas}>{copy.notifications.markRead}</button></div>
          <ul>{notificaciones.filter(item => !item.leido).map(item => <li key={item.id}><strong>{item.origen}</strong><p>{item.detalle}</p>{item.estado === 'alerta_apertura_inscripcion' && <button type="button" className="btn-primary" onClick={() => setSeccion('materias')}>{copy.notifications.goEnroll}</button>}</li>)}</ul>
        </section>}
        {contenido()}
      </div>
    </div>}
  </section>
  </>;
}
