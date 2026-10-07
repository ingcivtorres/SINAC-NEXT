import React, {useCallback, useEffect, useRef, useState} from 'react';
import ExpedienteCentralizadoCard from './ExpedienteCentralizadoCard';
import DashboardAnalitico from './DashboardAnalitico';
import {useAdminCopy} from './adminPanelTranslations';

const ESTADOS = ['pendiente', 'iniciado', 'revision', 'aceptado'];
const MENU_GROUPS = [
  {label: 'overview', items: [{id: 'overview', icon: '▦'}]},
  {label: 'community', items: [
    {id: 'users', icon: '♙'},
    {id: 'students', icon: '♧'},
    {id: 'faculty', icon: '◇'},
  ]},
  {label: 'academic', items: [
    {id: 'catalogs', icon: '▤'},
    {id: 'periods', icon: '◷'},
    {id: 'solicitudes', icon: '◈'},
  ]},
  {label: 'control', items: [
    {id: 'reports', icon: '▥'},
    {id: 'audit', icon: '✓'},
  ]},
  {label: 'system', items: [
    {id: 'security', icon: '⬡'},
    {id: 'maintenance', icon: '⚙'},
    {id: 'config', icon: '☷'},
  ]},
];
const MENU_ITEMS = MENU_GROUPS.flatMap(group => group.items);
const SALONES = [
  {value: 'salon_1', labelKey: 'roomOne'},
  {value: 'laboratorio_harold', labelKey: 'haroldLab'},
  {value: 'sala_juntas', labelKey: 'meetingRoom'},
];

function etiquetaEstado(estado, copy) {
  return copy.status[estado] || estado || copy.common.pending;
}

function getStatusLabel(rawStatus, copy) {
  const status = String(rawStatus || '').toLowerCase();
  if (status === 'aceptado') return copy.status.activo;
  return copy.status[status] || copy.common.pending;
}

function getUserStatus(aspirante, copy) {
  if (typeof aspirante?.is_active === 'boolean') {
    return aspirante.is_active ? copy.common.active : copy.common.inactive;
  }
  return getStatusLabel(aspirante?.proceso_estado, copy);
}

function roleLabel(role, copy) {
  const value = String(role || '').toLowerCase();
  if (value === 'admin' || value === 'administrador') return copy.roles.admin;
  if (value === 'director' || value === 'director de tesis') return copy.roles.director;
  if (value === 'servicios' || value === 'servicios escolares' || value === 'servicios_escolares') return copy.roles.servicios;
  if (value === 'docente') return copy.roles.docente;
  if (value === 'investigador') return copy.roles.investigador;
  if (value === 'alumno') return copy.roles.alumno;
  if (value === 'coordinacion' || value === 'coordinación') return copy.roles.coordinacion;
  return copy.roles.aspirante;
}

function passwordCumplePolitica(password) {
  return password.length >= 8 && /[A-Z]/.test(password) && /[a-z]/.test(password) && /[0-9]/.test(password);
}

function roleFormValue(role) {
  const value = String(role || '').toLowerCase();
  if (value.includes('admin')) return 'Administrador';
  if (value.includes('coordin')) return 'Coordinación';
  if (value.includes('docente')) return 'Docente';
  if (value.includes('director')) return 'Director de Tesis';
  if (value.includes('servicios')) return 'Servicios Escolares';
  if (value.includes('investigador')) return 'Investigador';
  if (value.includes('alumno') || value.includes('student')) return 'Alumno';
  return 'Aspirante';
}

