import React, {useCallback, useEffect, useRef, useState} from 'react';
import JuradoDefensaPanel from './JuradoDefensaPanel';
import DashboardAnalitico from './DashboardAnalitico';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import MiPerfilAcademico from './MiPerfilAcademico';
import ExpedienteCentralizadoCard from './ExpedienteCentralizadoCard';
import SolicitudesMatchDirector from './SolicitudesMatchDirector';
import {useDirectorCopy} from './directorPanelTranslations';
import {TablaHerramientas, TablaPaginacion, useEtiquetasFiltro, useTablaControl} from './TablaControles';
import './PanelDirector.css';

const ESTADOS_FINALES_EXAMEN = ['aprobado', 'reprobado', 'cancelado'];
const ESTADOS_ACTIVOS_EXAMEN = ['programado', 'iniciado', 'completado'];
const DICTAMENES = ['aprobado', 'observado', 'rechazado'];

function primerErrorApi(data, fallback) {
  if (!data || typeof data !== 'object') return fallback;
  if (typeof data.detail === 'string') return data.detail;
  const valor = Object.values(data).find(item => typeof item === 'string' || (Array.isArray(item) && typeof item[0] === 'string'));
  return (Array.isArray(valor) ? valor[0] : valor) || fallback;
}

const formatoPromedio = (valor) => valor == null || valor === '' ? '—' : Number(valor).toFixed(2);

