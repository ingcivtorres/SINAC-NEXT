import React, {useCallback, useEffect, useState} from 'react';

const ESTADOS = ['pendiente', 'iniciado', 'revision', 'aceptado'];
const MENU_ITEMS = [
  {id: 'overview', label: 'Resumen'},
  {id: 'users', label: 'Usuarios'},
  {id: 'solicitudes', label: 'Solicitudes'},
  {id: 'reports', label: 'Reportes'},
  {id: 'config', label: 'Configuración'},
];

const initialUsers = [
  {id: 1, name: 'Ana García', email: 'ana.garcia@sinac.edu.mx', role: 'Administrador', area: 'Coordinación', status: 'Activo', lastLogin: 'Hace 2h'},
  {id: 2, name: 'Luis Hernández', email: 'luis.hernandez@sinac.edu.mx', role: 'Docente', area: 'Ingeniería', status: 'Activo', lastLogin: 'Hace 5h'},
  {id: 3, name: 'María López', email: 'maria.lopez@sinac.edu.mx', role: 'Alumno', area: 'Sistemas', status: 'Inactivo', lastLogin: 'Hace 3 días'},
  {id: 4, name: 'Carlos Ruiz', email: 'carlos.ruiz@sinac.edu.mx', role: 'Coordinación', area: 'Académico', status: 'Activo', lastLogin: 'Hace 1h'},
  {id: 5, name: 'Sofía Mendoza', email: 'sofia.mendoza@sinac.edu.mx', role: 'Aspirante', area: 'Posgrado', status: 'Pendiente', lastLogin: 'Hace 1 día'},
];

function etiquetaEstado(estado) {
  return estado ? estado.charAt(0).toUpperCase() + estado.slice(1) : 'Pendiente';
}

function getStatusLabel(rawStatus) {
  const status = String(rawStatus || '').toLowerCase();
  if (status === 'aceptado') return 'Activo';
  if (status === 'revision') return 'En revisión';
  if (status === 'iniciado') return 'En proceso';
  return 'Pendiente';
}