export default function PanelAdministrador({session, onLogout}) {
  const copy = useAdminCopy();
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [dialog, setDialog] = useState(null);
  const [dialogValue, setDialogValue] = useState('');
  const dialogResolver = useRef(null);
  const [cargando, setCargando] = useState(true);
  const [filtro, setFiltro] = useState('todos');
  const [activeSection, setActiveSection] = useState('overview');
  const [userSearch, setUserSearch] = useState('');
  const [users, setUsers] = useState([]);
  const [usuariosCargados, setUsuariosCargados] = useState(false);
  const [alumnosAdmin, setAlumnosAdmin] = useState([]);
  const [alumnoSeleccionado, setAlumnoSeleccionado] = useState(null);
  const [studentSearch, setStudentSearch] = useState('');
  const [studentStatus, setStudentStatus] = useState('');
  const [alumnoAdminForm, setAlumnoAdminForm] = useState(null);
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
  const [catalogForm, setCatalogForm] = useState({tipo: 'materia', clave: '', nombre: '', creditos: 4, profesor: '', horario: '', salon: 'salon_1', capacidad: 42});
  const [periodoForm, setPeriodoForm] = useState({nombre: '', apertura: '', cierre: '', activo: true});
  const [apiStatus, setApiStatus] = useState('Sin comprobar');

  const pedirConfirmacion = (text) => new Promise(resolve => {
    dialogResolver.current = resolve;
    setMessage('');
    setDialog({type: 'confirm', text});
  });

  const pedirNuevaPassword = () => new Promise(resolve => {
    dialogResolver.current = resolve;
    setMessage('');
    setDialogValue('');
    setDialog({type: 'password'});
  });

  const resolverDialogo = (value) => {
    const resolve = dialogResolver.current;
    dialogResolver.current = null;
    setDialog(null);
    setDialogValue('');
    resolve?.(value);
  };

  useEffect(() => {
    if (!dialog && !message) return undefined;
    const cerrarConEscape = (event) => {
      if (event.key !== 'Escape') return;
      if (dialog) {
        const resolve = dialogResolver.current;
        dialogResolver.current = null;
        setDialog(null);
        setDialogValue('');
        resolve?.(dialog.type === 'confirm' ? false : null);
      } else {
        setMessage('');
      }
    };
    window.addEventListener('keydown', cerrarConEscape);
    return () => window.removeEventListener('keydown', cerrarConEscape);
  }, [dialog, message]);

  const cargarPanel = useCallback(async (signal) => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/administracion/panel/', {
        headers: {Authorization: `Bearer ${session.access}`},
        signal,
      });
      if (response.status === 401) {
        onLogout(copy.messages.expired);
        return;
      }
      if (response.status === 403) {
        throw new Error(copy.messages.forbidden);
      }
      if (!response.ok) throw new Error(copy.messages.loadPanel);
      setDatos(await response.json());
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || copy.messages.loadPanelShort);
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [copy, onLogout, session.access]);

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
      const responses = [usuariosResponse, alumnosResponse, docentesResponse, catalogosResponse, reportesResponse, auditoriaResponse, configResponse];
      if (responses.some((response) => response.status === 401)) {
        onLogout(copy.messages.expiredShort);
        return;
      }
      setError(responses.some((response) => !response.ok) ? copy.messages.loadModules : '');
      if (usuariosResponse.ok) {
        const userData = await usuariosResponse.json();
        setUsuariosCargados(true);
        setUsers((userData.usuarios || []).map((user) => ({
          id: user.id, name: user.nombre, usuario: user.usuario, email: user.correo,
          role: roleLabel(user.rol, copy), rawRole: user.rol, area: user.programa || user.departamento || 'General',
          status: user.is_active ? copy.common.active : copy.common.inactive, rawStatus: user.is_active ? 'Activo' : 'Inactivo', isActive: user.is_active, lastLogin: copy.messages.notAvailable,
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
      setError(err.message || copy.messages.loadModulesError);
    }
  }, [copy, onLogout, session.access]);

  useEffect(() => { cargarAdministracion(); }, [cargarAdministracion]);
  useEffect(() => {
    if (activeSection !== 'maintenance') return;
    const controller = new AbortController();
    fetch('/health/', {headers: {Authorization: `Bearer ${session.access}`}, signal: controller.signal})
      .then(response => { if (!response.ok) throw new Error(); setApiStatus('Operativa'); })
      .catch(error => { if (error.name !== 'AbortError') setApiStatus('No disponible'); });
    return () => controller.abort();
  }, [activeSection, session.access]);

  const apiUsers = (datos?.aspirantes || []).map((aspirante, index) => ({
    id: aspirante.id || index + 1,
    name: aspirante.nombre || copy.messages.unnamedUser,
    usuario: aspirante.usuario || '',
    email: aspirante.correo || 'correo@sinac.edu.mx',
    role: roleLabel(aspirante.rol, copy), rawRole: aspirante.rol || 'Aspirante',
    area: aspirante.programa || aspirante.unidad || copy.common.general,
    status: getUserStatus(aspirante, copy),
    rawStatus: typeof aspirante.is_active === 'boolean'
      ? aspirante.is_active ? 'Activo' : 'Inactivo'
      : aspirante.proceso_estado === 'aceptado' ? 'Activo'
        : aspirante.proceso_estado === 'revision' ? 'En revisión'
          : aspirante.proceso_estado === 'iniciado' ? 'En proceso' : 'Pendiente',
    isActive: typeof aspirante.is_active === 'boolean' ? aspirante.is_active : true,
    lastLogin: copy.messages.recent,
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
      if (response.status === 401) {
        onLogout(copy.messages.expiredShort);
        return;
      }
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || copy.messages.loadRecord);
      setAlumnoSeleccionado(body);
      setAlumnoAdminForm({
        programa: body.programa || '', departamento: body.departamento || '', unidad: body.unidad || '',
        matricula: body.matricula || '', proceso_estado: body.proceso_estado || 'pendiente',
      });
    } catch (err) { setError(err.message); }
  };

  const guardarAlumnoAdmin = async (event) => {
    event.preventDefault();
    if (!alumnoSeleccionado || !alumnoAdminForm) return;
    try {
      const response = await fetch(`/api/administracion/alumnos/${alumnoSeleccionado.id}/`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json', Authorization: `Bearer ${session.access}`},
        body: JSON.stringify(alumnoAdminForm),
      });
      if (response.status === 401) {
        onLogout(copy.messages.expiredShort);
        return;
      }
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || copy.messages.studentUpdateError);
      setAlumnosAdmin(previous => previous.map(alumno => alumno.id === body.id ? {...alumno, ...body} : alumno));
      setAlumnoSeleccionado(previous => ({...previous, ...body}));
      setMessage(copy.messages.studentUpdated);
    } catch (err) {
      setError(err.message || copy.messages.studentUpdateError);
    }
  };

  const alternarEstadoAlumno = async () => {
    if (!alumnoSeleccionado) return;
    const activar = !alumnoSeleccionado.is_active;
    const confirmacion = activar ? copy.messages.confirmStudentActivate : copy.messages.confirmStudentDeactivate;
    if (!(await pedirConfirmacion(confirmacion))) return;
    try {
      const response = await fetch(`/api/administracion/alumnos/${alumnoSeleccionado.id}/`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json', Authorization: `Bearer ${session.access}`},
        body: JSON.stringify({is_active: activar}),
      });
      if (response.status === 401) {
        onLogout(copy.messages.expiredShort);
        return;
      }
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || copy.messages.studentUpdateError);
      setAlumnosAdmin(previous => previous.map(alumno => alumno.id === body.id ? {...alumno, ...body} : alumno));
      setAlumnoSeleccionado(previous => ({...previous, ...body}));
      setMessage(activar ? copy.messages.studentActivated : copy.messages.studentDeactivated);
    } catch (err) {
      setError(err.message || copy.messages.studentUpdateError);
    }
  };

  const aspirantes = (datos?.aspirantes || []).filter((aspirante) => (
    String(aspirante.rol || '').trim().toLowerCase() === 'aspirante'
    && (filtro === 'todos' || aspirante.proceso_estado === filtro)
  ));
  const requestItems = (datos?.aspirantes || []).slice(0, 3).map((aspirante, index) => ({
    id: aspirante.id || index + 1,
    title: `${copy.shell.requestLabel} #${String(aspirante.id || index + 1).padStart(4, '0')}`,
    status: etiquetaEstado(aspirante.proceso_estado, copy),
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
      role: roleFormValue(user.rawRole || user.role),
      area: user.area,
      status: user.rawStatus || (user.isActive ? 'Activo' : 'Inactivo'),
    });
    setShowForm(true);
  };

  const handleDeleteUser = async (userId) => {
    if (!(await pedirConfirmacion(copy.messages.confirmDeactivate))) return;

    try {
      const response = await fetch(`/api/administracion/usuarios/${userId}/`, {
        method: 'DELETE',
        headers: {Authorization: `Bearer ${session.access}`},
      });

      if (response.status === 401) {
        onLogout(copy.messages.expiredShort);
        return;
      }

      if (response.ok) {
        setMessage(copy.messages.userDeactivated);
        await cargarAdministracion();
      } else if (!response.ok) {
        setError(copy.messages.deactivateError);
      }
    } catch (err) {
      setError(err.message || copy.messages.deactivateException);
    }
  };

  const handleResetPassword = async (userId) => {
    const password = await pedirNuevaPassword();
    if (!password) return;
    if (!passwordCumplePolitica(password)) { setError(copy.messages.passwordPolicy); return; }
    try {
      const response = await fetch(`/api/administracion/usuarios/${userId}/`, {
        method: 'PATCH', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${session.access}`},
        body: JSON.stringify({password}),
      });
      if (response.status === 401) {
        onLogout(copy.messages.expiredShort);
        return;
      }
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || copy.messages.passwordResetError);
      setError('');
      setMessage(copy.messages.passwordReset);
      cargarAdministracion();
    } catch (err) { setError(err.message); }
  };

  const handleFormChange = (event) => {
    const {name, value} = event.target;
    setFormData((prev) => ({...prev, [name]: value}));
  };

  const handleFormSubmit = async (event) => {
    event.preventDefault();
    if (!formData.name.trim() || !formData.usuario.trim() || !formData.email.trim()) {
      setError(copy.messages.requiredUserFields);
      return;
    }
    if ((!editingUser || formData.password) && !passwordCumplePolitica(formData.password)) {
      setError(copy.messages.passwordPolicy);
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
        onLogout(copy.messages.expiredShort);
        return;
      }

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        setError(errorBody.error || copy.messages.saveUserError);
        return;
      }

      const result = await response.json();

      if (editingUser) {
        setUsers((prev) => prev.map((user) => user.id === editingUser ? {
          ...user,
          name: formData.name,
          email: formData.email,
          usuario: formData.usuario,
          role: roleLabel(formData.role, copy),
          rawRole: formData.role,
          area: formData.area,
          status: formData.status === 'Activo' ? copy.common.active : formData.status === 'Inactivo' ? copy.common.inactive : copy.common.pending,
          rawStatus: formData.status,
          isActive: formData.status === 'Activo',
        } : user));
      } else {
        setUsers((prev) => [{
          id: result.id,
          name: result.nombre || formData.name,
          email: result.correo || formData.email,
          usuario: result.usuario || formData.usuario,
          role: roleLabel(result.rol || formData.role, copy),
          rawRole: result.rol || formData.role,
          area: result.programa || formData.area,
          status: formData.status === 'Activo' ? copy.common.active : formData.status === 'Inactivo' ? copy.common.inactive : copy.common.pending,
          rawStatus: formData.status,
          isActive: formData.status === 'Activo',
            lastLogin: copy.messages.recent,
        }, ...prev]);
      }

      setShowForm(false);
      setEditingUser(null);
      setFormData({name: '', usuario: '', email: '', password: '', role: 'Alumno', area: 'Sistemas', status: 'Activo'});
      setError('');
      cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || copy.messages.saveUserException);
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
      if (!response.ok) throw new Error(body.error || copy.messages.catalogError);
      setCatalogForm({tipo: 'materia', clave: '', nombre: '', creditos: 4, profesor: '', horario: '', salon: 'salon_1', capacidad: 42});
      await cargarAdministracion();
      setMessage(copy.messages.catalogSaved);
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
      if (!response.ok) throw new Error(body.error || copy.messages.periodError);
      setPeriodoForm({nombre: '', apertura: '', cierre: '', activo: true});
      await cargarAdministracion();
      setMessage(copy.messages.periodSaved);
    } catch (err) { setError(err.message); }
  };

  const guardarConfiguracion = async (event) => {
    event.preventDefault();
    try {
      const response = await fetch('/api/administracion/configuracion/', {
        method: 'PUT', headers: {'Content-Type': 'application/json', Authorization: `Bearer ${session.access}`},
        body: JSON.stringify(configuracion),
      });
      if (!response.ok) throw new Error(copy.messages.configError);
      setError('');
      setMessage(copy.messages.configSaved);
    } catch (err) { setError(err.message); }
  };

  const exportarReporte = async (formato = 'xlsx') => {
    try {
      const response = await fetch(`/api/administracion/reportes/?format=${formato}`, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error(copy.messages.reportError);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = `reporte_sinac.${formato}`; link.click(); URL.revokeObjectURL(url);
      setMessage(copy.messages.reportExported);
    } catch (err) { setError(err.message); }
  };

  return (
    <section className="admin-dashboard admin-dashboard--grouped" aria-label={copy.panel}>
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
          <div className="admin-brand-mark">S</div>
          <div>
            <p className="panel-kicker">{copy.operations}</p>
            <h2>{copy.title}</h2>
            <small>{copy.systemControl}</small>
          </div>
        </div>

        <nav className="admin-menu" aria-label={copy.menuLabel}>
          {MENU_GROUPS.map(group => <div className="admin-nav-group" key={group.label}>
            <p>{copy.menu[group.label]}</p>
            {group.items.map(item => <button key={item.id} type="button" className={`admin-menu-item ${activeSection === item.id ? 'is-active' : ''}`} onClick={() => setActiveSection(item.id)}>
              <i className="admin-menu-icon" aria-hidden="true">{item.icon}</i><span>{copy.menu[item.id]}</span>
              {menuCount(item) !== null && <small>{menuCount(item)}</small>}
            </button>)}
          </div>)}
        </nav>

        <div className="admin-side-card">
          <p>{copy.shell.performance}</p>
          <strong>{activosPct.toFixed(1)}%</strong>
          <span>{copy.common.activeUsers}</span>
        </div>

        <button type="button" className="admin-logout" onClick={() => onLogout(copy.logoutMessage)}>{copy.logout}</button>
      </aside>

      <main className="admin-main-panel">
        <header className="admin-topbar">
          <div>
            <p className="panel-kicker">{copy.title}</p>
            <h1>{copy.shell.systemPanel}</h1>
          </div>
          <div className="admin-top-actions">
            <div className="admin-export-actions"><button type="button" className="btn-secondary" onClick={() => exportarReporte('xlsx')}>{copy.shell.exportXlsx}</button><button type="button" className="btn-secondary" onClick={() => exportarReporte('pdf')}>{copy.shell.exportPdf}</button></div>
            <button type="button" className="btn-primary" onClick={handleOpenCreate}> + {copy.shell.addUser}</button>
          </div>
        </header>

        {error && <div className="api-error" role="alert">{error}</div>}
        {cargando && !datos && <div className="panel-card">{copy.shell.loading}</div>}

        {activeSection === 'overview' && datos && (
          <>
            <div className="admin-stat-grid">
              <div className="admin-stat-card accent">
                <span>{copy.shell.totalUsers}</span>
                <strong>{reportes?.usuarios_total ?? dashboardUsers.length}</strong>
                <small>{formatSigned(reportes?.usuarios_variacion_pct)} {copy.shell.thisMonth}</small>
              </div>
              <div className="admin-stat-card">
                <span>{copy.shell.requests}</span>
                <strong>{datos.resumen.total || 0}</strong>
                <small>{copy.shell.inProgress}</small>
              </div>
              <div className="admin-stat-card">
                <span>{copy.shell.approved}</span>
                <strong>{reportes?.aceptadas_ultimos_30_dias ?? datos.resumen.aceptado ?? 0}</strong>
                <small>{copy.shell.last30Days}</small>
              </div>
              <div className="admin-stat-card">
                <span>{copy.shell.pending}</span>
                <strong>{datos.resumen.pendiente || 0}</strong>
                <small>{copy.shell.requiresReview}</small>
              </div>
            </div>

            <div className="admin-grid-layout">
              <div className="admin-card admin-card-wide">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">{copy.shell.metrics}</p>
                    <h3>{copy.shell.activity}</h3>
                  </div>
                  <span className="pill success">{formatSigned(reportes?.usuarios_variacion_pct)}</span>
                </div>
                <div className="chart-bars" aria-label={copy.shell.activity}>
                  {chartValues.length ? chartValues.map((item) => (
                    <div key={item.mes} className="chart-column" title={`${item.total} ${copy.shell.records}`}>
                      <strong className="chart-value">{item.total}</strong>
                      <span style={{height: `${item.altura}%`}} />
                      <small>{item.mes}</small>
                    </div>
                  )) : <p className="empty-state">{copy.messages.noRecentActivity}</p>}
                </div>
              </div>

              <div className="admin-card">
                <div className="admin-card-head">
                  <div>
                    <p className="panel-kicker">{copy.shell.summary}</p>
                    <h3>{copy.shell.distribution}</h3>
                  </div>
                </div>
                <div className="donut-wrap">
                  <div className="donut-chart" style={{background: `conic-gradient(var(--primary) 0 ${activosPct}%, rgba(148,163,184,.28) ${activosPct}% 100%)`}}>
                    <div className="donut-center">
                      <strong>{activosPct.toFixed(1)}%</strong>
                      <small>{copy.shell.active}</small>
                    </div>
                  </div>
                  <ul className="legend-list">
                    <li><span className="legend-dot green" /> {copy.status.activo}: {reportes?.usuarios_activos || 0}</li>
                    <li><span className="legend-dot gray" /> {copy.shell.inactive}: {reportes?.usuarios_inactivos || 0}</li>
                    <li className="legend-note">{estadoTotal('revision')} {copy.shell.underReview} · {estadoTotal('pendiente')} {copy.shell.pendingPlural}</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">{copy.shell.processes}</p>
                  <h3>{copy.shell.registeredApplicants}</h3>
                </div>
                <label className="filter-inline">
                  {copy.shell.filterStatus}
                  <select value={filtro} onChange={(event) => setFiltro(event.target.value)}>
                    <option value="todos">{copy.common.all}</option>
                    {ESTADOS.map((estado) => <option key={estado} value={estado}>{etiquetaEstado(estado, copy)}</option>)}
                  </select>
                </label>
              </div>

              {aspirantes.length === 0 ? <p className="empty-state">{copy.messages.noApplicants}</p> : (
                <div className="admin-table-wrap">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>{copy.common.name}</th>
                        <th>{copy.common.username}</th>
                        <th>{copy.common.program}</th>
                        <th>{copy.common.unit}</th>
                        <th>{copy.common.status}</th>
                        <th>{copy.shell.registration}</th>
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
                          <td><span className={`estado-badge estado-${aspirante.proceso_estado}`}>{etiquetaEstado(aspirante.proceso_estado, copy)}</span></td>
                          <td>{new Intl.DateTimeFormat(copy.locale, {dateStyle: 'medium'}).format(new Date(aspirante.created_at))}</td>
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
                <p className="panel-kicker">{copy.users.management}</p>
                <h3>{copy.users.title}</h3>
              </div>
              <button type="button" className="btn-primary" onClick={handleOpenCreate}>+ {copy.shell.addUser}</button>
            </div>

            <div className="filter-inline" style={{marginBottom: '16px'}}><label htmlFor="admin-user-search">{copy.users.search}</label><input id="admin-user-search" value={userSearch} onChange={(event) => setUserSearch(event.target.value)} placeholder={copy.users.searchPlaceholder} /></div>

            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{copy.common.name}</th>
                    <th>{copy.common.email}</th>
                    <th>{copy.common.role}</th>
                    <th>{copy.common.area}</th>
                    <th>{copy.common.status}</th>
                    <th>{copy.users.lastLogin}</th>
                    <th>{copy.common.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleUsers.length ? visibleUsers.map((user) => (
                    <tr key={user.id}>
                      <td><strong>{user.name}</strong></td>
                      <td>{user.email}</td>
                      <td>{user.role}</td>
                      <td>{user.area}</td>
                      <td><span className={`estado-badge ${user.isActive ? 'estado-aceptado' : 'estado-pendiente'}`}>{user.status}</span></td>
                      <td>{user.lastLogin}</td>
                      <td>
                        <div className="row-actions">
                          <button type="button" className="icon-btn" onClick={() => handleEditUser(user)}>{copy.users.edit}</button>
                          <button type="button" className="icon-btn" onClick={() => handleResetPassword(user.id)}>{copy.users.reset}</button>
                          <button type="button" className="icon-btn danger" onClick={() => handleDeleteUser(user.id)}>{copy.users.deactivate}</button>
                        </div>
                      </td>
                    </tr>
                  )) : <tr><td colSpan="7">{copy.messages.noUsers}</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeSection === 'students' && (
          <div className="admin-card">
            {alumnoSeleccionado && <ExpedienteCentralizadoCard expedienteId={alumnoSeleccionado.expediente?.id} session={session}/>}
            <div className="admin-card-head">
              <div><p className="panel-kicker">{copy.students.records}</p><h3>{copy.students.title}</h3></div>
              <span className="pill success">{visibleAlumnos.length} {copy.common.records}</span>
            </div>
            <div className="filter-inline" style={{marginBottom: '16px', gap: '10px'}}>
              <label htmlFor="admin-student-search">{copy.common.search}</label>
              <input id="admin-student-search" value={studentSearch} onChange={(event) => setStudentSearch(event.target.value)} placeholder={copy.students.searchPlaceholder} />
              <select aria-label={copy.students.filterStatus} value={studentStatus} onChange={(event) => setStudentStatus(event.target.value)}>
                <option value="">{copy.common.all} {copy.common.status.toLowerCase()}</option><option value="aceptado">{copy.students.activeAccepted}</option><option value="inactivo">{copy.common.inactive}</option><option value="baja">{copy.status.baja}</option>
              </select>
            </div>
            <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.common.name}</th><th>{copy.common.enrollment}</th><th>{copy.common.program}</th><th>{copy.common.department}</th><th>{copy.students.subjects}</th><th>{copy.common.credits}</th><th>{copy.students.average}</th><th>{copy.students.action}</th></tr></thead><tbody>
              {visibleAlumnos.length ? visibleAlumnos.map((alumno) => <tr key={alumno.id}><td><strong>{alumno.nombre}</strong><br /><small>{alumno.correo}</small></td><td>{alumno.matricula || copy.common.pendingValue}</td><td>{alumno.programa || copy.common.noProgram}</td><td>{alumno.departamento || copy.common.noDepartment}</td><td>{alumno.materias_inscritas}</td><td>{alumno.creditos}</td><td>{alumno.promedio == null ? '—' : alumno.promedio.toFixed(2)}</td><td><button type="button" className="icon-btn" onClick={() => cargarDetalleAlumno(alumno.id)}>{copy.students.viewRecord}</button></td></tr>) : <tr><td colSpan="8">{copy.messages.noStudents}</td></tr>}
            </tbody></table></div>
            {alumnoSeleccionado && (
              <div className="admin-card" style={{marginTop: '18px'}}>
                <div className="admin-card-head">
                  <div><p className="panel-kicker">{copy.students.record}</p><h3>{alumnoSeleccionado.nombre}</h3></div>
                  <div className="row-actions">
                    <button type="button" className="icon-btn danger" onClick={alternarEstadoAlumno}>{alumnoSeleccionado.is_active ? copy.students.deactivate : copy.students.activate}</button>
                    <button type="button" className="icon-btn" onClick={() => {setAlumnoSeleccionado(null); setAlumnoAdminForm(null);}}>{copy.common.close}</button>
                  </div>
                </div>
                <div className="report-list">
                  <div><span>{copy.common.enrollment}</span><strong>{alumnoSeleccionado.matricula || copy.common.pendingValue}</strong></div>
                  <div><span>{copy.students.approvedCredits}</span><strong>{alumnoSeleccionado.creditos}</strong></div>
                  <div><span>{copy.students.average}</span><strong>{alumnoSeleccionado.promedio == null ? '—' : alumnoSeleccionado.promedio.toFixed(2)}</strong></div>
                  <div><span>{copy.students.recordFolio}</span><strong>{alumnoSeleccionado.expediente?.folio || copy.students.noRecord}</strong></div>
                </div>
                <form className="config-grid" onSubmit={guardarAlumnoAdmin}>
                  <label className="config-item">{copy.common.enrollment}<input value={alumnoAdminForm?.matricula || ''} onChange={event => setAlumnoAdminForm({...alumnoAdminForm, matricula: event.target.value})}/></label>
                  <label className="config-item">{copy.common.program}<input value={alumnoAdminForm?.programa || ''} onChange={event => setAlumnoAdminForm({...alumnoAdminForm, programa: event.target.value})}/></label>
                  <label className="config-item">{copy.common.department}<input value={alumnoAdminForm?.departamento || ''} onChange={event => setAlumnoAdminForm({...alumnoAdminForm, departamento: event.target.value})}/></label>
                  <label className="config-item">{copy.students.unit}<input value={alumnoAdminForm?.unidad || ''} onChange={event => setAlumnoAdminForm({...alumnoAdminForm, unidad: event.target.value})}/></label>
                  <label className="config-item">{copy.students.processStatus}<select value={alumnoAdminForm?.proceso_estado || 'pendiente'} onChange={event => setAlumnoAdminForm({...alumnoAdminForm, proceso_estado: event.target.value})}>
                    {['pendiente', 'iniciado', 'revision', 'aceptado', 'baja'].map(estado => <option key={estado} value={estado}>{copy.status[estado] || estado}</option>)}
                  </select></label>
                  <div className="config-item"><span>&nbsp;</span><button type="submit" className="btn-primary">{copy.students.saveChanges}</button></div>
                </form>
                <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.catalogs.key}</th><th>{copy.common.subject}</th><th>{copy.common.credits}</th><th>{copy.students.partials}</th><th>{copy.catalogs.final}</th><th>{copy.common.status}</th></tr></thead><tbody>{alumnoSeleccionado.inscripciones?.map((item) => <tr key={item.id}><td>{item.clave}</td><td>{item.materia}</td><td>{item.creditos}</td><td>{[item.parcial_1, item.parcial_2, item.parcial_3].map((value) => value ?? '—').join(' / ')}</td><td>{item.calificacion ?? '—'}</td><td>{item.calificacion == null ? copy.status.cursando : item.calificacion >= 7 ? copy.status.aprobada : copy.status.reprobada}</td></tr>)}</tbody></table></div>
              </div>
            )}
          </div>
        )}

        {activeSection === 'faculty' && (
          <div className="admin-card">
            <div className="admin-card-head"><div><p className="panel-kicker">{copy.faculty.affiliation}</p><h3>{copy.faculty.title}</h3></div><span className="pill success">{visibleDocentes.length} {copy.common.records}</span></div>
            <div className="filter-inline" style={{marginBottom: '16px'}}><label htmlFor="admin-faculty-search">{copy.common.search}</label><input id="admin-faculty-search" value={facultySearch} onChange={(event) => setFacultySearch(event.target.value)} placeholder={copy.users.searchPlaceholder} /></div>
            <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.faculty.name}</th><th>{copy.faculty.role}</th><th>{copy.common.department}</th><th>{copy.common.program}</th><th>{copy.faculty.subjects}</th><th>{copy.faculty.schedules}</th><th>{copy.faculty.thesisStudents}</th></tr></thead><tbody>
              {visibleDocentes.length ? visibleDocentes.map((persona) => <tr key={persona.id}><td><strong>{persona.nombre}</strong><br /><small>{persona.correo}</small></td><td>{persona.rol === 'director' ? copy.roles.director : persona.rol === 'investigador' ? copy.roles.investigador : copy.roles.docente}</td><td>{persona.departamento || copy.common.noDepartment}</td><td>{persona.programa || copy.common.noProgram}</td><td>{persona.total_materias}</td><td>{persona.materias.map((materia) => `${materia.clave}: ${materia.horario || copy.common.toAssign}`).join(' · ') || copy.messages.noCourseAssignments}</td><td>{persona.rol === 'director' ? persona.total_tesistas : '—'}</td></tr>) : <tr><td colSpan="7">{copy.messages.noFaculty}</td></tr>}
            </tbody></table></div>
            <p className="empty-state">{copy.messages.facultyNote}</p>
          </div>
        )}

        {activeSection === 'solicitudes' && (
          <div className="admin-grid-layout">
            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">{copy.requests.operation}</p>
                  <h3>{copy.requests.recent}</h3>
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
                  <li><strong>{copy.messages.noRequests}</strong><span>{copy.messages.noData}</span><button type="button" className="icon-btn">{copy.requests.view}</button></li>
                )}
              </ul>
            </div>

            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">{copy.requests.actions}</p>
                  <h3>{copy.requests.quick}</h3>
                </div>
              </div>
              <div className="quick-action-grid">
                <button type="button" className="admin-action" onClick={() => setActiveSection('users')}>{copy.menu.users}</button>
                <button type="button" className="admin-action" onClick={() => setActiveSection('reports')}>{copy.menu.reports}</button>
                <button type="button" className="admin-action" onClick={() => setActiveSection('periods')}>{copy.menu.periods}</button>
                <button type="button" className="admin-action" onClick={() => setActiveSection('audit')}>{copy.menu.audit}</button>
              </div>
            </div>
          </div>
        )}

        {activeSection === 'reports' && (
          <div className="admin-grid-layout">
            <DashboardAnalitico eyebrow={copy.reports.kicker} title={copy.reports.title} description={copy.reports.description} metrics={[{label:copy.reports.users, value:reportes?.usuarios_total ?? dashboardUsers.length}, {label:copy.reports.students, value:reportes?.alumnos ?? 0}, {label:copy.reports.enrollments, value:reportes?.inscripciones ?? 0}, {label:copy.reports.average, value:Number(reportes?.promedio_general || 0).toFixed(2)}]} distribution={[{label:copy.reports.active, value:reportes?.usuarios_activos ?? 0}, {label:copy.reports.inactive, value:reportes?.usuarios_inactivos ?? 0}, {label:copy.reports.pendingDocuments, value:reportes?.documentos_pendientes ?? 0}, {label:copy.reports.recentAcceptances, value:reportes?.aceptadas_ultimos_30_dias ?? 0}]} />
            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">{copy.reports.indicators}</p>
                  <h3>{copy.reports.reports}</h3>
                </div>
              </div>
              <div className="report-list">
                <div><span>{copy.reports.totalUsers}</span><strong>{reportes?.usuarios_total ?? dashboardUsers.length}</strong></div>
                <div><span>{copy.reports.active} {copy.reports.users.toLowerCase()}</span><strong>{reportes?.usuarios_activos ?? 0}</strong></div>
                <div><span>{copy.reports.students}</span><strong>{reportes?.alumnos ?? 0}</strong></div>
                <div><span>{copy.reports.enrollments}</span><strong>{reportes?.inscripciones ?? 0}</strong></div>
                <div><span>{copy.reports.generalAverage}</span><strong>{Number(reportes?.promedio_general || 0).toFixed(2)}</strong></div>
              </div>
            </div>
            <div className="admin-card">
              <div className="admin-card-head">
                <div>
                  <p className="panel-kicker">{copy.reports.alerts}</p>
                  <h3>{copy.reports.notifications}</h3>
                </div>
              </div>
              <ul className="mini-alerts">
                <li>{reportes?.documentos_pendientes || 0} {copy.reports.pendingValidation}</li>
                <li>{reportes?.auditoria_ultimos_30_dias || 0} {copy.reports.adminActions}</li>
                <li>{reportes?.aceptadas_ultimos_30_dias || 0} {copy.reports.acceptances30}</li>
              </ul>
            </div>
          </div>
        )}

        {activeSection === 'catalogs' && (
          <div className="admin-grid-layout">
            <div className="admin-card admin-card-wide">
              <div className="admin-card-head"><div><p className="panel-kicker">{copy.catalogs.structure}</p><h3>{copy.catalogs.subjects}</h3></div></div>
              <form className="config-grid" onSubmit={guardarCatalogo}>
                <label className="config-item">{copy.catalogs.key}<input value={catalogForm.clave} onChange={(e) => setCatalogForm({...catalogForm, clave: e.target.value})} placeholder="MAT-001" required /></label>
                <label className="config-item">{copy.catalogs.name}<input value={catalogForm.nombre} onChange={(e) => setCatalogForm({...catalogForm, nombre: e.target.value})} placeholder={copy.common.subject} required /></label>
                <label className="config-item">{copy.catalogs.credits}<select value={catalogForm.creditos} onChange={(e) => setCatalogForm({...catalogForm, creditos: Number(e.target.value)})}><option value="4">4</option><option value="5">5</option><option value="7">7</option></select></label>
                <label className="config-item">{copy.catalogs.professor}<input value={catalogForm.profesor} onChange={(e) => setCatalogForm({...catalogForm, profesor: e.target.value})} /></label>
                <label className="config-item">{copy.catalogs.schedule}<input value={catalogForm.horario} onChange={(e) => setCatalogForm({...catalogForm, horario: e.target.value})} /></label>
                <label className="config-item">{copy.catalogs.room}<select value={catalogForm.salon} onChange={(e) => setCatalogForm({...catalogForm, salon: e.target.value})}>{SALONES.map((salon) => <option key={salon.value} value={salon.value}>{copy.catalogs.rooms[salon.labelKey]}</option>)}</select></label>
                <label className="config-item">{copy.catalogs.capacity}<input type="number" min="1" max="32767" value={catalogForm.capacidad} onChange={(e) => setCatalogForm({...catalogForm, capacidad: Number(e.target.value)})} required /></label>
                <div className="config-item"><span>&nbsp;</span><button className="btn-primary" type="submit">{copy.catalogs.saveSubject}</button></div>
              </form>
              <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.catalogs.key}</th><th>{copy.common.subject}</th><th>{copy.common.credits}</th><th>{copy.common.professor}</th><th>{copy.common.schedule}</th><th>{copy.catalogs.room}</th><th>{copy.common.capacity}</th></tr></thead><tbody>{catalogos.materias.map((materia) => <tr key={materia.id}><td>{materia.clave}</td><td>{materia.nombre}</td><td>{materia.creditos}</td><td>{materia.profesor || copy.common.toAssign}</td><td>{materia.horario || copy.common.toAssign}</td><td>{copy.catalogs.rooms[SALONES.find((salon) => salon.value === materia.salon)?.labelKey] || copy.catalogs.roomPending}</td><td>{materia.capacidad ?? '—'}</td></tr>)}</tbody></table></div>
            </div>
            <div className="admin-card"><div className="admin-card-head"><div><p className="panel-kicker">{copy.catalogs.catalogs}</p><h3>{copy.catalogs.departmentsPrograms}</h3></div></div><p><strong>{copy.catalogs.departments}</strong> {catalogos.departamentos.join(', ') || copy.common.noRecords}</p><p><strong>{copy.catalogs.programs}</strong> {catalogos.programas.join(', ') || copy.common.noRecords}</p><p><strong>{copy.catalogs.roles}</strong> {catalogos.roles.join(', ')}</p></div>
          </div>
        )}

        {activeSection === 'periods' && (
          <div className="admin-card">
            <div className="admin-card-head"><div><p className="panel-kicker">{copy.periods.calendar}</p><h3>{copy.periods.title}</h3></div></div>
            <form className="config-grid" onSubmit={guardarPeriodo}>
              <label className="config-item">{copy.periods.period}<input value={periodoForm.nombre} onChange={(e) => setPeriodoForm({...periodoForm, nombre: e.target.value})} placeholder="2026-2" required /></label>
              <label className="config-item">{copy.periods.opening}<input type="datetime-local" value={periodoForm.apertura} onChange={(e) => setPeriodoForm({...periodoForm, apertura: e.target.value})} required /></label>
              <label className="config-item">{copy.periods.closing}<input type="datetime-local" value={periodoForm.cierre} onChange={(e) => setPeriodoForm({...periodoForm, cierre: e.target.value})} required /></label>
              <label className="config-item">{copy.common.status}<select value={periodoForm.activo ? 'true' : 'false'} onChange={(e) => setPeriodoForm({...periodoForm, activo: e.target.value === 'true'})}><option value="true">{copy.common.active}</option><option value="false">{copy.common.inactive}</option></select></label>
              <div className="config-item"><span>&nbsp;</span><button className="btn-primary" type="submit">{copy.periods.save}</button></div>
            </form>
            <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.periods.period}</th><th>{copy.periods.opening}</th><th>{copy.periods.closing}</th><th>{copy.common.status}</th></tr></thead><tbody>{catalogos.periodos.map((periodo) => <tr key={periodo.id}><td><strong>{periodo.nombre}</strong></td><td>{new Date(periodo.apertura).toLocaleString(copy.locale)}</td><td>{new Date(periodo.cierre).toLocaleString(copy.locale)}</td><td><span className={`estado-badge ${periodo.activo ? 'estado-aceptado' : 'estado-pendiente'}`}>{periodo.activo ? copy.common.active : copy.common.inactive}</span></td></tr>)}</tbody></table></div>
          </div>
        )}

        {activeSection === 'audit' && (
          <div className="admin-card"><div className="admin-card-head"><div><p className="panel-kicker">{copy.audit.traceability}</p><h3>{copy.audit.title}</h3></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.audit.date}</th><th>{copy.audit.user}</th><th>{copy.audit.action}</th><th>{copy.audit.object}</th><th>{copy.audit.ip}</th><th>{copy.audit.changes}</th></tr></thead><tbody>{auditoria.length ? auditoria.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString(copy.locale)}</td><td>{item.usuario}</td><td>{item.accion}</td><td>{item.modelo} #{item.objeto_id}</td><td>{item.ip || '—'}</td><td><small>{JSON.stringify(item.nuevos)}</small></td></tr>) : <tr><td colSpan="6">{copy.messages.noAudit}</td></tr>}</tbody></table></div></div>
        )}

        {activeSection === 'security' && (
          <div className="admin-grid-layout"><div className="admin-card"><p className="panel-kicker">{copy.security.title}</p><h3>{copy.security.controls}</h3><ul className="mini-alerts"><li>{copy.security.passwords}</li><li>{copy.security.inactive}</li><li>{copy.security.audit}</li><li>{copy.security.recovery}</li></ul></div><div className="admin-card"><p className="panel-kicker">{copy.security.state}</p><h3>{copy.security.accounts}</h3><div className="report-list"><div><span>{copy.security.active}</span><strong>{reportes?.usuarios_activos || 0}</strong></div><div><span>{copy.security.inactiveBlocked}</span><strong>{reportes?.usuarios_inactivos || 0}</strong></div></div></div></div>
        )}

        {activeSection === 'maintenance' && (
          <div className="admin-grid-layout"><div className="admin-card"><p className="panel-kicker">{copy.maintenance.title}</p><h3>{copy.maintenance.services}</h3><div className="report-list"><div><span>{copy.maintenance.database}</span><strong>{copy.maintenance.operational}</strong></div><div><span>{copy.maintenance.api}</span><strong>{copy.maintenance.operational}</strong></div><div><span>{copy.maintenance.log}</span><strong>{copy.maintenance.active}</strong></div></div></div><div className="admin-card"><p className="panel-kicker">{copy.maintenance.backup}</p><h3>{copy.maintenance.procedures}</h3><p>{copy.maintenance.backupNote}</p></div></div>
        )}

        {activeSection === 'config' && (
          <div className="admin-card">
            <div className="admin-card-head">
              <div>
                <p className="panel-kicker">{copy.config.system}</p>
                <h3>{copy.config.title}</h3>
              </div>
            </div>
            <form className="config-grid" onSubmit={guardarConfiguracion}>
              {Object.entries(configuracion).map(([key, value]) => <label className="config-item" key={key}>{key.replaceAll('_', ' ')}<input value={value} onChange={(e) => setConfiguracion({...configuracion, [key]: e.target.value})} /></label>)}
              <div className="config-item"><span>&nbsp;</span><button type="submit" className="btn-primary">{copy.config.save}</button></div>
            </form>
          </div>
        )}
      </main>

      {showForm && (
        <div className="modal-backdrop" onClick={() => setShowForm(false)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="modal-head">
              <div>
                <p className="panel-kicker">{copy.modal.users}</p>
                <h3>{editingUser ? copy.users.editing : copy.users.adding}</h3>
              </div>
              <button type="button" className="close-btn" onClick={() => setShowForm(false)}>×</button>
            </div>

            <form onSubmit={handleFormSubmit} className="modal-form">
              <div className="form-grid">
                <label>
                  {copy.modal.name}
                  <input name="name" value={formData.name} onChange={handleFormChange} placeholder={copy.users.exampleName} required />
                </label>
                <label>
                  {copy.modal.username}
                  <input name="usuario" value={formData.usuario} onChange={handleFormChange} placeholder={copy.users.exampleUsername} autoComplete="username" required minLength="3" />
                </label>
                <label>
                  {copy.modal.email}
                  <input name="email" type="email" value={formData.email} onChange={handleFormChange} placeholder={copy.users.emailPlaceholder} required />
                </label>
                <label>
                  {copy.modal.password}
                  <input
                    name="password"
                    type="password"
                    value={formData.password}
                    onChange={handleFormChange}
                    placeholder={editingUser ? copy.users.passwordHintEdit : copy.users.passwordHintCreate}
                    required={!editingUser}
                    pattern="(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9]).{8,}"
                  />
                </label>
                <label>
                  {copy.modal.role}
                  <select name="role" value={formData.role} onChange={handleFormChange}>
                    <option value="Administrador">{copy.roles.admin}</option>
                    <option value="Coordinación">{copy.roles.coordinacion}</option>
                    <option value="Docente">{copy.roles.docente}</option>
                    <option value="Director de Tesis">{copy.roles.director}</option>
                    <option value="Servicios Escolares">{copy.roles.servicios}</option>
                    <option value="Investigador">{copy.roles.investigador}</option>
                    <option value="Alumno">{copy.roles.alumno}</option>
                    <option value="Aspirante">{copy.roles.aspirante}</option>
                  </select>
                </label>
                <label>
                  {copy.modal.area}
                  <input name="area" value={formData.area} onChange={handleFormChange} placeholder={copy.users.areaPlaceholder} />
                </label>
                <label>
                  {copy.modal.status}
                  <select name="status" value={formData.status} onChange={handleFormChange}>
                    <option value="Activo">{copy.common.active}</option>
                    <option value="Inactivo">{copy.common.inactive}</option>
                  </select>
                </label>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{copy.modal.cancel}</button>
                <button type="submit" className="btn-primary">{editingUser ? copy.users.saveChanges : copy.users.create}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {dialog && (
        <div className="admin-dialog-backdrop" onClick={() => resolverDialogo(dialog.type === 'confirm' ? false : null)}>
          <section
            className={`admin-dialog-card admin-dialog-card--${dialog.type}`}
            role={dialog.type === 'confirm' ? 'alertdialog' : 'dialog'}
            aria-modal="true"
            aria-labelledby="admin-dialog-title"
            onClick={event => event.stopPropagation()}
          >
            <div className="admin-dialog-symbol" aria-hidden="true">{dialog.type === 'confirm' ? '!' : '↻'}</div>
            <div className="admin-dialog-copy">
              <h2 id="admin-dialog-title">{dialog.type === 'confirm' ? copy.dialog.confirmTitle : copy.dialog.passwordTitle}</h2>
              <p>{dialog.type === 'confirm' ? dialog.text : copy.messages.passwordPrompt}</p>
            </div>
            {dialog.type === 'password' && (
              <form className="admin-dialog-form" onSubmit={event => {event.preventDefault(); resolverDialogo(dialogValue);}}>
                <label htmlFor="admin-reset-password">{copy.modal.password}</label>
                <input
                  id="admin-reset-password"
                  type="password"
                  value={dialogValue}
                  onChange={event => setDialogValue(event.target.value)}
                  autoComplete="new-password"
                  minLength="8"
                  pattern="(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9]).{8,}"
                  required
                  autoFocus
                />
                <div className="admin-dialog-actions">
                  <button type="button" className="btn-secondary" onClick={() => resolverDialogo(null)}>{copy.dialog.cancel}</button>
                  <button type="submit" className="btn-primary">{copy.dialog.savePassword}</button>
                </div>
              </form>
            )}
            {dialog.type === 'confirm' && (
              <div className="admin-dialog-actions">
                <button type="button" className="btn-secondary" autoFocus onClick={() => resolverDialogo(false)}>{copy.dialog.cancel}</button>
                <button type="button" className="btn-primary" onClick={() => resolverDialogo(true)}>{copy.dialog.confirm}</button>
              </div>
            )}
          </section>
        </div>
      )}

      {!dialog && message && (
        <div className="admin-dialog-backdrop" onClick={() => setMessage('')}>
          <section className="admin-dialog-card admin-dialog-card--success" role="status" aria-live="polite" aria-modal="true" aria-labelledby="admin-success-title" onClick={event => event.stopPropagation()}>
            <div className="admin-dialog-symbol" aria-hidden="true">✓</div>
            <div className="admin-dialog-copy">
              <h2 id="admin-success-title">{copy.dialog.successTitle}</h2>
              <p>{message}</p>
            </div>
            <div className="admin-dialog-actions">
              <button type="button" className="btn-primary" autoFocus onClick={() => setMessage('')}>{copy.dialog.accept}</button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
