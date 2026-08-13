import React, {useCallback, useEffect, useState} from 'react';

const ESTADOS = ['pendiente', 'iniciado', 'revision', 'aceptado'];

function etiquetaEstado(estado) {
  return estado ? estado.charAt(0).toUpperCase() + estado.slice(1) : 'Pendiente';
}

export default function PanelAdministrador({session, onLogout}) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [filtro, setFiltro] = useState('todos');

  const cargarPanel = useCallback(async (signal) => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/administracion/panel/', {
        headers: {Authorization: `Bearer ${session.access}`},
        signal,
      });
      if (response.status === 401) {
        onLogout('Tu sesión ha caducado. Vuelve a iniciar sesión para continuar.');
        return;
      }
      if (response.status === 403) {
        throw new Error('No tienes permisos de administrador para acceder a este panel.');
      }
      if (!response.ok) throw new Error('No se pudo cargar la información administrativa.');
      setDatos(await response.json());
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

  const aspirantes = (datos?.aspirantes || []).filter((aspirante) => filtro === 'todos' || aspirante.proceso_estado === filtro);

  return (
    <section className="panel-section" aria-label="Panel de administración">
      <div className="panel-hero">
        <div><p className="panel-kicker">Administración</p><h1>Panel de control</h1><p className="panel-sub">Seguimiento de aspirantes y procesos de admisión</p></div>
        <button type="button" className="btn-outline-danger" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
      </div>

      {error && <div className="api-error" role="alert">{error}</div>}
      {cargando && !datos && <div className="panel-card">Cargando información administrativa...</div>}

      {datos && <>
        <div className="admin-stats" aria-label="Resumen de solicitudes">
          <div className="admin-stat"><span>{datos.resumen.total}</span><small>Total de aspirantes</small></div>
          {ESTADOS.map((estado) => <div className="admin-stat" key={estado}><span>{datos.resumen[estado]}</span><small>{etiquetaEstado(estado)}</small></div>)}
        </div>

        <div className="panel-card admin-list-card">
          <div className="admin-list-header"><h3>Aspirantes registrados</h3><label>Filtrar por estado<select value={filtro} onChange={(event) => setFiltro(event.target.value)}><option value="todos">Todos</option>{ESTADOS.map((estado) => <option key={estado} value={estado}>{etiquetaEstado(estado)}</option>)}</select></label></div>
          {aspirantes.length === 0 ? <p className="empty-state">No hay aspirantes para el filtro seleccionado.</p> : <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Nombre</th><th>Usuario</th><th>Programa</th><th>Unidad</th><th>Estado</th><th>Registro</th></tr></thead><tbody>{aspirantes.map((aspirante) => <tr key={aspirante.id}><td><strong>{aspirante.nombre}</strong><br/><span>{aspirante.correo}</span></td><td>{aspirante.usuario}</td><td>{aspirante.programa}</td><td>{aspirante.unidad}</td><td><span className={`estado-badge estado-${aspirante.proceso_estado}`}>{etiquetaEstado(aspirante.proceso_estado)}</span></td><td>{new Intl.DateTimeFormat('es-MX', {dateStyle: 'medium'}).format(new Date(aspirante.created_at))}</td></tr>)}</tbody></table></div>}
        </div>
      </>}
    </section>
  );
}
