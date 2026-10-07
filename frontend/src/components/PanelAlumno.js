import React, {useCallback, useEffect, useMemo, useState} from 'react';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import {useStudentCopy} from './studentPanelTranslations';
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
function EstadoInicioTesis({flujo, form, setForm, onSolicitar, cargando = false}) {
  const copy = useStudentCopy();
  const t = copy.thesis;
  const elegibilidad = flujo?.elegibilidad;
  const solicitud = flujo?.solicitud;
  const resumen = elegibilidad?.resumen || {};
  if (!elegibilidad) return <div className="panel-card"><h3>{t.lockTitle}</h3><p>{cargando ? t.checking : t.planUnavailable}</p></div>;
  return <div className="tesis-view">
    <div className="panel-card">
      <div className="alumno-section-title"><div><p className="panel-kicker">{t.kicker}</p><h3>{t.validation}</h3></div><Badge tone={elegibilidad.elegible ? 'success' : 'warning'}>{elegibilidad.elegible ? t.completed : t.missing}</Badge></div>
      {elegibilidad.configuracion && <><p>{elegibilidad.configuracion.grado_label} · {elegibilidad.configuracion.duracion_anios} {t.years} · {elegibilidad.configuracion.periodos_requeridos} {t.periods}.</p><div className="avance-metrics"><div><strong>{resumen.materias_obligatorias_aprobadas} / {resumen.materias_obligatorias}</strong><span>{t.requiredCourses}</span></div><div><strong>{resumen.creditos_aprobados} / {resumen.creditos_requeridos || '-'}</strong><span>{t.credits}</span></div><div><strong>{resumen.periodos_cursados} / {resumen.periodos_requeridos}</strong><span>{t.periodsComplete}</span></div></div></>}
      {!elegibilidad.elegible && <div className="api-error"><strong>{t.notReady}</strong><ul>{elegibilidad.motivos.map(motivo => <li key={motivo}>{motivo}</li>)}</ul></div>}
    </div>
    {elegibilidad.elegible && !solicitud && <div className="panel-card"><h3>{t.startTitle}</h3><p>{t.startText}</p><form className="tesis-form" onSubmit={onSolicitar}><label>{t.line}<input value={form.linea_investigacion} onChange={event => setForm({...form, linea_investigacion:event.target.value})} placeholder={t.linePlaceholder}/></label><label>{t.justification}<textarea required minLength="20" rows="4" value={form.justificacion} onChange={event => setForm({...form, justificacion:event.target.value})} placeholder={t.justificationPlaceholder}/></label><button className="btn-primary" type="submit">{t.sendCoord}</button></form></div>}
    {solicitud && solicitud.estado !== 'aprobada' && <div className="panel-card"><h3>{t.startTitle}</h3><Badge tone={solicitud.estado === 'rechazada' ? 'danger' : 'info'}>{etiquetaEstado(solicitud.estado, copy)}</Badge><p><strong>{t.line}:</strong> {solicitud.linea_investigacion || '—'}</p>{solicitud.observaciones && <p><strong>{t.comments}:</strong> {solicitud.observaciones}</p>}</div>}
  </div>;
}