export default function PanelAdministrador({session, onLogout}) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [filtro, setFiltro] = useState('todos');
  const [activeSection, setActiveSection] = useState('overview');
  const [users, setUsers] = useState(initialUsers);
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    name: '', email: '', role: 'Alumno', area: 'Sistemas', status: 'Activo',
  });

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

  const apiUsers = (datos?.aspirantes || []).map((aspirante, index) => ({
    id: aspirante.id || index + 1,
    name: aspirante.nombre || 'Usuario sin nombre',
    email: aspirante.correo || 'correo@sinac.edu.mx',
    role: aspirante.rol || 'Aspirante',
    area: aspirante.programa || aspirante.unidad || 'General',
    status: getStatusLabel(aspirante.proceso_estado),
    lastLogin: 'Reciente',
  }));

  const mergedUsers = [...apiUsers, ...users.filter((localUser) => !apiUsers.some((apiUser) => apiUser.id === localUser.id || apiUser.email === localUser.email))];
  const dashboardUsers = mergedUsers.length ? mergedUsers : users;

  const aspirantes = (datos?.aspirantes || []).filter((aspirante) => filtro === 'todos' || aspirante.proceso_estado === filtro);
  const requestItems = (datos?.aspirantes || []).slice(0, 3).map((aspirante, index) => ({
    id: aspirante.id || index + 1,
    title: `Solicitud #${String(aspirante.id || index + 1).padStart(4, '0')}`,
    status: etiquetaEstado(aspirante.proceso_estado),
    name: aspirante.nombre,
  }));

  const chartValues = [62, 78, 58, 87, 74, 92];

  const handleOpenCreate = () => {
    setEditingUser(null);
    setFormData({name: '', email: '', role: 'Alumno', area: 'Sistemas', status: 'Activo'});
    setShowForm(true);
  };

  const handleEditUser = (user) => {
    setEditingUser(user.id);
    setFormData({
      name: user.name,
      email: user.email,
      role: user.role,
      area: user.area,
      status: user.status,
    });
    setShowForm(true);
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('¿Estás seguro de que deseas eliminar este usuario?')) return;

    try {
      const response = await fetch(`/api/administracion/aspirantes/${userId}/`, {
        method: 'DELETE',
        headers: {Authorization: `Bearer ${session.access}`},
      });

      if (response.status === 401) {
        onLogout('Tu sesión ha caducado.');
        return;
      }

      if (response.status === 204) {
        setUsers((prev) => prev.filter((user) => user.id !== userId));
        cargarPanel(new AbortController().signal);
      } else if (!response.ok) {
        setError('No se pudo eliminar el usuario.');
      }
    } catch (err) {
      setError(err.message || 'Error al eliminar el usuario.');
    }
  };

  const handleFormChange = (event) => {
    const {name, value} = event.target;
    setFormData((prev) => ({...prev, [name]: value}));
  };

  const handleFormSubmit = async (event) => {
    event.preventDefault();
    if (!formData.name.trim() || !formData.email.trim()) {
      setError('Nombre y correo son obligatorios.');
      return;
    }

    try {
      const method = editingUser ? 'PUT' : 'POST';
      const url = editingUser
        ? `/api/administracion/aspirantes/${editingUser}/`
        : '/api/administracion/panel/';

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${session.access}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.status === 401) {
        onLogout('Tu sesión ha caducado.');
        return;
      }

      if (!response.ok) {
        const errData = await response.json();
        setError(errData.error || 'No se pudo guardar el usuario.');
        return;
      }

      const result = await response.json();

      if (editingUser) {
        setUsers((prev) => prev.map((user) => user.id === editingUser ? {...user, ...formData} : user));
      } else {
        setUsers((prev) => [{
          id: result.id,
          name: result.nombre || formData.name,
          email: result.correo || formData.email,
          role: result.rol || formData.role,
          area: result.programa || formData.area,
          status: getStatusLabel(result.proceso_estado),
          lastLogin: 'Recientemente',
        }, ...prev]);
      }

      setShowForm(false);
      setEditingUser(null);
      setFormData({name: '', email: '', role: 'Alumno', area: 'Sistemas', status: 'Activo'});
      setError('');
      cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || 'Error al guardar el usuario.');
    }
  };

  return (
    <section className="admin-dashboard" aria-label="Panel de administración">
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
          <div className="admin-brand-mark">S</div>
          <div>
            <p className="panel-kicker">Sistema</p>
            <h2>SINAC Admin</h2>
          </div>
        </div>

        <nav className="admin-menu" aria-label="Menú administrativo">
          {MENU_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`admin-menu-item ${activeSection === item.id ? 'is-active' : ''}`}
              onClick={() => setActiveSection(item.id)}
            >
              <span>{item.label}</span>
              <small>{item.id === 'users' ? dashboardUsers.length : item.id === 'overview' ? (datos?.resumen?.total || dashboardUsers.length) : item.id === 'solicitudes' ? (datos?.aspirantes?.length || dashboardUsers.length) : item.id === 'reports' ? (datos?.resumen?.aceptado || 0) : '24'}</small>
            </button>
          ))}
        </nav>

        <div className="admin-side-card">
          <p>Rendimiento</p>
          <strong>94.8%</strong>
          <span>Procesos completados</span>
        </div>

        <button type="button" className="admin-logout" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
      </aside>

      <main className="admin-main-panel">
        <header className="admin-topbar">
          <div>
            <p className="panel-kicker">Administración</p>
            <h1>Panel de control</h1>
          </div>
          <div className="admin-top-actions">
            <button type="button" className="btn-secondary">Exportar</button>
            <button type="button" className="btn-primary" onClick={handleOpenCreate}> + Agregar usuario</button>
          </div>
        </header>

        {error && <div className="api-error" role="alert">{error}</div>}
        {cargando && !datos && <div className="panel-card">Cargando información administrativa...</div>}

        {activeSection === 'overview' && datos && (
          <>
            <div className="admin-stat-grid">
              <div className="admin-stat-card accent">
                <span>Total usuarios</span>
                <strong>{dashboardUsers.length}</strong>
                <small>+12.4% este mes</small>
              </div>
              <div className="admin-stat-card">
                <span>Solicitudes</span>
                <strong>{datos.resumen.total || 0}</strong>
                <small>En proceso</small>
              </div>
              <div className="admin-stat-card">
                <span>Aprobados</span>
                <strong>{datos.resumen.aceptado || 0}</strong>
                <small>Últimos 30 días</small>
              </div>
              <div className="admin-stat-card">
                <span>Pendientes</span>
                <strong>{datos.resumen.pendiente || 0}</strong>
                <small>Requieren revisión</small>
              </div>
            </div>

            <div className="admin-grid-layout">
              <div className="admin-card admin-card-wide">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">Métricas</p>
                    <h3>Actividad del sistema</h3>
                  </div>
                  <span className="pill success">+18.2%</span>
                </div>
                <div className="chart-bars" aria-label="Gráfica de actividad del sistema">
                  {chartValues.map((value, index) => (
                    <div key={index} className="chart-column">
                      <span style={{height: `${value}%`}} />
                      <small>{['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'][index]}</small>
                    </div>
                  ))}
                </div>
              </div>

              <div className="admin-card">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">Resumen</p>
                    <h3>Distribución</h3>
                  </div>
                </div>
                <div className="donut-wrap">
                  <div className="donut-chart">
                    <div className="donut-center">
                      <strong>68%</strong>
                    </div>
                  </div>
                  <ul className="legend-list">
                    <li><span className="legend-dot green" /> Activos</li>
                    <li><span className="legend-dot blue" /> En revisión</li>
                    <li><span className="legend-dot amber" /> Pendientes</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">Procesos</p>
                  <h3>Aspirantes registrados</h3>
                </div>
                <label className="filter-inline">
                  Filtrar por estado
                  <select value={filtro} onChange={(event) => setFiltro(event.target.value)}>
                    <option value="todos">Todos</option>
                    {ESTADOS.map((estado) => <option key={estado} value={estado}>{etiquetaEstado(estado)}</option>)}
                  </select>
                </label>
              </div>

              {aspirantes.length === 0 ? <p className="empty-state">No hay aspirantes para el filtro seleccionado.</p> : (
                <div className="admin-table-wrap">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Nombre</th>
                        <th>Usuario</th>
                        <th>Programa</th>
                        <th>Unidad</th>
                        <th>Estado</th>
                        <th>Registro</th>
                      </tr>
                    </thead>
                    <tbody>
                      {aspirantes.map((aspirante) => (
                        <tr key={aspirante.id}>
                          <td>
                            <strong>{aspirante.nombre}</strong><br />
                            <span>{aspirante.correo}</span>
                          </td>
                          <td>{aspirante.usuario}</td>
                          <td>{aspirante.programa}</td>
                          <td>{aspirante.unidad}</td>
                          <td><span className={`estado-badge estado-${aspirante.proceso_estado}`}>{etiquetaEstado(aspirante.proceso_estado)}</span></td>
                          <td>{new Intl.DateTimeFormat('es-MX', {dateStyle: 'medium'}).format(new Date(aspirante.created_at))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}

        {activeSection === 'users' && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">Gestión</p>
                <h3>Usuarios del sistema</h3>
              </div>
              <button type="button" className="btn-primary" onClick={handleOpenCreate}>+ Agregar usuario</button>
            </div>

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Nombre</th>
                    <th>Correo</th>
                    <th>Rol</th>
                    <th>Área</th>
                    <th>Estado</th>
                    <th>Último acceso</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboardUsers.map((user) => (
                    <tr key={user.id}>
                      <td><strong>{user.name}</strong></td>
                      <td>{user.email}</td>
                      <td>{user.role}</td>
                      <td>{user.area}</td>
                      <td><span className={`estado-badge ${user.status === 'Activo' ? 'estado-aceptado' : user.status === 'Inactivo' ? 'estado-pendiente' : 'estado-iniciado'}`}>{user.status}</span></td>
                      <td>{user.lastLogin}</td>
                      <td>
                        <div className="row-actions">
                          <button type="button" className="icon-btn" onClick={() => handleEditUser(user)}>Editar</button>
                          <button type="button" className="icon-btn danger" onClick={() => handleDeleteUser(user.id)}>Eliminar</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSection === 'solicitudes' && (
          <div className="admin-grid-layout">
            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">Operación</p>
                  <h3>Solicitudes recientes</h3>
                </div>
              </div>
              <ul className="activity-list">
                {requestItems.length ? requestItems.map((item) => (
                  <li key={item.id}>
                    <strong>{item.title}</strong>
                    <span>{item.name || item.status}</span>
                    <button type="button" className="icon-btn">{item.status}</button>
                  </li>
                )) : (
                  <li><strong>Sin solicitudes</strong><span>No hay datos disponibles.</span><button type="button" className="icon-btn">Ver</button></li>
                )}
              </ul>
            </div>

            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">Acciones</p>
                  <h3>Gestión rápida</h3>
                </div>
              </div>
              <div className="quick-action-grid">
                <button type="button" className="admin-action">Aprobar solicitudes</button>
                <button type="button" className="admin-action">Enviar recordatorios</button>
                <button type="button" className="admin-action">Generar reportes</button>
                <button type="button" className="admin-action">Actualizar estado</button>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'reports' && (
          <div className="admin-grid-layout">
            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">Indicadores</p>
                  <h3>Reportes</h3>
                </div>
              </div>
              <div className="report-list">
                <div><span>Registro mensual</span><strong>{datos?.resumen?.total || dashboardUsers.length}</strong></div>
                <div><span>Usuarios activos</span><strong>{datos?.resumen?.aceptado || 0}</strong></div>
                <div><span>Pendientes</span><strong>{datos?.resumen?.pendiente || 0}</strong></div>
              </div>
            </div>
            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">Alertas</p>
                  <h3>Notificaciones</h3>
                </div>
              </div>
              <ul className="mini-alerts">
                <li>2 usuarios requieren validación</li>
                <li>3 documentos pendientes</li>
                <li>1 actualización de proceso</li>
              </ul>
            </div>
          </div>
        )}

        {activeSection === 'config' && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">Sistema</p>
                <h3>Configuración general</h3>
              </div>
            </div>
            <div className="config-grid">
              <div className="config-item"><label>Nombre del sistema</label><input defaultValue="SINAC NEXT" /></div>
              <div className="config-item"><label>Campus principal</label><input defaultValue="CINVESTAV" /></div>
              <div className="config-item"><label>Correo de soporte</label><input defaultValue="soporte@sinac.edu.mx" /></div>
              <div className="config-item"><label>Zona horaria</label><input defaultValue="UTC-6" /></div>
            </div>
          </div>
        )}
      </main>

      {showForm && (
        <div className="modal-backdrop" onClick={() => setShowForm(false)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="panel-kicker">Usuarios</p>
                <h3>{editingUser ? 'Editar usuario' : 'Agregar usuario'}</h3>
              </div>
              <button type="button" className="close-btn" onClick={() => setShowForm(false)}>×</button>
            </div>

            <form onSubmit={handleFormSubmit} className="modal-form">
              <div className="form-grid">
                <label>
                  Nombre
                  <input name="name" value={formData.name} onChange={handleFormChange} placeholder="Ej. María López" />
                </label>
                <label>
                  Correo
                  <input name="email" value={formData.email} onChange={handleFormChange} placeholder="correo@sinac.edu.mx" />
                </label>
                <label>
                  Rol
                  <select name="role" value={formData.role} onChange={handleFormChange}>
                    <option>Administrador</option>
                    <option>Coordinación</option>
                    <option>Docente</option>
                    <option>Alumno</option>
                    <option>Aspirante</option>
                  </select>
                </label>
                <label>
                  Área
                  <input name="area" value={formData.area} onChange={handleFormChange} placeholder="Sistemas" />
                </label>
                <label>
                  Estado
                  <select name="status" value={formData.status} onChange={handleFormChange}>
                    <option>Activo</option>
                    <option>Inactivo</option>
                    <option>Pendiente</option>
                  </select>
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancelar</button>
                <button type="submit" className="btn-primary">{editingUser ? 'Guardar cambios' : 'Crear usuario'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}
