import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import './PanelCoordinacion.css';

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
  const [evaluacionesColegio, setEvaluacionesColegio] = useState([]);
  const [evaluacionForm, setEvaluacionForm] = useState({aspirante: '', estado: 'en_revision', dictamen: ''});
  const [evaluacionFiltro, setEvaluacionFiltro] = useState('todas');
  const [busqueda, setBusqueda] = useState('');
  const [cargas, setCargas] = useState([]);
  const [periodoCarga, setPeriodoCarga] = useState('');
  const [periodoActual, setPeriodoActual] = useState(null);
  const [periodoForm, setPeriodoForm] = useState({nombre:'',apertura:'',cierre:'',activo:true});

  const cargarFlujoCargas = useCallback(async () => {
    try {
      const r = await fetch('/api/cargas-academicas/', {headers: {Authorization: `Bearer ${session.access}`}});
      if (r.status === 401) return onLogout('Tu sesión ha caducado.');
      if (!r.ok) throw new Error('No se pudieron cargar las cargas académicas.');
      setCargas(await r.json());
    } catch (e) { setError(e.message); }
  }, [onLogout, session.access]);

  async function crearCargaRevision() {
    const r = await fetch('/api/cargas-academicas/', {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({periodo: periodoCarga})});
    const data = await r.json();
    if (!r.ok) return setError(data.detail || 'No se pudo enviar la carga a revisión.');
    setSaveSuccess('Carga enviada a revisión.'); setPeriodoCarga(''); cargarFlujoCargas();
  }

  async function actualizarEstadoCarga(id, estado) {
    const r = await fetch(`/api/cargas-academicas/${id}/`, {method: 'PATCH', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({estado})});
    const data = await r.json();
    if (!r.ok) return setError(data.detail || 'No se pudo actualizar la carga.');
    setSaveSuccess(`Carga ${estado.replace('_',' ')} correctamente.`); cargarFlujoCargas();
  }
  async function descargarReporte(tipo='expedientes', formato='xlsx') { await downloadBlob(`/api/coordinacion/reportes/?tipo=${tipo}&format=${formato}`, `reporte-${tipo}-${new Date().toISOString().slice(0,10)}.${formato}`); }

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
    const primera = (datos?.aspirantes || []).find(a => a.rol === 'aspirante');
    if (primera && !seleccionado) {
      setSeleccionado(primera);
    }
  }, [datos, seleccionado]);

  useEffect(() => {
    if (!datos) return;
    fetch('/api/preregistro/evaluaciones-colegio/', {headers: {Authorization: `Bearer ${session.access}`}}).then(r => r.ok ? r.json() : Promise.reject(new Error('No se pudieron cargar las evaluaciones.'))).then(setEvaluacionesColegio).catch(err => setError(err.message));
  }, [datos, session.access]);

  useEffect(() => { if (['periodos', 'cargas', 'materias'].includes(activeSection)) cargarFlujoCargas(); }, [activeSection, cargarFlujoCargas]);
  useEffect(() => { if (['periodos', 'cargas', 'materias'].includes(activeSection)) fetch('/api/periodos-inscripcion/', {headers:{Authorization:`Bearer ${session.access}`}}).then(r=>r.ok?r.json():null).then(setPeriodoActual).catch(()=>{}); }, [activeSection, session.access]);
  async function crearPeriodo(){const r=await fetch('/api/periodos-inscripcion/',{method:'POST',headers:{'Authorization':`Bearer ${session.access}`,'Content-Type':'application/json'},body:JSON.stringify(periodoForm)});const d=await r.json().catch(()=>({}));if(!r.ok)return setError(d.detail||'No se pudo crear el periodo.');setPeriodoActual(d);setSaveSuccess('Periodo de inscripción configurado.');}

  async function guardarEvaluacionColegio(event) {
    event.preventDefault();
    if (!evaluacionForm.aspirante || !evaluacionForm.dictamen.trim()) return setError('Selecciona un aspirante y escribe el dictamen.');
    const editando = Boolean(evaluacionForm.id);
    const response = await fetch(editando ? `/api/preregistro/evaluaciones-colegio/${evaluacionForm.id}/` : '/api/preregistro/evaluaciones-colegio/', {method: editando ? 'PATCH' : 'POST', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify(evaluacionForm)});
    const data = await response.json();
    if (!response.ok) return setError(data.detail || data.aspirante || 'No se pudo guardar la evaluación.');
    setEvaluacionesColegio(items => editando ? items.map(item => item.id === data.id ? data : item) : [data, ...items]); setEvaluacionForm({aspirante: '', estado: 'en_revision', dictamen: ''}); setSaveSuccess(editando ? 'Evaluación del Colegio actualizada correctamente.' : 'Evaluación del Colegio guardada correctamente.'); setError('');
  }

  const aspirantes = useMemo(() => (datos?.aspirantes || []).filter((aspirante) => aspirante.rol === 'aspirante').filter((aspirante) => {
    if (filtro === 'por-revisar') return ['pendiente', 'iniciado'].includes(aspirante.proceso_estado);
    return filtro === 'todos' || aspirante.proceso_estado === filtro;
  }), [datos, filtro]);
  const alumnos = useMemo(() => (datos?.aspirantes || []).filter(a => a.rol === 'alumno'), [datos]);
  const docentes = useMemo(() => (datos?.aspirantes || []).filter(a => ['docente','director'].includes(a.rol)), [datos]);
  const directores = useMemo(() => (datos?.aspirantes || []).filter(a => a.rol === 'director' && a.is_active !== false), [datos]);
  const filtrarPersonas = (lista) => lista.filter(a => !busqueda.trim() || `${a.nombre} ${a.usuario} ${a.correo}`.toLowerCase().includes(busqueda.toLowerCase()));
  const analitica = useMemo(() => { const lista=datos?.aspirantes||[]; const total=lista.length||1; const estados=['pendiente','revision','aceptado','rechazado']; return {total:lista.length, aspirantes:lista.filter(a=>a.rol==='aspirante').length, alumnos:lista.filter(a=>a.rol==='alumno').length, personal:lista.filter(a=>['docente','director'].includes(a.rol)).length, estados:estados.map(e=>({key:e,label:etiquetaEstado(e),count:lista.filter(a=>a.proceso_estado===e).length,pct:Math.round(lista.filter(a=>a.proceso_estado===e).length*100/total)}))}; }, [datos]);
  const evaluacionesVisibles = useMemo(() => evaluacionFiltro === 'todas' ? evaluacionesColegio : evaluacionesColegio.filter(e => e.estado === evaluacionFiltro), [evaluacionesColegio, evaluacionFiltro]);

  const CAMPOS_EDITABLES = [
    'fecha_examen_admision', 'fecha_entrevista', 'fecha_inicio_curso_propedeutico',
    'curso_propedeutico_nota', 'curso_propedeutico_aprobado', 'apoyo_autorizado',
    'director_tesis',
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

  // Helper to download generated PDF/XLSX files
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
      const blob = await resp.blob();
      const urlBlob = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = urlBlob;
      a.download = `carga_academica_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(urlBlob);
      setSaveSuccess('Carga académica generada correctamente.');
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
              <button type="button" className={`sidebar-item${activeSection === 'periodos' ? ' is-active' : ''}`} onClick={() => setActiveSection('periodos')} aria-current={activeSection === 'periodos' ? 'page' : undefined}>Periodos de inscripción</button>
              <button type="button" className={`sidebar-item${activeSection === 'materias' ? ' is-active' : ''}`} onClick={() => setActiveSection('materias')} aria-current={activeSection === 'materias' ? 'page' : undefined}>Materias y cursos</button>
              <button type="button" className={`sidebar-item${activeSection === 'cargas' ? ' is-active' : ''}`} onClick={() => setActiveSection('cargas')} aria-current={activeSection === 'cargas' ? 'page' : undefined}>Aprobación de carga</button>
              <button type="button" className={`sidebar-item${activeSection === 'alumnos' ? ' is-active' : ''}`} onClick={() => setActiveSection('alumnos')}>Alumnos</button>
              <button type="button" className={`sidebar-item${activeSection === 'aspirantes' ? ' is-active' : ''}`} onClick={() => setActiveSection('aspirantes')}>Aspirantes</button>
              <button type="button" className={`sidebar-item${activeSection === 'personal' ? ' is-active' : ''}`} onClick={() => setActiveSection('personal')}>Docentes y Directores</button>
              <button type="button" className={`sidebar-item${activeSection === 'reportes' ? ' is-active' : ''}`} onClick={() => setActiveSection('reportes')} aria-current={activeSection === 'reportes' ? 'page' : undefined}>Reportes</button>
              <button type="button" className={`sidebar-item${activeSection === 'colegio' ? ' is-active' : ''}`} onClick={() => setActiveSection('colegio')} aria-current={activeSection === 'colegio' ? 'page' : undefined}>Colegio de Profesores</button>
            </nav>
            <div className="coord-sidebar-summary"><strong>{datos.resumen.total || 0}</strong><span>expedientes registrados</span><small>{datos.resumen.por_revisar || 0} requieren atención</small></div>
            <button type="button" className="sidebar-logout" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
          </aside>

          <div className="coordinacion-content">
            <div className="coordinacion-main-panel">
              <div className="coordinacion-main-body">
                {activeSection === 'resumen' && (<>
                  <div className="coord-analytics-grid"><div className="panel-card"><h3>Dashboard analítico</h3>{analitica.estados.map(e=><div className="analytics-bar" key={e.key}><div><span>{e.label}</span><strong>{e.count}</strong></div><div className="analytics-track"><i style={{width:`${e.pct}%`}} /></div></div>)}</div><div className="panel-card"><h3>Composición</h3><p>Aspirantes: <b>{analitica.aspirantes}</b></p><p>Alumnos: <b>{analitica.alumnos}</b></p><p>Personal académico: <b>{analitica.personal}</b></p></div></div>
                  <div className="panel-card analytics-pie-card"><h3>Composición del sistema</h3><div className="analytics-pie" style={{background:`conic-gradient(#009b8f 0 ${analitica.total?analitica.aspirantes*100/analitica.total:0}%, #1769aa 0 ${analitica.total?(analitica.aspirantes+analitica.alumnos)*100/analitica.total:0}%, #e09b3d 0 100%)`}}><span>{analitica.total}</span><small>registros</small></div><div className="analytics-legend"><span>Aspirantes: <b>{analitica.aspirantes}</b></span><span>Alumnos: <b>{analitica.alumnos}</b></span><span>Personal: <b>{analitica.personal}</b></span></div></div>
                  <div className="coord-export-actions"><button type="button" className="qa-btn" onClick={()=>descargarReporte('expedientes','xlsx')}>Expedientes XLSX</button><button type="button" className="qa-btn" onClick={()=>descargarReporte('expedientes','pdf')}>Expedientes PDF</button><button type="button" className="qa-btn" onClick={()=>descargarReporte('aspirantes','xlsx')}>Aspirantes XLSX</button><button type="button" className="qa-btn" onClick={()=>descargarReporte('alumnos','xlsx')}>Alumnos XLSX</button></div><div className="aspirante-section-card is-open">
                    <div className="section-panel">
                      <div className="coord-stats"><div className="admin-stat"><span>{datos.resumen.total}</span><small>Solicitudes totales</small></div><div className="admin-stat"><span>{datos.resumen.por_revisar}</span><small>Por revisar</small></div><div className="admin-stat"><span>{datos.resumen.revision}</span><small>En revisión</small></div><div className="admin-stat"><span>{datos.resumen.aceptado}</span><small>Aceptadas</small></div></div>
                    </div>
                  </div>
                  </>)}

            {activeSection === 'periodos' && <div className="periodo-config"><div><p className="panel-kicker">CALENDARIO ACADÉMICO</p><h3>Periodo de inscripción del alumno</h3><p>Define cuándo podrán realizarse las inscripciones y reinscripciones.</p></div>{periodoActual && <div className={`periodo-actual ${periodoActual.activo ? 'is-open' : 'is-closed'}`}><strong>{periodoActual.activo ? 'Periodo vigente' : 'Inscripciones cerradas'}</strong><span>{periodoActual.nombre || 'Sin nombre'} · {periodoActual.apertura ? formatearFecha(periodoActual.apertura) : 'Sin apertura'} — {periodoActual.cierre ? formatearFecha(periodoActual.cierre) : 'Sin cierre'}</span></div>}<div className="coord-form-grid"><input className="coord-search" placeholder="Nombre del periodo" value={periodoForm.nombre} onChange={e=>setPeriodoForm({...periodoForm,nombre:e.target.value})}/><input type="datetime-local" value={periodoForm.apertura} onChange={e=>setPeriodoForm({...periodoForm,apertura:e.target.value})}/><input type="datetime-local" value={periodoForm.cierre} onChange={e=>setPeriodoForm({...periodoForm,cierre:e.target.value})}/><button type="button" className="qa-btn" onClick={crearPeriodo}>Guardar periodo</button></div></div>}
            {activeSection === 'materias' && <div className="panel-card coord-directory coord-materias-card"><div className="admin-card-head"><div><p className="panel-kicker">OFERTA ACADÉMICA</p><h3>Materias y cursos</h3><p>Carga y consulta el catálogo que estará disponible para los alumnos.</p></div><div className="coord-action-row"><button type="button" className="qa-btn" onClick={handleCargarCursosClick}>Cargar cursos CSV</button><input ref={fileInputRef} type="file" accept=".csv" style={{display:'none'}} onChange={handleCargarCursosFile}/><button type="button" className="qa-btn" onClick={cargarMateriasDisponibles} disabled={materiasCargando}>{materiasCargando ? 'Cargando...' : 'Consultar materias'}</button></div></div>{materias ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Clave</th><th>Materia</th><th>Créditos</th><th>Profesor</th><th>Horario</th></tr></thead><tbody>{materias.map(m=><tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.creditos ?? '—'}</td><td>{m.profesor || 'Por asignar'}</td><td>{m.horario || 'Por definir'}</td></tr>)}</tbody></table></div> : <p className="empty-state">Consulta el catálogo para ver las materias cargadas.</p>}</div>}
            {activeSection === 'cargas' && <div className="panel-card coord-directory"><div className="admin-card-head"><div><p className="panel-kicker">FLUJO MULTIETAPA</p><h3>Aprobación de carga académica</h3><p>Envía la carga a Camunda y da seguimiento a la revisión y publicación.</p></div><button type="button" className="qa-btn" onClick={cargarFlujoCargas}>Actualizar</button></div><div className="coord-action-row"><input className="coord-search" placeholder="Periodo escolar (ej. 2026-1)" value={periodoCarga} onChange={e => setPeriodoCarga(e.target.value)} /><button type="button" className="qa-btn" disabled={!periodoCarga.trim()} onClick={crearCargaRevision}>Enviar a revisión</button></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Periodo</th><th>Estado</th><th>Creación</th><th>Camunda</th><th>Acciones</th></tr></thead><tbody>{cargas.length ? cargas.map(c => <tr key={c.id}><td>{c.periodo || 'Sin periodo'}</td><td><span className={`estado-badge estado-${c.estado}`}>{c.estado.replace('_',' ')}</span></td><td>{formatearFecha(c.created_at)}</td><td>{c.camunda_instance_id ? 'Conectada' : 'Pendiente'}</td><td><div className="coord-action-row">{c.estado === 'en_revision' && <><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'aprobada')}>Aprobar</button><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'rechazada')}>Rechazar</button></>}{c.estado === 'aprobada' && <button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'publicada')}>Publicar</button>}</div></td></tr>) : <tr><td colSpan="5">No hay cargas académicas en el flujo.</td></tr>}</tbody></table></div></div>}
            {false && (
              <div className="panel-card coord-directory">
                <div className="admin-card-head"><div><p className="panel-kicker">Flujo multietapa</p><h3>Aprobación de carga académica</h3></div><button type="button" className="qa-btn" onClick={cargarFlujoCargas}>Actualizar</button></div>
                <div className="coord-action-row"><input className="coord-search" placeholder="Periodo escolar (ej. 2026-1)" value={periodoCarga} onChange={e => setPeriodoCarga(e.target.value)} /><button type="button" className="qa-btn" disabled={!periodoCarga.trim()} onClick={crearCargaRevision}>Enviar a revisión</button></div>
                <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Periodo</th><th>Estado</th><th>Creación</th><th>Acciones</th></tr></thead><tbody>{cargas.length ? cargas.map(c => <tr key={c.id}><td>{c.periodo || 'Sin periodo'}</td><td><span className={`estado-badge estado-${c.estado}`}>{c.estado.replace('_',' ')}</span></td><td>{formatearFecha(c.created_at)}</td><td><div className="coord-action-row">{c.estado === 'en_revision' && <><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'aprobada')}>Aprobar</button><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'rechazada')}>Rechazar</button></>}{c.estado === 'aprobada' && <button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'publicada')}>Publicar</button>}</div></td></tr>) : <tr><td colSpan="4">No hay cargas académicas en el flujo.</td></tr>}</tbody></table></div>
                <div className="coord-materias coord-materias-card"><div className="admin-card-head"><div><p className="panel-kicker">Oferta académica</p><h3>Materias y cursos</h3><p>Administra las materias disponibles para el periodo de inscripción.</p></div><div className="coord-action-row"><button type="button" className="qa-btn" onClick={handleGenerarCarga}>Generar carga académica</button><button type="button" className="qa-btn" onClick={handleCargarCursosClick}>Cargar cursos (CSV)</button><input ref={fileInputRef} type="file" accept=".csv" style={{display:'none'}} onChange={handleCargarCursosFile}/><button type="button" className="qa-btn" onClick={cargarMateriasDisponibles} disabled={materiasCargando}>{materiasCargando ? 'Cargando...' : 'Consultar materias'}</button></div></div>{materias ? <table className="admin-table" style={{marginTop:12}}><thead><tr><th>Clave</th><th>Materia</th><th>Créditos</th><th>Profesor</th><th>Horario</th></tr></thead><tbody>{materias.map(m=><tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.creditos ?? '—'}</td><td>{m.profesor || 'Por asignar'}</td><td>{m.horario || 'Por definir'}</td></tr>)}</tbody></table> : <p className="empty-state">Consulta el catálogo para ver las materias cargadas.</p>}</div>
              </div>
            )}

            {['alumnos','aspirantes'].includes(activeSection) && datos && (
              <div className="panel-card coord-directory"><div className="admin-card-head"><div><p className="panel-kicker">Expedientes</p><h3>{activeSection === 'alumnos' ? 'Alumnos' : activeSection === 'aspirantes' ? 'Aspirantes' : 'Docentes y Directores de Tesis'}</h3></div><div className="coord-action-row"><button className="qa-btn" type="button" onClick={() => descargarReporte(activeSection === 'personal' ? 'personal' : activeSection)}>Descargar XLSX</button><button className="qa-btn" type="button" onClick={() => descargarReporte(activeSection === 'personal' ? 'personal' : activeSection, 'pdf')}>Descargar PDF</button></div></div><input className="coord-search" value={busqueda} onChange={e=>setBusqueda(e.target.value)} placeholder="Buscar por nombre, usuario o correo..." /> <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Nombre</th><th>Usuario</th><th>Correo</th><th>Programa / Departamento</th><th>{activeSection === 'personal' ? 'Materias / Tesistas' : 'Estado'}</th></tr></thead><tbody>{filtrarPersonas(activeSection==='alumnos'?alumnos:activeSection==='aspirantes'?(datos.aspirantes||[]):docentes).map(a=><tr key={a.id}><td><strong>{a.nombre}</strong></td><td>{a.usuario}</td><td>{a.correo}</td><td>{a.programa || a.departamento || a.unidad || '—'}</td><td>{activeSection === 'personal' ? <><strong>{a.total_materias || 0} materias</strong><small>{a.total_tesistas || 0} tesistas asignados · {a.horarios?.join(', ') || 'Sin horario'}</small></> : <span className={`estado-badge estado-${a.proceso_estado}`}>{etiquetaEstado(a.proceso_estado)}</span>}</td></tr>)}</tbody></table></div></div>
            )}

            {activeSection === 'personal' && datos && <div className="panel-card coord-directory personal-detail-card"><div className="admin-card-head"><div><p className="panel-kicker">Detalle académico</p><h3>Materias, horarios y tesistas</h3></div><div className="coord-action-row"><button className="qa-btn" type="button" onClick={() => descargarReporte('personal')}>Descargar XLSX</button><button className="qa-btn" type="button" onClick={() => descargarReporte('personal', 'pdf')}>Descargar PDF</button></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Docente / Director</th><th>Departamento</th><th>Materias</th><th>Horarios</th><th>Tesistas</th></tr></thead><tbody>{filtrarPersonas(docentes).map(persona => <tr key={`detalle-${persona.id}`}><td><strong>{persona.nombre}</strong><small>{persona.correo}</small></td><td>{persona.departamento || 'Sin departamento'}</td><td>{persona.total_materias || 0} · {persona.creditos_impartidos || 0} créditos</td><td>{persona.horarios?.join(' · ') || 'Sin horario asignado'}</td><td>{persona.total_tesistas || 0}</td></tr>)}</tbody></table></div></div>}

            {activeSection === 'reportes' && (
              <div className="aspirante-section-card is-open"><div className="section-panel"><div className="panel-card"><h3>Reportes de seguimiento</h3><p>Consulta rápidamente el estado general de los expedientes para priorizar la atención de Coordinación Académica.</p><div className="coord-report-grid"><div><strong>{datos.resumen.total || 0}</strong><span>Total de expedientes</span></div><div><strong>{datos.resumen.por_revisar || 0}</strong><span>Por revisar</span></div><div><strong>{datos.resumen.revision || 0}</strong><span>En revisión</span></div><div><strong>{datos.resumen.aceptado || 0}</strong><span>Aceptados</span></div></div></div></div></div>
            )}

            {activeSection === 'colegio' && (
              <div className="aspirante-section-card is-open"><div className="section-panel"><div className="panel-card"><h3>Evaluación del Colegio de Profesores</h3><p>Registra el dictamen colegiado de cada aspirante y conserva el seguimiento de la decisión.</p><form className="colegio-evaluacion-form" onSubmit={guardarEvaluacionColegio}><label>Aspirante<select value={evaluacionForm.aspirante} onChange={e => setEvaluacionForm({...evaluacionForm, aspirante: e.target.value})}><option value="">Selecciona un aspirante</option>{(datos.aspirantes || []).filter(a => a.rol === 'aspirante').map(a => <option key={a.id} value={a.id}>{a.nombre} — {a.programa || 'Sin programa'}</option>)}</select></label><label>Dictamen<select value={evaluacionForm.estado} onChange={e => setEvaluacionForm({...evaluacionForm, estado: e.target.value})}><option value="en_revision">En revisión</option><option value="favorable">Favorable</option><option value="no_favorable">No favorable</option></select></label><label>Observaciones y dictamen<textarea rows="4" value={evaluacionForm.dictamen} onChange={e => setEvaluacionForm({...evaluacionForm, dictamen: e.target.value})} placeholder="Escribe los acuerdos y observaciones del Colegio..." required /></label><button type="submit" className="qa-btn">{evaluacionForm.id ? 'Actualizar evaluación' : 'Guardar evaluación'}</button>{evaluacionForm.id && <button type="button" className="qa-btn qa-btn-secondary" onClick={() => setEvaluacionForm({aspirante: '', estado: 'en_revision', dictamen: ''})}>Cancelar edición</button>}</form></div><div className="panel-card"><div className="admin-card-head"><div><h3>Evaluaciones registradas</h3><p>Consulta el historial de dictámenes y filtra por etapa.</p></div><select className="coord-filter-select" value={evaluacionFiltro} onChange={e => setEvaluacionFiltro(e.target.value)}><option value="todas">Todas</option><option value="en_revision">En revisión</option><option value="favorable">Favorables</option><option value="no_favorable">No favorables</option></select></div>{evaluacionesVisibles.length ? <div className="colegio-evaluaciones-list">{evaluacionesVisibles.map(e => <article key={e.id}><div><strong>{e.aspirante_nombre || `Aspirante #${e.aspirante}`}</strong><small>{e.evaluador_nombre || 'Evaluador no disponible'} · {e.fecha_evaluacion ? formatearFecha(e.fecha_evaluacion) : 'Sin fecha'}</small><p>{e.dictamen || 'Sin dictamen capturado.'}</p></div><div className="coord-action-row"><span className={`estado-badge estado-${e.estado}`}>{e.estado_label}</span><button type="button" className="qa-btn" onClick={() => setEvaluacionForm({id:e.id, aspirante:e.aspirante, estado:e.estado, dictamen:e.dictamen || ''})}>Editar</button></div></article>)}</div> : <p className="empty-state">No hay evaluaciones para este filtro.</p>}</div></div></div>
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
                        <div className="coord-profile-photo">{seleccionado.profile_photo ? <img src={seleccionado.profile_photo.startsWith('http') ? seleccionado.profile_photo : `http://localhost:8000${seleccionado.profile_photo}`} alt="Foto de perfil" /> : <span>{(seleccionado.nombre || 'A').charAt(0).toUpperCase()}</span>}</div>
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
                                {detalle?.rol === 'aspirante' && <>
                                  <button type="button" className="qa-btn" onClick={() => cambiarEstado('revision')} disabled={actualizando}>Marcar en revisión</button>
                                  <button type="button" className="qa-btn" onClick={() => cambiarEstado('aceptado')} disabled={actualizando}>Aceptar</button>
                                  <button type="button" className="qa-btn" onClick={() => cambiarEstado('rechazado')} disabled={actualizando}>Rechazar</button>
                                </>}
                            {/* Conversion actions: only available once the aspirante is an alumno */}
                            {detalle?.rol === 'aspirante' && detalle?.proceso_estado === 'aceptado' && (
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
                            <div><span>Director de Tesis</span><strong>{detalle.director_tesis_nombre || 'Sin asignar'}</strong></div>
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
                              <label className="coord-field">
                                <span>Director de Tesis</span>
                                <select
                                  value={editData?.director_tesis || ''}
                                  onChange={(event) => handleFieldChange('director_tesis', event.target.value ? Number(event.target.value) : null)}
                                >
                                  <option value="">Sin asignar</option>
                                  {directores.map((director) => <option key={director.id} value={director.id}>{director.nombre} ({director.usuario})</option>)}
                                </select>
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
                  ) : (
                    <div className="empty-state">
                      <h3>Selecciona un expediente</h3>
                      <p>Elige un aspirante, alumno o integrante del personal desde la bandeja o los apartados correspondientes para consultar su información.</p>
                      <button type="button" className="qa-btn" onClick={() => setActiveSection('bandeja')}>Ir a bandeja</button>
                    </div>
                  )}
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
