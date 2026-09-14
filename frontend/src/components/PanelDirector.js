import React, {useEffect, useState} from 'react';

const sections = [
  ['resumen', 'Resumen', '▦'],
  ['tesistas', 'Mis tesistas', '♙'],
  ['expedientes', 'Expedientes digitales', '▤'],
  ['avances', 'Avances de tesis', '◴'],
  ['evaluaciones', 'Evaluaciones', '✓'],
  ['perfil', 'Mi perfil', '●'],
];

const formatDate = (value) => value ? new Date(value).toLocaleDateString('es-MX') : 'Pendiente';

function estadoMateria(materia) {
  if (materia.calificacion == null) return 'Cursando';
  if (materia.calificacion < 7) return 'Reprobada';
  if (materia.calificacion < 8) return 'Aprobada con seguimiento';
  return 'Aprobada';
}

export default function PanelDirector({session, onLogout}) {
  const [active, setActive] = useState('resumen');
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [firmaMsg, setFirmaMsg] = useState('');

  const cargarPanel = async () => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/director/panel/', {headers: {Authorization: `Bearer ${session.access}`}});
      const body = await response.json().catch(() => ({}));
      if (response.status === 401) return onLogout('Tu sesión ha caducado.');
      if (!response.ok) throw new Error(body.detail || 'No se pudo cargar el panel del director.');
      setDatos(body);
    } catch (err) {
      setError(err.message || 'No se pudo cargar el panel del director.');
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => { cargarPanel(); }, [session.access]);

  const director = datos?.director || {};
  const tesistas = datos?.tesistas || [];
  const expedientes = datos?.expedientes || [];
  const resumen = datos?.resumen || {};
  const evaluaciones = tesistas.flatMap((tesista) => (tesista.materias || []).map((materia) => ({...materia, tesista: tesista.nombre})));

  async function firmar(expediente) {
    setFirmaMsg('');
    const response = await fetch(`/api/expedientes/${expediente.id}/firma/`, {
      method: 'POST',
      headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
      body: JSON.stringify({rol_firmante: 'director'}),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      setFirmaMsg(body.detail || 'No se pudo firmar el expediente.');
      return;
    }
    setFirmaMsg('Expediente firmado electrónicamente.');
    await cargarPanel();
  }

  const nombre = director.nombre || 'Director de Tesis';
  const titulo = sections.find((section) => section[0] === active)?.[1] || 'Panel';

  return (
    <section className="director-shell" aria-label="Panel de Director de Tesis">
      <aside className="director-sidebar">
        <div className="director-identity"><div className="director-avatar">{nombre.charAt(0)}</div><div><small>ACADÉMICO</small><strong>{nombre}</strong><span>Director de Tesis</span></div></div>
        <nav className="director-nav" aria-label="Secciones del director">{sections.map(([id, label, icon]) => <button key={id} type="button" className={active === id ? 'is-active' : ''} onClick={() => setActive(id)}><i>{icon}</i>{label}</button>)}</nav>
        <button type="button" className="director-logout" onClick={() => onLogout('Sesión cerrada correctamente.')}>Cerrar sesión</button>
      </aside>

      <main className="director-main">
        <header className="director-heading"><div><span>GESTIÓN ACADÉMICA</span><h1>{titulo}</h1><p>Consulta y da seguimiento a los estudiantes asignados.</p></div><div className="director-status"><b>●</b> Sesión activa</div></header>
        {error && <div className="api-error" role="alert">{error}</div>}
        {cargando && <div className="director-empty"><div>◌</div><h3>Cargando información</h3><p>Estamos consultando tus tesistas y expedientes.</p></div>}

        {!cargando && active === 'resumen' && <>
          <div className="director-welcome"><div><small>Panel de Director de Tesis</small><h2>Bienvenido, {nombre.split(' ')[0]}</h2><p>La información se limita a los tesistas asignados por Coordinación Académica.</p></div><div className="director-welcome-mark">DT</div></div>
          <div className="director-stats"><article><span>Tesistas asignados</span><strong>{resumen.tesistas_asignados || 0}</strong><small>Asignados a tu cuenta</small></article><article><span>Expedientes activos</span><strong>{resumen.expedientes_activos || 0}</strong><small>{resumen.expedientes_sin_firma || 0} pendientes de firma</small></article><article><span>Evaluaciones</span><strong>{resumen.evaluaciones || 0}</strong><small>Materias registradas</small></article><article><span>Avances por revisar</span><strong>{resumen.avances_por_revisar || 0}</strong><small>{datos?.avance_tesis_disponible ? 'Seguimientos pendientes' : 'Módulo pendiente de habilitar'}</small></article></div>
          {tesistas.length ? <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">SEGUIMIENTO</span><h2>Tesistas recientes</h2></div><button type="button" className="btn-secondary" onClick={() => setActive('tesistas')}>Ver todos</button></div><div className="director-mini-grid">{tesistas.slice(0, 3).map((tesista) => <article key={tesista.id}><strong>{tesista.nombre}</strong><span>{tesista.matricula || 'Sin matrícula'} · {tesista.programa || 'Sin programa'}</span><b>{tesista.materias_aprobadas}/{tesista.total_materias} materias aprobadas</b></article>)}</div></div> : <div className="director-empty"><div>◈</div><h3>Aún no tienes tesistas asignados</h3><p>Coordinación Académica debe registrar tu nombre como tutor/director en el expediente del alumno.</p></div>}
        </>}

        {!cargando && active === 'tesistas' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">ASIGNACIÓN ACADÉMICA</span><h2>Mis tesistas</h2></div><span className="director-count">{tesistas.length} registros</span></div>{tesistas.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>Alumno</th><th>Matrícula</th><th>Programa</th><th>Materias</th><th>Aprobadas</th><th>Promedio</th></tr></thead><tbody>{tesistas.map((tesista) => <tr key={tesista.id}><td><strong>{tesista.nombre}</strong><small>{tesista.correo}</small></td><td>{tesista.matricula || 'Pendiente'}</td><td>{tesista.programa || 'Sin programa'}</td><td>{tesista.total_materias}</td><td>{tesista.materias_aprobadas}</td><td>{tesista.promedio == null ? '—' : tesista.promedio.toFixed(2)}</td></tr>)}</tbody></table></div> : <div className="director-empty"><h3>No hay tesistas asignados</h3><p>La asignación se realiza desde Coordinación Académica.</p></div>}</div>}

        {!cargando && active === 'expedientes' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">EXPEDIENTE DIGITAL</span><h2>Expedientes de mis tesistas</h2></div><span className="director-count">{expedientes.length} expedientes</span></div>{firmaMsg && <p className="api-success">{firmaMsg}</p>}{expedientes.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>Alumno</th><th>Folio</th><th>Creación</th><th>Estado</th><th>Firma</th><th>Acción</th></tr></thead><tbody>{expedientes.map((expediente) => { const firmado = (expediente.firmas || []).some((firma) => firma.rol_firmante === 'director'); return <tr key={expediente.id}><td><strong>{expediente.aspirante_nombre}</strong><small>{expediente.matricula || expediente.usuario}</small></td><td>{expediente.folio}</td><td>{formatDate(expediente.fecha_creacion)}</td><td>{expediente.estado}</td><td>{firmado ? `Firmado ${formatDate((expediente.firmas || []).find((firma) => firma.rol_firmante === 'director')?.firmado_at)}` : 'Pendiente'}</td><td><button type="button" className="btn-primary" onClick={() => firmar(expediente)} disabled={firmado}>{firmado ? 'Firmado' : 'Firmar expediente'}</button></td></tr>; })}</tbody></table></div> : <div className="director-empty"><h3>No hay expedientes asignados</h3><p>Los expedientes se crean automáticamente cuando el aspirante es aceptado.</p></div>}</div>}

        {!cargando && active === 'avances' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">AVANCE ACADÉMICO</span><h2>Avance de mis tesistas</h2></div></div>{tesistas.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>Tesista</th><th>Materias</th><th>Aprobadas</th><th>Reprobadas</th><th>Créditos</th><th>Promedio</th></tr></thead><tbody>{tesistas.map((tesista) => <tr key={tesista.id}><td><strong>{tesista.nombre}</strong></td><td>{tesista.total_materias}</td><td><span className="director-status-badge success">{tesista.materias_aprobadas}</span></td><td><span className="director-status-badge danger">{tesista.materias_reprobadas}</span></td><td>{tesista.creditos_aprobados}</td><td>{tesista.promedio == null ? '—' : tesista.promedio.toFixed(2)}</td></tr>)}</tbody></table></div> : <div className="director-empty"><h3>Sin información de avance</h3><p>Cuando se asignen tesistas, su avance académico aparecerá aquí.</p></div>}<p className="director-note">{datos?.avance_tesis_mensaje}</p></div>}

        {!cargando && active === 'evaluaciones' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">EVALUACIONES</span><h2>Trayectoria académica</h2></div><span className="director-count">{evaluaciones.length} materias</span></div>{evaluaciones.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>Tesista</th><th>Materia</th><th>Parciales</th><th>Final</th><th>Estado</th></tr></thead><tbody>{evaluaciones.map((materia) => <tr key={`${materia.id}-${materia.tesista}`}><td>{materia.tesista}</td><td><strong>{materia.materia_clave}</strong><small>{materia.materia_nombre}</small></td><td>{[materia.parcial_1, materia.parcial_2, materia.parcial_3].map((value) => value ?? '—').join(' / ')}</td><td>{materia.calificacion ?? '—'}</td><td><span className={`director-status-badge ${materia.color || 'neutral'}`}>{estadoMateria(materia)}</span></td></tr>)}</tbody></table></div> : <div className="director-empty"><h3>No hay evaluaciones disponibles</h3><p>Las calificaciones aparecen cuando el alumno tiene materias inscritas.</p></div>}</div>}

        {!cargando && active === 'perfil' && <div className="director-card director-profile"><div className="director-card-head"><div><span className="panel-kicker">CUENTA</span><h2>Mi perfil académico</h2></div></div><div className="director-profile-grid"><div><span>Nombre</span><strong>{director.nombre || '—'}</strong></div><div><span>Usuario</span><strong>{director.usuario || '—'}</strong></div><div><span>Correo</span><strong>{director.correo || '—'}</strong></div><div><span>Departamento</span><strong>{director.departamento || '—'}</strong></div><div><span>Programa</span><strong>{director.programa || '—'}</strong></div></div></div>}
      </main>
    </section>
  );
}
