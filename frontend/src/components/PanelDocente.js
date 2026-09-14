import React, {useCallback, useEffect, useState} from 'react';

const MENU_ITEMS = [
  {id: 'overview', label: 'Resumen'},
  {id: 'cursos', label: 'Mis Cursos'},
  {id: 'carga', label: 'Mi carga académica'},
  {id: 'catalogo', label: 'Elegir materia'},
  {id: 'estudiantes', label: 'Estudiantes'},
  {id: 'calificaciones', label: 'Calificaciones'},
  {id: 'examenes', label: 'Exámenes'},
  {id: 'entrevistas', label: 'Entrevistas'},
  {id: 'solicitudes', label: 'Solicitudes'},
  {id: 'reportes', label: 'Reportes'},
];

function etiquetaEstado(estado) {
  const mapa = {
    'cursando': 'Cursando',
    'aprobada': 'Aprobada',
    'reprobada': 'Reprobada',
    'pendiente': 'Pendiente',
    'aceptado': 'Aceptado',
    'rechazado': 'Rechazado',
    'programado': 'Programado',
    'iniciado': 'Iniciado',
    'completado': 'Completado',
    'aprobado': 'Aprobado',
    'cancelado': 'Cancelado',
    'programada': 'Programada',
    'iniciada': 'Iniciada',
    'completada': 'Completada',
    'cancelada': 'Cancelada',
  };
  return mapa[estado] || estado;
}

