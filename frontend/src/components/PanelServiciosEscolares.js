import React, {useEffect, useMemo, useState} from 'react';

const MENU = [
  ['resumen', 'Resumen', '⌂'],
  ['alumnos', 'Alumnos', '◉'],
  ['inscripciones', 'Inscripciones', '▦'],
  ['historial', 'Historial académico', '▤'],
  ['calificaciones', 'Calificaciones', '✓'],
  ['constancias', 'Constancias y documentos', '▣'],
  ['egreso', 'Egreso', '◆'],
  ['reportes', 'Reportes', '◒'],
];

const estadoTexto = estado => ({
  activo: 'Activo', baja: 'Baja', inactivo: 'Inactivo', egresado: 'Egresado',
  cursando: 'Cursando', aprobada: 'Aprobada', reprobada: 'Reprobada',
}[estado] || estado || 'Pendiente');

function fecha(value, incluirHora = false) {
  if (!value) return '—';
  return new Intl.DateTimeFormat('es-MX', incluirHora ? {dateStyle: 'short', timeStyle: 'short'} : {dateStyle: 'medium'}).format(new Date(value));
}

function Estado({value}) {
  const clase = String(value || 'pendiente').toLowerCase().replace(/\s+/g, '-');
  return <span className={`servicios-status servicios-status--${clase}`}>{estadoTexto(value)}</span>;
}