export default function PanelAlumno({session, onLogout}) {
  const copy = useStudentCopy();
  const [perfil, setPerfil] = useState(null), [inscripciones, setInscripciones] = useState([]), [materias, setMaterias] = useState([]), [solicitudes, setSolicitudes] = useState([]), [entrevistas, setEntrevistas] = useState([]), [examenes, setExamenes] = useState([]), [proyectosTesis, setProyectosTesis] = useState([]), [inscribiendo, setInscribiendo] = useState(false);
  const [materiasSeleccionadas, setMateriasSeleccionadas] = useState([]);
  const [antiplagioForm, setAntiplagioForm] = useState({archivo: null, proveedor: 'turnitin'});
  const [revisionAntiplagio, setRevisionAntiplagio] = useState(null);
  const [subiendoAntiplagio, setSubiendoAntiplagio] = useState(false);
  const [seccion, setSeccion] = useState('resumen'), [error, setError] = useState(''), [loading, setLoading] = useState(true), [message, setMessage] = useState('');
  const [periodoInscripcion, setPeriodoInscripcion] = useState(null);
  const [respuestasExamen, setRespuestasExamen] = useState({});
  const [proyectoForm, setProyectoForm] = useState({titulo:'', resumen:'', linea_investigacion:'', objetivos:'', metodologia:''});
  const [flujoTesis, setFlujoTesis] = useState(null);
  const [solicitudTesisForm, setSolicitudTesisForm] = useState({director_sugerido:'', linea_investigacion:'', justificacion:''});
  const apiHeaders = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);
  const cargarDatos = useCallback(async signal => {
    setLoading(true); setError('');
    try {
      const rs = await Promise.all(['me/', 'inscripciones/', 'materias/', 'solicitudes-academicas/', 'entrevistas/', 'examenes/'].map(path => fetch(`/api/preregistro/${path}`, {headers: apiHeaders, signal})));
      if (rs.some(r => r.status === 401)) { onLogout(copy.messages.expired); return; }
      if (rs.some(r => !r.ok)) throw new Error(copy.messages.loadError);
      setPerfil(await rs[0].json()); setInscripciones(await rs[1].json()); setMaterias(await rs[2].json()); setSolicitudes(await rs[3].json());
      const data = await rs[4].json(); setEntrevistas(data.entrevistas || []); const examenesData = await rs[5].json(); setExamenes(examenesData.examenes || []);
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
  const promedio = useMemo(() => { const a = inscripciones.map(i => Number(i.calificacion)).filter(n => !Number.isNaN(n)); return a.length ? (a.reduce((x, n) => x + n, 0) / a.length).toFixed(2) : null; }, [inscripciones]);
  const descargar = useCallback(async (ruta, nombre) => { try { const r = await fetch(ruta, {headers: apiHeaders}); if (!r.ok) throw new Error(copy.messages.downloadError); const url = URL.createObjectURL(await r.blob()); const a = document.createElement('a'); a.href = url; a.download = nombre; a.click(); URL.revokeObjectURL(url); setMessage(`${nombre}: ${copy.docs.pdf}`); } catch (e) { setError(e.message); } }, [apiHeaders, copy]);
  async function inscribirMateriasSeleccionadas() {
    if (inscribiendo) return;
    if (!periodoInscripcion?.activo) {
      setError(copy.enrollment.activeClosed);
      return;
    }
    const inscripcionesPeriodo = inscripciones.filter(item => item.periodo_nombre === periodoInscripcion.nombre).length;
    const faltan = Math.max(0, 4 - inscripcionesPeriodo);
    if (materiasSeleccionadas.length !== faltan) {
      setError(copy.enrollment.exactCount.replace('{count}', faltan));
      return;
    }
    if (!window.confirm(copy.enrollment.confirm.replace('{count}', materiasSeleccionadas.length).replace('{period}', periodoInscripcion.nombre))) return;
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
    } catch (e) { setError(e.message || copy.messages.courseLoadError); } finally { setInscribiendo(false); }
  }
  async function iniciarExamen(examen) { const r = await fetch('/api/preregistro/examenes/', {method: 'POST', headers: {...apiHeaders, 'Content-Type': 'application/json'}, body: JSON.stringify({id: examen.id})}); const data = await r.json(); if (!r.ok) return setError(data.detail || copy.exams.noStart); setExamenes(items => items.map(item => item.id === data.id ? data : item)); setMessage(copy.exams.started); }
  async function enviarExamen(examen) { const r = await fetch('/api/preregistro/examenes/', {method: 'PUT', headers: {...apiHeaders, 'Content-Type': 'application/json'}, body: JSON.stringify({id: examen.id, respuestas: respuestasExamen})}); const data = await r.json(); if (!r.ok) return setError(data.detail || copy.exams.noSend); setExamenes(items => items.map(item => item.id === data.id ? data : item)); setMessage(`${copy.exams.sent} ${copy.exams.score}: ${data.calificacion}`); }
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
    if (seccion === 'tesis' && (!flujoTesis || !flujoTesis.elegibilidad?.elegible || flujoTesis.solicitud?.estado !== 'aprobada')) return <EstadoInicioTesis flujo={flujoTesis} form={solicitudTesisForm} setForm={setSolicitudTesisForm} onSolicitar={solicitarDireccionTesis} cargando={loading}/>;
    if (seccion === 'diploma') return <div className="panel-card"><div className="alumno-section-title"><div><p className="panel-kicker">{copy.diploma.kicker}</p><h3>{copy.diploma.title}</h3></div><Badge tone="info">{copy.diploma.defense}</Badge></div><p>{copy.diploma.intro}</p>{proyectosTesis.length ? <div className="tesis-list">{proyectosTesis.map(proyecto => <article key={proyecto.id}><div><strong>{proyecto.titulo}</strong><small>{proyecto.defensa ? etiquetaEstado(proyecto.defensa.estado, copy) : copy.diploma.pending}</small><JuradoDefensaAlumno proyecto={proyecto} session={session}/></div></article>)}</div> : <p>{copy.diploma.noProjects}</p>}</div>;
    if (seccion === 'predoctoral') {
      const examenesPredoctorales = examenes.filter(examen => examen.tipo === 'predoctoral');
      return <div className="panel-card"><div className="alumno-section-title"><div><p className="panel-kicker">{copy.predoctoral.kicker}</p><h3>{copy.predoctoral.title}</h3></div><Badge tone="info">{copy.predoctoral.academic}</Badge></div><p>{copy.predoctoral.intro}</p>{examenesPredoctorales.length ? <div className="request-list">{examenesPredoctorales.map(examen => <article key={examen.id}><strong>{examen.titulo}</strong><p>{examen.descripcion || copy.predoctoral.evaluation}</p><p><strong>{copy.common.date}:</strong> {formatoFecha(examen.fecha_programada, copy.locale, copy.communication.datePending)} · <strong>{copy.common.duration}:</strong> {examen.duracion_minutos || 120} {copy.common.minutes}</p><Badge tone={examen.color || 'neutral'}>{etiquetaEstado(examen.estado, copy)}</Badge>{examen.calificacion !== null && examen.calificacion !== undefined && <p>{copy.common.result}: <strong>{examen.calificacion}</strong></p>}{examen.retroalimentacion && <p><strong>{copy.common.feedback}:</strong> {examen.retroalimentacion}</p>}</article>)}</div> : <p>{copy.predoctoral.noExam}</p>}</div>;
    }
    if (seccion === 'examenes') return <div className="panel-card"><h3>{copy.exams.title}</h3><p>{copy.exams.intro}</p>{examenes.length ? <div className="request-list">{examenes.map(examen => <article key={examen.id}><strong>{examen.titulo}</strong><p>{examen.tipo_label} · {examen.duracion_minutos} {copy.common.minutes}</p><span>{etiquetaEstado(examen.estado, copy)}</span>{examen.estado === 'programado' && <button type="button" className="btn-primary" onClick={() => iniciarExamen(examen)}>{copy.exams.start}</button>}{examen.estado === 'iniciado' && <p>{copy.exams.started}</p>}{examen.calificacion !== null && <p>{copy.exams.score}: <strong>{examen.calificacion}</strong></p>}</article>)}</div> : <p>{copy.exams.noExams}</p>}</div>;
    if (seccion === 'resumen') return <div className="alumno-dashboard-grid"><div className="panel-card alumno-welcome-card"><h3>{copy.summary.welcome}, {perfil.nombre || copy.summary.student}</h3><p>{copy.summary.user}: <strong>{perfil.usuario || perfil.correo || '-'}</strong></p><div className="info-grid"><InfoRow label={copy.summary.program} value={perfil.programa}/><InfoRow label={copy.summary.unit} value={perfil.unidad}/><InfoRow label={copy.summary.modality} value={perfil.modalidad}/><InfoRow label={copy.summary.currentStatus} value={etiquetaEstado(perfil.proceso_estado, copy)}/></div></div><div className="alumno-stats"><div><strong>{inscripciones.length}</strong><span>{copy.summary.registered}</span></div><div><strong>{promedio || '-'}</strong><span>{copy.summary.average}</span></div><div><strong>{solicitudes.length}</strong><span>{copy.summary.requests}</span></div><div><strong>{entrevistas.length}</strong><span>{copy.summary.interviews}</span></div></div><div className="panel-card"><h3>{copy.summary.quick}</h3><div className="action-grid"><button className="btn-secondary" onClick={() => setSeccion('horario')}>{copy.summary.schedule}</button><button className="btn-secondary" onClick={() => setSeccion('solicitudes')}>{copy.summary.viewRequests}</button><button className="btn-secondary" onClick={() => setSeccion('tramites')}>{copy.summary.downloadDocs}</button></div></div></div>;
    if (seccion === 'materias') { const inscritas = new Set(inscripciones.map(i => Number(i.materia))); const periodoActivo = Boolean(periodoInscripcion?.activo); const periodoActualInscripciones = inscripciones.filter(i => i.periodo_nombre === periodoInscripcion?.nombre).length; const faltan = Math.max(0, 4 - periodoActualInscripciones); const seleccionadas = new Set(materiasSeleccionadas); const fecha = valor => valor ? new Date(valor).toLocaleDateString(copy.locale) : '-'; const alternarMateria = id => setMateriasSeleccionadas(actual => actual.includes(id) ? actual.filter(item => item !== id) : actual.length < faltan ? [...actual, id] : actual); return <div className="alumno-materias-view"><div className="panel-card"><h3>{copy.summary.courses}</h3><p>{copy.enrollment.exact}</p><div className={`inscripcion-periodo ${periodoActivo ? 'is-open' : 'is-closed'}`}><strong>{periodoActivo ? `${copy.enrollment.open}: ${periodoInscripcion.nombre}` : copy.enrollment.closed}</strong><span>{periodoInscripcion ? `${fecha(periodoInscripcion.apertura)} - ${fecha(periodoInscripcion.cierre)}` : copy.enrollment.notEnabled}</span></div>{periodoActivo && <p className="form-hint">{copy.enrollment.load}: {periodoActualInscripciones} / 4 · {copy.enrollment.selected}: {materiasSeleccionadas.length} / {faltan}</p>}{materias.length > 0 && periodoActivo ? <><div className="materias-grid">{materias.map(m => { const yaInscrita = inscritas.has(Number(m.id)); const seleccionada = seleccionadas.has(m.id); return <article className={`materia-card ${yaInscrita || seleccionada ? 'is-selected' : ''}`} key={m.id}><span className="materia-card-clave">{m.clave}</span><strong className="materia-card-nombre">{m.nombre}</strong><small>{copy.common.period}: {m.periodo_sugerido}<br/>{copy.common.teacher}: {m.profesor || copy.common.notAssigned}<br/>{copy.docs.schedule}: {m.horario || copy.common.toDefine}<br/>{copy.common.roomPending}: {m.salon_label || copy.common.roomPending}<br/>{copy.common.enrolled}: {m.inscritos || 0} / {m.capacidad || 42}</small>{yaInscrita ? <Badge tone="success">{copy.enrollment.already}</Badge> : <button type="button" className="btn-primary" disabled={inscribiendo || faltan === 0 || (!seleccionada && materiasSeleccionadas.length >= faltan)} onClick={() => alternarMateria(m.id)}>{seleccionada ? copy.enrollment.selectedLabel : copy.enrollment.select}</button>}</article>; })}</div><button type="button" className="btn-primary" disabled={inscribiendo || faltan === 0 || materiasSeleccionadas.length !== faltan} onClick={inscribirMateriasSeleccionadas}>{inscribiendo ? copy.enrollment.submitting : faltan === 0 ? `${copy.enrollment.load} (4/4)` : `${copy.enrollment.submit}: ${faltan}`}</button></> : <p>{periodoActivo ? copy.enrollment.noAvailableCourses : copy.enrollment.activeClosed}</p>}</div><div className="panel-card"><h3>{copy.summary.registered}</h3>{inscripciones.length ? <div className="subject-list">{inscripciones.map(m => <MateriaRow key={m.id} materia={m}/>)}</div> : <p>{copy.common.noCourses}</p>}</div></div>; }
    if (seccion === 'calificaciones') return <div className="panel-card"><div className="alumno-section-title"><div><p className="panel-kicker">{copy.grade.kicker}</p><h3>{copy.grade.title}</h3></div></div><AvanceCurricular inscripciones={inscripciones} plan={flujoTesis?.elegibilidad?.configuracion?.materias_plan || []}/><div className="subject-list">{inscripciones.length ? inscripciones.map(m => <MateriaRow key={m.id} materia={m}/>) : <p>{copy.common.noCourses}</p>}</div></div>;
    if (seccion === 'horario' || seccion === 'tramites') {
      const cicloEscolar = inscripciones.find(materia => materia.periodo_nombre)?.periodo_nombre || periodoInscripcion?.nombre || '—';
      const documentos = [
        {tipo: 'constancia', titulo: copy.docs.schoolCertificate, descripcion: copy.docs.schoolCertificateDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/constancia/` : null},
        {tipo: 'calificaciones', titulo: copy.docs.gradesCertificate, descripcion: copy.docs.gradesCertificateDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/calificaciones/` : null},
        {tipo: 'historial', titulo: copy.docs.transcript, descripcion: copy.docs.transcriptDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/historial/` : null},
        {tipo: 'inscripcion', titulo: copy.docs.enrollmentCertificate, descripcion: copy.docs.enrollmentCertificateDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/inscripcion/` : null},
        {tipo: 'egreso', titulo: copy.docs.graduation, descripcion: copy.docs.graduationDesc, ruta: perfil ? `/api/servicios-escolares/alumnos/${perfil.id}/documentos/egreso/` : null},
        {tipo: 'horario', titulo: copy.docs.schedule, descripcion: copy.docs.scheduleDesc, ruta: '/api/preregistro/horario/download/'},
        {tipo: 'boleta', titulo: copy.docs.enrollmentSlip, descripcion: copy.docs.enrollmentSlipDesc, ruta: '/api/preregistro/boleta-inscripcion/download/'},
        {tipo: 'reinscripcion', titulo: copy.docs.reenrollmentSlip, descripcion: copy.docs.reenrollmentSlipDesc, ruta: '/api/preregistro/reinscripcion/download/'},
      ];
      return <div className="panel-card"><h3>{seccion === 'horario' ? copy.docs.scheduleAndReenroll : copy.docs.documentsAndProcedures}</h3><p>{copy.docs.intro}</p>{seccion === 'horario' && <div className="inscripcion-periodo"><strong>{copy.docs.schoolYear}: {cicloEscolar}</strong></div>}{seccion === 'horario' ? <div className="action-grid"><button className="btn-secondary" onClick={() => descargar('/api/preregistro/horario/download/', 'horario.pdf')}>{copy.docs.schedulePdf}</button><button className="btn-secondary" onClick={() => descargar('/api/preregistro/boleta-inscripcion/download/', 'boleta_inscripcion.pdf')}>{copy.docs.enrollmentPdf}</button><button className="btn-secondary" onClick={() => descargar('/api/preregistro/reinscripcion/download/', 'reinscripcion.pdf')}>{copy.docs.reenrollmentPdf}</button></div> : <div className="action-grid">{documentos.filter(doc => doc.ruta).map(doc => <button key={doc.tipo} className="btn-secondary" onClick={() => descargar(doc.ruta, `${doc.tipo}.pdf`)}>{doc.titulo}</button>)}</div>}{seccion === 'horario' && <div className="subject-list">{inscripciones.map(m => <div className="subject-row" key={m.id}><strong>{m.materia_clave}</strong> {m.materia_nombre}<span>{m.materia_profesor || copy.grade.professorMissing} · {m.materia_horario || m.horario || copy.common.toDefine} · {m.materia_salon || copy.common.roomPending}</span></div>)}</div>}</div>;
    }
    if (seccion === 'solicitudes') return <div className="panel-card"><h3>{copy.requests.title}</h3>{solicitudes.length ? <ul className="request-list">{solicitudes.map(i => <li key={i.id}><strong>{i.tipo_label}</strong><p>{i.comentario || '—'}</p><span>{etiquetaEstado(i.estado, copy)}</span></li>)}</ul> : <p>{copy.requests.noRequests}</p>}</div>;
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
  return <section className="panel-section" aria-label={copy.panel}>
    <div className="panel-hero"><div><p className="panel-kicker">{copy.summary.student}</p><h1>{copy.panel}</h1><p className="panel-sub">{copy.extra.intro}</p></div><button className="btn-secondary" onClick={() => cargarDatos(new AbortController().signal)}>{copy.refresh}</button></div>
    {message && <div className="api-success">{message}</div>}
    {error && <div className="api-error">{error}<button className="link-btn" onClick={() => cargarDatos(new AbortController().signal)}>{copy.common.retry}</button></div>}
    {loading && !perfil && <div className="panel-card">{copy.loadingData}</div>}
    {perfil && <div className="alumno-layout">
      <aside className="alumno-sidebar"><div className="alumno-sidebar-user"><span className="alumno-avatar" style={{position:'relative',overflow:'hidden'}}>{(perfil.nombre || 'A').charAt(0).toUpperCase()}{perfil.profile_photo && <img src={fotoUrl(perfil.profile_photo)} alt="" style={{position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'cover'}} onError={event => {event.currentTarget.style.display = 'none';}}/>}</span><div><strong>{perfil.nombre || copy.summary.student}</strong><small>{perfil.programa || copy.summary.program}</small></div></div>
        <nav className="alumno-nav" aria-label={copy.panel}>{MENU.map(group => <div className="alumno-nav-group" key={group.label}><p>{copy.groups[group.label]}</p>{group.items.map(([id, , icon]) => <button type="button" key={id} className={`alumno-nav-item ${seccion === id ? 'is-active' : ''}`} onClick={() => setSeccion(id)}><span className="alumno-nav-icon">{icon}</span><span>{copy.menu[id]}</span>{id === 'materias' && <b>{inscripciones.length}</b>}{id === 'solicitudes' && <b>{solicitudes.length}</b>}{id === 'entrevistas' && <b>{entrevistas.length}</b>}</button>)}</div>)}</nav>
        <button className="sidebar-logout" onClick={() => onLogout(copy.logout)}>{copy.logout}</button>
      </aside>
      <div className="alumno-content"><div className="alumno-section-header"><div><p className="panel-kicker">{copy.panel}</p><h2>{titulo}</h2></div>{loading && <span className="panel-sub">{copy.loading}</span>}</div>{contenido()}</div>
    </div>}
  </section>;
}