export default function PanelDocente({session, onLogout}) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [activeSection, setActiveSection] = useState('overview');
  const [cursoSeleccionado, setCursoSeleccionado] = useState(null);
  const [showCalificacionForm, setShowCalificacionForm] = useState(false);
  const [calificacionForm, setCalificacionForm] = useState({inscripcion_id: '', calificacion: '', parcial: '', numero_parcial: '1'});
  const [catalogo, setCatalogo] = useState([]);
  const [horarios, setHorarios] = useState({});
  const [periodo, setPeriodo] = useState(null);
  async function leerJson(response, mensaje) { const tipo=response.headers.get('content-type')||''; if (!response.ok || !tipo.includes('application/json')) throw new Error(mensaje); return response.json(); }
  const [cargas, setCargas] = useState([]);
  const [periodoCarga, setPeriodoCarga] = useState('');

  async function cargarCargas() {
    const r = await fetch('/api/cargas-academicas/', {headers: {Authorization: `Bearer ${session.access}`} });
    if (r.ok) setCargas(await r.json());
  }
  useEffect(() => { if (activeSection === 'carga') cargarCargas(); }, [activeSection]);
  async function enviarCarga() {
    const r = await fetch('/api/cargas-academicas/', {method:'POST', headers:{'Authorization':`Bearer ${session.access}`,'Content-Type':'application/json'}, body:JSON.stringify({periodo: periodoCarga})});
    const body = await r.json().catch(() => ({}));
    if (!r.ok) return setError(body.detail || 'No se pudo enviar la carga.');
    setPeriodoCarga(''); setError(''); cargarCargas();
  }

  const cargarPanel = useCallback(async (signal) => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/docente/panel/', {
        headers: {Authorization: `Bearer ${session.access}`},
        signal,
      });
      if (response.status === 401) {
        onLogout('Tu sesión ha caducado. Vuelve a iniciar sesión.');
        return;
      }
      if (response.status === 403) {
        throw new Error('No tienes permisos de docente para acceder a este panel.');
      }
      if (!response.ok) {
        let detail = '';
        try { const body = await response.json(); detail = body.error || body.detail || ''; } catch (ignore) { /* respuesta no JSON */ }
        throw new Error(detail || `No se pudo cargar el panel del docente (HTTP ${response.status}).`);
      }
      setDatos(await leerJson(response, 'No se pudo cargar el panel del docente.'));
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'No se pudo cargar el panel.');
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [onLogout, session.access]);

  useEffect(() => {
    const controller = new AbortController();
    cargarPanel(controller.signal);
    return () => controller.abort();
  }, [cargarPanel]);

  useEffect(() => {
    if (activeSection !== 'catalogo') return;
    fetch('/api/docente/catalogo-materias/', {headers: {Authorization: `Bearer ${session.access}`}})
      .then(response => response.ok ? response.json() : Promise.reject(new Error('No se pudo cargar el catálogo.')))
      .then(setCatalogo).catch(err => setError(err.message));
  }, [activeSection, session.access]);
  useEffect(() => { fetch('/api/periodos-inscripcion/', {headers:{Authorization:`Bearer ${session.access}`}}).then(r=>r.ok && (r.headers.get('content-type')||'').includes('application/json') ? r.json() : null).then(setPeriodo).catch(()=>setPeriodo(null)); }, [session.access]);

  async function seleccionarMateria(materia) {
    const horario = (horarios[materia.id] || '').trim();
    if (!horario) { setError('Escribe el horario antes de seleccionar la materia.'); return; }
    try {
      const response = await fetch(`/api/docente/catalogo-materias/${materia.id}/`, {method: 'PATCH', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({horario})});
      if (response.status === 401) { onLogout('Tu sesión ha caducado.'); return; }
      if (!response.ok) { const body = await response.json().catch(() => ({})); setError(body.detail || 'No se pudo asignar la materia.'); return; }
      setError(''); setCatalogo(items => items.map(item => item.id === materia.id ? {...item, profesor: datos?.docente?.nombre || 'Docente', horario} : item));
    } catch { setError('No se pudo conectar con el servidor.'); return; }
    cargarPanel(new AbortController().signal);
  }

  const handleCalificacionChange = (event) => {
    const {name, value} = event.target;
    setCalificacionForm((prev) => ({...prev, [name]: value}));
  };

  const handleCalificacionSubmit = async (event) => {
    event.preventDefault();
    if (!calificacionForm.inscripcion_id || !calificacionForm.calificacion) {
      setError('Completa todos los campos.');
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

      if (!response.ok) {
        const errData = (response.headers.get('content-type') || '').includes('application/json') ? await response.json().catch(() => ({})) : {};
        setError(errData.error || 'No se pudo registrar la calificación.');
        return;
      }

      setShowCalificacionForm(false);
      setCalificacionForm({inscripcion_id: '', calificacion: '', parcial: '', numero_parcial: '1'});
      setError('');
      cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || 'Error al registrar calificación.');
    }
  };

  function exportarCalificaciones() {
    if (!datos?.inscripciones?.length) {
      setError('No hay estudiantes o calificaciones para exportar.');
      return;
    }
    const encabezados = ['Estudiante', 'Usuario', 'Curso', 'Programa', 'Parcial 1', 'Parcial 2', 'Parcial 3', 'Final', 'Estado'];
    const escapar = valor => `"${String(valor ?? '').replace(/"/g, '""')}"`;
    const filas = datos.inscripciones.map(item => [
      item.aspirante?.nombre,
      item.aspirante?.usuario,
      item.materia_clave,
      item.aspirante?.programa,
      item.parcial_1,
      item.parcial_2,
      item.parcial_3,
      item.calificacion,
      etiquetaEstado(item.estado),
    ]);
    const contenido = [encabezados, ...filas].map(fila => fila.map(escapar).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([`\ufeff${contenido}`], {type: 'text/csv;charset=utf-8'}));
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = 'calificaciones_docente.csv';
    enlace.click();
    URL.revokeObjectURL(url);
    setError('');
  }

  return (
    <section className="admin-dashboard docente-dashboard" aria-label="Panel del docente">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
          <div className="admin-brand-mark">D</div>
          <div>
            <p className="panel-kicker">Sistema</p>
            <h2>Docente</h2>
          </div>
        </div>

        <nav className="admin-menu" aria-label="Menú docente">
          {MENU_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`admin-menu-item ${activeSection === item.id ? 'is-active' : ''}`}
              onClick={() => setActiveSection(item.id)}
            >
              <span>{item.label}</span>
              <small>
                {item.id === 'cursos' && (datos?.resumen?.total_materias || 0)}
                {item.id === 'estudiantes' && (datos?.resumen?.total_inscripciones || 0)}
                {item.id === 'calificaciones' && (datos?.resumen?.total_inscripciones || 0)}
                {item.id === 'examenes' && (datos?.resumen?.examenes_total || 0)}
                {item.id === 'solicitudes' && (datos?.resumen?.solicitudes_pendientes || 0)}
                {item.id === 'reportes' && '3'}
              </small>
            </button>
          ))}
        </nav>

        <div className="admin-side-card">
          <p>Desempeño</p>
          <strong>92.5%</strong>
          <span>Calificaciones registradas</span>
        </div>

        <button type="button" className="admin-logout" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
      </aside>

      <main className="admin-main-panel">
        <header className="admin-topbar">
          <div>
            <p className="panel-kicker">Docencia</p>
            <h1>Panel de docente</h1>
          </div>
          <div className="admin-top-actions">
            <button type="button" className="btn-secondary" onClick={exportarCalificaciones}>Exportar</button>
            <button type="button" className="btn-primary" disabled={!datos?.inscripciones?.length} onClick={() => setShowCalificacionForm(true)}>+ Registrar calificación</button>
          </div>
        </header>

        {periodo && <div className={`periodo-banner ${periodo.activo ? 'is-open' : ''}`}><strong>Inscripciones {periodo.activo ? 'abiertas' : 'cerradas'}: {periodo.nombre}</strong><span>{periodo.apertura ? new Date(periodo.apertura).toLocaleString('es-MX') : 'Fecha pendiente'} — {periodo.cierre ? new Date(periodo.cierre).toLocaleString('es-MX') : 'Fecha pendiente'}</span></div>}

        {error && <div className="api-error" role="alert">{error}</div>}
        {cargando && !datos && <div className="panel-card">Cargando panel del docente...</div>}

        {activeSection !== 'overview' && (!datos || cargando) && (
          <div className="panel-card">Cargando datos...</div>
        )}

        {activeSection === 'overview' && datos && (
          <>
            <div className="admin-stat-grid">
              <div className="admin-stat-card accent">
                <span>Mis cursos</span>
                <strong>{datos.resumen.total_materias}</strong>
                <small>Materias asignadas</small>
              </div>
              <div className="admin-stat-card">
                <span>Estudiantes</span>
                <strong>{datos.resumen.total_inscripciones}</strong>
                <small>Total inscrito</small>
              </div>
              <div className="admin-stat-card">
                <span>Aprobados</span>
                <strong>{datos.resumen.inscripciones_aprobadas}</strong>
                <small>Últimas sesiones</small>
              </div>
              <div className="admin-stat-card">
                <span>Exámenes</span>
                <strong>{datos.resumen.examenes_total}</strong>
                <small>Total en línea</small>
              </div>
              <div className="admin-stat-card">
                <span>Entrevistas</span>
                <strong>{datos.resumen.entrevistas_total || 0}</strong>
                <small>Total programadas</small>
              </div>
              <div className="admin-stat-card">
                <span>Solicitudes</span>
                <strong>{datos.resumen.solicitudes_pendientes}</strong>
                <small>Pendientes de revisar</small>
              </div>
            </div>

            <div className="admin-grid-layout">
              <div className="admin-card admin-card-wide">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">Cursos</p>
                    <h3>Mis materias este semestre</h3>
                  </div>
                </div>
                {datos.materias.length ? (
                  <div className="materias-grid">
                    {datos.materias.map((materia) => (
                      <div key={materia.id} className="materia-card" onClick={() => {setCursoSeleccionado(materia); setActiveSection('cursos');}}>
                        <h4>{materia.clave}</h4>
                        <p>{materia.nombre}</p>
                        <small>Horario: {materia.horario || 'N/A'}</small>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="empty-state">No hay materias asignadas actualmente.</p>
                )}
              </div>

              <div className="admin-card">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">Actividad</p>
                    <h3>Últimas solicitudes</h3>
                  </div>
                </div>
                <ul className="activity-list">
                  {datos.solicitudes.slice(0, 3).map((solicitud) => (
                    <li key={solicitud.id}>
                      <strong>{solicitud.get_tipo_display || solicitud.tipo}</strong>
                      <span>{etiquetaEstado(solicitud.estado)}</span>
                      <button type="button" className="icon-btn">Ver</button>
                    </li>
                  ))}
                  {datos.solicitudes.length === 0 && <li><strong>Sin solicitudes</strong><span>Todas resueltas</span><button type="button" className="icon-btn">OK</button></li>}
                </ul>
              </div>
            </div>
          </>
        )}

        {activeSection === 'carga' && (
          <div className="admin-card"><div className="admin-card-head"><div><p className="panel-kicker">Flujo de aprobación</p><h3>Mi carga académica</h3></div><button type="button" className="btn-secondary" onClick={cargarCargas}>Actualizar</button></div><p>Envía tu propuesta de carga a Coordinación Académica para revisión.</p><div className="coord-action-row"><input className="coord-search" placeholder="Periodo escolar (ej. 2026-1)" value={periodoCarga} onChange={e=>setPeriodoCarga(e.target.value)} /><button type="button" className="btn-primary" disabled={!periodoCarga.trim()} onClick={enviarCarga}>Enviar a revisión</button></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Periodo</th><th>Estado</th></tr></thead><tbody>{cargas.length ? cargas.map(c=><tr key={c.id}><td>{c.periodo || 'Sin periodo'}</td><td><span className="estado-badge">{c.estado.replace('_',' ')}</span></td></tr>) : <tr><td colSpan="2">Aún no has enviado cargas académicas.</td></tr>}</tbody></table></div></div>
        )}

        {activeSection === 'cursos' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">Cursos</p>
                <h3>{cursoSeleccionado ? cursoSeleccionado.nombre : 'Mis materias'}</h3>
              </div>
            </div>

            {cursoSeleccionado ? (
              <>
                <div className="curso-detalles">
                  <div><strong>Clave:</strong> {cursoSeleccionado.clave}</div>
                  <div><strong>Horario:</strong> {cursoSeleccionado.horario || 'N/A'}</div>
                  <button type="button" className="btn-secondary" onClick={() => setCursoSeleccionado(null)}>← Volver</button>
                </div>
                <h4 style={{marginTop: '20px'}}>Estudiantes inscritos</h4>
                <div className="admin-table-wrap">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Nombre</th>
                        <th>Usuario</th>
                        <th>Programa</th>
                        <th>Estado</th>
                          <th>Parcial 1</th><th>Parcial 2</th><th>Parcial 3</th><th>Final</th>
                      </tr>
                    </thead>
                    <tbody>
                      {datos.inscripciones.filter((i) => i.materia === cursoSeleccionado.id).map((inscripcion) => (
                        <tr key={inscripcion.id}>
                          <td><strong>{inscripcion.aspirante.nombre || 'N/A'}</strong></td>
                          <td>{inscripcion.aspirante.usuario || 'N/A'}</td>
                          <td>{inscripcion.aspirante.programa || 'N/A'}</td>
                          <td><span className={`estado-badge estado-${inscripcion.estado}`}>{etiquetaEstado(inscripcion.estado)}</span></td>
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
                    <small>Horario: {materia.horario || 'N/A'}</small>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeSection === 'catalogo' && datos && (
          <div className="admin-card"><div className="admin-card-head"><div><p className="panel-kicker">Oferta académica</p><h3>Elige la materia que impartirás</h3></div></div><p className="panel-sub">Coordinación Académica carga el catálogo. Selecciona una materia disponible y registra el horario propuesto.</p><div className="materias-grid">{catalogo.map(materia => { const propia = materia.profesor && materia.profesor.toLowerCase() === datos.docente.nombre.toLowerCase(); const ocupada = Boolean(materia.profesor) && !propia; return <div key={materia.id} className={`materia-card ${propia ? 'is-selected' : ''}`}><span className="materia-card-clave">{materia.clave}</span><strong className="materia-card-nombre">{materia.nombre}</strong><small>Profesor: {materia.profesor || 'Disponible'}</small><input className="calificacion-form-input" disabled={ocupada} placeholder="Ej. lunes y miércoles 08:00-10:00" value={horarios[materia.id] ?? materia.horario ?? ''} onChange={event => setHorarios(previous => ({...previous, [materia.id]: event.target.value}))}/><button type="button" className="btn-primary" disabled={ocupada} onClick={() => seleccionarMateria(materia)}>{ocupada ? 'Asignada a otro docente' : propia ? 'Actualizar horario' : 'Seleccionar materia'}</button></div>; })}</div>{!catalogo.length && <p className="empty-state">Coordinación aún no ha cargado materias.</p>}</div>
        )}

        {activeSection === 'estudiantes' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">Gestión</p>
                <h3>Mis estudiantes</h3>
              </div>
            </div>

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Usuario</th>
                    <th>Curso</th>
                    <th>Programa</th>
                    <th>Estado</th>
                    <th>Parcial 1</th><th>Parcial 2</th><th>Parcial 3</th><th>Final</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.inscripciones.map((inscripcion) => (
                    <tr key={inscripcion.id}>
                      <td><strong>{inscripcion.aspirante.nombre}</strong></td>
                      <td>{inscripcion.aspirante.usuario}</td>
                        <td>{inscripcion.materia_clave}</td>
                      <td>{inscripcion.aspirante.programa}</td>
                      <td><span className={`estado-badge estado-${inscripcion.estado}`}>{etiquetaEstado(inscripcion.estado)}</span></td>
                      <td>{inscripcion.parcial_1 ?? '-'}</td>
                      <td>{inscripcion.parcial_2 ?? '-'}</td>
                      <td>{inscripcion.parcial_3 ?? '-'}</td>
                      <td><strong>{inscripcion.calificacion ?? '-'}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSection === 'calificaciones' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">Actas</p>
                <h3>Registro de calificaciones</h3>
              </div>
              <button type="button" className="btn-primary" disabled={!datos?.inscripciones?.length} onClick={() => setShowCalificacionForm(true)}>+ Nueva calificación</button>
            </div>

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Estudiante</th>
                    <th>Curso</th>
                    <th>Parcial 1</th>
                    <th>Parcial 2</th>
                    <th>Parcial 3</th>
                    <th>Final</th>
                    <th>Estado</th>
                    <th>Fecha de registro</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.inscripciones.filter((i) => i.calificacion !== null || i.parcial_1 !== null || i.parcial_2 !== null || i.parcial_3 !== null).map((inscripcion) => (
                    <tr key={inscripcion.id}>
                      <td><strong>{inscripcion.aspirante.nombre}</strong></td>
                      <td>{inscripcion.materia_clave}</td>
                      <td>{inscripcion.parcial_1 ?? '-'}</td><td>{inscripcion.parcial_2 ?? '-'}</td><td>{inscripcion.parcial_3 ?? '-'}</td><td><strong>{inscripcion.calificacion ?? '-'}</strong></td>
                      <td><span className={`estado-badge estado-${inscripcion.estado}`}>{etiquetaEstado(inscripcion.estado)}</span></td>
                      <td>{new Intl.DateTimeFormat('es-MX', {dateStyle: 'medium'}).format(new Date(inscripcion.updated_at))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSection === 'examenes' && datos && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">Evaluación</p>
                <h3>Exámenes en línea</h3>
              </div>
            </div>

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Estudiante</th>
                    <th>Tipo de examen</th>
                    <th>Fecha programada</th>
                    <th>Estado</th>
                    <th>Calificación</th>
                    <th>Intentos</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.examenes && datos.examenes.length > 0 ? (
                    datos.examenes.map((examen) => (
                      <tr key={examen.id}>
                        <td><strong>{examen.aspirante?.nombre || 'N/A'}</strong></td>
                        <td>{examen.tipo_label || examen.tipo}</td>
                        <td>{examen.fecha_programada ? new Intl.DateTimeFormat('es-MX', {dateStyle: 'short', timeStyle: 'short'}).format(new Date(examen.fecha_programada)) : '-'}</td>
                        <td><span className={`estado-badge estado-${examen.estado}`}>{etiquetaEstado(examen.estado)}</span></td>
                        <td><strong>{examen.calificacion !== null ? examen.calificacion : '-'}</strong></td>
                        <td>{examen.intentos}/{examen.max_intentos}</td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan="6" style={{textAlign: 'center', padding: '20px'}}>No hay exámenes en línea</td></tr>
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
                <p className="panel-kicker">Comunicación</p>
                <h3>Entrevistas virtuales</h3>
              </div>
            </div>

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Estudiante</th>
                    <th>Propósito</th>
                    <th>Fecha programada</th>
                    <th>Estado</th>
                    <th>Jitsi</th>
                    <th>Notas</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.entrevistas && datos.entrevistas.length > 0 ? (
                    datos.entrevistas.map((entrevista) => (
                      <tr key={entrevista.id}>
                        <td><strong>{entrevista.aspirante?.nombre || 'N/A'}</strong></td>
                        <td>{entrevista.proposito_label || entrevista.proposito}</td>
                        <td>{entrevista.fecha_programada ? new Intl.DateTimeFormat('es-MX', {dateStyle: 'short', timeStyle: 'short'}).format(new Date(entrevista.fecha_programada)) : '-'}</td>
                        <td><span className={`estado-badge estado-${entrevista.estado}`}>{etiquetaEstado(entrevista.estado)}</span></td>
                        <td>{entrevista.jitsi_room_link ? <a href={entrevista.jitsi_room_link} target="_blank" rel="noopener noreferrer" style={{color: '#0066cc'}}>Abrir sala</a> : '-'}</td>
                        <td><small>{entrevista.notas_docente ? entrevista.notas_docente.substring(0, 50) + '...' : '-'}</small></td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan="6" style={{textAlign: 'center', padding: '20px'}}>No hay entrevistas virtuales</td></tr>
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
                <p className="panel-kicker">Gestión</p>
                <h3>Solicitudes académicas</h3>
              </div>
            </div>

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Estudiante</th>
                    <th>Tipo de solicitud</th>
                    <th>Comentario</th>
                    <th>Estado</th>
                    <th>Fecha</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.solicitudes.map((solicitud) => (
                    <tr key={solicitud.id}>
                      <td><strong>{solicitud.aspirante?.nombre || 'N/A'}</strong></td>
                      <td>{solicitud.tipo_label || solicitud.tipo}</td>
                      <td>{solicitud.comentario || '-'}</td>
                      <td><span className={`estado-badge estado-${solicitud.estado}`}>{etiquetaEstado(solicitud.estado)}</span></td>
                      <td>{new Intl.DateTimeFormat('es-MX', {dateStyle: 'medium'}).format(new Date(solicitud.created_at))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSection === 'reportes' && datos && (
          <div className="admin-grid-layout">
            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">Desempeño</p>
                  <h3>Estadísticas generales</h3>
                </div>
              </div>
              <div className="report-list">
                <div><span>Total de estudiantes</span><strong>{datos.resumen.total_inscripciones}</strong></div>
                <div><span>Aprobados</span><strong>{datos.resumen.inscripciones_aprobadas}</strong></div>
                <div><span>Reprobados</span><strong>{datos.resumen.inscripciones_reprobadas}</strong></div>
              </div>
            </div>

            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">Datos</p>
                  <h3>Información del docente</h3>
                </div>
              </div>
              <div style={{padding: '16px'}}>
                <div><strong>Nombre:</strong> {datos.docente.nombre}</div>
                <div><strong>Usuario:</strong> {datos.docente.usuario}</div>
                <div><strong>Programa:</strong> {datos.docente.programa}</div>
                <div><strong>Unidad:</strong> {datos.docente.unidad}</div>
              </div>
            </div>
          </div>
        )}
      </main>

      {showCalificacionForm && (
        <div className="modal-backdrop" onClick={() => setShowCalificacionForm(false)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="panel-kicker">Calificaciones</p>
                <h3>Registrar nueva calificación</h3>
              </div>
              <button type="button" className="close-btn" onClick={() => setShowCalificacionForm(false)}>×</button>
            </div>

            <form onSubmit={handleCalificacionSubmit} className="modal-form"><label>Tipo de evaluación<select name="numero_parcial" value={calificacionForm.numero_parcial} onChange={handleCalificacionChange}><option value="1">Parcial 1</option><option value="2">Parcial 2</option><option value="3">Parcial 3</option><option value="final">Calificación final</option></select></label>
              <div className="form-grid">
                <label>
                  Estudiante
                  <select name="inscripcion_id" value={calificacionForm.inscripcion_id} onChange={handleCalificacionChange}>
                    <option value="">Selecciona un estudiante</option>
                    {datos?.inscripciones?.map((inscripcion) => (
                      <option key={inscripcion.id} value={inscripcion.id}>
                        {inscripcion.aspirante.nombre} - {inscripcion.materia_clave}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Calificación (0-10)
                  <input 
                    type="number" 
                    name="calificacion" 
                    value={calificacionForm.calificacion} 
                    onChange={handleCalificacionChange} 
                    placeholder="8.5"
                    min="0"
                    max="10"
                    step="0.5"
                  />
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowCalificacionForm(false)}>Cancelar</button>
                <button type="submit" className="btn-primary">Registrar calificación</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