export default function PanelServiciosEscolares({session, onLogout}) {
  const [active, setActive] = useState('resumen');
  const [datos, setDatos] = useState({alumnos: [], filtros: {programas: [], departamentos: []}, resumen: {}});
  const [reportes, setReportes] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [filters, setFilters] = useState({q: '', programa: '', departamento: '', estado: ''});
  const [formAlumno, setFormAlumno] = useState(null);
  const [movimiento, setMovimiento] = useState({estado: '', detalle: ''});
  const [altaAbierta, setAltaAbierta] = useState(false);
  const [alta, setAlta] = useState({nombre: '', usuario: '', correo: '', curp: '', password: '', telefono: '', matricula: '', programa: '', departamento: ''});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);
  const alumno = useMemo(() => datos.alumnos.find(item => item.id === selectedId) || null, [datos.alumnos, selectedId]);
  const inscripciones = useMemo(() => datos.alumnos.flatMap(item => (item.inscripciones || []).map(inscripcion => ({...inscripcion, alumno: item}))), [datos.alumnos]);

  async function cargar() {
    setLoading(true);
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
      const response = await fetch(`/api/servicios-escolares/panel/?${params.toString()}`, {headers});
      if (response.status === 401) { onLogout('Tu sesión ha caducado. Vuelve a iniciar sesión.'); return; }
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || 'No se pudo cargar Servicios Escolares.');
      setDatos(body);
    } catch (err) {
      setError(err.message || 'No se pudo cargar el panel.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { cargar(); }, [session.access, filters.q, filters.programa, filters.departamento, filters.estado]);

  useEffect(() => {
    if (active !== 'reportes') return;
    fetch('/api/servicios-escolares/reportes/', {headers})
      .then(response => response.ok ? response.json() : Promise.reject(new Error('No se pudieron cargar los reportes.')))
      .then(setReportes)
      .catch(err => setError(err.message));
  }, [active, session.access]);

  function seleccionar(item) {
    setSelectedId(item.id);
    setFormAlumno({
      nombre: item.nombre || '', matricula: item.matricula || '', correo: item.correo || '',
      telefono: item.telefono || '', programa: item.programa || '', departamento: item.departamento || '',
      unidad: item.unidad || '', modalidad: item.modalidad || 'Presencial', proceso_estado: item.proceso_estado || 'activo',
      is_active: Boolean(item.is_active),
    });
  }

  async function guardarAlumno(event) {
    event.preventDefault();
    if (!alumno || !formAlumno) return;
    setError('');
    const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/`, {method: 'PATCH', headers: {...headers, 'Content-Type': 'application/json'}, body: JSON.stringify(formAlumno)});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) return setError(body.detail || 'No se pudieron guardar los datos administrativos.');
    setMessage('Datos administrativos actualizados correctamente.');
    await cargar();
  }

  async function darDeAlta(event) {
    event.preventDefault();
    const response = await fetch('/api/servicios-escolares/panel/', {method: 'POST', headers: {...headers, 'Content-Type': 'application/json'}, body: JSON.stringify(alta)});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) return setError(body.detail || 'No se pudo dar de alta al alumno.');
    setAlta({nombre: '', usuario: '', correo: '', curp: '', password: '', telefono: '', matricula: '', programa: '', departamento: ''});
    setAltaAbierta(false);
    setMessage('Alumno dado de alta correctamente.');
    await cargar();
  }

  async function registrarMovimiento(event) {
    event.preventDefault();
    if (!alumno || !movimiento.detalle.trim()) return setError('Describe el movimiento administrativo.');
    const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/`, {method: 'POST', headers: {...headers, 'Content-Type': 'application/json'}, body: JSON.stringify(movimiento)});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) return setError(body.detail || body.detalle || 'No se pudo registrar el movimiento.');
    setMovimiento({estado: '', detalle: ''});
    setMessage('Movimiento administrativo registrado.');
    await cargar();
  }

  async function validarInscripcion(inscripcionId, validar = true) {
    if (!alumno) return;
    const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/validar-inscripcion/`, {method: 'POST', headers: {...headers, 'Content-Type': 'application/json'}, body: JSON.stringify({inscripcion_id: inscripcionId, validar})});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) return setError(body.detail || 'No se pudo validar la inscripción.');
    setMessage(validar ? 'Inscripción validada administrativamente.' : 'Inscripción marcada para revisión.');
    await cargar();
  }

  async function descargar(tipo, id = selectedId) {
    if (!id) return setError('Selecciona un alumno primero.');
    const response = await fetch(`/api/servicios-escolares/alumnos/${id}/documentos/${tipo}/`, {headers});
    if (!response.ok) return setError('No se pudo generar el documento.');
    const url = URL.createObjectURL(await response.blob());
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = `${tipo}_${id}.pdf`;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(url);
  }

  const label = MENU.find(item => item[0] === active)?.[1] || 'Resumen';
  const mostrarDetalle = Boolean(alumno);

  function tablaAlumnos() {
    return <div className="servicios-table-wrap"><table className="admin-table servicios-table"><thead><tr><th>Alumno</th><th>Matrícula</th><th>Programa</th><th>Departamento</th><th>Estatus</th><th>Acciones</th></tr></thead><tbody>{datos.alumnos.length ? datos.alumnos.map(item => <tr key={item.id}><td><strong>{item.nombre}</strong><small>{item.correo}</small></td><td>{item.matricula || 'Sin matrícula'}</td><td>{item.programa || '—'}</td><td>{item.departamento || '—'}</td><td><Estado value={item.is_active ? item.proceso_estado || 'activo' : 'inactivo'} /></td><td><button type="button" className="servicios-link" onClick={() => seleccionar(item)}>Consultar expediente</button></td></tr>) : <tr><td colSpan="6" className="servicios-empty">No hay alumnos que coincidan con los filtros.</td></tr>}</tbody></table></div>;
  }

  function detalleAlumno() {
    if (!mostrarDetalle) return <div className="servicios-empty-card"><span>◉</span><h3>Selecciona un alumno</h3><p>Consulta aquí su expediente, historial, estatus y movimientos administrativos.</p></div>;
    return <div className="servicios-detail-grid"><article className="servicios-card servicios-profile-card"><div className="servicios-profile-head"><div className="servicios-avatar">{alumno.nombre.charAt(0).toUpperCase()}</div><div><h3>{alumno.nombre}</h3><p>{alumno.matricula || 'Sin matrícula'} · {alumno.programa || 'Sin programa'}</p></div><Estado value={alumno.is_active ? alumno.proceso_estado || 'activo' : 'inactivo'} /></div><div className="servicios-info-grid"><div><span>Correo</span><strong>{alumno.correo || '—'}</strong></div><div><span>Teléfono</span><strong>{alumno.telefono || '—'}</strong></div><div><span>Departamento</span><strong>{alumno.departamento || '—'}</strong></div><div><span>Unidad</span><strong>{alumno.unidad || '—'}</strong></div><div><span>Promedio</span><strong>{alumno.promedio_academico ?? alumno.promedio ?? '—'}</strong></div><div><span>Expediente</span><strong>{alumno.expediente?.folio || 'Pendiente de generar'}</strong></div></div></article><form className="servicios-card servicios-form" onSubmit={guardarAlumno}><div className="servicios-card-heading"><div><span className="panel-kicker">GESTIÓN</span><h3>Datos administrativos</h3></div><button type="submit" className="btn-primary">Guardar</button></div><div className="servicios-form-grid"><label>Nombre<input value={formAlumno?.nombre || ''} onChange={e => setFormAlumno({...formAlumno, nombre: e.target.value})}/></label><label>Matrícula<input value={formAlumno?.matricula || ''} onChange={e => setFormAlumno({...formAlumno, matricula: e.target.value})}/></label><label>Programa<input value={formAlumno?.programa || ''} onChange={e => setFormAlumno({...formAlumno, programa: e.target.value})}/></label><label>Departamento<input value={formAlumno?.departamento || ''} onChange={e => setFormAlumno({...formAlumno, departamento: e.target.value})}/></label><label>Correo<input type="email" value={formAlumno?.correo || ''} onChange={e => setFormAlumno({...formAlumno, correo: e.target.value})}/></label><label>Teléfono<input value={formAlumno?.telefono || ''} onChange={e => setFormAlumno({...formAlumno, telefono: e.target.value})}/></label><label>Estatus<select value={formAlumno?.proceso_estado || 'activo'} onChange={e => setFormAlumno({...formAlumno, proceso_estado: e.target.value})}><option value="activo">Activo</option><option value="baja">Baja</option><option value="suspendido">Suspendido</option><option value="egresado">Egresado</option></select></label><label className="servicios-check"><input type="checkbox" checked={Boolean(formAlumno?.is_active)} onChange={e => setFormAlumno({...formAlumno, is_active: e.target.checked})}/> Cuenta activa</label></div></form><form className="servicios-card servicios-form" onSubmit={registrarMovimiento}><div className="servicios-card-heading"><div><span className="panel-kicker">AUDITORÍA</span><h3>Movimiento administrativo</h3></div></div><div className="servicios-form-grid servicios-form-grid--movement"><label>Tipo / situación<select value={movimiento.estado} onChange={e => setMovimiento({...movimiento, estado: e.target.value})}><option value="">Selecciona una situación</option><option value="activo">Activo / reingreso</option><option value="baja">Baja</option><option value="suspendido">Suspensión</option><option value="egresado">Egreso</option><option value="cambio_programa">Cambio de programa</option></select></label><label>Detalle<textarea value={movimiento.detalle} onChange={e => setMovimiento({...movimiento, detalle: e.target.value})} placeholder="Describe el movimiento y su fundamento administrativo." rows="3"/></label></div><button type="submit" className="btn-secondary">Registrar movimiento</button></form></div>;
  }

  function contenido() {
    if (active === 'resumen') return <><div className="servicios-kpi-grid"><article><span>Alumnos activos</span><strong>{datos.resumen.activos || 0}</strong><small>Con cuenta vigente</small></article><article><span>Total de alumnos</span><strong>{datos.resumen.total || 0}</strong><small>Registro oficial</small></article><article><span>Candidatos a egreso</span><strong>{datos.resumen.candidatos_egreso || 0}</strong><small>Revisión preliminar</small></article><article><span>Promedio institucional</span><strong>{datos.resumen.promedio_institucional ?? '—'}</strong><small>Promedio de ingreso</small></article></div><div className="servicios-card"><div className="servicios-card-heading"><div><span className="panel-kicker">CONSULTA RÁPIDA</span><h3>Alumnos registrados</h3></div><button className="btn-secondary" onClick={() => setActive('alumnos')}>Ver gestión de alumnos</button></div>{tablaAlumnos()}</div></>;
    if (active === 'alumnos') return <><div className="servicios-toolbar"><input value={filters.q} onChange={e => setFilters({...filters, q: e.target.value})} placeholder="Buscar por nombre, matrícula, usuario o correo"/><select value={filters.programa} onChange={e => setFilters({...filters, programa: e.target.value})}><option value="">Todos los programas</option>{datos.filtros.programas.map(value => <option key={value} value={value}>{value}</option>)}</select><select value={filters.departamento} onChange={e => setFilters({...filters, departamento: e.target.value})}><option value="">Todos los departamentos</option>{datos.filtros.departamentos.map(value => <option key={value} value={value}>{value}</option>)}</select><select value={filters.estado} onChange={e => setFilters({...filters, estado: e.target.value})}><option value="">Todos los estatus</option><option value="activo">Activos</option><option value="inactivo">Inactivos</option><option value="egresado">Egresados</option><option value="baja">Bajas</option></select><button type="button" className="btn-primary" onClick={() => setAltaAbierta(!altaAbierta)}>+ Dar de alta</button></div>{altaAbierta && <form className="servicios-card servicios-alta-card" onSubmit={darDeAlta}><div className="servicios-card-heading"><div><span className="panel-kicker">NUEVO ALUMNO</span><h3>Dar de alta</h3></div><button type="button" className="btn-secondary" onClick={() => setAltaAbierta(false)}>Cancelar</button></div><div className="servicios-form-grid"><label>Nombre completo<input required value={alta.nombre} onChange={e => setAlta({...alta, nombre: e.target.value})}/></label><label>Usuario institucional<input required value={alta.usuario} onChange={e => setAlta({...alta, usuario: e.target.value})}/></label><label>Correo institucional<input required type="email" value={alta.correo} onChange={e => setAlta({...alta, correo: e.target.value})}/></label><label>CURP<input required maxLength="18" value={alta.curp} onChange={e => setAlta({...alta, curp: e.target.value.toUpperCase()})}/></label><label>Contraseña inicial<input required type="password" minLength="8" value={alta.password} onChange={e => setAlta({...alta, password: e.target.value})}/></label><label>Teléfono<input value={alta.telefono} onChange={e => setAlta({...alta, telefono: e.target.value})}/></label><label>Matrícula<input value={alta.matricula} onChange={e => setAlta({...alta, matricula: e.target.value})}/></label><label>Programa<input value={alta.programa} onChange={e => setAlta({...alta, programa: e.target.value})}/></label><label>Departamento<input value={alta.departamento} onChange={e => setAlta({...alta, departamento: e.target.value})}/></label></div><button type="submit" className="btn-primary">Crear alumno</button></form>}<div className="servicios-card">{tablaAlumnos()}</div>{detalleAlumno()}</>;
    if (active === 'inscripciones') return <div className="servicios-card"><div className="servicios-card-heading"><div><span className="panel-kicker">INSCRIPCIONES Y REINSCRIPCIONES</span><h3>{alumno ? `Materias de ${alumno.nombre}` : 'Alumnos inscritos'}</h3></div>{alumno && <button className="btn-secondary" onClick={() => setSelectedId(null)}>Ver todos</button>}</div>{alumno ? <div className="servicios-table-wrap"><table className="admin-table"><thead><tr><th>Clave</th><th>Materia</th><th>Créditos</th><th>Profesor</th><th>Final</th><th>Estado</th><th>Validación</th></tr></thead><tbody>{alumno.inscripciones.length ? alumno.inscripciones.map(item => <tr key={item.id}><td>{item.materia_clave}</td><td>{item.materia_nombre}</td><td>{item.materia_creditos ?? '—'}</td><td>{item.materia_profesor || 'Por asignar'}</td><td>{item.calificacion ?? 'Pendiente'}</td><td><Estado value={item.estado}/></td><td><button className="servicios-link" onClick={() => validarInscripcion(item.id, true)}>Validar</button></td></tr>) : <tr><td colSpan="7" className="servicios-empty">No hay materias inscritas.</td></tr>}</tbody></table></div> : <><p className="servicios-muted">Selecciona un alumno desde la tabla para validar sus inscripciones y requisitos administrativos.</p>{tablaAlumnos()}</>}</div>;
    if (active === 'historial' || active === 'calificaciones') return <div className="servicios-card"><div className="servicios-card-heading"><div><span className="panel-kicker">{active === 'historial' ? 'TRAYECTORIA COMPLETA' : 'CONSULTA Y VALIDACIÓN'}</span><h3>{alumno ? `${active === 'historial' ? 'Historial académico' : 'Calificaciones'} · ${alumno.nombre}` : active === 'historial' ? 'Historial académico' : 'Calificaciones institucionales'}</h3></div>{alumno && <button className="btn-secondary" onClick={() => descargar(active === 'historial' ? 'historial' : 'calificaciones')}>Descargar PDF</button>}</div>{alumno ? <><div className="servicios-history-summary"><div><strong>{alumno.materias_aprobadas}</strong><span>Materias aprobadas</span></div><div><strong>{alumno.creditos_obtenidos}</strong><span>Créditos obtenidos</span></div><div><strong>{alumno.promedio_academico ?? '—'}</strong><span>Promedio final</span></div></div><div className="servicios-table-wrap"><table className="admin-table"><thead><tr><th>Clave</th><th>Materia</th><th>Créditos</th><th>Parcial 1</th><th>Parcial 2</th><th>Parcial 3</th><th>Final</th><th>Estado</th></tr></thead><tbody>{alumno.inscripciones.length ? alumno.inscripciones.map(item => <tr key={item.id}><td>{item.materia_clave}</td><td>{item.materia_nombre}</td><td>{item.materia_creditos ?? '—'}</td><td>{item.parcial_1 ?? '—'}</td><td>{item.parcial_2 ?? '—'}</td><td>{item.parcial_3 ?? '—'}</td><td>{item.calificacion ?? 'Pendiente'}</td><td><Estado value={item.estado}/></td></tr>) : <tr><td colSpan="8" className="servicios-empty">No hay calificaciones registradas.</td></tr>}</tbody></table></div><p className="servicios-note">Servicios Escolares consulta y valida registros; la captura o modificación académica corresponde al docente autorizado.</p></> : <><p className="servicios-muted">Selecciona un alumno desde la sección Alumnos para consultar su trayectoria.</p>{tablaAlumnos()}</>}</div>;
    if (active === 'constancias') return <div className="servicios-card"><div className="servicios-card-heading"><div><span className="panel-kicker">DOCUMENTOS OFICIALES</span><h3>Constancias y documentos</h3></div></div>{alumno ? <div className="servicios-doc-grid"><div className="servicios-doc-student"><div className="servicios-avatar">{alumno.nombre.charAt(0).toUpperCase()}</div><strong>{alumno.nombre}</strong><span>{alumno.matricula || 'Sin matrícula'}</span></div>{[['constancia', 'Constancia de estudios', 'Acredita que el alumno está registrado.'], ['calificaciones', 'Constancia de calificaciones', 'Resumen oficial de calificaciones.'], ['historial', 'Historial académico', 'Materias, parciales, finales y estados.'], ['inscripcion', 'Constancia de inscripción', 'Documento oficial de inscripción.'], ['egreso', 'Prevalidación de egreso', 'Revisión preliminar de requisitos.']].map(([tipo, titulo, descripcion]) => <article key={tipo}><h4>{titulo}</h4><p>{descripcion}</p><button className="btn-secondary" onClick={() => descargar(tipo)}>Generar PDF</button></article>)}</div> : <><p className="servicios-muted">Selecciona un alumno para generar sus documentos oficiales.</p>{tablaAlumnos()}</>}</div>;
    if (active === 'egreso') return <div className="servicios-card"><div className="servicios-card-heading"><div><span className="panel-kicker">CONTROL DE EGRESO</span><h3>{alumno ? `Prevalidación · ${alumno.nombre}` : 'Candidatos a egreso'}</h3></div></div>{alumno ? <div className="servicios-egreso"><div className="servicios-check-list"><div className={alumno.matricula ? 'ok' : 'pending'}><span>{alumno.matricula ? '✓' : '!'}</span>Matrícula asignada</div><div className={alumno.materias_aprobadas > 0 ? 'ok' : 'pending'}><span>{alumno.materias_aprobadas > 0 ? '✓' : '!'}</span>Materias aprobadas registradas</div><div className={alumno.requisitos_completos ? 'ok' : 'pending'}><span>{alumno.requisitos_completos ? '✓' : '!'}</span>Requisitos administrativos completos</div><div className={alumno.proceso_estado === 'egresado' ? 'ok' : 'pending'}><span>{alumno.proceso_estado === 'egresado' ? '✓' : '!'}</span>Situación marcada como egresado</div></div><button className="btn-secondary" onClick={() => descargar('egreso')}>Descargar prevalidación</button></div> : <><p className="servicios-muted">Selecciona un alumno para revisar requisitos de egreso.</p>{tablaAlumnos()}</>}</div>;
    return <div className="servicios-card"><div className="servicios-card-heading"><div><span className="panel-kicker">ESTADÍSTICAS INSTITUCIONALES</span><h3>Reportes</h3></div></div>{reportes ? <><div className="servicios-kpi-grid servicios-kpi-grid--reports"><article><span>Inscripciones</span><strong>{reportes.inscripciones}</strong></article><article><span>Aprobadas</span><strong>{reportes.aprobadas}</strong></article><article><span>Reprobadas</span><strong>{reportes.reprobadas}</strong></article><article><span>En curso</span><strong>{reportes.en_curso}</strong></article></div><div className="servicios-report-columns"><div><h4>Matrícula por programa</h4>{reportes.por_programa.map(item => <div className="servicios-bar-row" key={item.programa || 'sin-programa'}><span>{item.programa || 'Sin programa'}</span><strong>{item.total}</strong><i style={{width: `${Math.min(100, item.total * 12)}%`}} /></div>)}</div><div><h4>Matrícula por departamento</h4>{reportes.por_departamento.map(item => <div className="servicios-bar-row" key={item.departamento || 'sin-departamento'}><span>{item.departamento || 'Sin departamento'}</span><strong>{item.total}</strong><i style={{width: `${Math.min(100, item.total * 12)}%`}} /></div>)}</div></div></> : <p className="servicios-muted">Cargando reportes...</p>}</div>;
  }

  return <section className="servicios-shell" aria-label="Panel de Servicios Escolares"><aside className="servicios-sidebar"><div className="servicios-identity"><div className="servicios-mark">SE</div><div><small>ADMINISTRACIÓN ACADÉMICA</small><strong>Servicios Escolares</strong><span>Custodia y validación institucional</span></div></div><nav className="servicios-nav" aria-label="Módulos de Servicios Escolares">{MENU.map(([id, text, icon]) => <button type="button" key={id} className={active === id ? 'is-active' : ''} onClick={() => setActive(id)}><span className="servicios-nav-icon">{icon}</span><span>{text}</span>{id === 'alumnos' && <b>{datos.resumen.total || 0}</b>}{id === 'inscripciones' && <b>{inscripciones.length}</b>}</button>)}</nav><div className="servicios-sidebar-note"><strong>Rol administrativo</strong><span>Consulta, valida y genera documentos.</span></div><button type="button" className="servicios-logout" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button></aside><main className="servicios-main"><header className="servicios-heading"><div><span>SERVICIOS ESCOLARES</span><h1>{label}</h1><p>Gestión oficial de alumnos, inscripciones, historial y documentos.</p></div><button type="button" className="btn-secondary" onClick={cargar}>Actualizar</button></header>{message && <div className="api-success">{message}</div>}{error && <div className="api-error" role="alert">{error}<button type="button" className="link-btn" onClick={() => setError('')}>Cerrar</button></div>}{loading && !datos.alumnos.length ? <div className="servicios-empty-card">Cargando información institucional...</div> : contenido()}</main></section>;
}
