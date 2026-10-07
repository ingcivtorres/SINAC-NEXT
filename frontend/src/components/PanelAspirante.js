import React, {useCallback, useEffect, useState} from 'react';
import DocumentosAspirante from './DocumentosAspirante';
import SeguimientoSolicitud from './SeguimientoSolicitud';
import SolicitudApoyo from './SolicitudApoyo';
import PerfilAspirante from './PerfilAspirante';
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
  {id: 'examenes'},
];

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
      <button type="button" className="section-trigger" onClick={onToggle} aria-expanded={open} aria-controls={`section-${id}`}>
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
  const [openSections, setOpenSections] = useState({inicio: true, perfil: false, expediente: false, proceso: false, documentos: false, notificaciones: false});
  const [seguimiento, setSeguimiento] = useState(null);
  const [seguimientoCargando, setSeguimientoCargando] = useState(true);
  const [confirmarConversion, setConfirmarConversion] = useState(false);
  const [convirtiendo, setConvirtiendo] = useState(false);
  const [mensajeConversion, setMensajeConversion] = useState('');
  const [examenes, setExamenes] = useState([]);
  const [expedienteCentral, setExpedienteCentral] = useState(null);
  const [expedienteCargando, setExpedienteCargando] = useState(false);

  const toggleSection = (id) => {
    setOpenSections((prev) => {
      const next = Object.keys(prev).reduce((sections, key) => ({...sections, [key]: key === id}), {});
      // if opening notifications, mark them as read
      if (id === 'notificaciones' && !prev.notificaciones) {
        marcarNotificacionesLeidas();
      }
      return next;
    });
  };

  async function marcarNotificacionesLeidas() {
    try {
      const res = await fetch('/api/preregistro/notificaciones/marcar-leidas/', {
        method: 'POST',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
      });
      if (res.ok) {
        cargarSeguimiento(new AbortController().signal);
      }
    } catch (e) {
      // ignore
    }
  }

  const cargarPerfil = useCallback(async (signal) => {
    setCargando(true);
    setError('');

    try {
      const response = await fetch('/api/preregistro/me/', {
        headers: {Authorization: `Bearer ${session.access}`},
        signal,
      });

      if (response.status === 401) {
        onLogout(copy.messages.sessionExpired);
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      setPerfil(await response.json());
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(copy.messages.profileLoadError);
      }
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [copy, onLogout, session.access]);

  const cargarSeguimiento = useCallback(async (signal) => {
    setSeguimientoCargando(true);
    try {
      const response = await fetch('/api/preregistro/seguimiento/', {headers: {Authorization: `Bearer ${session.access}`}, signal});
      if (response.status === 401) {
        onLogout(copy.messages.sessionExpired);
        return;
      }
      if (!response.ok) throw new Error(copy.messages.trackingError);
      setSeguimiento(await response.json());
    } catch (err) {
      if (err.name !== 'AbortError') setSeguimiento(null);
    } finally {
      if (!signal.aborted) setSeguimientoCargando(false);
    }
  }, [copy, onLogout, session.access]);

  useEffect(() => {
    const controller = new AbortController();
    const sctrl = new AbortController();
    cargarPerfil(controller.signal);
    cargarSeguimiento(sctrl.signal);
    return () => {
      controller.abort();
      sctrl.abort();
    };
  }, [cargarPerfil, cargarSeguimiento]);

  useEffect(() => {
    fetch('/api/preregistro/examenes/', {headers: {Authorization: `Bearer ${session.access}`}}).then(r => r.ok ? r.json() : {examenes: []}).then(data => setExamenes(data.examenes || []));
  }, [session.access]);

  useEffect(() => {
    const expedienteId = perfil?.expediente_digital?.id;
    if (!expedienteId) {
      setExpedienteCentral(null);
      return;
    }
    const controller = new AbortController();
    setExpedienteCargando(true);
    fetch(`/api/expedientes/${expedienteId}/centralizado/`, {headers: {Authorization: `Bearer ${session.access}`}, signal: controller.signal})
      .then(response => response.ok ? response.json() : null)
      .then(setExpedienteCentral)
      .catch(() => setExpedienteCentral(null))
      .finally(() => { if (!controller.signal.aborted) setExpedienteCargando(false); });
    return () => controller.abort();
  }, [perfil?.expediente_digital?.id, session.access]);

  useEffect(() => {
    const interval = setInterval(() => {
      cargarSeguimiento(new AbortController().signal);
    }, 7000);
    return () => clearInterval(interval);
  }, [cargarSeguimiento]);

  const etapa = etapaIndex(perfil?.proceso_estado);
  const estadoTerminal = ['rechazado', 'baja'].includes(perfil?.proceso_estado);

  const manejarConversion = async (confirmado) => {
    if (!confirmado) {
      setConfirmarConversion(false);
      setMensajeConversion(copy.messages.conversionDeclined);
      return;
    }

    try {
      setConvirtiendo(true);
      setError('');
      const response = await fetch('/api/preregistro/convertir-misma-cuenta/', {
        method: 'POST',
        headers: {Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'},
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || copy.messages.conversionError);
      }
      setConfirmarConversion(false);
      setMensajeConversion(copy.messages.conversionSuccess);
      onLogout(copy.messages.conversionLogout);
    } catch (err) {
      setConfirmarConversion(false);
      setError(err.message || copy.messages.conversionError);
    } finally {
      setConvirtiendo(false);
    }
  };

  const mostrarConversion = perfil?.proceso_estado === 'aceptado' && perfil?.rol !== 'alumno';

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

      {confirmarConversion && (
        <div className="conversion-modal-backdrop" role="dialog" aria-modal="true" aria-label={copy.conversion.aria}>
          <div className="conversion-modal">
            <div className="conversion-modal-icon">🎓</div>
            <h3>{copy.conversion.title}</h3>
            <p>{copy.conversion.question}</p>
            <div className="conversion-modal-actions">
              <button type="button" className="conversion-modal-btn secondary" onClick={() => manejarConversion(false)} disabled={convirtiendo}>{copy.conversion.cancel}</button>
              <button type="button" className="conversion-modal-btn primary" onClick={() => manejarConversion(true)} disabled={convirtiendo}>{convirtiendo ? copy.conversion.processing : copy.conversion.confirm}</button>
            </div>
          </div>
        </div>
      )}

      {perfil && <div className="aspirante-layout">
        <aside className="aspirante-sidebar" aria-label="Menú de navegación del panel">
          <div className="aspirante-sidebar-header">
            <h2>{copy.sidebarTitle}</h2>
            <p>{copy.sidebarHint}</p>
          </div>
          <nav>
            <button
              type="button"
              className={`sidebar-item${openSections.notificaciones ? ' is-active' : ''}`}
              onClick={() => toggleSection('notificaciones')}
              aria-expanded={openSections.notificaciones}
            >
              <span>{copy.notifications}</span>
              <span className="notif-badge">{seguimiento?.eventos?.filter(e => !e.leido).length || 0}</span>
            </button>
            {MENU_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`sidebar-item${openSections[item.id] ? ' is-active' : ''}`}
                onClick={() => toggleSection(item.id)}
                aria-expanded={openSections[item.id]}
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
                  {mostrarConversion && (
                    <button type="button" className="qa-btn" onClick={() => setConfirmarConversion(true)}>{copy.overview.continueStudent}</button>
                  )}
                </div>
              </div>
              {mensajeConversion && (
                <div className="panel-card" style={{gridColumn: '1 / -1'}}>
                  <h3>{copy.overview.next}</h3>
                  <p className="support-locked">{mensajeConversion}</p>
                </div>
              )}
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
                <button type="button" className="qa-btn" onClick={() => cargarSeguimiento(new AbortController().signal)}>{copy.overview.update}</button>
              </div>
              {seguimientoCargando && !seguimiento ? <p>{copy.messages.loadingNotifications}</p> : null}
              {!seguimientoCargando && (!seguimiento || !seguimiento.eventos || seguimiento.eventos.length === 0) ? (
                <p className="empty-state">{copy.messages.noNotifications}</p>
              ) : (
                <div className="notifs-list">
                  {(seguimiento?.eventos || []).map((evt) => (
                    <article key={evt.id} className="notif-item">
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
            <SeguimientoSolicitud seguimiento={seguimiento} cargando={seguimientoCargando} onActualizar={() => cargarSeguimiento(new AbortController().signal)} />
          </SectionPanel>

          <SectionPanel id="documentos" label={copy.menu.documentos} open={openSections.documentos} onToggle={() => toggleSection('documentos')}>
            <DocumentosAspirante session={session} />
          </SectionPanel>

          <SectionPanel id="examenes" label={copy.menu.examenes} open={openSections.examenes} onToggle={() => toggleSection('examenes')}>
            <div className="panel-card"><h3>{copy.overview.examsTitle}</h3>{examenes.length ? <div className="request-list">{examenes.map(examen => <article key={examen.id}><strong>{examen.titulo}</strong><p>{examen.tipo_label} · {examen.duracion_minutos} {copy.overview.minutes}</p><span>{examen.estado_label}</span></article>)}</div> : <p className="empty-state">{copy.messages.noExams}</p>}</div>
          </SectionPanel>
        </div>
      </div>}
    </section>
  );
}
