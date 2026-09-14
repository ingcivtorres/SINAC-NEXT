import React, {useCallback, useEffect, useState} from 'react';

const ESTADOS = ['pendiente', 'iniciado', 'revision', 'aceptado'];
const MENU_ITEMS = [
  {id: 'overview', label: 'Resumen'},
  {id: 'users', label: 'Usuarios'},
  {id: 'students', label: 'Alumnos'},
  {id: 'faculty', label: 'Docentes y directores'},
  {id: 'catalogs', label: 'Catálogos'},
  {id: 'periods', label: 'Periodos académicos'},
  {id: 'solicitudes', label: 'Solicitudes'},
  {id: 'reports', label: 'Reportes'},
  {id: 'audit', label: 'Auditoría'},
  {id: 'security', label: 'Seguridad'},
  {id: 'maintenance', label: 'Mantenimiento'},
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

function getUserStatus(aspirante) {
  if (typeof aspirante?.is_active === 'boolean') {
    return aspirante.is_active ? 'Activo' : 'Inactivo';
  }
  return getStatusLabel(aspirante?.proceso_estado);
}

function roleLabel(role) {
  const value = String(role || '').toLowerCase();
  if (value === 'director' || value === 'director de tesis') return 'Director de Tesis';
  if (value === 'servicios' || value === 'servicios escolares' || value === 'servicios_escolares') return 'Servicios Escolares';
  if (value === 'docente') return 'Docente';
  if (value === 'investigador') return 'Investigador';
  if (value === 'alumno') return 'Alumno';
  if (value === 'coordinacion' || value === 'coordinación') return 'Coordinación';
  return value === 'admin' ? 'Administrador' : 'Aspirante';
}

export default function PanelAdministrador({session, onLogout}) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [filtro, setFiltro] = useState('todos');
  const [activeSection, setActiveSection] = useState('overview');
  const [userSearch, setUserSearch] = useState('');
  const [users, setUsers] = useState(initialUsers);
  const [usuariosCargados, setUsuariosCargados] = useState(false);
  const [alumnosAdmin, setAlumnosAdmin] = useState([]);
  const [alumnoSeleccionado, setAlumnoSeleccionado] = useState(null);
  const [studentSearch, setStudentSearch] = useState('');
  const [studentStatus, setStudentStatus] = useState('');
  const [docentesAdmin, setDocentesAdmin] = useState([]);
  const [facultySearch, setFacultySearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    name: '', usuario: '', email: '', password: '', role: 'Alumno', area: 'Sistemas', status: 'Activo',
  });
  const [catalogos, setCatalogos] = useState({materias: [], periodos: [], departamentos: [], programas: [], roles: []});
  const [reportes, setReportes] = useState(null);
  const [auditoria, setAuditoria] = useState([]);
  const [configuracion, setConfiguracion] = useState({});
  const [catalogForm, setCatalogForm] = useState({tipo: 'materia', clave: '', nombre: '', creditos: 4, profesor: '', horario: ''});
  const [periodoForm, setPeriodoForm] = useState({nombre: '', apertura: '', cierre: '', activo: true});

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

  const cargarAdministracion = useCallback(async () => {
    try {
      const headers = {Authorization: `Bearer ${session.access}`};
      const [usuariosResponse, alumnosResponse, docentesResponse, catalogosResponse, reportesResponse, auditoriaResponse, configResponse] = await Promise.all([
        fetch('/api/administracion/usuarios/', {headers}),
        fetch('/api/administracion/alumnos/', {headers}),
        fetch('/api/administracion/docentes/', {headers}),
        fetch('/api/administracion/catalogos/', {headers}),
        fetch('/api/administracion/reportes/', {headers}),
        fetch('/api/administracion/auditoria/', {headers}),
        fetch('/api/administracion/configuracion/', {headers}),
      ]);
      if ([usuariosResponse, alumnosResponse, docentesResponse, catalogosResponse, reportesResponse, auditoriaResponse, configResponse].some((response) => response.status === 401)) {
        onLogout('Tu sesión ha caducado.');
        return;
      }
      if (usuariosResponse.ok) {
        const userData = await usuariosResponse.json();
        setUsuariosCargados(true);
        setUsers((userData.usuarios || []).map((user) => ({
          id: user.id, name: user.nombre, usuario: user.usuario, email: user.correo,
          role: roleLabel(user.rol), area: user.programa || user.departamento || 'General',
          status: user.is_active ? 'Activo' : 'Inactivo', isActive: user.is_active, lastLogin: 'No disponible',
        })));
      }
      if (alumnosResponse.ok) {
        const alumnosData = await alumnosResponse.json();
        setAlumnosAdmin(alumnosData.alumnos || []);
      }
      if (docentesResponse.ok) {
        const docentesData = await docentesResponse.json();
        setDocentesAdmin(docentesData.docentes || []);
      }
      if (catalogosResponse.ok) setCatalogos(await catalogosResponse.json());
      if (reportesResponse.ok) setReportes(await reportesResponse.json());
      if (auditoriaResponse.ok) setAuditoria(await auditoriaResponse.json());
      if (configResponse.ok) setConfiguracion(await configResponse.json());
    } catch (err) {
      setError(err.message || 'No se pudieron cargar los módulos administrativos.');
    }
  }, [onLogout, session.access]);

  useEffect(() => { cargarAdministracion(); }, [cargarAdministracion]);

  const apiUsers = (datos?.aspirantes || []).map((aspirante, index) => ({
    id: aspirante.id || index + 1,
    name: aspirante.nombre || 'Usuario sin nombre',
    usuario: aspirante.usuario || '',
    email: aspirante.correo || 'correo@sinac.edu.mx',
    role: aspirante.rol || 'Aspirante',
    area: aspirante.programa || aspirante.unidad || 'General',
    status: getUserStatus(aspirante),
    isActive: typeof aspirante.is_active === 'boolean' ? aspirante.is_active : true,
    lastLogin: 'Reciente',
  }));

  const dashboardUsers = usuariosCargados ? users : (apiUsers.length ? apiUsers : users);
  const visibleUsers = dashboardUsers.filter((user) => {
    const query = userSearch.trim().toLowerCase();
    return !query || [user.name, user.usuario, user.email, user.role, user.area].some((value) => String(value || '').toLowerCase().includes(query));
  });
  const visibleAlumnos = alumnosAdmin.filter((alumno) => {
    const query = studentSearch.trim().toLowerCase();
    const matchesText = !query || [alumno.nombre, alumno.usuario, alumno.matricula, alumno.programa, alumno.departamento].some((value) => String(value || '').toLowerCase().includes(query));
    const matchesStatus = !studentStatus || alumno.proceso_estado === studentStatus || (studentStatus === 'inactivo' && !alumno.is_active);
    return matchesText && matchesStatus;
  });
  const visibleDocentes = docentesAdmin.filter((persona) => {
    const query = facultySearch.trim().toLowerCase();
    return !query || [persona.nombre, persona.usuario, persona.correo, persona.rol, persona.departamento, persona.programa].some((value) => String(value || '').toLowerCase().includes(query));
  });

  const cargarDetalleAlumno = async (id) => {
    try {
      const response = await fetch(`/api/administracion/alumnos/${id}/`, {headers: {Authorization: `Bearer ${session.access}`}});
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'No se pudo cargar el expediente.');
      setAlumnoSeleccionado(body);
    } catch (err) { setError(err.message); }
  };

  const aspirantes = (datos?.aspirantes || []).filter((aspirante) => filtro === 'todos' || aspirante.proceso_estado === filtro);
  const requestItems = (datos?.aspirantes || []).slice(0, 3).map((aspirante, index) => ({
    id: aspirante.id || index + 1,
    title: `Solicitud #${String(aspirante.id || index + 1).padStart(4, '0')}`,
    status: etiquetaEstado(aspirante.proceso_estado),
    name: aspirante.nombre,
  }));

  const actividadMensual = reportes?.actividad_mensual || [];
  const chartMax = Math.max(...actividadMensual.map((item) => item.total), 1);
  const chartValues = actividadMensual.map((item) => ({...item, altura: Math.max((item.total / chartMax) * 100, item.total ? 12 : 0)}));
  const activosPct = Number(reportes?.usuarios_activos_pct || 0);
  const formatSigned = (value) => {
    const number = Number(value || 0);
    return `${number > 0 ? '+' : ''}${number.toFixed(1)}%`;
  };
  const estadoTotal = (estado) => reportes?.estados_aspirantes?.find((item) => item.proceso_estado === estado)?.total || 0;
  const menuCount = (item) => {
    if (item.id === 'users') return dashboardUsers.length;
    if (item.id === 'students') return reportes?.alumnos || 0;
    if (item.id === 'faculty') return reportes?.docentes || 0;
    if (item.id === 'overview') return reportes?.usuarios_total || dashboardUsers.length;
    if (item.id === 'solicitudes') return datos?.aspirantes?.length || 0;
    if (item.id === 'reports') return reportes?.inscripciones || 0;
    if (item.id === 'audit') return auditoria.length;
    return null;
  };

  const handleOpenCreate = () => {
    setEditingUser(null);
    setFormData({name: '', usuario: '', email: '', password: '', role: 'Alumno', area: 'Sistemas', status: 'Activo'});
    setShowForm(true);
  };

  const handleEditUser = (user) => {
    setEditingUser(user.id);
    setFormData({
      name: user.name,
      usuario: user.usuario || '',
      email: user.email,
      password: '',
      role: roleLabel(user.role),
      area: user.area,
      status: user.status,
    });
    setShowForm(true);
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('¿Estás seguro de que deseas eliminar este usuario?')) return;

    try {
      const response = await fetch(`/api/administracion/usuarios/${userId}/`, {
        method: 'DELETE',
        headers: {Authorization: `Bearer ${session.access}`},
      });

      if (response.status === 401) {
        onLogout('Tu sesión ha caducado.');
        return;
      }

      if (response.ok) {
        setUsers((prev) => prev.filter((user) => user.id !== userId));
        cargarPanel(new AbortController().signal);
      } else if (!response.ok) {
        setError('No se pudo eliminar el usuario.');
      }
    } catch (err) {
      setError(err.message || 'Error al eliminar el usuario.');
    }
  };

  const handleResetPassword = async (userId) => {
    const password = window.prompt('Escribe la nueva contraseña temporal (mínimo 8 caracteres):');
    if (!password) return;
    if (password.length < 8) { setError('La contraseña debe tener al menos 8 caracteres.'); return; }
    try {
      const response = await fetch(`/api/administracion/usuarios/${userId}/`, {
        method: 'PATCH', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${session.access}`},
        body: JSON.stringify({password}),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'No se pudo restablecer la contraseña.');
      setError('Contraseña restablecida correctamente.');
      cargarAdministracion();
    } catch (err) { setError(err.message); }
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
      const method = editingUser ? 'PATCH' : 'POST';
      const url = editingUser
        ? `/api/administracion/usuarios/${editingUser}/`
        : '/api/administracion/usuarios/';

      const payload = {
        ...formData,
        usuario: formData.usuario.trim(),
        status: formData.status === 'Activo' ? 'Activo' : formData.status === 'Inactivo' ? 'Inactivo' : 'Pendiente',
      };

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${session.access}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
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
        setUsers((prev) => prev.map((user) => user.id === editingUser ? {
          ...user,
          name: formData.name,
          email: formData.email,
          usuario: formData.usuario,
          role: formData.role,
          area: formData.area,
          status: formData.status,
          isActive: formData.status === 'Activo',
        } : user));
      } else {
        setUsers((prev) => [{
          id: result.id,
          name: result.nombre || formData.name,
          email: result.correo || formData.email,
          usuario: result.usuario || formData.usuario,
          role: result.rol || formData.role,
          area: result.programa || formData.area,
          status: formData.status,
          isActive: formData.status === 'Activo',
          lastLogin: 'Recientemente',
        }, ...prev]);
      }

      setShowForm(false);
      setEditingUser(null);
      setFormData({name: '', usuario: '', email: '', password: '', role: 'Alumno', area: 'Sistemas', status: 'Activo'});
      setError('');
      cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || 'Error al guardar el usuario.');
    }
  };

  const guardarCatalogo = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch('/api/administracion/catalogos/', {
        method: 'POST', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${session.access}`},
        body: JSON.stringify(catalogForm),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'No se pudo guardar el catálogo.');
      setCatalogForm({tipo: 'materia', clave: '', nombre: '', creditos: 4, profesor: '', horario: ''});
      await cargarAdministracion();
    } catch (err) { setError(err.message); }
  };

  const guardarPeriodo = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch('/api/administracion/catalogos/', {
        method: 'POST', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${session.access}`},
        body: JSON.stringify({tipo: 'periodo', ...periodoForm}),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || 'No se pudo guardar el periodo.');
      setPeriodoForm({nombre: '', apertura: '', cierre: '', activo: true});
      await cargarAdministracion();
    } catch (err) { setError(err.message); }
  };

  const guardarConfiguracion = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch('/api/administracion/configuracion/', {
        method: 'PUT', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${session.access}`},
        body: JSON.stringify(configuracion),
      });
      if (!response.ok) throw new Error('No se pudo guardar la configuración.');
      setError('');
    } catch (err) { setError(err.message); }
  };

  const exportarReporte = async (formato = 'xlsx') => {
    try {
      const response = await fetch(`/api/administracion/reportes/?format=${formato}`, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error('No se pudo generar el reporte.');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = `reporte_sinac.${formato}`; link.click(); URL.revokeObjectURL(url);
    } catch (err) { setError(err.message); }
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
              {menuCount(item) !== null && <small>{menuCount(item)}</small>}
            </button>
          ))}
        </nav>

        <div className="admin-side-card">
          <p>Rendimiento</p>
          <strong>{activosPct.toFixed(1)}%</strong>
          <span>Usuarios activos</span>
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
            <div className="admin-export-actions"><button type="button" className="btn-secondary" onClick={() => exportarReporte('xlsx')}>Exportar XLSX</button><button type="button" className="btn-secondary" onClick={() => exportarReporte('pdf')}>Exportar PDF</button></div>
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
                <strong>{reportes?.usuarios_total ?? dashboardUsers.length}</strong>
                <small>{formatSigned(reportes?.usuarios_variacion_pct)} este mes</small>
              </div>
              <div className="admin-stat-card">
                <span>Solicitudes</span>
                <strong>{datos.resumen.total || 0}</strong>
                <small>En proceso</small>
              </div>
              <div className="admin-stat-card">
                <span>Aprobados</span>
                <strong>{reportes?.aceptadas_ultimos_30_dias ?? datos.resumen.aceptado ?? 0}</strong>
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
                  <span className="pill success">{formatSigned(reportes?.usuarios_variacion_pct)}</span>
                </div>
                <div className="chart-bars" aria-label="Gráfica de actividad del sistema">
                  {chartValues.length ? chartValues.map((item) => (
                    <div key={item.mes} className="chart-column" title={`${item.total} registros`}>
                      <strong className="chart-value">{item.total}</strong>
                      <span style={{height: `${item.altura}%`}} />
                      <small>{item.mes}</small>
                    </div>
                  )) : <p className="empty-state">Aún no hay actividad registrada en los últimos seis meses.</p>}
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
                  <div className="donut-chart" style={{background: `conic-gradient(var(--primary) 0 ${activosPct}%, rgba(148,163,184,.28) ${activosPct}% 100%)`}}>
                    <div className="donut-center">
                      <strong>{activosPct.toFixed(1)}%</strong>
                      <small>activos</small>
                    </div>
                  </div>
                  <ul className="legend-list">
                    <li><span className="legend-dot green" /> Activos: {reportes?.usuarios_activos || 0}</li>
                    <li><span className="legend-dot gray" /> Inactivos: {reportes?.usuarios_inactivos || 0}</li>
                    <li className="legend-note">{estadoTotal('revision')} en revisión · {estadoTotal('pendiente')} pendientes</li>
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

            <div className="filter-inline" style={{marginBottom: '16px'}}><label htmlFor="admin-user-search">Buscar usuario</label><input id="admin-user-search" value={userSearch} onChange={(event) => setUserSearch(event.target.value)} placeholder="Nombre, usuario, correo o rol" /></div>

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
                  {visibleUsers.map((user) => (
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
                          <button type="button" className="icon-btn" onClick={() => handleResetPassword(user.id)}>Restablecer</button>
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

        {activeSection === 'students' && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div><p className="panel-kicker">Expedientes académicos</p><h3>Alumnos</h3></div>
              <span className="pill success">{visibleAlumnos.length} registros</span>
            </div>
            <div className="filter-inline" style={{marginBottom: '16px', gap: '10px'}}>
              <label htmlFor="admin-student-search">Buscar</label>
              <input id="admin-student-search" value={studentSearch} onChange={(event) => setStudentSearch(event.target.value)} placeholder="Nombre, matrícula, programa..." />
              <select aria-label="Filtrar estatus" value={studentStatus} onChange={(event) => setStudentStatus(event.target.value)}>
                <option value="">Todos los estatus</option><option value="aceptado">Activo/aceptado</option><option value="inactivo">Inactivo</option><option value="baja">Baja</option>
              </select>
            </div>
            <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Alumno</th><th>Matrícula</th><th>Programa</th><th>Departamento</th><th>Materias</th><th>Créditos</th><th>Promedio</th><th>Acción</th></tr></thead><tbody>
              {visibleAlumnos.length ? visibleAlumnos.map((alumno) => <tr key={alumno.id}><td><strong>{alumno.nombre}</strong><br /><small>{alumno.correo}</small></td><td>{alumno.matricula || 'Pendiente'}</td><td>{alumno.programa || 'Sin programa'}</td><td>{alumno.departamento || 'Sin departamento'}</td><td>{alumno.materias_inscritas}</td><td>{alumno.creditos}</td><td>{alumno.promedio == null ? '—' : alumno.promedio.toFixed(2)}</td><td><button type="button" className="icon-btn" onClick={() => cargarDetalleAlumno(alumno.id)}>Ver expediente</button></td></tr>) : <tr><td colSpan="8">No hay alumnos para los filtros seleccionados.</td></tr>}
            </tbody></table></div>
            {alumnoSeleccionado && <div className="admin-card" style={{marginTop: '18px'}}><div className="admin-card-head"><div><p className="panel-kicker">Expediente</p><h3>{alumnoSeleccionado.nombre}</h3></div><button type="button" className="icon-btn" onClick={() => setAlumnoSeleccionado(null)}>Cerrar</button></div><div className="report-list"><div><span>Matrícula</span><strong>{alumnoSeleccionado.matricula || 'Pendiente'}</strong></div><div><span>Créditos aprobados</span><strong>{alumnoSeleccionado.creditos}</strong></div><div><span>Promedio</span><strong>{alumnoSeleccionado.promedio == null ? '—' : alumnoSeleccionado.promedio.toFixed(2)}</strong></div><div><span>Folio de expediente</span><strong>{alumnoSeleccionado.expediente?.folio || 'Sin expediente'}</strong></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Clave</th><th>Materia</th><th>Créditos</th><th>Parciales</th><th>Final</th><th>Estado</th></tr></thead><tbody>{alumnoSeleccionado.inscripciones?.map((item) => <tr key={item.id}><td>{item.clave}</td><td>{item.materia}</td><td>{item.creditos}</td><td>{[item.parcial_1, item.parcial_2, item.parcial_3].map((value) => value ?? '—').join(' / ')}</td><td>{item.calificacion ?? '—'}</td><td>{item.calificacion == null ? 'Cursando' : item.calificacion >= 7 ? 'Aprobada' : 'Reprobada'}</td></tr>)}</tbody></table></div></div>}
          </div>
        )}

        {activeSection === 'faculty' && (
          <div className="admin-card">
            <div className="admin-card-head"><div><p className="panel-kicker">Adscripción académica</p><h3>Docentes y directores de tesis</h3></div><span className="pill success">{visibleDocentes.length} registros</span></div>
            <div className="filter-inline" style={{marginBottom: '16px'}}><label htmlFor="admin-faculty-search">Buscar</label><input id="admin-faculty-search" value={facultySearch} onChange={(event) => setFacultySearch(event.target.value)} placeholder="Nombre, correo, departamento o rol..." /></div>
            <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Nombre</th><th>Rol</th><th>Departamento</th><th>Programa</th><th>Materias</th><th>Horarios</th><th>Tesistas</th></tr></thead><tbody>
              {visibleDocentes.length ? visibleDocentes.map((persona) => <tr key={persona.id}><td><strong>{persona.nombre}</strong><br /><small>{persona.correo}</small></td><td>{persona.rol === 'director' ? 'Director de Tesis' : persona.rol === 'investigador' ? 'Investigador' : 'Docente'}</td><td>{persona.departamento || 'Sin departamento'}</td><td>{persona.programa || 'Sin programa'}</td><td>{persona.total_materias}</td><td>{persona.materias.map((materia) => `${materia.clave}: ${materia.horario || 'Por asignar'}`).join(' · ') || 'Sin materias asignadas'}</td><td>{persona.rol === 'director' ? persona.total_tesistas : '—'}</td></tr>) : <tr><td colSpan="7">No hay docentes o directores para el filtro seleccionado.</td></tr>}
            </tbody></table></div>
            <p className="empty-state">El avance detallado de tesis requiere un expediente de tesis específico; actualmente solo se muestran los tesistas vinculados mediante el campo de tutor propuesto.</p>
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
                <div><span>Usuarios totales</span><strong>{reportes?.usuarios_total ?? dashboardUsers.length}</strong></div>
                <div><span>Usuarios activos</span><strong>{reportes?.usuarios_activos ?? 0}</strong></div>
                <div><span>Alumnos</span><strong>{reportes?.alumnos ?? 0}</strong></div>
                <div><span>Inscripciones</span><strong>{reportes?.inscripciones ?? 0}</strong></div>
                <div><span>Promedio general</span><strong>{Number(reportes?.promedio_general || 0).toFixed(2)}</strong></div>
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
                <li>{reportes?.documentos_pendientes || 0} documentos pendientes de validación</li>
                <li>{reportes?.auditoria_ultimos_30_dias || 0} acciones administrativas en los últimos 30 días</li>
                <li>{reportes?.aceptadas_ultimos_30_dias || 0} aceptaciones en los últimos 30 días</li>
              </ul>
            </div>
          </div>
        )}

        {activeSection === 'catalogs' && (
          <div className="admin-grid-layout">
            <div className="admin-card admin-card-wide">
              <div className="admin-card-head"><div><p className="panel-kicker">Estructura académica</p><h3>Materias y asignaturas</h3></div></div>
              <form className="config-grid" onSubmit={guardarCatalogo}>
                <label className="config-item">Clave<input value={catalogForm.clave} onChange={(e) => setCatalogForm({...catalogForm, clave: e.target.value})} placeholder="MAT-001" required /></label>
                <label className="config-item">Nombre<input value={catalogForm.nombre} onChange={(e) => setCatalogForm({...catalogForm, nombre: e.target.value})} placeholder="Materia" required /></label>
                <label className="config-item">Créditos<select value={catalogForm.creditos} onChange={(e) => setCatalogForm({...catalogForm, creditos: Number(e.target.value)})}><option value="4">4</option><option value="5">5</option><option value="7">7</option></select></label>
                <label className="config-item">Profesor<input value={catalogForm.profesor} onChange={(e) => setCatalogForm({...catalogForm, profesor: e.target.value})} /></label>
                <label className="config-item">Horario<input value={catalogForm.horario} onChange={(e) => setCatalogForm({...catalogForm, horario: e.target.value})} /></label>
                <div className="config-item"><span>&nbsp;</span><button className="btn-primary" type="submit">Guardar materia</button></div>
              </form>
              <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Clave</th><th>Materia</th><th>Créditos</th><th>Profesor</th><th>Horario</th></tr></thead><tbody>{catalogos.materias.map((materia) => <tr key={materia.id}><td>{materia.clave}</td><td>{materia.nombre}</td><td>{materia.creditos}</td><td>{materia.profesor || 'Por asignar'}</td><td>{materia.horario || 'Por asignar'}</td></tr>)}</tbody></table></div>
            </div>
            <div className="admin-card"><div className="admin-card-head"><div><p className="panel-kicker">Catálogos</p><h3>Departamentos y programas</h3></div></div><p><strong>Departamentos:</strong> {catalogos.departamentos.join(', ') || 'Sin registros'}</p><p><strong>Programas:</strong> {catalogos.programas.join(', ') || 'Sin registros'}</p><p><strong>Roles:</strong> {catalogos.roles.join(', ')}</p></div>
          </div>
        )}

        {activeSection === 'periods' && (
          <div className="admin-card">
            <div className="admin-card-head"><div><p className="panel-kicker">Calendario escolar</p><h3>Periodos académicos</h3></div></div>
            <form className="config-grid" onSubmit={guardarPeriodo}>
              <label className="config-item">Periodo<input value={periodoForm.nombre} onChange={(e) => setPeriodoForm({...periodoForm, nombre: e.target.value})} placeholder="2026-2" required /></label>
              <label className="config-item">Apertura<input type="datetime-local" value={periodoForm.apertura} onChange={(e) => setPeriodoForm({...periodoForm, apertura: e.target.value})} required /></label>
              <label className="config-item">Cierre<input type="datetime-local" value={periodoForm.cierre} onChange={(e) => setPeriodoForm({...periodoForm, cierre: e.target.value})} required /></label>
              <label className="config-item">Estado<select value={periodoForm.activo ? 'true' : 'false'} onChange={(e) => setPeriodoForm({...periodoForm, activo: e.target.value === 'true'})}><option value="true">Activo</option><option value="false">Inactivo</option></select></label>
              <div className="config-item"><span>&nbsp;</span><button className="btn-primary" type="submit">Guardar periodo</button></div>
            </form>
            <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Periodo</th><th>Apertura</th><th>Cierre</th><th>Estado</th></tr></thead><tbody>{catalogos.periodos.map((periodo) => <tr key={periodo.id}><td><strong>{periodo.nombre}</strong></td><td>{new Date(periodo.apertura).toLocaleString('es-MX')}</td><td>{new Date(periodo.cierre).toLocaleString('es-MX')}</td><td><span className={`estado-badge ${periodo.activo ? 'estado-aceptado' : 'estado-pendiente'}`}>{periodo.activo ? 'Activo' : 'Inactivo'}</span></td></tr>)}</tbody></table></div>
          </div>
        )}

        {activeSection === 'audit' && (
          <div className="admin-card"><div className="admin-card-head"><div><p className="panel-kicker">Trazabilidad</p><h3>Bitácora de auditoría</h3></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Objeto</th><th>IP</th><th>Cambios</th></tr></thead><tbody>{auditoria.length ? auditoria.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString('es-MX')}</td><td>{item.usuario}</td><td>{item.accion}</td><td>{item.modelo} #{item.objeto_id}</td><td>{item.ip || '—'}</td><td><small>{JSON.stringify(item.nuevos)}</small></td></tr>) : <tr><td colSpan="6">Aún no hay eventos registrados.</td></tr>}</tbody></table></div></div>
        )}

        {activeSection === 'security' && (
          <div className="admin-grid-layout"><div className="admin-card"><p className="panel-kicker">Seguridad</p><h3>Controles de acceso</h3><ul className="mini-alerts"><li>Las contraseñas se almacenan con hash seguro.</li><li>Los usuarios inactivos no pueden iniciar sesión.</li><li>Los cambios administrativos se registran en auditoría.</li><li>La recuperación de contraseña debe realizarse mediante el administrador.</li></ul></div><div className="admin-card"><p className="panel-kicker">Estado</p><h3>Cuentas</h3><div className="report-list"><div><span>Activas</span><strong>{reportes?.usuarios_activos || 0}</strong></div><div><span>Inactivas/bloqueadas</span><strong>{reportes?.usuarios_inactivos || 0}</strong></div></div></div></div>
        )}

        {activeSection === 'maintenance' && (
          <div className="admin-grid-layout"><div className="admin-card"><p className="panel-kicker">Mantenimiento</p><h3>Estado de servicios</h3><div className="report-list"><div><span>Base de datos</span><strong>Operativa</strong></div><div><span>API SINAC</span><strong>Operativa</strong></div><div><span>Bitácora</span><strong>Activa</strong></div></div></div><div className="admin-card"><p className="panel-kicker">Respaldo</p><h3>Procedimientos controlados</h3><p>Los respaldos y restauraciones deben ejecutarse desde la infraestructura autorizada. El panel no expone operaciones destructivas.</p></div></div>
        )}

        {activeSection === 'config' && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">Sistema</p>
                <h3>Configuración general</h3>
              </div>
            </div>
            <form className="config-grid" onSubmit={guardarConfiguracion}>
              {Object.entries(configuracion).map(([key, value]) => <label className="config-item" key={key}>{key.replaceAll('_', ' ')}<input value={value} onChange={(e) => setConfiguracion({...configuracion, [key]: e.target.value})} /></label>)}
              <div className="config-item"><span>&nbsp;</span><button type="submit" className="btn-primary">Guardar configuración</button></div>
            </form>
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
                  Nombre de usuario
                  <input name="usuario" value={formData.usuario} onChange={handleFormChange} placeholder="Ej. david.torres" autoComplete="username" />
                </label>
                <label>
                  Correo
                  <input name="email" value={formData.email} onChange={handleFormChange} placeholder="correo@sinac.edu.mx" />
                </label>
                <label>
                  Contraseña
                  <input
                    name="password"
                    type="password"
                    value={formData.password}
                    onChange={handleFormChange}
                    placeholder={editingUser ? 'Dejar vacío para conservar la actual' : 'Mínimo 8 caracteres'}
                  />
                </label>
                <label>
                  Rol
                  <select name="role" value={formData.role} onChange={handleFormChange}>
                    <option>Administrador</option>
                    <option>Coordinación</option>
                    <option>Docente</option>
                    <option>Director de Tesis</option>
                    <option>Servicios Escolares</option>
                    <option>Investigador</option>
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
