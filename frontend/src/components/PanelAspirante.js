import React, {useCallback, useEffect, useRef, useState} from 'react';
import DocumentosAspirante from './DocumentosAspirante';
import SeguimientoSolicitud from './SeguimientoSolicitud';
import SolicitudApoyo from './SolicitudApoyo';
import PerfilAspirante from './PerfilAspirante';
import ExamenesEnLinea from './ExamenesEnLinea';
import EntrevistasAspirante from './EntrevistasAspirante';
import {useApplicantCopy} from './aspirantPanelTranslations';
import './PanelAspirante.css';
import './PanelAspiranteSingle.css';

const ETAPAS = [
  {id: 'pendiente', icon: '1'},
  {id: 'iniciado', icon: '2'},
  {id: 'revision', icon: '3'},
  {id: 'aceptado', icon: '4'},
];

const MENU_ITEMS = [
  {id: 'perfil'},
  {id: 'inicio'},
  {id: 'expediente'},
  {id: 'proceso'},
  {id: 'documentos'},
  {id: 'entrevistas'},
  {id: 'examenes'},
];

const ESTADOS_RESUELTOS = ['aceptado', 'rechazado', 'baja'];
const INTERVALO_SEGUIMIENTO = 30000;

function etapaIndex(estado) {
  const index = ETAPAS.findIndex((etapa) => etapa.id === estado);
  return index === -1 ? 0 : index;
}

function EstadoBadge({estado, labels}) {
  return <span className={`estado-badge estado-${estado || 'pendiente'}`}>{labels[estado] || estado || labels.pendiente}</span>;
}

function fechaSeguimiento(valor, locale) {
  try {
    return new Intl.DateTimeFormat(locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(valor));
  } catch (e) {
    return valor;
  }
}

function InfoItem({label, value}) {
  return (
    <div className="exp-item">
      <span className="exp-label">{label}</span>
      <span className="exp-value">{value || '—'}</span>
    </div>
  );
}

function SectionPanel({id, label, open, onToggle, children}) {
  return (
    <div className={`aspirante-section-card${open ? ' is-open' : ''}`}>
      <button type="button" className="section-trigger" onClick={onToggle} aria-expanded={Boolean(open)} aria-controls={`section-${id}`}>
        <span>{label}</span>
        <span className="section-indicator">{open ? '−' : '+'}</span>
      </button>
      <div id={`section-${id}`} className="section-panel">
        {children}
      </div>
    </div>
  );
}

function mensajeEtapa(estado, mensajes) {
  return mensajes[estado] || mensajes.pendiente;
}

