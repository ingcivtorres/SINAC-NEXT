import React, {useCallback, useEffect, useState} from 'react';
import DocumentosAspirante from './DocumentosAspirante';
import SeguimientoSolicitud from './SeguimientoSolicitud';
import SolicitudApoyo from './SolicitudApoyo';
import PerfilAspirante from './PerfilAspirante';
import './PanelAspirante.css';
import './PanelAspiranteSingle.css';
import {useLanguage} from '../translations';

const ETAPAS = [
  {id: 'pendiente', label: 'Pre-registro recibido', icon: '1'},
  {id: 'iniciado', label: 'Proceso iniciado', icon: '2'},
  {id: 'revision', label: 'En revisión', icon: '3'},
  {id: 'aceptado', label: 'Aceptado', icon: '4'},
];

const MENU_ITEMS = [
  {id: 'perfil', label: 'Mi perfil'},
  {id: 'inicio', label: 'Inicio'},
  {id: 'expediente', label: 'Expediente'},
  {id: 'proceso', label: 'Seguimiento LIDA'},
  {id: 'documentos', label: 'Documentos'},
  {id: 'examenes', label: 'Exámenes en línea'},
];

function etapaIndex(estado) {
  const index = ETAPAS.findIndex((etapa) => etapa.id === estado);
  return index === -1 ? 0 : index;
}

function EstadoBadge({estado}) {
  return <span className={`estado-badge estado-${estado || 'pendiente'}`}>{estado || 'pendiente'}</span>;
}

