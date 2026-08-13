import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';

const FILTROS = [
  {id: 'todos', label: 'Todas'},
  {id: 'por-revisar', label: 'Por revisar'},
  {id: 'revision', label: 'En revisión'},
  {id: 'aceptado', label: 'Aceptadas'},
];

function etiquetaEstado(estado) {
  return estado === 'revision' ? 'En revisión' : estado ? estado.charAt(0).toUpperCase() + estado.slice(1) : 'Pendiente';
}

function formatearFecha(valor) {
  try {
    return new Intl.DateTimeFormat('es-MX', {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(valor));
  } catch (e) {
    return valor;
  }
}

function formatoDateTimeLocal(valor) {
  if (!valor) return '';
  const date = new Date(valor);
  if (Number.isNaN(date.getTime())) return '';
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date - offset).toISOString().slice(0, 16);
}

export default function PanelCoordinacion({session, onLogout}) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [filtro, setFiltro] = useState('por-revisar');
  const [seleccionado, setSeleccionado] = useState(null);
  const [detalle, setDetalle] = useState(null);
  const [detalleCargando, setDetalleCargando] = useState(false);
  const [editData, setEditData] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState('');
  const [materias, setMaterias] = useState(null);
  const [materiasCargando, setMateriasCargando] = useState(false);
  const fileInputRef = useRef(null);
  const [actualizando, setActualizando] = useState(false);
  const [activeSection, setActiveSection] = useState('bandeja');

  const cargarPanel = useCallback(async (signal) => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/coordinacion/panel/', {headers: {Authorization: `Bearer ${session.access}`}, signal});
      if (response.status === 401) return onLogout('Tu sesión ha caducado. Vuelve a iniciar sesión para continuar.');
      if (response.status === 403) throw new Error('Esta cuenta no tiene permisos de Coordinación Académica.');
      if (!response.ok) throw new Error('No fue posible cargar las solicitudes.');
      setDatos(await response.json());
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'No fue posible cargar las solicitudes.');
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [onLogout, session.access]);

  const cargarDetalle = useCallback(async (aspiranteId, signal) => {
    setDetalleCargando(true);
    setSaveError('');
    try {
      const response = await fetch(`/api/coordinacion/aspirantes/${aspiranteId}/`, {
        headers: {Authorization: `Bearer ${session.access}`},
        signal,
      });
      if (response.status === 401) return onLogout('Tu sesión ha caducado. Vuelve a iniciar sesión para continuar.');
      if (response.status === 403) throw new Error('No tienes permisos para ver este aspirante.');
      if (!response.ok) throw new Error('No fue posible cargar los datos del aspirante.');
      const data = await response.json();
      setDetalle(data);
      setEditData(data);
    } catch (err) {
      if (err.name !== 'AbortError') setSaveError(err.message || 'No se pudo cargar el detalle del aspirante.');
    } finally {
      if (!signal.aborted) setDetalleCargando(false);
    }
  }, [onLogout, session.access]);

  useEffect(() => {
    const controller = new AbortController();
    if (seleccionado) cargarDetalle(seleccionado.id, controller.signal);
    return () => controller.abort();
  }, [seleccionado, cargarDetalle]);

  useEffect(() => {
    const controller = new AbortController();
    cargarPanel(controller.signal);
    return () => controller.abort();
  }, [cargarPanel]);

  useEffect(() => {
    if (datos?.aspirantes?.length && !seleccionado) {
      setSeleccionado(datos.aspirantes[0]);
    }
  }, [datos, seleccionado]);

  const aspirantes = useMemo(() => (datos?.aspirantes || []).filter((aspirante) => {
    if (filtro === 'por-revisar') return ['pendiente', 'iniciado'].includes(aspirante.proceso_estado);
    return filtro === 'todos' || aspirante.proceso_estado === filtro;
  }), [datos, filtro]);

  const CAMPOS_EDITABLES = [
    'fecha_examen_admision', 'fecha_entrevista', 'fecha_inicio_curso_propedeutico',
    'curso_propedeutico_nota', 'curso_propedeutico_aprobado', 'apoyo_autorizado',
  ];

  function payloadEditable(data) {
    return CAMPOS_EDITABLES.reduce((payload, campo) => {
      if (data?.[campo] !== undefined) payload[campo] = data[campo];
      return payload;
    }, {});
  }

  async function handleGuardarCambios() {
    if (!detalle || !editData || guardando) return;
    setGuardando(true);
    setSaveError('');
    setSaveSuccess('');
    try {
      const response = await fetch(`/api/coordinacion/aspirantes/${detalle.id}/`, {
        method: 'PATCH',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify(payloadEditable(editData)),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'No se pudieron guardar los cambios.');
      }
      const actualizado = await response.json();
      setDetalle(actualizado);
      setEditData(actualizado);
      setSaveSuccess('Cambios guardados correctamente.');
      setDatos((actual) => ({...actual, aspirantes: actual.aspirantes.map((aspirante) => aspirante.id === actualizado.id ? actualizado : aspirante)}));
      setSeleccionado(actualizado);
    } catch (err) {
      setSaveError(err.message || 'No se pudieron guardar los cambios.');
    } finally {
      setGuardando(false);
    }
  }

  function handleFieldChange(field, value) {
    setEditData((prev) => ({...prev, [field]: value}));
  }

  async function cambiarEstado(estado) {
    if (!seleccionado || actualizando) return;
    setActualizando(true);
    setError('');
    try {
      const response = await fetch(`/api/coordinacion/aspirantes/${seleccionado.id}/estado/`, {
        method: 'PATCH',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({proceso_estado: estado}),
      });
      if (!response.ok) throw new Error('No se pudo actualizar el estado de la solicitud.');
      const actualizado = await response.json();
      setDatos((actual) => ({...actual, aspirantes: actual.aspirantes.map((aspirante) => aspirante.id === actualizado.id ? actualizado : aspirante)}));
      setSeleccionado(actualizado);
      setDetalle(actualizado);
      setEditData(actualizado);
    } catch (err) {
      setError(err.message || 'No se pudo actualizar la solicitud.');
    } finally {
      setActualizando(false);
    }
  }

  // Helper to download blobs (PDF/CSV)
  async function downloadBlob(url, filename) {
    try {
      const resp = await fetch(url, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!resp.ok) throw new Error('No fue posible descargar el archivo.');
      const blob = await resp.blob();
      const urlBlob = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = urlBlob;
      a.download = filename || 'download';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(urlBlob);
    } catch (err) {
      setError(err.message || 'Error en la descarga.');
    }
  }

  async function handleDescargarCalificaciones() {
    if (!detalle) return setError('Selecciona un aspirante primero.');
    await downloadBlob(`/api/coordinacion/aspirantes/${detalle.id}/calificaciones/?format=pdf`, `${detalle.usuario || detalle.curp || detalle.id}-calificaciones.pdf`);
  }

  async function handleDescargarAdscripcion() {
    if (!detalle) return setError('Selecciona un aspirante primero.');
    await downloadBlob(`/api/coordinacion/aspirantes/${detalle.id}/adscripcion/download/`, `${detalle.usuario || detalle.curp || detalle.id}-adscripcion.pdf`);
  }

  async function handleDarBaja() {
    if (!seleccionado) return setError('Selecciona un aspirante primero.');
    if (!confirm('Confirmar baja del alumno seleccionado? Esta acción no es reversible.')) return;
    try {
      const resp = await fetch(`/api/coordinacion/aspirantes/${seleccionado.id}/dar_baja/`, {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`}});
      if (!resp.ok) throw new Error('No se pudo dar de baja al alumno.');
      setSaveSuccess('Alumno dado de baja correctamente.');
      // refresh panel
      cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || 'Error al dar de baja.');
    }
  }

  async function handleGenerarCarga() {
    try {
      const resp = await fetch('/api/coordinacion/cargas/generar/', {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`}});
      if (!resp.ok) throw new Error('No se pudo generar la carga académica.');
      const data = await resp.json();
      setSaveSuccess(data.detail || 'Carga generada correctamente.');
    } catch (err) {
      setError(err.message || 'Error al generar carga académica.');
    }
  }

  function handleCargarCursosClick() {
    fileInputRef.current?.click();
  }

  async function handleCargarCursosFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
      const resp = await fetch('/api/coordinacion/cursos/upload/', {method: 'POST', headers: {Authorization: `Bearer ${session.access}`}, body: form});
      if (!resp.ok) throw new Error('No se pudo cargar el archivo de cursos.');
      const data = await resp.json();
      setSaveSuccess(data.detail || 'Cursos cargados correctamente.');
      cargarMateriasDisponibles();
    } catch (err) {
      setError(err.message || 'Error al cargar cursos.');
    } finally {
      event.target.value = '';
    }
  }

  async function cargarMateriasDisponibles() {
    setMateriasCargando(true);
    try {
      const resp = await fetch('/api/coordinacion/materias/', {headers: {Authorization: `Bearer ${session.access}`}});
      if (!resp.ok) throw new Error('No fue posible cargar las materias.');
      setMaterias(await resp.json());
    } catch (err) {
      setError(err.message || 'Error al cargar materias.');
    } finally {
      setMateriasCargando(false);
    }
  }

  return (
    <section className="panel-section" aria-label="Panel de Coordinación Académica">
      <div className="panel-hero">
        <div>
          <p className="panel-kicker">Coordinación Académica</p>
          <h1>Gestión de solicitudes</h1>
          <p className="panel-sub">Revisa expedientes y da seguimiento a los procesos de admisión.</p>
        </div>
        <button type="button" className="btn-outline-danger" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
      </div>
      {error && <div className="api-error" role="alert">{error}</div>}
      {cargando && !datos && <div className="panel-card">Cargando solicitudes...</div>}
      {datos && (
        <div className="coordinacion-layout">
          <aside className="coordinacion-sidebar" aria-label="Menú de coordinacion">
            <div className="aspirante-sidebar-header">
              <h2>Secciones</h2>
              <p className="panel-sub">Abre cada apartado para ver su contenido.</p>
            </div>
            <nav className="coordinacion-sidebar-nav">
              <button type="button" className={`sidebar-item${activeSection === 'resumen' ? ' is-active' : ''}`} onClick={() => setActiveSection('resumen')} aria-current={activeSection === 'resumen' ? 'page' : undefined}>Resumen</button>
              <button type="button" className={`sidebar-item${activeSection === 'bandeja' ? ' is-active' : ''}`} onClick={() => setActiveSection('bandeja')} aria-current={activeSection === 'bandeja' ? 'page' : undefined}>Bandeja</button>
              <button type="button" className={`sidebar-item${activeSection === 'detalle' ? ' is-active' : ''}`} onClick={() => setActiveSection('detalle')} aria-current={activeSection === 'detalle' ? 'page' : undefined}>Detalle</button>
            </nav>
            <button type="button" className="sidebar-logout" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
          </aside>

          <div className="coordinacion-content">
            <div className="coordinacion-main-panel">
              <div className="coordinacion-main-body">
                {activeSection === 'resumen' && (
                  <div className="aspirante-section-card is-open">
                    <div className="section-panel">
                      <div className="coord-stats"><div className="admin-stat"><span>{datos.resumen.total}</span><small>Solicitudes totales</small></div><div className="admin-stat"><span>{datos.resumen.por_revisar}</span><small>Por revisar</small></div><div className="admin-stat"><span>{datos.resumen.revision}</span><small>En revisión</small></div><div className="admin-stat"><span>{datos.resumen.aceptado}</span><small>Aceptadas</small></div></div>
                    </div>
                  </div>
                )}

            {activeSection === 'bandeja' && (
              <div className="aspirante-section-card is-open">
                <div className="section-panel">
                  <div className="panel-card coord-queue"><div className="coord-queue-head"><h3>Bandeja de solicitudes</h3><div className="coord-filters">{FILTROS.map((item) => <button type="button" key={item.id} className={filtro === item.id ? 'is-active' : ''} onClick={() => setFiltro(item.id)}>{item.label}</button>)}</div></div><div className="coord-list">{aspirantes.length === 0 ? <p className="empty-state">No hay solicitudes en esta bandeja.</p> : aspirantes.map((aspirante) => <button type="button" key={aspirante.id} className={`coord-item${seleccionado?.id === aspirante.id ? ' is-selected' : ''}`} onClick={() => { setSeleccionado(aspirante); setActiveSection('detalle'); }}><span><strong>{aspirante.nombre}</strong><small>{aspirante.programa} · {aspirante.unidad}</small></span><span className={`estado-badge estado-${aspirante.proceso_estado}`}>{etiquetaEstado(aspirante.proceso_estado)}</span></button>)}</div></div>
                </div>
              </div>
            )}

            {activeSection === 'detalle' && (
              <div className="aspirante-section-card is-open">
                <div className="section-panel">
                  <div className="panel-card coord-detail">
                  {seleccionado ? (
                    <div>
                      <div className="coord-detail-head">
                        <div>
                          <p className="panel-kicker">Expediente</p>
                          <h3>{seleccionado.nombre}</h3>
                          <p>{seleccionado.correo} · {seleccionado.telefono}</p>
                        </div>
                        <span className={`estado-badge estado-${seleccionado.proceso_estado}`}>{etiquetaEstado(seleccionado.proceso_estado)}</span>
                      </div>

                      {detalleCargando && !detalle ? (
                        <div className="panel-card">Cargando detalles...</div>
                      ) : detalle ? (
                        <div>
                          {saveError && <div className="api-error" role="alert">{saveError}</div>}
                          {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}

                          <div className="coord-action-row">
                                <button type="button" className="qa-btn" onClick={() => cambiarEstado('revision')} disabled={actualizando}>Marcar en revisión</button>
                                <button type="button" className="qa-btn" onClick={() => cambiarEstado('aceptado')} disabled={actualizando}>Aceptar</button>
                                <button type="button" className="qa-btn" onClick={() => cambiarEstado('rechazado')} disabled={actualizando}>Rechazar</button>
                            {/* Conversion actions: only available once the aspirante is an alumno */}
                            {detalle?.rol !== 'alumno' && detalle?.proceso_estado === 'aceptado' && (
                              <button type="button" className="qa-btn" onClick={async () => {
                                try {
                                  const resp = await fetch(`/api/coordinacion/aspirantes/${detalle.id}/convertir/`, {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`}});
                                  if (!resp.ok) throw new Error('No se pudo convertir al alumno.');
                                  const data = await resp.json();
                                  setDetalle((d) => ({...d, rol: data.rol}));
                                  setSaveSuccess('Aspirante convertido a alumno. Ahora puedes usar las funciones académicas.');
                                  cargarPanel(new AbortController().signal);
                                } catch (err) {
                                  setError(err.message || 'Error al convertir aspirante.');
                                }
                              }}>Convertir a alumno</button>
                            )}

                            {detalle?.rol === 'alumno' && (
                              <div>
                                <button type="button" className="qa-btn" onClick={handleDescargarCalificaciones}>Descargar historial de calificaciones</button>
                                <button type="button" className="qa-btn" onClick={handleDescargarAdscripcion}>Descargar formato de adscripción</button>
                                <button type="button" className="qa-btn" onClick={handleDarBaja}>Dar de baja</button>
                                <button type="button" className="qa-btn" onClick={handleGenerarCarga}>Generar carga académica</button>
                                <button type="button" className="qa-btn" onClick={handleCargarCursosClick}>Cargar cursos (CSV)</button>
                                <input ref={fileInputRef} type="file" accept=".csv" style={{display:'none'}} onChange={handleCargarCursosFile} />
                              </div>
                            )}
                          </div>

                          <div className="coord-data">
                            <div><span>CURP</span><strong>{detalle.curp}</strong></div>
                            <div><span>Usuario</span><strong>{detalle.usuario}</strong></div>
                            <div><span>Programa</span><strong>{detalle.programa || '—'}</strong></div>
                            <div><span>Unidad</span><strong>{detalle.unidad || '—'}</strong></div>
                            <div><span>Departamento</span><strong>{detalle.departamento || '—'}</strong></div>
                            <div><span>Sección</span><strong>{detalle.seccion || '—'}</strong></div>
                            <div><span>Modalidad</span><strong>{detalle.modalidad || '—'}</strong></div>
                            <div><span>Último grado</span><strong>{detalle.ultimo_grado || '—'}</strong></div>
                            <div><span>Institución</span><strong>{detalle.institucion || '—'}</strong></div>
                          </div>

                          <div className="coord-form">
                            <div className="coord-form-heading">
                              <div>
                                <h4>Fechas y curso propedéutico</h4>
                                <p>Registra las fechas clave y el estado de aprobación del curso para mantener al aspirante informado.</p>
                              </div>
                              <div className="coord-form-actions">
                                <button type="button" className="qa-btn coord-btn" onClick={handleGuardarCambios} disabled={guardando}>
                                  {guardando ? 'Guardando...' : 'Guardar cambios'}
                                </button>
                              </div>
                            </div>
                            {saveError && <div className="api-error" role="alert">{saveError}</div>}
                            {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}
                            <div className="coord-form-grid">
                              <label className="coord-field">
                                <span>Fecha examen de admisión</span>
                                <input
                                  type="datetime-local"
                                  value={formatoDateTimeLocal(editData?.fecha_examen_admision)}
                                  onChange={(event) => handleFieldChange('fecha_examen_admision', event.target.value)}
                                />
                              </label>
                              <label className="coord-field">
                                <span>Fecha entrevista</span>
                                <input
                                  type="datetime-local"
                                  value={formatoDateTimeLocal(editData?.fecha_entrevista)}
                                  onChange={(event) => handleFieldChange('fecha_entrevista', event.target.value)}
                                />
                              </label>
                              <label className="coord-field">
                                <span>Inicio curso propedéutico</span>
                                <input
                                  type="datetime-local"
                                  value={formatoDateTimeLocal(editData?.fecha_inicio_curso_propedeutico)}
                                  onChange={(event) => handleFieldChange('fecha_inicio_curso_propedeutico', event.target.value)}
                                />
                              </label>
                              <label className="coord-field">
                                <span>Nota del curso propedéutico</span>
                                <input
                                  type="number"
                                  min="0"
                                  max="10"
                                  step="0.01"
                                  value={editData?.curso_propedeutico_nota ?? ''}
                                  onChange={(event) => handleFieldChange('curso_propedeutico_nota', event.target.value)}
                                />
                              </label>
                            </div>
                            <div className="coord-checkbox-row">
                              <label className="coord-checkbox">
                                <input
                                  type="checkbox"
                                  checked={editData?.curso_propedeutico_aprobado || false}
                                  onChange={(event) => handleFieldChange('curso_propedeutico_aprobado', event.target.checked)}
                                />
                                Curso propedéutico aprobado
                              </label>
                              <label className="coord-checkbox">
                                <input
                                  type="checkbox"
                                  checked={editData?.apoyo_autorizado || false}
                                  onChange={(event) => handleFieldChange('apoyo_autorizado', event.target.checked)}
                                />
                                Apoyo autorizado
                              </label>
                            </div>
                          </div>

                          <div className="coord-documents">
                            <h4>Documentos recibidos</h4>
                            {detalle.documentos?.length ? (
                              <ul>
                                {detalle.documentos.map((documento) => (
                                  <li key={documento.id}>
                                    <span>{documento.tipo_label}</span>
                                    <a href={documento.archivo} target="_blank" rel="noreferrer">Ver archivo</a>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="empty-state">Aún no se han cargado documentos.</p>
                            )}
                          </div>

                          <div className="coord-materias">
                            <h4>Materias disponibles</h4>
                            <div>
                              <button type="button" className="qa-btn" onClick={cargarMateriasDisponibles} disabled={materiasCargando}>{materiasCargando ? 'Cargando...' : 'Refrescar materias'}</button>
                            </div>
                            {materias ? (
                              <table className="admin-table" style={{marginTop:12}}>
                                <thead><tr><th>Clave</th><th>Materia</th><th>Profesor</th><th>Horario</th></tr></thead>
                                <tbody>
                                  {materias.map((m) => (
                                    <tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.profesor || '—'}</td><td>{m.horario || '—'}</td></tr>
                                  ))}
                                </tbody>
                              </table>
                            ) : <p className="empty-state">No hay materias cargadas.</p>}
                          </div>

                          <div className="coord-timeline">
                            <h4>Historial de seguimiento</h4>
                            {detalle.seguimientos?.length ? (
                              detalle.seguimientos.map((evento) => (
                                <article className="coord-event" key={evento.id}>
                                  <div className="coord-event-head">
                                    <strong>{etiquetaEstado(evento.estado)}</strong>
                                    <time>{formatearFecha(evento.created_at)}</time>
                                  </div>
                                  <p>{evento.detalle}</p>
                                  <small>{evento.origen}</small>
                                </article>
                              ))
                            ) : (
                              <p className="empty-state">No hay movimientos de seguimiento registrados.</p>
                            )}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : (
                    <div className="coord-empty"><h3>Selecciona una solicitud</h3><p>Elige un aspirante de la bandeja para consultar su expediente y actualizar su estado.</p></div>
                  )}
                  </div>
                </div>
              </div>
            )}
            </div>
          </div>
        </div>
      </div>
      )}
    </section>
  );
}