export default function PanelAspirante({session, onLogout}) {
  const copy = useApplicantCopy();
  const [perfil, setPerfil] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [openSections, setOpenSections] = useState({inicio: true});
  const [seguimiento, setSeguimiento] = useState(null);
  const [seguimientoCargando, setSeguimientoCargando] = useState(true);
  const [examenes, setExamenes] = useState([]);
  const [examenesError, setExamenesError] = useState('');
  const [entrevistas, setEntrevistas] = useState([]);
  const [entrevistasError, setEntrevistasError] = useState('');
  const [evaluaciones, setEvaluaciones] = useState([]);
  const [expedienteCentral, setExpedienteCentral] = useState(null);
  const [expedienteCargando, setExpedienteCargando] = useState(false);
  const sesionCerradaRef = useRef(false);
  const logoutRef = useRef(onLogout);
  logoutRef.current = onLogout;

  const obtener = useCallback(async (url, signal) => {
    const response = await fetch(url, {headers: {Authorization: `Bearer ${session.access}`}, signal});
    if (response.status === 401) {
      if (!sesionCerradaRef.current) {
        sesionCerradaRef.current = true;
        logoutRef.current(copy.messages.sessionExpired);
      }
      const error = new Error(copy.messages.sessionExpired);
      error.name = 'AbortError';
      throw error;
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }, [copy, session.access]);

  const cargarPerfil = useCallback(async (signal) => {
    setCargando(true);
    setError('');
    try {
      setPerfil(await obtener('/api/preregistro/me/', signal));
    } catch (err) {
      if (err.name !== 'AbortError') setError(copy.messages.profileLoadError);
    } finally {
      if (!signal?.aborted) setCargando(false);
    }
  }, [copy, obtener]);

  const cargarSeguimiento = useCallback(async (signal) => {
    setSeguimientoCargando(true);
    try {
      setSeguimiento(await obtener('/api/preregistro/seguimiento/', signal));
    } catch (err) {
      // Ante un fallo temporal se conserva el último seguimiento recibido.
    } finally {
      if (!signal?.aborted) setSeguimientoCargando(false);
    }
  }, [obtener]);

  const cargarExamenes = useCallback(async (signal) => {
    try {
      const data = await obtener('/api/preregistro/examenes/', signal);
      setExamenes(data.examenes || []);
      setExamenesError('');
    } catch (err) {
      if (err.name !== 'AbortError') setExamenesError(copy.messages.examsLoadError);
    }
  }, [copy, obtener]);

  const cargarEntrevistas = useCallback(async (signal) => {
    try {
      const data = await obtener('/api/preregistro/entrevistas/', signal);
      setEntrevistas(data.entrevistas || []);
      setEntrevistasError('');
    } catch (err) {
      if (err.name !== 'AbortError') setEntrevistasError(copy.interviews.loadError);
    }
  }, [copy, obtener]);

  const marcarNotificacionesLeidas = useCallback(async () => {
    if (!seguimiento?.no_leidas) return;
    try {
      const res = await fetch('/api/preregistro/notificaciones/marcar-leidas/', {
        method: 'POST',
        headers: {Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'},
      });
      if (res.ok) {
        setSeguimiento(actual => actual && {...actual, no_leidas: 0, eventos: (actual.eventos || []).map(evento => ({...evento, leido: true}))});
      }
    } catch (e) {
      // El contador se corrige en el siguiente refresco.
    }
  }, [seguimiento?.no_leidas, session.access]);

  const toggleSection = (id) => {
    const abrir = !openSections[id];
    setOpenSections({[id]: true});
    if (abrir && id === 'notificaciones') marcarNotificacionesLeidas();
    if (abrir && id === 'examenes') cargarExamenes();
    if (abrir && id === 'entrevistas') cargarEntrevistas();
  };

  useEffect(() => {
    const controller = new AbortController();
    cargarPerfil(controller.signal);
    cargarSeguimiento(controller.signal);
    cargarExamenes(controller.signal);
    cargarEntrevistas(controller.signal);
    obtener('/api/preregistro/evaluaciones-colegio/', controller.signal)
      .then(data => setEvaluaciones(Array.isArray(data) ? data : []))
      .catch(() => {});
    return () => controller.abort();
  }, [cargarPerfil, cargarSeguimiento, cargarExamenes, cargarEntrevistas, obtener]);

  useEffect(() => {
    const expedienteId = perfil?.expediente_digital?.id;
    if (!expedienteId) {
      setExpedienteCentral(null);
      return;
    }
    const controller = new AbortController();
    setExpedienteCargando(true);
    obtener(`/api/expedientes/${expedienteId}/centralizado/`, controller.signal)
      .then(setExpedienteCentral)
      .catch(() => setExpedienteCentral(null))
      .finally(() => { if (!controller.signal.aborted) setExpedienteCargando(false); });
    return () => controller.abort();
  }, [perfil?.expediente_digital?.id, obtener]);

  useEffect(() => {
    let controller = null;
    const interval = setInterval(() => {
      if (document.hidden) return;
      if (controller) controller.abort();
      controller = new AbortController();
      cargarSeguimiento(controller.signal);
    }, INTERVALO_SEGUIMIENTO);
    return () => {
      clearInterval(interval);
      if (controller) controller.abort();
    };
  }, [cargarSeguimiento]);

  const etapa = etapaIndex(perfil?.proceso_estado);
  const estadoTerminal = ['rechazado', 'baja'].includes(perfil?.proceso_estado);
  const documentosSoloLectura = perfil && (perfil.rol !== 'aspirante' || ESTADOS_RESUELTOS.includes(perfil.proceso_estado));


  return (
    <section className="panel-section" aria-label={copy.panelTitle}>
      <div className="panel-hero">
        <div>
          <p className="panel-kicker">{copy.panelTitle}</p>
          <h1>{perfil?.nombre || (cargando ? copy.loading : copy.requestFallback)}</h1>
          {perfil && (
            <p className="panel-sub">
              {perfil.programa} — {perfil.unidad} <EstadoBadge estado={perfil.proceso_estado} labels={copy.stages}/>
            </p>
          )}
        </div>
      </div>

      {error && (
        <div className="api-error" role="alert">
          {error} <button type="button" className="link-btn" onClick={() => cargarPerfil(new AbortController().signal)}>{copy.retry}</button>
        </div>
      )}

      {cargando && !perfil && <div className="panel-card">{copy.loadingRequest}</div>}

      {perfil && <div className="aspirante-layout">
        <aside className="aspirante-sidebar" aria-label={copy.navAria}>
          <div className="aspirante-sidebar-header">
            <h2>{copy.sidebarTitle}</h2>
            <p>{copy.sidebarHint}</p>
          </div>
          <nav>
            <button
              type="button"
              className={`sidebar-item${openSections.notificaciones ? ' is-active' : ''}`}
              onClick={() => toggleSection('notificaciones')}
              aria-expanded={Boolean(openSections.notificaciones)}
            >
              <span>{copy.notifications}</span>
              <span className="notif-badge">{seguimiento?.no_leidas || 0}</span>
            </button>
            {MENU_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`sidebar-item${openSections[item.id] ? ' is-active' : ''}`}
                onClick={() => toggleSection(item.id)}
                aria-expanded={Boolean(openSections[item.id])}
              >
                <span>{copy.menu[item.id]}</span>
                <span>{openSections[item.id] ? '−' : '+'}</span>
              </button>
            ))}
          </nav>
          <button type="button" className="sidebar-logout" onClick={() => onLogout(copy.logout)}>{copy.logout}</button>
        </aside>

        <div className="aspirante-content">
          <SectionPanel id="inicio" label={copy.menu.inicio} open={openSections.inicio} onToggle={() => toggleSection('inicio')}>
            <div className="panel-grid">
              {perfil.proceso_estado === 'aceptado' && perfil.rol === 'aspirante' && (
                <div className="panel-card aspirant-enrollment-notice" role="status">
                  <span className="aspirant-enrollment-notice-icon" aria-hidden="true">✓</span>
                  <div><h3>{copy.overview.next}</h3><p>{copy.stageMessages.aceptado}</p></div>
                </div>
              )}
              <div className="panel-card panel-card--wide">
                <h3>{copy.overview.summary}</h3>
                <div className="panel-stepper">
                  {ETAPAS.map((item, index) => {
                    const done = !estadoTerminal && index < etapa;
                    const active = !estadoTerminal && index === etapa;
                    return (
                      <div key={item.id} className={`stepper-item${done ? ' stepper-item--done' : ''}${active ? ' stepper-item--active' : ''}`}>
                        <div className="stepper-dot">{item.icon}</div>
                        <span>{copy.stages[item.id]}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="summary-row">
                  <div className="summary-stat"><span className="summary-num">{estadoTerminal ? '—' : `${etapa + 1} / ${ETAPAS.length}`}</span><span className="summary-desc">{copy.overview.currentStage}</span></div>
                  <div className="summary-stat"><span className="summary-num">{perfil.modalidad || '—'}</span><span className="summary-desc">{copy.overview.currentModality}</span></div>
                  <div className="summary-stat"><span className="summary-num">{perfil.unidad || '—'}</span><span className="summary-desc">{copy.overview.currentUnit}</span></div>
                </div>
              </div>
              <div className="panel-card">
                <h3>{copy.overview.stage}</h3>
                <div className="etapa-desc"><div className="etapa-icon">{estadoTerminal ? '!' : ETAPAS[etapa].icon}</div><div><strong>{estadoTerminal ? (perfil.proceso_estado === 'baja' ? copy.overview.low : copy.overview.rejected) : copy.stages[perfil.proceso_estado]}</strong><p>{mensajeEtapa(perfil.proceso_estado, copy.stageMessages)}</p></div></div>
              </div>
              <div className="panel-card">
                <h3>{copy.overview.quick}</h3>
                <div className="quick-actions">
                  <button type="button" className="qa-btn" onClick={() => toggleSection('expediente')}>{copy.overview.fullRecord}</button>
                  <button type="button" className="qa-btn" onClick={() => toggleSection('proceso')}>{copy.overview.track}</button>
                </div>
              </div>
              <SolicitudApoyo perfil={perfil} session={session} onActualizado={() => cargarPerfil(new AbortController().signal)}/>
            </div>
          </SectionPanel>

          <SectionPanel id="perfil" label={copy.menu.perfil} open={openSections.perfil} onToggle={() => toggleSection('perfil')}>
            <PerfilAspirante perfil={perfil} session={session} onActualizado={(actualizado) => setPerfil((actual) => ({...actual, ...actualizado}))}/>
          </SectionPanel>

          <SectionPanel id="notificaciones" label={copy.notifications} open={openSections.notificaciones} onToggle={() => toggleSection('notificaciones')}>
            <div className="panel-card">
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <h3>{copy.overview.recentNotifications}</h3>
                <button type="button" className="qa-btn" onClick={() => cargarSeguimiento()}>{copy.overview.update}</button>
              </div>
              {seguimientoCargando && !seguimiento ? <p>{copy.messages.loadingNotifications}</p> : null}
              {!seguimientoCargando && (!seguimiento || !seguimiento.eventos || seguimiento.eventos.length === 0) ? (
                <p className="empty-state">{copy.messages.noNotifications}</p>
              ) : (
                <div className="notifs-list">
                  {(seguimiento?.eventos || []).map((evt) => (
                    <article key={evt.id} className={`notif-item${evt.leido ? '' : ' is-unread'}`}>
                      <div className="notif-head"><strong>{evt.origen}</strong><time>{fechaSeguimiento(evt.created_at, copy.locale)}</time></div>
                      <p>{evt.detalle}</p>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </SectionPanel>

          <SectionPanel id="expediente" label={copy.menu.expediente} open={openSections.expediente} onToggle={() => toggleSection('expediente')}>
            {expedienteCargando && <div className="panel-card">{copy.messages.integratingRecord}</div>}
            {expedienteCentral && <div className="panel-card panel-card--wide"><div className="alumno-section-title"><div><p className="panel-kicker">{copy.overview.centralRecord}</p><h3>{expedienteCentral.expediente.folio}</h3></div><EstadoBadge estado={expedienteCentral.expediente.estado} labels={copy.stages}/></div><div className="info-grid"><InfoItem label={copy.overview.documents} value={expedienteCentral.documentos.length}/><InfoItem label={copy.overview.enrollments} value={expedienteCentral.inscripciones.length}/><InfoItem label={copy.overview.requests} value={expedienteCentral.solicitudes_academicas.length}/><InfoItem label={copy.overview.signaturesCount} value={expedienteCentral.firmas.length}/><InfoItem label={copy.overview.thesisProjects} value={expedienteCentral.tesis.length}/><InfoItem label={copy.overview.movements} value={expedienteCentral.seguimiento.length}/></div>{expedienteCentral.tesis.length > 0 && <div className="request-list"><h4>{copy.overview.thesis}</h4>{expedienteCentral.tesis.map(proyecto => <article key={proyecto.id}><strong>{proyecto.titulo}</strong><p>{proyecto.estado_label}{proyecto.defensa ? ` · ${copy.overview.defense}: ${proyecto.defensa.estado_label}` : ''}</p></article>)}</div>}{expedienteCentral.firmas.length > 0 && <div className="request-list"><h4>{copy.overview.signatures}</h4>{expedienteCentral.firmas.map(firma => <article key={firma.id}><strong>{firma.rol_firmante}</strong><p>{firma.firmante_nombre}</p></article>)}</div>}</div>}
            <div className="panel-grid">
              <div className="panel-card"><h3>{copy.overview.personal}</h3><InfoItem label={copy.overview.name} value={perfil.nombre}/><InfoItem label={copy.overview.curp} value={perfil.curp}/><InfoItem label={copy.overview.email} value={perfil.correo}/><InfoItem label={copy.overview.phone} value={perfil.telefono}/><InfoItem label={copy.overview.birth} value={perfil.nacimiento}/></div>
              <div className="panel-card"><h3>{copy.overview.addresses}</h3><p className="exp-section-title">{copy.overview.current}</p><InfoItem label={copy.overview.state} value={perfil.estado_actual}/><InfoItem label={copy.overview.municipality} value={perfil.municipio_actual}/><InfoItem label={copy.overview.address} value={perfil.direccion_actual}/><p className="exp-section-title" style={{marginTop: 12}}>{copy.overview.permanent}</p><InfoItem label={copy.overview.state} value={perfil.estado_permanente}/><InfoItem label={copy.overview.municipality} value={perfil.municipio_permanente}/><InfoItem label={copy.overview.address} value={perfil.direccion_permanente}/></div>
              <div className="panel-card"><h3>{copy.overview.education}</h3><InfoItem label={copy.overview.degree} value={perfil.ultimo_grado}/><InfoItem label={copy.overview.institution} value={perfil.institucion}/><InfoItem label={copy.overview.average} value={perfil.promedio}/><InfoItem label={copy.overview.languages} value={perfil.idiomas}/><InfoItem label={copy.overview.publications} value={perfil.publicaciones}/><InfoItem label={copy.overview.experience} value={perfil.experiencia}/></div>
              <div className="panel-card"><h3>{copy.overview.affiliation}</h3><InfoItem label={copy.overview.currentUnit} value={perfil.unidad}/><InfoItem label={copy.overview.department} value={perfil.departamento}/><InfoItem label={copy.overview.section} value={perfil.seccion}/><InfoItem label={copy.overview.program} value={perfil.programa}/><InfoItem label={copy.overview.mode} value={perfil.modalidad}/><InfoItem label={copy.overview.advisor} value={perfil.tutor_propuesto}/></div>
            </div>
          </SectionPanel>

          <SectionPanel id="proceso" label={copy.menu.proceso} open={openSections.proceso} onToggle={() => toggleSection('proceso')}>
            <SeguimientoSolicitud seguimiento={seguimiento} evaluaciones={evaluaciones} cargando={seguimientoCargando} onActualizar={() => cargarSeguimiento()} />
          </SectionPanel>

          <SectionPanel id="documentos" label={copy.menu.documentos} open={openSections.documentos} onToggle={() => toggleSection('documentos')}>
            <DocumentosAspirante session={session} soloLectura={documentosSoloLectura} />
          </SectionPanel>

          <SectionPanel id="entrevistas" label={copy.menu.entrevistas} open={openSections.entrevistas} onToggle={() => toggleSection('entrevistas')}>
            <EntrevistasAspirante entrevistas={entrevistas} error={entrevistasError} />
          </SectionPanel>

          <SectionPanel id="examenes" label={copy.menu.examenes} open={openSections.examenes} onToggle={() => toggleSection('examenes')}>
            {examenesError && <div className="api-error" role="alert">{examenesError}</div>}
            <ExamenesEnLinea session={session} examenes={examenes} onChange={setExamenes} />
          </SectionPanel>
        </div>
      </div>}
    </section>
  );
}