function fechaSeguimiento(valor) {
  try {
    return new Intl.DateTimeFormat('es-MX', {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(valor));
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

function mensajeEtapa(estado) {
  const mensajes = {
    pendiente: 'Tu pre-registro fue recibido. La Coordinación Académica lo revisará pronto.',
    iniciado: 'El flujo LIDA fue iniciado. Pronto estará en revisión.',
    revision: 'Tu expediente está siendo revisado por la Coordinación Académica.',
    aceptado: '¡Felicidades! Tu solicitud fue aceptada.',
  };
  return mensajes[estado] || mensajes.pendiente;
}

export default function PanelAspirante({session, onLogout}) {
  const {language} = useLanguage();
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
  const menuLabels = language === 'en' ? {perfil:'My profile', inicio:'Home', expediente:'Academic record', proceso:'LIDA tracking', documentos:'Documents', examenes:'Online exams'} : {};

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
        onLogout('Tu sesión ha caducado. Vuelve a iniciar sesión para continuar.');
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      setPerfil(await response.json());
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError('No se pudo cargar tu perfil. Verifica la conexión e inténtalo de nuevo.');
      }
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [onLogout, session.access]);

  const cargarSeguimiento = useCallback(async (signal) => {
    setSeguimientoCargando(true);
    try {
      const response = await fetch('/api/preregistro/seguimiento/', {headers: {Authorization: `Bearer ${session.access}`}, signal});
      if (response.status === 401) {
        onLogout('Tu sesión ha caducado. Vuelve a iniciar sesión para continuar.');
        return;
      }
      if (!response.ok) throw new Error('No se pudo cargar las notificaciones.');
      setSeguimiento(await response.json());
    } catch (err) {
      if (err.name !== 'AbortError') setSeguimiento(null);
    } finally {
      if (!signal.aborted) setSeguimientoCargando(false);
    }
  }, [onLogout, session.access]);

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
    const interval = setInterval(() => {
      cargarSeguimiento(new AbortController().signal);
    }, 7000);
    return () => clearInterval(interval);
  }, [cargarSeguimiento]);

  const etapa = etapaIndex(perfil?.proceso_estado);

  const manejarConversion = async (confirmado) => {
    if (!confirmado) {
      setConfirmarConversion(false);
      setMensajeConversion('Si deseas solicitar apoyo más adelante, puedes hacerlo una vez más.');
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
        throw new Error(data.detail || 'No se pudo completar la transición.');
      }
      setConfirmarConversion(false);
      setMensajeConversion('Tu cuenta quedó activa como alumno. Inicia sesión nuevamente para entrar al panel de alumno con tus mismas credenciales.');
      onLogout('Tu cuenta fue convertida a alumno. Inicia sesión nuevamente para continuar.');
    } catch (err) {
      setConfirmarConversion(false);
      setError(err.message || 'No se pudo completar la transición.');
    } finally {
      setConvirtiendo(false);
    }
  };

  const mostrarConversion = perfil?.proceso_estado === 'aceptado' && perfil?.rol !== 'alumno';

  return (
    <section className="panel-section" aria-label="Panel del Aspirante">
      <div className="panel-hero">
        <div>
          <p className="panel-kicker">Panel del Aspirante</p>
          <h1>{perfil?.nombre || (cargando ? 'Cargando...' : 'Tu solicitud')}</h1>
          {perfil && (
            <p className="panel-sub">
              {perfil.programa} — {perfil.unidad} <EstadoBadge estado={perfil.proceso_estado}/>
            </p>
          )}
        </div>
      </div>

      {error && (
        <div className="api-error" role="alert">
          {error} <button type="button" className="link-btn" onClick={() => cargarPerfil(new AbortController().signal)}>Reintentar</button>
        </div>
      )}

      {cargando && !perfil && <div className="panel-card">Cargando información de tu solicitud...</div>}

      {confirmarConversion && (
        <div className="conversion-modal-backdrop" role="dialog" aria-modal="true" aria-label="Confirmación de transición">
          <div className="conversion-modal">
            <div className="conversion-modal-icon">🎓</div>
            <h3>Continuar como alumno</h3>
            <p>¿Deseas convertir tu cuenta a alumno ahora y entrar al panel correspondiente con tus mismas credenciales?</p>
            <div className="conversion-modal-actions">
              <button type="button" className="conversion-modal-btn secondary" onClick={() => manejarConversion(false)} disabled={convirtiendo}>No, recordar después</button>
              <button type="button" className="conversion-modal-btn primary" onClick={() => manejarConversion(true)} disabled={convirtiendo}>{convirtiendo ? 'Procesando...' : 'Sí, continuar'}</button>
            </div>
          </div>
        </div>
      )}

      {perfil && <div className="aspirante-layout">
        <aside className="aspirante-sidebar" aria-label="Menú de navegación del panel">
          <div className="aspirante-sidebar-header">
            <h2>Secciones</h2>
            <p>Abre cada apartado para ver su contenido.</p>
          </div>
          <nav>
            <button
              type="button"
              className={`sidebar-item${openSections.notificaciones ? ' is-active' : ''}`}
              onClick={() => toggleSection('notificaciones')}
              aria-expanded={openSections.notificaciones}
            >
              <span>Notificaciones</span>
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
                <span>{menuLabels[item.id] || item.label}</span>
                <span>{openSections[item.id] ? '−' : '+'}</span>
              </button>
            ))}
          </nav>
          <button type="button" className="sidebar-logout" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
        </aside>

        <div className="aspirante-content">
          <SectionPanel id="inicio" label="Inicio" open={openSections.inicio} onToggle={() => toggleSection('inicio')}>
            <div className="panel-grid">
              <div className="panel-card panel-card--wide">
                <h3>Resumen de tu solicitud</h3>
                <div className="panel-stepper">
                  {ETAPAS.map((item, index) => {
                    const done = index < etapa;
                    const active = index === etapa;
                    return (
                      <div key={item.id} className={`stepper-item${done ? ' stepper-item--done' : ''}${active ? ' stepper-item--active' : ''}`}>
                        <div className="stepper-dot">{item.icon}</div>
                        <span>{item.label}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="summary-row">
                  <div className="summary-stat"><span className="summary-num">{etapa + 1} / {ETAPAS.length}</span><span className="summary-desc">Etapa actual</span></div>
                  <div className="summary-stat"><span className="summary-num">{perfil.modalidad || '—'}</span><span className="summary-desc">Modalidad</span></div>
                  <div className="summary-stat"><span className="summary-num">{perfil.unidad || '—'}</span><span className="summary-desc">Unidad</span></div>
                </div>
              </div>
              <div className="panel-card">
                <h3>Etapa actual</h3>
                <div className="etapa-desc"><div className="etapa-icon">{ETAPAS[etapa].icon}</div><div><strong>{ETAPAS[etapa].label}</strong><p>{mensajeEtapa(perfil.proceso_estado)}</p></div></div>
              </div>
              <div className="panel-card">
                <h3>Acceso rápido</h3>
                <div className="quick-actions">
                  <button type="button" className="qa-btn" onClick={() => toggleSection('expediente')}>Ver expediente completo</button>
                  <button type="button" className="qa-btn" onClick={() => toggleSection('proceso')}>Ver proceso LIDA</button>
                  {mostrarConversion && (
                    <button type="button" className="qa-btn" onClick={() => setConfirmarConversion(true)}>Continuar como alumno</button>
                  )}
                </div>
              </div>
              {mensajeConversion && (
                <div className="panel-card" style={{gridColumn: '1 / -1'}}>
                  <h3>Próximo paso</h3>
                  <p className="support-locked">{mensajeConversion}</p>
                </div>
              )}
              <SolicitudApoyo perfil={perfil} session={session} onActualizado={() => cargarPerfil(new AbortController().signal)}/>
            </div>
          </SectionPanel>

          <SectionPanel id="perfil" label="Mi perfil" open={openSections.perfil} onToggle={() => toggleSection('perfil')}>
            <PerfilAspirante perfil={perfil} session={session} onActualizado={(actualizado) => setPerfil((actual) => ({...actual, ...actualizado}))}/>
          </SectionPanel>

          <SectionPanel id="notificaciones" label="Notificaciones" open={openSections.notificaciones} onToggle={() => toggleSection('notificaciones')}>
            <div className="panel-card">
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <h3>Notificaciones recientes</h3>
                <button type="button" className="qa-btn" onClick={() => cargarSeguimiento(new AbortController().signal)}>Actualizar</button>
              </div>
              {seguimientoCargando && !seguimiento ? <p>Cargando notificaciones...</p> : null}
              {!seguimientoCargando && (!seguimiento || !seguimiento.eventos || seguimiento.eventos.length === 0) ? (
                <p className="empty-state">No hay notificaciones recientes.</p>
              ) : (
                <div className="notifs-list">
                  {(seguimiento?.eventos || []).map((evt) => (
                    <article key={evt.id} className="notif-item">
                      <div className="notif-head"><strong>{evt.origen}</strong><time>{fechaSeguimiento(evt.created_at)}</time></div>
                      <p>{evt.detalle}</p>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </SectionPanel>

          <SectionPanel id="expediente" label="Expediente" open={openSections.expediente} onToggle={() => toggleSection('expediente')}>
            <div className="panel-grid">
              <div className="panel-card"><h3>Datos personales</h3><InfoItem label="Nombre" value={perfil.nombre}/><InfoItem label="CURP" value={perfil.curp}/><InfoItem label="Correo" value={perfil.correo}/><InfoItem label="Teléfono" value={perfil.telefono}/><InfoItem label="Nacimiento" value={perfil.nacimiento}/></div>
              <div className="panel-card"><h3>Domicilios</h3><p className="exp-section-title">Actual</p><InfoItem label="Estado" value={perfil.estado_actual}/><InfoItem label="Municipio" value={perfil.municipio_actual}/><InfoItem label="Dirección" value={perfil.direccion_actual}/><p className="exp-section-title" style={{marginTop: 12}}>Permanente</p><InfoItem label="Estado" value={perfil.estado_permanente}/><InfoItem label="Municipio" value={perfil.municipio_permanente}/><InfoItem label="Dirección" value={perfil.direccion_permanente}/></div>
              <div className="panel-card"><h3>Escolaridad</h3><InfoItem label="Último grado" value={perfil.ultimo_grado}/><InfoItem label="Institución" value={perfil.institucion}/><InfoItem label="Promedio" value={perfil.promedio}/><InfoItem label="Idiomas" value={perfil.idiomas}/><InfoItem label="Publicaciones" value={perfil.publicaciones}/><InfoItem label="Experiencia" value={perfil.experiencia}/></div>
              <div className="panel-card"><h3>Adscripción</h3><InfoItem label="Unidad" value={perfil.unidad}/><InfoItem label="Departamento" value={perfil.departamento}/><InfoItem label="Sección" value={perfil.seccion}/><InfoItem label="Programa" value={perfil.programa}/><InfoItem label="Modalidad" value={perfil.modalidad}/><InfoItem label="Tutor" value={perfil.tutor_propuesto}/></div>
            </div>
          </SectionPanel>

          <SectionPanel id="proceso" label="Seguimiento LIDA" open={openSections.proceso} onToggle={() => toggleSection('proceso')}>
            <SeguimientoSolicitud session={session} />
          </SectionPanel>

          <SectionPanel id="documentos" label="Documentos" open={openSections.documentos} onToggle={() => toggleSection('documentos')}>
            <DocumentosAspirante session={session} />
          </SectionPanel>

          <SectionPanel id="examenes" label="Exámenes en línea" open={openSections.examenes} onToggle={() => toggleSection('examenes')}>
            <div className="panel-card"><h3>Exámenes de admisión y selección</h3>{examenes.length ? <div className="request-list">{examenes.map(examen => <article key={examen.id}><strong>{examen.titulo}</strong><p>{examen.tipo_label} · {examen.duracion_minutos} minutos</p><span>{examen.estado_label}</span></article>)}</div> : <p className="empty-state">Aún no tienes exámenes asignados.</p>}</div>
          </SectionPanel>
        </div>
      </div>}
    </section>
  );
}