export default function PanelDirector({session, onLogout}) {
  const copy = useDirectorCopy();
  const x = copy.extra;
  const sectionGroups = [
    {label: copy.groups.panorama, items: [['resumen', copy.menu.resumen, '▦'], ['analitica', copy.menu.analitica, '▥']]},
    {label: copy.groups.followup, items: [['tesistas', copy.menu.tesistas, '♙'], ['avances', copy.menu.avances, '◴']]},
    {label: copy.groups.evaluation, items: [['predoctoral', copy.menu.predoctoral, '✦'], ['evaluaciones', copy.menu.evaluaciones, '✓'], ['jurado', copy.menu.jurado, '⚖']]},
    {label: copy.groups.academic, items: [['expedientes', copy.menu.expedientes, '▤'], ['proyectos', copy.menu.proyectos, '✦']]},
    {label: copy.groups.account, items: [['perfil', copy.menu.perfil, '●']]},
  ];
  const sections = sectionGroups.flatMap(group => group.items);

  const formatDate = (value) => value ? new Intl.DateTimeFormat(copy.locale, {dateStyle: 'medium'}).format(new Date(value)) : copy.common.pending;
  const formatDateTime = (value) => value ? new Intl.DateTimeFormat(copy.locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value)) : copy.common.pending;

  function estadoMateria(materia) {
    if (materia.calificacion == null) return copy.status.cursando;
    if (materia.calificacion < 7) return copy.status.reprobada;
    if (materia.calificacion < 8) return copy.status.aprobadaSeguimiento;
    return copy.status.aprobada;
  }

  const [active, setActive] = useState('resumen');
  const [datos, setDatos] = useState(null);
  const [solicitudesDireccion, setSolicitudesDireccion] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [mensaje, setMensaje] = useState(null);
  const [avanceProyecto, setAvanceProyecto] = useState({});
  const [guardando, setGuardando] = useState(null);
  const [expedienteVisto, setExpedienteVisto] = useState(null);
  const [examenesPredoctorales, setExamenesPredoctorales] = useState([]);
  const [predoctoralForm, setPredoctoralForm] = useState({aspirante_id: '', descripcion: '', fecha_programada: '', duracion_minutos: 120});
  const [dictamen, setDictamen] = useState(null);
  const [resultado, setResultado] = useState(null);

  const sesionRef = useRef({access: session.access, onLogout, expired: copy.messages.expired});
  sesionRef.current = {access: session.access, onLogout, expired: copy.messages.expired};

  const solicitar = useCallback(async (url, {method = 'GET', body} = {}) => {
    const {access, onLogout: cerrar, expired} = sesionRef.current;
    const headers = {Authorization: `Bearer ${access}`};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch(url, {method, headers, body: body !== undefined ? JSON.stringify(body) : undefined});
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      cerrar(expired);
      throw new Error('');
    }
    return {response, data};
  }, []);

  const avisar = useCallback((texto) => setMensaje(texto ? {tipo: 'ok', texto} : null), []);
  const fallar = useCallback((texto) => setMensaje(texto ? {tipo: 'error', texto} : null), []);

  const cargarExamenes = useCallback(async () => {
    const {response, data} = await solicitar('/api/predoctoral/examenes/');
    if (response.ok) setExamenesPredoctorales(data.examenes || []);
  }, [solicitar]);

  const cargarPanel = useCallback(async () => {
    setCargando(true);
    try {
      const {response, data} = await solicitar('/api/director/panel/');
      if (!response.ok) throw new Error(primerErrorApi(data, copy.messages.loadPanel));
      setDatos(data);
      setSolicitudesDireccion(data.solicitudes_direccion || []);
      await cargarExamenes();
    } catch (err) {
      if (err.message) fallar(err.message);
    } finally {
      setCargando(false);
    }
  }, [solicitar, cargarExamenes, fallar, copy.messages.loadPanel]);

  useEffect(() => { cargarPanel(); }, [session.access]);

  function cambiarSeccion(id) {
    setActive(id);
    setMensaje(null);
    setDictamen(null);
    setResultado(null);
  }

  const director = datos?.director || {};
  const tesistas = datos?.tesistas || [];
  const expedientes = datos?.expedientes || [];
  const proyectos = datos?.proyectos_tesis || [];
  const proyectosAprobados = proyectos.filter(proyecto => proyecto.estado === 'aprobado');
  const resumen = datos?.resumen || {};
  const evaluaciones = tesistas.flatMap((tesista) => (tesista.materias || []).map((materia) => ({...materia, tesista: tesista.nombre})));
  const etiquetasFiltro = useEtiquetasFiltro();
  const camposTesista = tesista => [tesista.nombre, tesista.correo, tesista.matricula, tesista.programa];
  const tesistasTabla = useTablaControl(tesistas, {campos: camposTesista, filtros: {programa: tesista => tesista.programa}});
  const avancesTabla = useTablaControl(tesistas, {campos: camposTesista, filtros: {programa: tesista => tesista.programa}});
  const firmaDirector = expediente => (expediente.firmas || []).find((item) => item.rol_firmante === 'director');
  const expedientesTabla = useTablaControl(expedientes, {
    campos: expediente => [expediente.aspirante_nombre, expediente.matricula, expediente.usuario, expediente.folio],
    filtros: {estado: expediente => expediente.estado, firma: expediente => firmaDirector(expediente) ? 'firmado' : 'pendiente'},
  });
  const proyectosTabla = useTablaControl(proyectos, {
    campos: proyecto => [proyecto.titulo, proyecto.alumno_nombre, proyecto.alumno_matricula, proyecto.resumen, proyecto.linea_investigacion],
    filtros: {estado: proyecto => proyecto.estado_label || proyecto.estado, linea: proyecto => proyecto.linea_investigacion, programa: proyecto => proyecto.alumno_programa},
    porPagina: 5,
  });
  const evaluacionesTabla = useTablaControl(evaluaciones, {
    campos: materia => [materia.tesista, materia.materia_clave, materia.materia_nombre],
    filtros: {tesista: materia => materia.tesista, estado: materia => estadoMateria(materia)},
  });
  const predoctoralTabla = useTablaControl(examenesPredoctorales, {
    campos: examen => [examen.alumno?.nombre, examen.alumno?.matricula, examen.retroalimentacion],
    filtros: {estado: examen => examen.estado_label || examen.estado},
  });
  const alumnoDeExamen = (examen) => examen.alumno?.id ?? examen.aspirante?.id;
  const tesistasPredoctoral = tesistas.filter(tesista => tesista.es_doctorado && !tesista.predoctoral_motivos?.length && !examenesPredoctorales.some(examen =>
    alumnoDeExamen(examen) === tesista.id && (ESTADOS_ACTIVOS_EXAMEN.includes(examen.estado) || examen.estado === 'aprobado')
  ));
  const tesistasSinRequisitos = tesistas.filter(tesista => tesista.es_doctorado && tesista.predoctoral_motivos?.length);
  const menuCounts = {
    tesistas: resumen.tesistas_asignados || 0,
    avances: (resumen.avances_por_revisar || 0) + solicitudesDireccion.length,
    predoctoral: examenesPredoctorales.length,
    evaluaciones: evaluaciones.length,
    jurado: proyectosAprobados.length,
    expedientes: expedientes.length,
    proyectos: proyectos.length,
  };
  const materiasAprobadas = tesistas.reduce((total, item) => total + (item.materias_aprobadas || 0), 0);
  const materiasTotales = tesistas.reduce((total, item) => total + (item.total_materias || 0), 0);
  const porcentajeAprobacion = materiasTotales ? Math.round((materiasAprobadas / materiasTotales) * 100) : 0;
  const promedioTesistas = tesistas.length
    ? (tesistas.reduce((total, item) => total + (Number(item.promedio) || 0), 0) / tesistas.length).toFixed(2)
    : '—';

  async function firmar(expediente) {
    setMensaje(null);
    setGuardando(`firma-${expediente.id}`);
    try {
      const {response, data} = await solicitar(`/api/expedientes/${expediente.id}/firma/`, {method: 'POST', body: {rol_firmante: 'director'}});
      if (!response.ok) throw new Error(primerErrorApi(data, copy.messages.signError));
      avisar(copy.messages.expedienteSigned);
      await cargarPanel();
    } catch (err) { if (err.message) fallar(err.message); } finally { setGuardando(null); }
  }

  async function emitirDictamen(event, proyecto) {
    event.preventDefault();
    if (!dictamen) return;
    const comentario = dictamen.comentario.trim();
    if (dictamen.estado !== 'aprobado' && !comentario) return fallar(x.dictamen.commentRequired);
    setMensaje(null);
    setGuardando(`dictamen-${proyecto.id}`);
    try {
      const body = {estado: dictamen.estado};
      if (comentario) body.comentarios_revision = comentario;
      const {response, data} = await solicitar(`/api/proyectos-tesis/${proyecto.id}/`, {method: 'PATCH', body});
      if (!response.ok) throw new Error(primerErrorApi(data, copy.messages.projectUpdate));
      setDictamen(null);
      avisar(`${copy.messages.projectUpdated} ${data.estado_label || dictamen.estado}.`);
      await cargarPanel();
    } catch (err) { if (err.message) fallar(err.message); } finally { setGuardando(null); }
  }

  async function actualizarAvanceProyecto(event, proyecto) {
    event.preventDefault();
    setMensaje(null);
    setGuardando(`avance-${proyecto.id}`);
    try {
      const {response, data} = await solicitar(`/api/proyectos-tesis/${proyecto.id}/`, {method: 'PATCH', body: {avance_porcentaje: Number(avanceProyecto[proyecto.id] ?? proyecto.avance_porcentaje ?? 0)}});
      if (!response.ok) throw new Error(primerErrorApi(data, copy.messages.projectUpdate));
      avisar(copy.messages.progressUpdated);
      await cargarPanel();
    } catch (err) { if (err.message) fallar(err.message); } finally { setGuardando(null); }
  }

  async function programarPredoctoral(event) {
    event.preventDefault();
    if (!predoctoralForm.aspirante_id) return fallar(copy.messages.selectionRequired);
    if (!predoctoralForm.fecha_programada) return fallar(copy.messages.dateRequired);
    setMensaje(null);
    setGuardando('predoctoral');
    try {
      const {response, data} = await solicitar('/api/predoctoral/examenes/', {method: 'POST', body: {...predoctoralForm, titulo: x.predoctoral.title, fecha_programada: new Date(predoctoralForm.fecha_programada).toISOString()}});
      if (!response.ok) throw new Error(primerErrorApi(data, copy.messages.examProgram));
      setPredoctoralForm({aspirante_id: '', descripcion: '', fecha_programada: '', duracion_minutos: 120});
      avisar(copy.messages.examScheduled);
      await cargarExamenes();
    } catch (err) { if (err.message) fallar(err.message); } finally { setGuardando(null); }
  }

  async function actualizarPredoctoral(examen, cambios, exito = x.predoctoral.examUpdated) {
    setMensaje(null);
    setGuardando(`examen-${examen.id}`);
    try {
      const {response, data} = await solicitar(`/api/predoctoral/examenes/${examen.id}/`, {method: 'PATCH', body: cambios});
      if (!response.ok) throw new Error(primerErrorApi(data, copy.messages.updateExam));
      setExamenesPredoctorales(items => items.map(item => item.id === data.id ? {...item, ...data} : item));
      avisar(exito);
      return true;
    } catch (err) {
      if (err.message) fallar(err.message);
      return false;
    } finally { setGuardando(null); }
  }

  async function registrarResultado(event, examen) {
    event.preventDefault();
    const nota = Number(resultado?.calificacion);
    if (resultado?.calificacion === '' || Number.isNaN(nota) || nota < 0 || nota > 10) return fallar(x.predoctoral.gradeRange);
    const cambios = {calificacion: nota};
    if (resultado.retroalimentacion.trim()) cambios.retroalimentacion = resultado.retroalimentacion.trim();
    if (await actualizarPredoctoral(examen, cambios, x.predoctoral.resultSaved)) setResultado(null);
  }

  const nombre = director.nombre || copy.common.defaultDirector;
  const titulo = sections.find((section) => section[0] === active)?.[1] || copy.menu.panel;
  const listo = Boolean(datos);

  function accionesExamen(examen) {
    if (ESTADOS_FINALES_EXAMEN.includes(examen.estado)) return <small>{x.predoctoral.finalState}</small>;
    const ocupado = guardando === `examen-${examen.id}`;
    const yaOcurrio = !examen.fecha_programada || new Date(examen.fecha_programada) <= new Date();
    return <>
      {examen.estado === 'programado' && <button type="button" className="btn-secondary" disabled={ocupado || !yaOcurrio} onClick={() => actualizarPredoctoral(examen, {estado: 'iniciado'})}>{x.predoctoral.start}</button>}
      {examen.estado === 'iniciado' && <button type="button" className="btn-secondary" disabled={ocupado} onClick={() => actualizarPredoctoral(examen, {estado: 'completado'})}>{x.predoctoral.finish}</button>}
      <button type="button" className="btn-primary" disabled={ocupado || !yaOcurrio} title={yaOcurrio ? undefined : x.predoctoral.notYet} onClick={() => setResultado({id: examen.id, calificacion: examen.calificacion ?? '', retroalimentacion: examen.retroalimentacion || ''})}>{x.predoctoral.record}</button>
      <button type="button" className="btn-secondary" disabled={ocupado} onClick={() => actualizarPredoctoral(examen, {estado: 'cancelado'})}>{x.predoctoral.cancel}</button>
      {!yaOcurrio && <small>{x.predoctoral.notYet}</small>}
    </>;
  }

  function accionesProyecto(proyecto) {
    if (proyecto.estado === 'en_revision') {
      if (dictamen?.proyectoId === proyecto.id) {
        const requiereComentario = dictamen.estado !== 'aprobado';
        return <form className="tesis-form" onSubmit={(event) => emitirDictamen(event, proyecto)}>
          <strong>{x.dictamen.decision[dictamen.estado]}</strong>
          <label>{x.dictamen.comment}<textarea rows="3" required={requiereComentario} value={dictamen.comentario} onChange={(event) => setDictamen({...dictamen, comentario: event.target.value})}/></label>
          <small>{requiereComentario ? x.dictamen.commentRequired : x.dictamen.commentOptional}</small>
          <div className="director-project-actions">
            <button type="submit" className="btn-primary" disabled={guardando === `dictamen-${proyecto.id}`}>{guardando === `dictamen-${proyecto.id}` ? x.dictamen.saving : x.dictamen.submit}</button>
            <button type="button" className="btn-secondary" onClick={() => setDictamen(null)}>{x.dictamen.cancel}</button>
          </div>
        </form>;
      }
      return DICTAMENES.map(estado => <button key={estado} type="button" className={estado === 'aprobado' ? 'btn-primary' : 'btn-secondary'} onClick={() => { setMensaje(null); setDictamen({proyectoId: proyecto.id, estado, comentario: ''}); }}>{x.dictamen.decision[estado]}</button>);
    }
    if (proyecto.estado === 'borrador') return <small>{x.dictamen.waitingDraft}</small>;
    if (proyecto.estado === 'observado') return <small>{x.dictamen.waitingFixes}</small>;
    return <small>{x.dictamen.closed}</small>;
  }

  return (
    <section className="admin-dashboard docente-dashboard director-dashboard" aria-label={copy.panel}>
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
          <div className="admin-brand-mark director-brand-mark">{director.profile_photo ? <img src={fotoUrl(director.profile_photo)} alt={copy.common.profilePhoto} /> : nombre.charAt(0)}</div>
          <div><p className="panel-kicker">{copy.kicker}</p><h2>{copy.title}</h2><small>{copy.subtitle}</small></div>
        </div>
        <nav className="admin-menu" aria-label={copy.panel}>
          {sectionGroups.map(group => <div className="docente-nav-group" key={group.label}><p>{group.label}</p>{group.items.map(([id, label, icon]) => <button key={id} type="button" className={`admin-menu-item ${active === id ? 'is-active' : ''}`} onClick={() => cambiarSeccion(id)}><i aria-hidden="true">{icon}</i><span>{label}</span>{menuCounts[id] != null && <small>{menuCounts[id]}</small>}</button>)}</div>)}
        </nav>
        <div className="admin-side-card"><p>{copy.cards.followUp}</p><strong>{resumen.tesistas_asignados || 0}</strong><span>{copy.welcome.assigned}</span></div>
        <button type="button" className="admin-logout" onClick={() => onLogout(copy.messages.sessionClosed)}>{copy.logout}</button>
      </aside>

      <main className="admin-main-panel">
        <header className="admin-topbar"><div><p className="panel-kicker">{copy.menu.panel}</p><h1>{titulo}</h1></div><div className="admin-top-actions"><button type="button" className="btn-secondary" onClick={cargarPanel} disabled={cargando}>{copy.refresh}</button></div></header>
        {mensaje && <div className={mensaje.tipo === 'ok' ? 'api-success' : 'api-error'} role={mensaje.tipo === 'ok' ? 'status' : 'alert'}>{mensaje.texto}</div>}
        {!listo && cargando && <div className="director-empty"><div>◌</div><h3>{copy.loading}</h3><p>{copy.loadingText}</p></div>}
        {listo && active === 'analitica' && <DashboardAnalitico title={copy.dashboard.title} description={copy.dashboard.description} metrics={[{label: copy.dashboard.students, value:resumen.tesistas_asignados || 0}, {label: copy.dashboard.activeFiles, value:resumen.expedientes_activos || 0}, {label: copy.dashboard.projects, value:proyectos.length}, {label: copy.dashboard.average, value:tesistas.length ? (tesistas.reduce((total, item) => total + (Number(item.promedio) || 0), 0) / tesistas.length).toFixed(2) : '0.00'}]} distribution={[{label: copy.dashboard.approvedSubjects, value:tesistas.reduce((total, item) => total + (item.materias_aprobadas || 0), 0)}, {label: copy.dashboard.inProgressSubjects, value:tesistas.reduce((total, item) => total + (item.materias_cursando || 0), 0)}, {label: copy.dashboard.failedSubjects, value:tesistas.reduce((total, item) => total + (item.materias_reprobadas || 0), 0)}, {label: copy.dashboard.projectReview, value:resumen.avances_por_revisar || 0}]} />}
        {listo && active === 'jurado' && <JuradoDefensaPanel solicitar={solicitar} proyectos={proyectosAprobados} onUpdated={cargarPanel} onMessage={avisar} onError={fallar} />}

        {listo && active === 'predoctoral' && <div className="director-card">
          <div className="director-card-head"><div><span className="panel-kicker">{x.predoctoral.kicker}</span><h2>{x.predoctoral.title}</h2><p>{x.predoctoral.description}</p></div><span className="director-count">{examenesPredoctorales.length} {x.predoctoral.count}</span></div>
          {tesistasPredoctoral.length ? <form className="tesis-form" onSubmit={programarPredoctoral}>
            <label>{x.predoctoral.student}<select required value={predoctoralForm.aspirante_id} onChange={event => setPredoctoralForm({...predoctoralForm, aspirante_id: event.target.value})}><option value="">{x.predoctoral.selectStudent}</option>{tesistasPredoctoral.map(tesista => <option key={tesista.id} value={tesista.id}>{tesista.nombre} · {tesista.matricula || copy.common.noEnrollment}</option>)}</select></label>
            <small>{x.predoctoral.onlyDoctoral}</small>
            <label>{x.predoctoral.dateTime}<input type="datetime-local" required value={predoctoralForm.fecha_programada} onChange={event => setPredoctoralForm({...predoctoralForm, fecha_programada: event.target.value})}/></label>
            <label>{x.predoctoral.duration}<input type="number" min="15" value={predoctoralForm.duracion_minutos} onChange={event => setPredoctoralForm({...predoctoralForm, duracion_minutos: event.target.value})}/></label>
            <label>{x.predoctoral.descriptionLabel}<textarea rows="2" value={predoctoralForm.descripcion} onChange={event => setPredoctoralForm({...predoctoralForm, descripcion: event.target.value})} placeholder={x.predoctoral.placeholder}/></label>
            <button type="submit" className="btn-primary" disabled={guardando === 'predoctoral'}>{guardando === 'predoctoral' ? x.dictamen.saving : x.predoctoral.schedule}</button>
          </form> : <p className="director-note">{x.predoctoral.noDoctoral}</p>}
          {tesistasSinRequisitos.length > 0 && <div className="director-note"><strong>{x.predoctoral.notYetEligible}</strong><ul>{tesistasSinRequisitos.map(tesista => <li key={tesista.id}>{tesista.nombre}: {tesista.predoctoral_motivos.join(' ')}</li>)}</ul></div>}
          {examenesPredoctorales.length ? <><TablaHerramientas control={predoctoralTabla} filtros={[{clave: 'estado', etiqueta: x.predoctoral.status}]} /><div className="director-table-wrap tabla-scroll"><table className="director-table"><thead><tr><th>{x.predoctoral.student}</th><th>{x.predoctoral.date}</th><th>{x.predoctoral.status}</th><th>{x.predoctoral.grade}</th><th>{x.predoctoral.actions}</th></tr></thead><tbody>{predoctoralTabla.visibles.map(examen => <React.Fragment key={examen.id}>
            <tr><td><strong>{examen.alumno?.nombre || copy.common.noStudent}</strong><small>{examen.alumno?.matricula || ''}</small></td><td>{formatDateTime(examen.fecha_programada)}</td><td><span className={`director-status-badge ${examen.color || 'neutral'}`}>{examen.estado_label}</span></td><td>{examen.calificacion ?? x.predoctoral.pending}{examen.retroalimentacion && <small>{examen.retroalimentacion}</small>}</td><td>{accionesExamen(examen)}</td></tr>
            {resultado?.id === examen.id && <tr><td colSpan="5"><form className="tesis-form" onSubmit={(event) => registrarResultado(event, examen)}>
              <label>{x.predoctoral.gradeLabel}<input type="number" min="0" max="10" step="0.1" required value={resultado.calificacion} onChange={event => setResultado({...resultado, calificacion: event.target.value})}/></label>
              <small>{x.predoctoral.gradeHint}</small>
              <label>{x.predoctoral.feedback}<textarea rows="3" value={resultado.retroalimentacion} onChange={event => setResultado({...resultado, retroalimentacion: event.target.value})}/></label>
              <div className="director-project-actions"><button type="submit" className="btn-primary" disabled={guardando === `examen-${examen.id}`}>{x.predoctoral.save}</button><button type="button" className="btn-secondary" onClick={() => setResultado(null)}>{x.predoctoral.close}</button></div>
            </form></td></tr>}
          </React.Fragment>)}</tbody></table></div><TablaPaginacion control={predoctoralTabla} /></> : <div className="director-empty"><h3>{x.predoctoral.emptyTitle}</h3><p>{x.predoctoral.emptyText}</p></div>}
        </div>}

        {listo && active === 'resumen' && <>
          <section className="alumno-dashboard-hero director-summary-hero">
            <div className="alumno-dashboard-identity">
              <span className="alumno-dashboard-avatar">
                {nombre.charAt(0).toUpperCase()}
                {director.profile_photo && <img src={fotoUrl(director.profile_photo)} alt="" onError={event => {event.currentTarget.style.display = 'none';}}/>}
              </span>
              <div className="alumno-dashboard-greeting">
                <p className="panel-kicker">{copy.panel}</p>
                <h3>{copy.welcome.greeting}, {nombre.split(' ')[0]}</h3>
                <p>{copy.common.professor}: <strong>{director.usuario || director.correo || '—'}</strong></p>
              </div>
            </div>
            <span className="badge badge--info">{copy.subtitle}</span>
            <div className="alumno-dashboard-profile" aria-label={copy.menu.resumen}>
              <div className="info-row"><span>{copy.tables.program}</span><strong>{director.programa || copy.common.noProgram}</strong></div>
              <div className="info-row"><span>{copy.welcome.activeFiles}</span><strong>{resumen.expedientes_activos || 0}</strong></div>
              <div className="info-row"><span>{copy.welcome.evaluations}</span><strong>{resumen.evaluaciones || 0}</strong></div>
            </div>
          </section>

          <section className="alumno-stats director-summary-stats" aria-label={copy.menu.resumen}>
            <article className="alumno-stat-card director-summary-stat director-summary-stat--students"><span aria-hidden="true">♙</span><strong>{resumen.tesistas_asignados || 0}</strong><small>{copy.welcome.assigned}</small></article>
            <article className="alumno-stat-card director-summary-stat director-summary-stat--files"><span aria-hidden="true">▤</span><strong>{resumen.expedientes_activos || 0}</strong><small>{copy.welcome.activeFiles}</small></article>
            <article className="alumno-stat-card director-summary-stat director-summary-stat--courses"><span aria-hidden="true">✓</span><strong>{resumen.evaluaciones || 0}</strong><small>{copy.welcome.evaluations}</small></article>
            <article className="alumno-stat-card director-summary-stat director-summary-stat--reviews"><span aria-hidden="true">◷</span><strong>{menuCounts.avances}</strong><small>{copy.welcome.advances}</small></article>
          </section>

          <section className="panel-card alumno-dashboard-actions director-summary-actions">
            <div className="alumno-dashboard-section-heading"><p className="panel-kicker">{copy.panel}</p><h3>{copy.dashboard.quickAccess}</h3></div>
            <div className="alumno-dashboard-action-grid">
              <button type="button" onClick={() => cambiarSeccion('tesistas')}><span aria-hidden="true">♙</span><strong>{copy.menu.tesistas}</strong><span aria-hidden="true">↗</span></button>
              <button type="button" onClick={() => cambiarSeccion('avances')}><span aria-hidden="true">◷</span><strong>{copy.menu.avances}</strong><span aria-hidden="true">↗</span></button>
              <button type="button" onClick={() => cambiarSeccion('proyectos')}><span aria-hidden="true">✦</span><strong>{copy.menu.proyectos}</strong><span aria-hidden="true">↗</span></button>
            </div>
          </section>

          {tesistas.length ? <section className="panel-card alumno-dashboard-actions director-summary-followup">
              <div className="alumno-dashboard-section-heading director-summary-followup-heading"><div><p className="panel-kicker">{copy.welcome.followUp}</p><h3>{copy.tables.studentProgress}</h3></div><button type="button" className="btn-secondary" onClick={() => cambiarSeccion('tesistas')}>{copy.welcome.visible}</button></div>
              <div className="director-summary-advisee-list">{tesistas.slice(0, 4).map((tesista) => {
                const total = tesista.total_materias || 0;
                const aprobadas = tesista.materias_aprobadas || 0;
                const progreso = total ? Math.round((aprobadas / total) * 100) : 0;
                return <article className="director-summary-advisee" key={tesista.id}>
                  <span className="director-summary-advisee-avatar" aria-hidden="true">{tesista.nombre?.trim().charAt(0).toUpperCase() || '•'}</span>
                  <div className="director-summary-advisee-main">
                    <div className="director-summary-advisee-heading"><div className="director-summary-advisee-info"><strong>{tesista.nombre}</strong><small>{tesista.matricula || copy.common.noEnrollment} · {tesista.programa || copy.common.noProgram}</small></div><b>{formatoPromedio(tesista.promedio)}</b></div>
                    <div className="director-summary-progress-track" role="progressbar" aria-valuenow={progreso} aria-valuemin="0" aria-valuemax="100" aria-label={`${copy.tables.approved}: ${progreso}%`}><span style={{width: `${progreso}%`}}/></div>
                    <small className="director-summary-progress-label">{aprobadas}/{total} {copy.tables.approved.toLowerCase()} {copy.tables.matters.toLowerCase()}</small>
                  </div>
                </article>;
              })}</div>
              <div className="director-summary-aggregate"><span>{copy.dashboard.academicProgress}</span><strong>{porcentajeAprobacion}%</strong><small>{materiasAprobadas}/{materiasTotales} {copy.tables.approved.toLowerCase()} · {copy.tables.average}: {promedioTesistas}</small></div>
          </section> : <div className="director-empty"><div>◈</div><h3>{copy.welcome.noAssignmentsTitle}</h3><p>{copy.welcome.noAssignmentsText}</p></div>}
        </>}

        {listo && active === 'tesistas' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.welcome.academicAssign}</span><h2>{copy.menu.tesistas}</h2></div><span className="director-count">{tesistas.length} {copy.common.records}</span></div>{tesistas.length ? <><TablaHerramientas control={tesistasTabla} filtros={[{clave: 'programa', etiqueta: copy.tables.program}]} /><div className="director-table-wrap tabla-scroll"><table className="director-table"><thead><tr><th>{copy.tables.students}</th><th>{copy.tables.enrollment}</th><th>{copy.tables.program}</th><th>{copy.tables.subjects}</th><th>{copy.tables.approved}</th><th>{copy.tables.average}</th></tr></thead><tbody>{tesistasTabla.visibles.map((tesista) => <tr key={tesista.id}><td><strong>{tesista.nombre}</strong><small>{tesista.correo}</small></td><td>{tesista.matricula || copy.common.pending}</td><td>{tesista.programa || copy.common.noProgram}</td><td>{tesista.total_materias}</td><td>{tesista.materias_aprobadas}</td><td>{formatoPromedio(tesista.promedio)}</td></tr>)}</tbody></table></div><TablaPaginacion control={tesistasTabla} /></> : <div className="director-empty"><h3>{copy.records.noTesistasTitle}</h3><p>{copy.records.noTesistasText}</p></div>}</div>}

        {listo && active === 'expedientes' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.menu.expedientes}</span><h2>{copy.menu.expedientes}</h2></div><span className="director-count">{expedientes.length} {copy.common.records}</span></div>{expedientes.length ? <><TablaHerramientas control={expedientesTabla} filtros={[{clave: 'estado', etiqueta: copy.tables.state}, {clave: 'firma', etiqueta: copy.tables.firm, opciones: [{value: 'firmado', label: copy.common.signed}, {value: 'pendiente', label: copy.common.pending}]}]} /><div className="director-table-wrap tabla-scroll"><table className="director-table"><thead><tr><th>{copy.tables.students}</th><th>{copy.tables.file}</th><th>{copy.tables.created}</th><th>{copy.tables.state}</th><th>{copy.tables.firm}</th><th>{copy.tables.action}</th></tr></thead><tbody>{expedientesTabla.visibles.map((expediente) => { const firma = firmaDirector(expediente); return <tr key={expediente.id}><td><strong>{expediente.aspirante_nombre}</strong><small>{expediente.matricula || expediente.usuario}</small></td><td>{expediente.folio}</td><td>{formatDate(expediente.fecha_creacion)}</td><td>{expediente.estado}</td><td>{firma ? `${copy.common.signed} ${formatDate(firma.firmado_at)}` : copy.common.pending}</td><td>{!firma && <button type="button" className="btn-primary" onClick={() => firmar(expediente)} disabled={guardando === `firma-${expediente.id}`}>{copy.common.sign}</button>} <button type="button" className="btn-secondary" onClick={() => setExpedienteVisto(expedienteVisto === expediente.id ? null : expediente.id)}>{expedienteVisto === expediente.id ? x.hideRecord : x.viewRecord}</button></td></tr>; })}</tbody></table></div><TablaPaginacion control={expedientesTabla} /></> : <div className="director-empty"><h3>{copy.records.noExpedientesTitle}</h3><p>{copy.records.noExpedientesText}</p></div>}{expedienteVisto && <ExpedienteCentralizadoCard key={`${expedienteVisto}-${expedientes.find((e) => e.id === expedienteVisto)?.firmas?.length || 0}`} expedienteId={expedienteVisto} session={session}/>}</div>}

        {listo && active === 'proyectos' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.dashboard.projectTitle}</span><h2>{copy.dashboard.projectTitle}</h2><p>{copy.dashboard.projectDescription}</p></div><span className="director-count">{proyectos.length} {copy.dashboard.projects}</span></div>{proyectos.length ? <><TablaHerramientas control={proyectosTabla} filtros={[{clave: 'estado', etiqueta: etiquetasFiltro.status}, {clave: 'linea', etiqueta: etiquetasFiltro.line}, {clave: 'programa', etiqueta: copy.tables.program}]} /><div className="director-project-list tabla-scroll-lista">{proyectosTabla.visibles.map((proyecto) => { const progreso = Number(proyecto.avance_porcentaje) || 0; return <article key={proyecto.id}><div><strong>{proyecto.titulo}</strong><small>{proyecto.alumno_nombre} · {proyecto.alumno_matricula || copy.common.noEnrollment} · {proyecto.alumno_programa || copy.common.noProgram}</small><p>{proyecto.resumen}</p><span className="director-project-meta">{proyecto.linea_investigacion || copy.tables.linePending} · {copy.tables.updated} {formatDate(proyecto.updated_at)}</span><div className="director-thesis-progress"><div className="director-thesis-progress-heading"><strong>{copy.dashboard.thesisProgress}</strong><span>{progreso}%</span></div><div className="director-thesis-progress-track" role="progressbar" aria-label={copy.dashboard.thesisProgress} aria-valuemin="0" aria-valuemax="100" aria-valuenow={progreso}><span style={{width: `${progreso}%`}}/></div><form onSubmit={(event) => actualizarAvanceProyecto(event, proyecto)}><label htmlFor={`thesis-progress-${proyecto.id}`}>{copy.dashboard.thesisProgress}</label><input id={`thesis-progress-${proyecto.id}`} type="number" min="0" max="100" step="1" required value={avanceProyecto[proyecto.id] ?? progreso} onChange={(event) => setAvanceProyecto(current => ({...current, [proyecto.id]: event.target.value}))}/><button type="submit" className="btn-secondary" disabled={guardando === `avance-${proyecto.id}`}>{guardando === `avance-${proyecto.id}` ? copy.dashboard.savingProgress : copy.dashboard.saveProgress}</button></form></div>{proyecto.comentarios_revision && <blockquote>{proyecto.comentarios_revision}</blockquote>}</div><div className="director-project-actions"><span className={`director-status-badge ${proyecto.estado === 'aprobado' ? 'success' : proyecto.estado === 'rechazado' ? 'danger' : proyecto.estado === 'observado' ? 'warning' : 'neutral'}`}>{proyecto.estado_label}</span>{accionesProyecto(proyecto)}</div></article>; })}</div><TablaPaginacion control={proyectosTabla} /></> : <div className="director-empty"><h3>{copy.records.noProjectsTitle}</h3><p>{copy.records.noProjectsText}</p></div>}</div>}

        {listo && active === 'avances' && <><div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.dashboard.reviewPanel}</span><h2>{copy.dashboard.academicProgress}</h2></div></div>{tesistas.length ? <><TablaHerramientas control={avancesTabla} filtros={[{clave: 'programa', etiqueta: copy.tables.program}]} /><div className="director-table-wrap tabla-scroll"><table className="director-table"><thead><tr><th>{x.progress.student}</th><th>{x.progress.subjects}</th><th>{x.progress.approved}</th><th>{x.progress.failed}</th><th>{x.progress.credits}</th><th>{x.progress.average}</th></tr></thead><tbody>{avancesTabla.visibles.map((tesista) => <tr key={tesista.id}><td><strong>{tesista.nombre}</strong></td><td>{tesista.total_materias}</td><td><span className="director-status-badge success">{tesista.materias_aprobadas}</span></td><td><span className="director-status-badge danger">{tesista.materias_reprobadas}</span></td><td>{tesista.creditos_aprobados}</td><td>{formatoPromedio(tesista.promedio)}</td></tr>)}</tbody></table></div><TablaPaginacion control={avancesTabla} /></> : <div className="director-empty"><h3>{copy.cards.noAcademicProgress}</h3><p>{copy.cards.noAcademicProgressText}</p></div>}<p className="director-note">{datos?.avance_tesis_mensaje}</p></div><SolicitudesMatchDirector solicitudes={solicitudesDireccion} session={session} onUpdated={cargarPanel} onMessage={avisar} onError={fallar}/></>}

        {listo && active === 'evaluaciones' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.dashboard.evaluationTitle}</span><h2>{copy.dashboard.academicTrajectory}</h2></div><span className="director-count">{evaluaciones.length} {copy.tables.matters}</span></div>{evaluaciones.length ? <><TablaHerramientas control={evaluacionesTabla} filtros={[{clave: 'tesista', etiqueta: copy.tables.student}, {clave: 'estado', etiqueta: copy.tables.state}]} /><div className="director-table-wrap tabla-scroll"><table className="director-table"><thead><tr><th>{copy.tables.student}</th><th>{copy.tables.subjects}</th><th>{copy.tables.partials}</th><th>{copy.common.grade}</th><th>{copy.tables.state}</th></tr></thead><tbody>{evaluacionesTabla.visibles.map((materia) => <tr key={`${materia.id}-${materia.tesista}`}><td>{materia.tesista}</td><td><strong>{materia.materia_clave}</strong><small>{materia.materia_nombre}</small></td><td>{[materia.parcial_1, materia.parcial_2, materia.parcial_3].map((value) => value ?? '—').join(' / ')}</td><td>{materia.calificacion ?? '—'}</td><td><span className={`director-status-badge ${materia.color || 'neutral'}`}>{estadoMateria(materia)}</span></td></tr>)}</tbody></table></div><TablaPaginacion control={evaluacionesTabla} /></> : <div className="director-empty"><h3>{copy.records.noEvaluationsTitle}</h3><p>{copy.records.noEvaluationsText}</p></div>}</div>}

        {listo && active === 'perfil' && <section className="docente-profile-layout director-profile-layout">
          <header className="docente-profile-hero">
            <div className="docente-profile-avatar">
              {director.profile_photo
                ? <img src={fotoUrl(director.profile_photo)} alt={nombre}/>
                : <span>{nombre.charAt(0).toUpperCase()}</span>}
            </div>
            <div className="docente-profile-identity">
              <p className="panel-kicker">{copy.menu.perfil}</p>
              <h2>{nombre}</h2>
              <p>{copy.subtitle}</p>
            </div>
            <div className="docente-profile-details">
              <div><span>{copy.common.user}</span><strong>{director.usuario || '—'}</strong></div>
              <div><span>{copy.common.email}</span><strong>{director.correo || '—'}</strong></div>
              <div><span>{copy.tables.program}</span><strong>{director.programa || copy.common.noProgram}</strong></div>
              <div><span>{copy.common.unit}</span><strong>{director.unidad || director.departamento || '—'}</strong></div>
            </div>
          </header>
          <div className="docente-profile-sections">
            <MiPerfilAcademico session={session} docenteId={director.id} onLogout={onLogout} />
            <PerfilAspirante perfil={{...director, telefono: director.telefono || ''}} session={session} onActualizado={(actualizado) => setDatos(actual => ({...actual, director: {...actual.director, ...actualizado}}))} />
          </div>
        </section>}
      </main>
    </section>
  );
}
