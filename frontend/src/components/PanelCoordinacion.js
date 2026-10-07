import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import ExpedienteCentralizadoCard from './ExpedienteCentralizadoCard';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import {useCoordinationCopy} from './coordinationPanelTranslations';
import './PanelCoordinacion.css';

const FILTROS = [
  {id: 'todos', key: 'all'},
  {id: 'por-revisar', key: 'review'},
  {id: 'revision', key: 'inReview'},
  {id: 'aceptado', key: 'accepted'},
];

const COORDINATION_NAV = [
  {label: 'overview', items: [['resumen', 'Resumen', '▦'], ['bandeja', 'Bandeja de solicitudes', '◷'], ['detalle', 'Detalle de expediente', '◉']]},
  {label: 'academic', items: [['periodos', 'Periodos de inscripción', '◫'], ['planes', 'Planes de estudio', '▧'], ['materias', 'Materias y cursos', '▤'], ['cargas', 'Aprobación de carga', '↗']]},
  {label: 'research', items: [['tesis', 'Proyectos de tesis', '◆'], ['asignaciones', 'Asignación de directores', '↔'], ['predoctoral', 'Examen predoctoral', '✦'], ['colegio', 'Colegio de Profesores', '◈']]},
  {label: 'community', items: [['alumnos', 'Alumnos', '♙'], ['aspirantes', 'Aspirantes', '◎'], ['personal', 'Docentes y Directores', '◇'], ['reportes', 'Reportes', '▥'], ['perfil', 'Mi perfil', '●']]},
];

function etiquetaEstado(estado, copy) {
  return copy.status[estado] || (estado ? estado.charAt(0).toUpperCase() + estado.slice(1) : copy.status.pendiente);
}

function formatearFecha(valor, locale = document.documentElement.lang || 'es') {
  const pending = {es: 'Pendiente', en: 'Pending', de: 'Ausstehend', zh: '待定', pt: 'Pendente'}[locale] || 'Pendiente';
  if (!valor) return pending;
  try {
    return new Intl.DateTimeFormat(locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(valor));
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

function periodosPredeterminados(grado, periodicidad) {
  const duracionAnios = grado === 'doctorado' ? 4 : 2;
  return duracionAnios * (periodicidad === 'cuatrimestral' ? 3 : 2);
}

function nuevoPlanEstudio() {
  return {
    id: null,
    programa: '',
    grado: 'maestria',
    periodicidad: 'semestral',
    periodos_requeridos: periodosPredeterminados('maestria', 'semestral'),
    creditos_requeridos: 0,
    activo: true,
    materias_plan: [],
  };
}

export default function PanelCoordinacion({session, onLogout: onLogoutProp}) {
  const onLogoutRef = useRef(onLogoutProp);
  onLogoutRef.current = onLogoutProp;
  const onLogout = useCallback((...args) => onLogoutRef.current?.(...args), []);
  const copy = useCoordinationCopy();
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
  const [periodosInscripcion, setPeriodosInscripcion] = useState([]);
  const [periodoForm, setPeriodoForm] = useState({id:null,nombre:'',apertura:'',cierre:'',activo:true});
  const [guardandoPeriodo, setGuardandoPeriodo] = useState(false);
  const [configuracionesPlan, setConfiguracionesPlan] = useState([]);
  const [materiasPlan, setMateriasPlan] = useState([]);
  const [planForm, setPlanForm] = useState(nuevoPlanEstudio);
  const [guardandoPlan, setGuardandoPlan] = useState(false);
  const [ciclosAlumno, setCiclosAlumno] = useState({});
  const [alumnoGuardandoCiclo, setAlumnoGuardandoCiclo] = useState(null);
  const [confirmacionCiclo, setConfirmacionCiclo] = useState('');
  const [proyectosTesis, setProyectosTesis] = useState([]);
  const [examenesPredoctorales, setExamenesPredoctorales] = useState([]);
  const [solicitudesTesis, setSolicitudesTesis] = useState([]);
  const [directoresTesis, setDirectoresTesis] = useState([]);

  const cargarFlujoCargas = useCallback(async () => {
    try {
      const r = await fetch('/api/cargas-academicas/', {headers: {Authorization: `Bearer ${session.access}`}});
      if (r.status === 401) return onLogout(copy.messages.expired);
      if (!r.ok) throw new Error(copy.messages.loadCharges);
      setCargas(await r.json());
    } catch (e) { setError(e.message || copy.messages.loadCharges); }
  }, [copy, onLogout, session.access]);

  async function crearCargaRevision() {
    try {
      const r = await fetch('/api/cargas-academicas/', {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({periodo: periodoCarga})});
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || copy.loads.sendError);
      setSaveSuccess(copy.loads.sent); setPeriodoCarga(''); cargarFlujoCargas();
    } catch (e) { setError(e.message || copy.loads.sendError); }
  }

  async function actualizarEstadoCarga(id, estado) {
    try {
      const r = await fetch(`/api/cargas-academicas/${id}/`, {method: 'PATCH', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({estado})});
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || copy.loads.updateError);
      setSaveSuccess(`${copy.loads.updated} ${etiquetaEstado(estado, copy)}.`); cargarFlujoCargas();
    } catch (e) { setError(e.message || copy.loads.updateError); }
  }
  const cargarProyectosTesis = useCallback(async () => {
    try {
      const r = await fetch('/api/proyectos-tesis/', {headers: {Authorization: `Bearer ${session.access}`}});
      if (!r.ok) throw new Error(copy.messages.loadProjects);
      setProyectosTesis(await r.json());
    } catch (e) { setError(e.message || copy.messages.loadProjects); }
  }, [copy, session.access]);
  async function actualizarProyectoTesis(proyecto, estado) {
    const comentario = window.prompt(copy.thesis.comment, proyecto.comentarios_revision || '');
    if (comentario === null) return;
    const r = await fetch(`/api/proyectos-tesis/${proyecto.id}/`, {method:'PATCH', headers:{'Authorization':`Bearer ${session.access}`,'Content-Type':'application/json'}, body:JSON.stringify({estado, comentarios_revision: comentario})});
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return setError(data.detail || copy.thesis.updateError);
    setProyectosTesis(items => items.map(item => item.id === data.id ? data : item));
    setSaveSuccess(`${copy.thesis.updatedTo} ${etiquetaEstado(data.estado, copy)}.`);
  }
  async function descargarReporte(tipo='expedientes', formato='xlsx') { await downloadBlob(`/api/coordinacion/reportes/?tipo=${tipo}&format=${formato}`, `reporte-${tipo}-${new Date().toISOString().slice(0,10)}.${formato}`); }

  const cargarPanel = useCallback(async (signal) => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/coordinacion/panel/', {headers: {Authorization: `Bearer ${session.access}`}, signal});
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (response.status === 403) throw new Error(copy.messages.noPermission);
      if (!response.ok) throw new Error(copy.messages.loadError);
      const data = await response.json();
      setDatos({...data, personas: data.aspirantes || [], aspirantes: (data.aspirantes || []).filter(persona => persona.rol === 'aspirante')});
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || copy.messages.loadError);
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [copy, onLogout, session.access]);

  const cargarDetalle = useCallback(async (aspiranteId, signal) => {
    setDetalleCargando(true);
    setSaveError('');
    try {
      const response = await fetch(`/api/coordinacion/aspirantes/${aspiranteId}/`, {
        headers: {Authorization: `Bearer ${session.access}`},
        signal,
      });
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (response.status === 403) throw new Error(copy.messages.detailPermission);
      if (!response.ok) throw new Error(copy.messages.detailError);
      const data = await response.json();
      setDetalle(data);
      setEditData(data);
    } catch (err) {
      if (err.name !== 'AbortError') setSaveError(err.message || copy.messages.detailError);
    } finally {
      if (!signal.aborted) setDetalleCargando(false);
    }
  }, [copy, onLogout, session.access]);

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
    fetch('/api/preregistro/evaluaciones-colegio/', {headers: {Authorization: `Bearer ${session.access}`}}).then(r => r.ok ? r.json() : Promise.reject(new Error(copy.messages.loadEvaluations))).then(setEvaluacionesColegio).catch(err => setError(err.message));
  }, [copy, datos, session.access]);

  useEffect(() => { if (['periodos', 'cargas', 'materias'].includes(activeSection)) cargarFlujoCargas(); }, [activeSection, cargarFlujoCargas]);
  useEffect(() => { if (activeSection === 'tesis') cargarProyectosTesis(); }, [activeSection, cargarProyectosTesis]);
  useEffect(() => {
    if (activeSection !== 'asignaciones') return;
    fetch('/api/tesis/flujo/', {headers: {Authorization: `Bearer ${session.access}`}})
      .then(response => response.ok ? response.json() : Promise.reject(new Error(copy.messages.loadAssignments)))
      .then(data => { setSolicitudesTesis(data.solicitudes || []); setDirectoresTesis(data.directores || []); })
      .catch(err => setError(err.message));
  }, [activeSection, copy, session.access]);
  useEffect(() => { if (activeSection !== 'predoctoral') return; fetch('/api/predoctoral/examenes/', {headers: {Authorization: `Bearer ${session.access}`}}).then(r => r.ok ? r.json() : Promise.reject(new Error(copy.messages.loadAssignments))).then(data => setExamenesPredoctorales(data.examenes || [])).catch(err => setError(err.message)); }, [activeSection, copy, session.access]);
  async function actualizarExamenPredoctoral(examen, cambios) { const r = await fetch(`/api/predoctoral/examenes/${examen.id}/`, {method:'PATCH', headers:{'Authorization':`Bearer ${session.access}`,'Content-Type':'application/json'}, body:JSON.stringify(cambios)}); const data = await r.json().catch(()=>({})); if (!r.ok) return setError(data.detail || copy.predoctoral.saveError); setExamenesPredoctorales(items => items.map(item => item.id === data.id ? {...item, ...data} : item)); }
  async function actualizarSolicitudTesis(solicitud, estado, directorId = '') {
    const response = await fetch(`/api/tesis/solicitudes/${solicitud.id}/`, {method: 'PATCH', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({estado, director_asignado: directorId || null})});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) return setError(body.detail || copy.assignments.updateError);
    setSolicitudesTesis(items => items.map(item => item.id === body.id ? body : item));
    setSaveSuccess(`${solicitud.alumno?.nombre || copy.thesis.student}: ${copy.loads.updated}`);
  }
  useEffect(() => {
    if (!['periodos', 'cargas', 'materias'].includes(activeSection)) return;
    const controller = new AbortController();
    fetch('/api/periodos-inscripcion/?todos=1', {headers:{Authorization:`Bearer ${session.access}`}, signal:controller.signal})
      .then(response => {
        if (response.status === 401) {
          onLogout(copy.messages.expired);
          return Promise.reject(Object.assign(new Error(), {name:'AbortError'}));
        }
        return response.ok ? response.json() : Promise.reject(new Error(copy.periods.createError));
      })
      .then(data => {
        const periodos = Array.isArray(data) ? data : [];
        setPeriodosInscripcion(periodos);
        const periodoInicial = periodos.find(periodo => periodo.activo) || periodos[0] || null;
        if (periodoInicial) seleccionarPeriodo(periodoInicial);
        else {
          setPeriodoActual(null);
          setPeriodoForm({id:null,nombre:'',apertura:'',cierre:'',activo:true});
        }
      })
      .catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => controller.abort();
  }, [activeSection, copy.messages.expired, copy.periods.createError, onLogout, session.access]);

  function seleccionarPeriodo(periodo) {
    setPeriodoActual(periodo);
    setPeriodoForm({
      id: periodo.id,
      nombre: periodo.nombre || '',
      apertura: formatoDateTimeLocal(periodo.apertura),
      cierre: formatoDateTimeLocal(periodo.cierre),
      activo: periodo.habilitado ?? periodo.activo,
    });
    setError('');
    setSaveSuccess('');
  }

  function prepararNuevoPeriodo() {
    setPeriodoForm({id:null,nombre:'',apertura:'',cierre:'',activo:true});
    setError('');
    setSaveSuccess('');
  }

  async function guardarPeriodoInscripcion(event) {
    event.preventDefault();
    if (guardandoPeriodo) return;
    const nombre = periodoForm.nombre.trim();
    if (!nombre) {
      setError(copy.periods.nameRequired);
      setSaveSuccess('');
      return;
    }
    if (!periodoForm.apertura || !periodoForm.cierre || periodoForm.apertura >= periodoForm.cierre) {
      setError(copy.periods.invalidRange);
      setSaveSuccess('');
      return;
    }
    const editando = Boolean(periodoForm.id);
    setGuardandoPeriodo(true);
    setError('');
    setSaveSuccess('');
    try {
      const response = await fetch('/api/periodos-inscripcion/', {
        method: editando ? 'PUT' : 'POST',
        headers: {'Authorization':`Bearer ${session.access}`,'Content-Type':'application/json'},
        body: JSON.stringify({...periodoForm, nombre}),
      });
      if (response.status === 401) return onLogout(copy.messages.expired);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = data.detail || data.error || Object.values(data)
          .flat()
          .find(value => typeof value === 'string');
        throw new Error(detail || copy.periods.createError);
      }
      setPeriodoActual(data);
      setPeriodosInscripcion(previous => previous.some(periodo => periodo.id === data.id)
        ? previous.map(periodo => periodo.id === data.id ? data : periodo)
        : [data, ...previous]);
      setPeriodoForm({id:data.id,nombre:data.nombre,apertura:formatoDateTimeLocal(data.apertura),cierre:formatoDateTimeLocal(data.cierre),activo:data.habilitado ?? data.activo});
      setSaveSuccess(editando ? copy.periods.updated : copy.periods.saved);
      setError('');
    } catch (error) {
      setError(error.message || copy.periods.createError);
    } finally {
      setGuardandoPeriodo(false);
    }
  }

  useEffect(() => {
    if (activeSection !== 'planes') return;
    const controller = new AbortController();
    fetch('/api/tesis/flujo/', {headers:{Authorization:`Bearer ${session.access}`}, signal:controller.signal})
      .then(response => {
        if (response.status === 401) {
          onLogout(copy.messages.expired);
          return Promise.reject(Object.assign(new Error(), {name:'AbortError'}));
        }
        return response.ok ? response.json() : Promise.reject(new Error(copy.plans.loadError));
      })
      .then(data => {
        const configuraciones = data.configuraciones || [];
        setConfiguracionesPlan(configuraciones);
        setMateriasPlan(data.materias || []);
        if (configuraciones.length) seleccionarPlan(configuraciones[0]);
        else setPlanForm(nuevoPlanEstudio());
      })
      .catch(error => {if (error.name !== 'AbortError') setError(error.message || copy.plans.loadError);});
    return () => controller.abort();
  }, [activeSection, copy.messages.expired, copy.plans.loadError, onLogout, session.access]);

  function seleccionarPlan(configuracion) {
    setPlanForm({
      id: configuracion.id,
      programa: configuracion.programa || '',
      grado: configuracion.grado || 'maestria',
      periodicidad: configuracion.periodicidad || 'semestral',
      periodos_requeridos: configuracion.periodos_requeridos || 1,
      creditos_requeridos: configuracion.creditos_requeridos || 0,
      activo: Boolean(configuracion.activo),
      materias_plan: (configuracion.materias_plan || []).map(item => ({...item, slotId:`existing-${item.id}`})),
    });
    setError('');
    setSaveSuccess('');
  }

  function prepararNuevoPlan() {
    setPlanForm(nuevoPlanEstudio());
    setError('');
    setSaveSuccess('');
  }

  function actualizarDuracionPlan(cambios) {
    setPlanForm(current => {
      const nuevoGrado = cambios.grado || current.grado;
      const nuevaPeriodicidad = cambios.periodicidad || current.periodicidad;
      const periodoPredeterminadoActual = periodosPredeterminados(current.grado, current.periodicidad);
      const periodoPredeterminadoNuevo = periodosPredeterminados(nuevoGrado, nuevaPeriodicidad);
      const periodosRequeridos = Number(current.periodos_requeridos) === periodoPredeterminadoActual
        ? periodoPredeterminadoNuevo
        : Number(current.periodos_requeridos);
      return {
        ...current,
        ...cambios,
        periodos_requeridos: periodosRequeridos,
        materias_plan: current.materias_plan.filter(item => Number(item.periodo_sugerido) <= periodosRequeridos),
      };
    });
  }

  function generarMateriasMinimasPlan() {
    setPlanForm(current => {
      const rows = [...current.materias_plan];
      const periodos = Math.max(1, Number(current.periodos_requeridos) || 1);
      for (let period = 1; period <= periodos; period += 1) {
        const rowsInPeriod = rows.filter(item => Number(item.periodo_sugerido) === period).length;
        for (let index = rowsInPeriod; index < 4; index += 1) {
          rows.push({slotId:`new-${period}-${index}-${Date.now()}-${Math.random()}`,materia:'',periodo_sugerido:period,obligatoria:true});
        }
      }
      return {...current,materias_plan:rows};
    });
  }

  function actualizarMateriaPlan(slotId, cambios) {
    setPlanForm(current => ({...current,materias_plan:current.materias_plan.map(item => item.slotId === slotId ? {...item,...cambios} : item)}));
  }

  async function guardarPlanEstudio(event) {
    event.preventDefault();
    if (guardandoPlan) return;
    setError('');
    setSaveSuccess('');
    const periodos = Number(planForm.periodos_requeridos);
    const filas = planForm.materias_plan.filter(item => item.materia !== '' && item.materia != null);
    if (!planForm.programa.trim()) return setError(copy.plans.programRequired);
    if (!periodos || periodos < 1) return setError(copy.plans.periodsRequired);
    if (new Set(filas.map(item => Number(item.materia))).size !== filas.length) return setError(copy.plans.duplicateCourse);
    const counts = Array.from({length:periodos}, (_, index) => filas.filter(item => Number(item.periodo_sugerido) === index + 1).length);
    if (counts.some(count => count < 4)) return setError(copy.plans.minimumFour);
    setGuardandoPlan(true);
    try {
      const response = await fetch('/api/tesis/flujo/', {
        method:'POST',
        headers:{Authorization:`Bearer ${session.access}`,'Content-Type':'application/json'},
        body:JSON.stringify({...planForm,periodos_requeridos:periodos,creditos_requeridos:Number(planForm.creditos_requeridos)||0,materias_plan:filas.map(({materia,periodo_sugerido,obligatoria})=>({materia:Number(materia),periodo_sugerido:Number(periodo_sugerido),obligatoria:Boolean(obligatoria)}))}),
      });
      if (response.status === 401) return onLogout(copy.messages.expired);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || copy.plans.saveError);
      setConfiguracionesPlan(current => current.some(item => item.id === data.id)
        ? current.map(item => item.id === data.id ? data : item)
        : [...current,data].sort((a,b)=>a.programa.localeCompare(b.programa)));
      seleccionarPlan(data);
      setSaveSuccess(copy.plans.saved);
    } catch (error) {
      setError(error.message || copy.plans.saveError);
    } finally {
      setGuardandoPlan(false);
    }
  }
  async function guardarCicloAlumno(alumno) {
    if (alumnoGuardandoCiclo === alumno.id) return;
    const value = Number(ciclosAlumno[alumno.id] ?? alumno.numero_periodo_actual);
    if (!Number.isInteger(value) || value < 1) {
      setConfirmacionCiclo('');
      setError(copy.periods.number);
      return;
    }
    setAlumnoGuardandoCiclo(alumno.id);
    setConfirmacionCiclo('');
    setError('');
    try {
      const response = await fetch(`/api/coordinacion/aspirantes/${alumno.id}/`, {
        method: 'PATCH',
        headers: {Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({numero_periodo_actual: value}),
      });
      if (response.status === 401) {
        onLogout(copy.messages.expired);
        return;
      }
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.numero_periodo_actual?.[0] || data.detail || copy.messages.detailError);
      }
      setDatos(current => current
        ? {...current, personas: current.personas.map(item => item.id === alumno.id ? {...item, ...data} : item)}
        : current);
      setCiclosAlumno(current => ({...current, [alumno.id]: String(data.numero_periodo_actual)}));
      setConfirmacionCiclo(`${copy.directory.savedCycle} ${alumno.nombre} (${copy.directory.term.toLowerCase()} ${data.numero_periodo_actual}).`);
    } catch (error) {
      setError(error.message || copy.messages.detailError);
    } finally {
      setAlumnoGuardandoCiclo(null);
    }
  }

  async function guardarEvaluacionColegio(event) {
    event.preventDefault();
    if (!evaluacionForm.aspirante || !evaluacionForm.dictamen.trim()) return setError(copy.college.selectDecision);
    const editando = Boolean(evaluacionForm.id);
    const response = await fetch(editando ? `/api/preregistro/evaluaciones-colegio/${evaluacionForm.id}/` : '/api/preregistro/evaluaciones-colegio/', {method: editando ? 'PATCH' : 'POST', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify(evaluacionForm)});
    const data = await response.json();
    if (!response.ok) return setError(data.detail || data.aspirante || copy.college.saveError);
    setEvaluacionesColegio(items => editando ? items.map(item => item.id === data.id ? data : item) : [data, ...items]); setEvaluacionForm({aspirante: '', estado: 'en_revision', dictamen: ''}); setSaveSuccess(editando ? copy.college.updated : copy.college.saved); setError('');
  }

  const aspirantesRegistrados = useMemo(() => (datos?.aspirantes || []).filter((aspirante) => aspirante.rol === 'aspirante'), [datos]);
  const aspirantes = useMemo(() => aspirantesRegistrados.filter((aspirante) => {
    if (filtro === 'por-revisar') return ['pendiente', 'iniciado'].includes(aspirante.proceso_estado);
    return filtro === 'todos' || aspirante.proceso_estado === filtro;
  }), [aspirantesRegistrados, filtro]);
  const alumnos = useMemo(() => (datos?.personas || []).filter(a => a.rol === 'alumno'), [datos]);
  const docentes = useMemo(() => (datos?.personas || []).filter(a => ['docente','director'].includes(a.rol)), [datos]);
  const directores = useMemo(() => (datos?.personas || []).filter(a => a.rol === 'director' && a.is_active !== false), [datos]);
  const filtrarPersonas = (lista) => lista.filter(a => !busqueda.trim() || `${a.nombre} ${a.usuario} ${a.correo}`.toLowerCase().includes(busqueda.toLowerCase()));
  const analitica = useMemo(() => { const lista=datos?.personas||[]; const total=lista.length||1; const estados=['pendiente','revision','aceptado','rechazado']; return {total:lista.length, aspirantes:lista.filter(a=>a.rol==='aspirante').length, alumnos:lista.filter(a=>a.rol==='alumno').length, personal:lista.filter(a=>['docente','director'].includes(a.rol)).length, estados:estados.map(e=>({key:e,label:etiquetaEstado(e, copy),count:lista.filter(a=>a.rol==='aspirante'&&a.proceso_estado===e).length,pct:Math.round(lista.filter(a=>a.rol==='aspirante'&&a.proceso_estado===e).length*100/Math.max(1,lista.filter(a=>a.rol==='aspirante').length))}))}; }, [copy, datos]);
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
        throw new Error(data.detail || copy.detail.saveError);
      }
      const actualizado = await response.json();
      setDetalle(actualizado);
      setEditData(actualizado);
      setSaveSuccess(copy.detail.saved);
      setDatos((actual) => ({...actual, aspirantes: actual.aspirantes.map((aspirante) => aspirante.id === actualizado.id ? actualizado : aspirante)}));
      setSeleccionado(actualizado);
    } catch (err) {
      setSaveError(err.message || copy.detail.saveError);
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
      if (!response.ok) throw new Error(copy.detail.updateError);
      const actualizado = await response.json();
      setDatos((actual) => ({...actual, aspirantes: actual.aspirantes.map((aspirante) => aspirante.id === actualizado.id ? actualizado : aspirante)}));
      setSeleccionado(actualizado);
      setDetalle(actualizado);
      setEditData(actualizado);
    } catch (err) {
      setError(err.message || copy.detail.updateError);
    } finally {
      setActualizando(false);
    }
  }

  // Helper to download generated PDF/XLSX files
  async function downloadBlob(url, filename) {
    try {
      const resp = await fetch(url, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!resp.ok) throw new Error(copy.detail.downloadError);
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
      setError(err.message || copy.detail.downloadError);
    }
  }

  async function handleDescargarCalificaciones() {
    if (!detalle) return setError(copy.detail.selectApplicant);
    await downloadBlob(`/api/coordinacion/aspirantes/${detalle.id}/calificaciones/?format=pdf`, `${detalle.usuario || detalle.curp || detalle.id}-calificaciones.pdf`);
  }

  async function handleDescargarAdscripcion() {
    if (!detalle) return setError(copy.detail.selectApplicant);
    await downloadBlob(`/api/coordinacion/aspirantes/${detalle.id}/adscripcion/download/`, `${detalle.usuario || detalle.curp || detalle.id}-adscripcion.pdf`);
  }

  async function handleDarBaja() {
    if (!seleccionado) return setError(copy.detail.selectApplicant);
    if (!confirm(copy.detail.confirmDrop)) return;
    try {
      const resp = await fetch(`/api/coordinacion/aspirantes/${seleccionado.id}/dar_baja/`, {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`}});
      if (!resp.ok) throw new Error(copy.detail.dropoutError);
      setSaveSuccess(copy.detail.dropped);
      // refresh panel
      cargarPanel(new AbortController().signal);
    } catch (err) {
      setError(err.message || copy.detail.dropoutError);
    }
  }

  async function handleGenerarCarga() {
    try {
      const resp = await fetch('/api/coordinacion/cargas/generar/', {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`}});
      if (!resp.ok) throw new Error(copy.loads.sendError);
      const blob = await resp.blob();
      const urlBlob = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = urlBlob;
      a.download = `carga_academica_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a); a.click(); a.remove(); window.URL.revokeObjectURL(urlBlob);
      setSaveSuccess(copy.loads.generated);
    } catch (err) {
      setError(err.message || copy.loads.sendError);
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
      if (!resp.ok) throw new Error(copy.subjects.uploadError);
      const data = await resp.json();
      setSaveSuccess(data.detail || copy.subjects.uploaded);
      cargarMateriasDisponibles();
    } catch (err) {
      setError(err.message || copy.subjects.uploadError);
    } finally {
      event.target.value = '';
    }
  }

  async function cargarMateriasDisponibles() {
    setMateriasCargando(true);
    try {
      const resp = await fetch('/api/coordinacion/materias/', {headers: {Authorization: `Bearer ${session.access}`}});
      if (!resp.ok) throw new Error(copy.subjects.noSubjects);
      setMaterias(await resp.json());
    } catch (err) {
      setError(err.message || copy.subjects.noSubjects);
    } finally {
      setMateriasCargando(false);
    }
  }

  return (
    <section className="panel-section" aria-label={copy.panel}>
      <div className="panel-hero">
        <div>
          <p className="panel-kicker">{copy.panel}</p>
          <h1>{copy.title}</h1>
          <p className="panel-sub">{copy.subtitle}</p>
        </div>
        <button type="button" className="btn-outline-danger" onClick={() => onLogout(copy.logout)}>{copy.logout}</button>
      </div>
      {error && <div className="api-error" role="alert">{error}</div>}
      {cargando && !datos && <div className="panel-card">{copy.loading}</div>}
      {datos && (
        <div className="coordinacion-layout">
          <aside className="coordinacion-sidebar" aria-label={copy.title}>
            <div className="coord-nav-brand">
              <span>{datos.usuario?.profile_photo ? <img style={{width: '100%', height: '100%', objectFit: 'cover', borderRadius: 'inherit'}} src={fotoUrl(datos.usuario.profile_photo)} alt="Profile photo" /> : 'CA'}</span><div><small>{copy.profile.operations}</small><h2>{copy.profile.brand}</h2></div>
            </div>
            <nav className="coordinacion-sidebar-nav">
              {COORDINATION_NAV.map(group => <div className="coord-nav-group" key={group.label}><p>{copy.groups[group.label]}</p>{group.items.map(([id, , icon]) => <button type="button" key={id} className={`sidebar-item${activeSection === id ? ' is-active' : ''}`} onClick={() => setActiveSection(id)} aria-current={activeSection === id ? 'page' : undefined}><i aria-hidden="true">{icon}</i><span>{copy.nav[id]}</span>{id === 'bandeja' && <b>{datos.resumen.por_revisar || 0}</b>}</button>)}</div>)}
            </nav>
            <div className="coord-sidebar-summary"><strong>{datos.resumen.total || 0}</strong><span>{copy.profile.summary}</span><small>{datos.resumen.por_revisar || 0} {copy.profile.attention}</small></div>
            <button type="button" className="sidebar-logout" onClick={() => onLogout(copy.logout)}>{copy.logout}</button>
          </aside>

          <div className="coordinacion-content">
            <div className="coordinacion-main-panel">
              <div className="coordinacion-main-body">
                {activeSection === 'resumen' && (<>
                  <div className="coord-analytics-grid"><div className="panel-card"><h3>{copy.summary.dashboard}</h3>{analitica.estados.map(e=><div className="analytics-bar" key={e.key}><div><span>{e.label}</span><strong>{e.count}</strong></div><div className="analytics-track"><i style={{width:`${e.pct}%`}} /></div></div>)}</div><div className="panel-card"><h3>{copy.summary.composition}</h3><p>{copy.summary.applicants}: <b>{analitica.aspirantes}</b></p><p>{copy.summary.students}: <b>{analitica.alumnos}</b></p><p>{copy.summary.staff}: <b>{analitica.personal}</b></p></div></div>
                  <div className="panel-card analytics-pie-card"><h3>{copy.summary.system}</h3><div className="analytics-pie" style={{background:`conic-gradient(#009b8f 0 ${analitica.total?analitica.aspirantes*100/analitica.total:0}%, #1769aa 0 ${analitica.total?(analitica.aspirantes+analitica.alumnos)*100/analitica.total:0}%, #e09b3d 0 100%)`}}><span>{analitica.total}</span><small>{copy.summary.records}</small></div><div className="analytics-legend"><span>{copy.summary.applicants}: <b>{analitica.aspirantes}</b></span><span>{copy.summary.students}: <b>{analitica.alumnos}</b></span><span>{copy.summary.staff}: <b>{analitica.personal}</b></span></div></div>
                  <div className="coord-export-actions"><button type="button" className="qa-btn" onClick={()=>descargarReporte('expedientes','xlsx')}>{copy.reports.files} XLSX</button><button type="button" className="qa-btn" onClick={()=>descargarReporte('expedientes','pdf')}>{copy.reports.files} PDF</button><button type="button" className="qa-btn" onClick={()=>descargarReporte('aspirantes','xlsx')}>{copy.summary.applicantsXlsx}</button><button type="button" className="qa-btn" onClick={()=>descargarReporte('alumnos','xlsx')}>{copy.summary.studentsXlsx}</button></div><div className="aspirante-section-card is-open">
                    <div className="section-panel">
                      <div className="coord-stats"><div className="admin-stat"><span>{datos.resumen.total}</span><small>{copy.summary.totalRequests}</small></div><div className="admin-stat"><span>{datos.resumen.por_revisar}</span><small>{copy.summary.review}</small></div><div className="admin-stat"><span>{datos.resumen.revision}</span><small>{copy.summary.inReview}</small></div><div className="admin-stat"><span>{datos.resumen.aceptado}</span><small>{copy.summary.accepted}</small></div></div>
                    </div>
                  </div>
                  </>)}

            {activeSection === 'periodos' && (
              <section className="periodo-config" aria-labelledby="periodo-title">
                <header className="periodo-config-heading">
                  <div>
                    <p className="panel-kicker">{copy.periods.kicker}</p>
                    <h3 id="periodo-title">{copy.periods.title}</h3>
                    <p>{copy.periods.intro}</p>
                  </div>
                  {periodoForm.id && <button type="button" className="qa-btn qa-btn-secondary" disabled={guardandoPeriodo} onClick={prepararNuevoPeriodo}>{copy.periods.createNew}</button>}
                </header>
                {periodosInscripcion.length > 0 && (
                  <label className="periodo-existing-select">
                    <span>{copy.periods.selectExisting}</span>
                    <select value={periodoForm.id || ''} disabled={guardandoPeriodo} onChange={event => {
                      const selectedPeriod = periodosInscripcion.find(periodo => String(periodo.id) === event.target.value);
                      if (selectedPeriod) seleccionarPeriodo(selectedPeriod);
                      else prepararNuevoPeriodo();
                    }}>
                      <option value="">{copy.periods.createNew}</option>
                      {periodosInscripcion.map(periodo => <option key={periodo.id} value={periodo.id}>{periodo.nombre || copy.periods.noName} · {formatearFecha(periodo.apertura, copy.locale)}</option>)}
                    </select>
                  </label>
                )}
                {periodoActual?.id && (
                  <div className={`periodo-actual ${periodoActual.activo ? 'is-open' : 'is-closed'}`}>
                    <strong>{periodoActual.activo ? copy.periods.current : periodoActual.habilitado ? copy.periods.scheduled : copy.periods.closed}</strong>
                    <span>{periodoActual.nombre || copy.periods.noName} · {periodoActual.apertura ? formatearFecha(periodoActual.apertura, copy.locale) : copy.periods.noOpen} — {periodoActual.cierre ? formatearFecha(periodoActual.cierre, copy.locale) : copy.periods.noClose}</span>
                  </div>
                )}
                <form className="periodo-form-grid" onSubmit={guardarPeriodoInscripcion}>
                  <label><span>{copy.periods.name}</span><input value={periodoForm.nombre} disabled={guardandoPeriodo} onChange={event => setPeriodoForm({...periodoForm,nombre:event.target.value})} required maxLength="40" /></label>
                  <label><span>{copy.periods.opening}</span><input type="datetime-local" value={periodoForm.apertura} disabled={guardandoPeriodo} onChange={event => setPeriodoForm({...periodoForm,apertura:event.target.value})} required /></label>
                  <label><span>{copy.periods.closing}</span><input type="datetime-local" value={periodoForm.cierre} disabled={guardandoPeriodo} onChange={event => setPeriodoForm({...periodoForm,cierre:event.target.value})} required /></label>
                  <label><span>{copy.periods.enabled}</span><select value={periodoForm.activo ? 'true' : 'false'} disabled={guardandoPeriodo} onChange={event => setPeriodoForm({...periodoForm,activo:event.target.value === 'true'})}><option value="true">{copy.periods.yes}</option><option value="false">{copy.periods.no}</option></select></label>
                  <div className="periodo-form-actions"><button type="submit" className="qa-btn" disabled={guardandoPeriodo}>{guardandoPeriodo ? copy.periods.saving : periodoForm.id ? copy.periods.update : copy.periods.save}</button>{periodoForm.id && <button type="button" className="qa-btn qa-btn-secondary" disabled={guardandoPeriodo} onClick={() => seleccionarPeriodo(periodoActual)}>{copy.periods.reset}</button>}</div>
                </form>
                {saveSuccess && <div className="api-success periodo-save-success" role="status" aria-live="polite">{saveSuccess}</div>}
              </section>
            )}
            {activeSection === 'planes' && (
              <section className="panel-card coord-directory coord-plan-panel">
                <header className="admin-card-head">
                  <div>
                    <p className="panel-kicker">{copy.plans.title}</p>
                    <h3>{copy.plans.intro}</h3>
                  </div>
                  <button type="button" className="qa-btn" onClick={prepararNuevoPlan}>{copy.plans.new}</button>
                </header>
                {configuracionesPlan.length > 0 && (
                  <label className="coord-plan-existing">
                    <span>{copy.plans.choose}</span>
                    <select value={planForm.id || ''} onChange={event => {
                      const plan = configuracionesPlan.find(item => String(item.id) === event.target.value);
                      if (plan) seleccionarPlan(plan);
                      else prepararNuevoPlan();
                    }}>
                      <option value="">{copy.plans.new}</option>
                      {configuracionesPlan.map(plan => <option value={plan.id} key={plan.id}>{plan.programa} · {plan.grado_label} ({plan.materias_plan?.length || 0})</option>)}
                    </select>
                  </label>
                )}
                {materiasPlan.length === 0 && <p className="coord-plan-notice">{copy.plans.catalogEmpty}</p>}
                {configuracionesPlan.length === 0 && <p className="coord-plan-notice">{copy.plans.noPlans}</p>}
                <form className="coord-plan-form" onSubmit={guardarPlanEstudio}>
                  <div className="coord-plan-fields">
                    <label><span>{copy.plans.program}</span><input value={planForm.programa} disabled={guardandoPlan} maxLength="180" required onChange={event => setPlanForm({...planForm,programa:event.target.value})}/></label>
                    <label><span>{copy.plans.degree}</span><select value={planForm.grado} disabled={guardandoPlan} onChange={event => actualizarDuracionPlan({grado:event.target.value})}><option value="maestria">{copy.plans.masters}</option><option value="doctorado">{copy.plans.doctorate}</option></select></label>
                    <label><span>{copy.plans.periodicity}</span><select value={planForm.periodicidad} disabled={guardandoPlan} onChange={event => actualizarDuracionPlan({periodicidad:event.target.value})}><option value="semestral">{copy.plans.semesters}</option><option value="cuatrimestral">{copy.plans.quarters}</option></select></label>
                    <label><span>{copy.plans.periods}</span><input type="number" min="1" max="24" value={planForm.periodos_requeridos} disabled={guardandoPlan} required onChange={event => {
                      const periodos = Number(event.target.value);
                      setPlanForm(current => ({...current,periodos_requeridos:periodos,materias_plan:current.materias_plan.filter(item => Number(item.periodo_sugerido) <= periodos)}));
                    }}/></label>
                    <label><span>{copy.plans.credits}</span><input type="number" min="0" value={planForm.creditos_requeridos} disabled={guardandoPlan} onChange={event => setPlanForm({...planForm,creditos_requeridos:Number(event.target.value)})}/></label>
                    <label><span>{copy.plans.active}</span><select value={planForm.activo ? 'true' : 'false'} disabled={guardandoPlan} onChange={event => setPlanForm({...planForm,activo:event.target.value === 'true'})}><option value="true">{copy.periods.yes}</option><option value="false">{copy.periods.no}</option></select></label>
                  </div>
                  <div className="coord-plan-course-heading">
                    <div><h4>{copy.plans.courses}</h4><p>{copy.plans.minimumFour}</p></div>
                    <button type="button" className="qa-btn qa-btn-secondary" disabled={guardandoPlan || materiasPlan.length === 0} onClick={generarMateriasMinimasPlan}>{copy.plans.generateSlots}</button>
                  </div>
                  {planForm.materias_plan.length > 0 && (
                    <div className="coord-plan-course-list">
                      {planForm.materias_plan.map((item,index) => (
                        <div className="coord-plan-course-row" key={item.slotId || item.id || index}>
                          <label><span>{copy.plans.course}</span><select value={item.materia || ''} disabled={guardandoPlan} onChange={event => actualizarMateriaPlan(item.slotId, {materia:event.target.value})}>
                            <option value="">{copy.subjects.subject}</option>
                            {materiasPlan.map(materia => {
                              const usada = planForm.materias_plan.some((other,otherIndex) => otherIndex !== index && Number(other.materia) === materia.id);
                              return <option key={materia.id} value={materia.id} disabled={usada}>{materia.clave} · {materia.nombre}</option>;
                            })}
                          </select></label>
                          <label><span>{copy.plans.suggestedPeriod}</span><select value={item.periodo_sugerido || 1} disabled={guardandoPlan} onChange={event => actualizarMateriaPlan(item.slotId, {periodo_sugerido:Number(event.target.value)})}>
                            {Array.from({length:Math.max(1,Number(planForm.periodos_requeridos)||1)},(_,periodIndex)=><option key={periodIndex+1} value={periodIndex+1}>{periodIndex+1}</option>)}
                          </select></label>
                          <label className="coord-plan-required"><input type="checkbox" checked={Boolean(item.obligatoria)} disabled={guardandoPlan} onChange={event => actualizarMateriaPlan(item.slotId, {obligatoria:event.target.checked})}/><span>{copy.plans.mandatory}</span></label>
                          <button type="button" className="qa-btn qa-btn-secondary" disabled={guardandoPlan} onClick={() => setPlanForm(current => ({...current,materias_plan:current.materias_plan.filter((_,rowIndex)=>rowIndex!==index)}))}>{copy.plans.remove}</button>
                        </div>
                      ))}
                    </div>
                  )}
                  <footer className="coord-plan-footer">
                    <button type="button" className="qa-btn qa-btn-secondary" disabled={guardandoPlan || materiasPlan.length === 0} onClick={() => setPlanForm(current => ({...current,materias_plan:[...current.materias_plan,{slotId:`manual-${Date.now()}-${Math.random()}`,materia:'',periodo_sugerido:1,obligatoria:true}]}))}>{copy.plans.addCourse}</button>
                    <button type="submit" className="qa-btn" disabled={guardandoPlan || materiasPlan.length === 0}>{guardandoPlan ? copy.plans.saving : copy.plans.save}</button>
                  </footer>
                </form>
                {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}
              </section>
            )}
            {activeSection === 'materias' && <div className="panel-card coord-directory coord-materias-card"><div className="admin-card-head"><div><p className="panel-kicker">{copy.subjects.kicker}</p><h3>{copy.subjects.title}</h3><p>{copy.subjects.intro}</p></div><div className="coord-action-row"><button type="button" className="qa-btn" onClick={handleCargarCursosClick}>{copy.subjects.upload}</button><input ref={fileInputRef} type="file" accept=".csv" style={{display:'none'}} onChange={handleCargarCursosFile}/><button type="button" className="qa-btn" onClick={cargarMateriasDisponibles} disabled={materiasCargando}>{materiasCargando ? copy.subjects.loading : copy.subjects.query}</button></div></div>{materias ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.subjects.key}</th><th>{copy.subjects.subject}</th><th>{copy.subjects.credits}</th><th>{copy.subjects.teacher}</th><th>{copy.subjects.schedule}</th></tr></thead><tbody>{materias.map(m=><tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.creditos ?? '—'}</td><td>{m.profesor || copy.subjects.assign}</td><td>{m.horario || copy.subjects.define}</td></tr>)}</tbody></table></div> : <p className="empty-state">{copy.subjects.noCatalog}</p>}</div>}
            {activeSection === 'cargas' && <div className="panel-card coord-directory"><div className="admin-card-head"><div><p className="panel-kicker">{copy.loads.kicker}</p><h3>{copy.loads.title}</h3><p>{copy.loads.intro}</p></div><button type="button" className="qa-btn" onClick={cargarFlujoCargas}>{copy.refresh}</button></div><div className="coord-action-row"><input className="coord-search" placeholder={copy.loads.example} value={periodoCarga} onChange={e => setPeriodoCarga(e.target.value)} /><button type="button" className="qa-btn" disabled={!periodoCarga.trim()} onClick={crearCargaRevision}>{copy.loads.send}</button></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.loads.period}</th><th>{copy.detail.state}</th><th>{copy.loads.created}</th><th>{copy.loads.camunda}</th><th>{copy.loads.actions}</th></tr></thead><tbody>{cargas.length ? cargas.map(c => <tr key={c.id}><td>{c.periodo || '—'}</td><td><span className={`estado-badge estado-${c.estado}`}>{etiquetaEstado(c.estado, copy)}</span></td><td>{formatearFecha(c.created_at, copy.locale)}</td><td>{c.camunda_instance_id ? copy.loads.connected : copy.loads.pending}</td><td><div className="coord-action-row">{c.estado === 'en_revision' && <><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'aprobada')}>{copy.loads.approve}</button><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'rechazada')}>{copy.loads.reject}</button></>}{c.estado === 'aprobada' && <button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'publicada')}>{copy.loads.publish}</button>}</div></td></tr>) : <tr><td colSpan="5">{copy.loads.noLoads}</td></tr>}</tbody></table></div></div>}
            {false && (
              <div className="panel-card coord-directory">
                <div className="admin-card-head"><div><p className="panel-kicker">Flujo multietapa</p><h3>Aprobación de carga académica</h3></div><button type="button" className="qa-btn" onClick={cargarFlujoCargas}>Actualizar</button></div>
                <div className="coord-action-row"><input className="coord-search" placeholder="Periodo escolar (ej. 2026-1)" value={periodoCarga} onChange={e => setPeriodoCarga(e.target.value)} /><button type="button" className="qa-btn" disabled={!periodoCarga.trim()} onClick={crearCargaRevision}>Enviar a revisión</button></div>
                <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Periodo</th><th>Estado</th><th>Creación</th><th>Acciones</th></tr></thead><tbody>{cargas.length ? cargas.map(c => <tr key={c.id}><td>{c.periodo || 'Sin periodo'}</td><td><span className={`estado-badge estado-${c.estado}`}>{c.estado.replace('_',' ')}</span></td><td>{formatearFecha(c.created_at)}</td><td><div className="coord-action-row">{c.estado === 'en_revision' && <><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'aprobada')}>Aprobar</button><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'rechazada')}>Rechazar</button></>}{c.estado === 'aprobada' && <button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id,'publicada')}>Publicar</button>}</div></td></tr>) : <tr><td colSpan="4">No hay cargas académicas en el flujo.</td></tr>}</tbody></table></div>
                <div className="coord-materias coord-materias-card"><div className="admin-card-head"><div><p className="panel-kicker">Oferta académica</p><h3>Materias y cursos</h3><p>Administra las materias disponibles para el periodo de inscripción.</p></div><div className="coord-action-row"><button type="button" className="qa-btn" onClick={handleGenerarCarga}>Generar carga académica</button><button type="button" className="qa-btn" onClick={handleCargarCursosClick}>Cargar cursos (CSV)</button><input ref={fileInputRef} type="file" accept=".csv" style={{display:'none'}} onChange={handleCargarCursosFile}/><button type="button" className="qa-btn" onClick={cargarMateriasDisponibles} disabled={materiasCargando}>{materiasCargando ? 'Cargando...' : 'Consultar materias'}</button></div></div>{materias ? <table className="admin-table" style={{marginTop:12}}><thead><tr><th>Clave</th><th>Materia</th><th>Créditos</th><th>Profesor</th><th>Horario</th></tr></thead><tbody>{materias.map(m=><tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.creditos ?? '—'}</td><td>{m.profesor || 'Por asignar'}</td><td>{m.horario || 'Por definir'}</td></tr>)}</tbody></table> : <p className="empty-state">Consulta el catálogo para ver las materias cargadas.</p>}</div>
              </div>
            )}

            {['alumnos','aspirantes'].includes(activeSection) && datos && (
              <div className="panel-card coord-directory">
                <div className="admin-card-head">
                  <div><p className="panel-kicker">{copy.detail.title}</p><h3>{copy.nav[activeSection]}</h3></div>
                  <div className="coord-action-row">
                    <button className="qa-btn" type="button" onClick={() => descargarReporte(activeSection)}>{copy.reports.xlsx}</button>
                    <button className="qa-btn" type="button" onClick={() => descargarReporte(activeSection, 'pdf')}>{copy.reports.pdf}</button>
                  </div>
                </div>
                <input className="coord-search" value={busqueda} onChange={e=>setBusqueda(e.target.value)} placeholder={copy.directory.search} />
                <div className="admin-table-wrap">
                  <table className="admin-table">
                    <thead><tr><th>{copy.directory.name}</th><th>{copy.directory.username}</th><th>{copy.directory.email}</th><th>{copy.directory.programDepartment}</th><th>{activeSection === 'alumnos' ? copy.directory.term : copy.detail.state}</th></tr></thead>
                    <tbody>
                      {filtrarPersonas(activeSection==='alumnos'?alumnos:(datos.aspirantes||[])).map(a=><tr key={a.id}>
                        <td><strong>{a.nombre}</strong></td><td>{a.usuario}</td><td>{a.correo}</td><td>{a.programa || a.departamento || a.unidad || '—'}</td>
                        <td>{activeSection === 'alumnos'
                          ? <div className="coord-action-row">
                            <input
                              aria-label={`${copy.directory.term} ${a.nombre}`}
                              type="number"
                              min="1"
                              step="1"
                              disabled={alumnoGuardandoCiclo !== null}
                              value={ciclosAlumno[a.id] ?? a.numero_periodo_actual ?? ''}
                              onChange={event => {
                                setCiclosAlumno(current => ({...current, [a.id]: event.target.value}));
                                setConfirmacionCiclo('');
                                setError('');
                              }}
                            />
                            <button type="button" className="qa-btn" disabled={alumnoGuardandoCiclo !== null} onClick={() => guardarCicloAlumno(a)}>
                              {copy.directory.save}
                            </button>
                          </div>
                          : <span className={`estado-badge estado-${a.proceso_estado}`}>{etiquetaEstado(a.proceso_estado, copy)}</span>}
                        </td>
                      </tr>)}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeSection === 'alumnos' && confirmacionCiclo && <div className="api-success" role="status" aria-live="polite">{confirmacionCiclo}</div>}

            {activeSection === 'personal' && datos && <div className="panel-card coord-directory personal-detail-card"><div className="admin-card-head"><div><p className="panel-kicker">{copy.faculty.kicker}</p><h3>{copy.faculty.title}</h3></div><div className="coord-action-row"><button className="qa-btn" type="button" onClick={() => descargarReporte('personal')}>{copy.faculty.downloadXlsx}</button><button className="qa-btn" type="button" onClick={() => descargarReporte('personal', 'pdf')}>{copy.reports.pdf}</button></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.faculty.name}</th><th>{copy.faculty.department}</th><th>{copy.faculty.courses}</th><th>{copy.faculty.schedule}</th><th>{copy.faculty.students}</th></tr></thead><tbody>{filtrarPersonas(docentes).map(persona => <tr key={`detalle-${persona.id}`}><td><strong>{persona.nombre}</strong><small>{persona.correo}</small></td><td>{persona.departamento || copy.faculty.noDepartment}</td><td>{persona.total_materias || 0} · {persona.creditos_impartidos || 0} {copy.directory.credits}</td><td>{persona.horarios?.join(' · ') || copy.faculty.noSchedule}</td><td>{persona.total_tesistas || 0}</td></tr>)}</tbody></table></div></div>}

            {activeSection === 'tesis' && <div className="panel-card coord-directory"><div className="admin-card-head"><div><p className="panel-kicker">{copy.thesis.kicker}</p><h3>{copy.thesis.title}</h3><p>{copy.thesis.intro}</p></div><button type="button" className="qa-btn" onClick={cargarProyectosTesis}>{copy.refresh}</button></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.thesis.project}</th><th>{copy.thesis.student}</th><th>{copy.thesis.director}</th><th>{copy.thesis.status}</th><th>{copy.thesis.updated}</th><th>{copy.loads.actions}</th></tr></thead><tbody>{proyectosTesis.length ? proyectosTesis.map(proyecto => <tr key={proyecto.id}><td><strong>{proyecto.titulo}</strong><small>{proyecto.linea_investigacion || copy.thesis.linePending}</small></td><td>{proyecto.alumno_nombre}<small>{proyecto.alumno_matricula || copy.thesis.noEnrollment}</small></td><td>{proyecto.director_nombre || copy.thesis.noDirector}</td><td><span className={`estado-badge estado-${proyecto.estado}`}>{etiquetaEstado(proyecto.estado, copy)}</span></td><td>{formatearFecha(proyecto.updated_at, copy.locale)}</td><td><div className="coord-action-row">{['en_revision','observado'].includes(proyecto.estado) && <><button type="button" className="qa-btn" onClick={() => actualizarProyectoTesis(proyecto, 'aprobado')}>{copy.thesis.approve}</button><button type="button" className="qa-btn" onClick={() => actualizarProyectoTesis(proyecto, 'observado')}>{copy.thesis.observe}</button><button type="button" className="qa-btn" onClick={() => actualizarProyectoTesis(proyecto, 'rechazado')}>{copy.thesis.reject}</button></>}</div></td></tr>) : <tr><td colSpan="6">{copy.thesis.noProjects}</td></tr>}</tbody></table></div></div>}

            {activeSection === 'asignaciones' && <div className="panel-card coord-directory"><div className="admin-card-head"><div><p className="panel-kicker">{copy.assignments.kicker}</p><h3>{copy.assignments.title}</h3><p>{copy.assignments.intro}</p></div></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.assignments.student}</th><th>{copy.assignments.line}</th><th>{copy.assignments.suggested}</th><th>{copy.assignments.assigned}</th><th>{copy.detail.state}</th><th>{copy.loads.actions}</th></tr></thead><tbody>{solicitudesTesis.length ? solicitudesTesis.map(solicitud => <tr key={solicitud.id}><td><strong>{solicitud.alumno?.nombre}</strong><small>{solicitud.alumno?.programa || copy.assignments.noProgram}</small></td><td>{solicitud.linea_investigacion || copy.assignments.notSpecified}</td><td>{solicitud.director_sugerido?.nombre || copy.assignments.noSuggestion}</td><td><select value={solicitud.director_asignado?.id || solicitud.director_sugerido?.id || ''} onChange={event => actualizarSolicitudTesis(solicitud, 'aprobada', event.target.value)}><option value="">{copy.assignments.selectDirector}</option>{directoresTesis.map(director => <option key={director.id} value={director.id}>{director.nombre}</option>)}</select></td><td><span className={`estado-badge estado-${solicitud.estado}`}>{etiquetaEstado(solicitud.estado, copy)}</span></td><td><div className="coord-action-row"><button type="button" className="qa-btn" onClick={() => actualizarSolicitudTesis(solicitud, 'rechazada')}>{copy.assignments.reject}</button>{solicitud.estado === 'aprobada' && <button type="button" className="qa-btn" onClick={() => actualizarSolicitudTesis(solicitud, 'cancelada')}>{copy.assignments.cancel}</button>}</div></td></tr>) : <tr><td colSpan="6">{copy.assignments.noRequests}</td></tr>}</tbody></table></div></div>}

            {activeSection === 'predoctoral' && <div className="panel-card coord-directory"><div className="admin-card-head"><div><p className="panel-kicker">{copy.predoctoral.kicker}</p><h3>{copy.predoctoral.title}</h3><p>{copy.predoctoral.intro}</p></div><button type="button" className="qa-btn" onClick={() => { fetch('/api/predoctoral/examenes/', {headers: {Authorization: `Bearer ${session.access}`}}).then(r => r.ok ? r.json() : Promise.reject()).then(data => setExamenesPredoctorales(data.examenes || [])).catch(() => setError(copy.messages.loadAssignments)); }}>{copy.refresh}</button></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.predoctoral.student}</th><th>{copy.predoctoral.program}</th><th>{copy.predoctoral.scheduled}</th><th>{copy.predoctoral.status}</th><th>{copy.predoctoral.result}</th><th>{copy.predoctoral.action}</th></tr></thead><tbody>{examenesPredoctorales.length ? examenesPredoctorales.map(examen => <tr key={examen.id}><td><strong>{examen.alumno?.nombre || copy.predoctoral.unavailable}</strong><small>{examen.alumno?.matricula || copy.predoctoral.noEnrollment}</small></td><td>{examen.alumno?.programa || copy.predoctoral.noProgram}</td><td>{formatearFecha(examen.fecha_programada, copy.locale)}</td><td><span className={`estado-badge estado-${examen.estado}`}>{etiquetaEstado(examen.estado, copy)}</span></td><td>{examen.calificacion ?? copy.loads.pending}</td><td><button type="button" className="qa-btn" onClick={() => { const valor = window.prompt(copy.predoctoral.prompt, examen.calificacion ?? ''); if (valor !== null) actualizarExamenPredoctoral(examen, {calificacion: valor}); }}>{copy.predoctoral.validate}</button></td></tr>) : <tr><td colSpan="6">{copy.predoctoral.noExams}</td></tr>}</tbody></table></div></div>}

            {activeSection === 'perfil' && datos && <PerfilAspirante perfil={{...datos.usuario, telefono: datos.usuario?.telefono || ''}} session={session} onActualizado={(actualizado) => setDatos(actual => ({...actual, usuario: {...actual.usuario, ...actualizado}}))} />}

            {activeSection === 'reportes' && (
              <div className="aspirante-section-card is-open"><div className="section-panel"><div className="panel-card"><h3>{copy.reports.title}</h3><p>{copy.reports.intro}</p><div className="coord-report-grid"><div><strong>{datos.resumen.total || 0}</strong><span>{copy.reports.total}</span></div><div><strong>{datos.resumen.por_revisar || 0}</strong><span>{copy.reports.review}</span></div><div><strong>{datos.resumen.revision || 0}</strong><span>{copy.reports.inReview}</span></div><div><strong>{datos.resumen.aceptado || 0}</strong><span>{copy.reports.accepted}</span></div></div></div></div></div>
            )}

            {activeSection === 'colegio' && (
              <div className="aspirante-section-card is-open"><div className="section-panel"><div className="panel-card"><h3>{copy.college.title}</h3><p>{copy.college.intro}</p><form className="colegio-evaluacion-form" onSubmit={guardarEvaluacionColegio}><label>{copy.college.applicant}<select value={evaluacionForm.aspirante} onChange={e => setEvaluacionForm({...evaluacionForm, aspirante: e.target.value})}><option value="">{copy.college.selectApplicant}</option>{(datos.aspirantes || []).filter(a => a.rol === 'aspirante').map(a => <option key={a.id} value={a.id}>{a.nombre} — {a.programa || copy.college.noProgram}</option>)}</select></label><label>{copy.college.decision}<select value={evaluacionForm.estado} onChange={e => setEvaluacionForm({...evaluacionForm, estado: e.target.value})}><option value="en_revision">{copy.status.en_revision}</option><option value="favorable">{copy.status.favorable}</option><option value="no_favorable">{copy.status.no_favorable}</option></select></label><label>{copy.college.comments}<textarea rows="4" value={evaluacionForm.dictamen} onChange={e => setEvaluacionForm({...evaluacionForm, dictamen: e.target.value})} placeholder={copy.college.placeholder} required /></label><button type="submit" className="qa-btn">{evaluacionForm.id ? copy.college.update : copy.college.save}</button>{evaluacionForm.id && <button type="button" className="qa-btn qa-btn-secondary" onClick={() => setEvaluacionForm({aspirante: '', estado: 'en_revision', dictamen: ''})}>{copy.college.cancel}</button>}</form></div><div className="panel-card"><div className="admin-card-head"><div><h3>{copy.college.registered}</h3><p>{copy.college.history}</p></div><select className="coord-filter-select" value={evaluacionFiltro} onChange={e => setEvaluacionFiltro(e.target.value)}><option value="todas">{copy.college.all}</option><option value="en_revision">{copy.status.en_revision}</option><option value="favorable">{copy.college.favorable}</option><option value="no_favorable">{copy.college.noFavorable}</option></select></div>{evaluacionesVisibles.length ? <div className="colegio-evaluaciones-list">{evaluacionesVisibles.map(e => <article key={e.id}><div><strong>{e.aspirante_nombre || `Aspirante #${e.aspirante}`}</strong><small>{e.evaluador_nombre || copy.predoctoral.unavailable} · {formatearFecha(e.fecha_evaluacion, copy.locale)}</small><p>{e.dictamen || '—'}</p></div><div className="coord-action-row"><span className={`estado-badge estado-${e.estado}`}>{etiquetaEstado(e.estado, copy)}</span><button type="button" className="qa-btn" onClick={() => setEvaluacionForm({id:e.id, aspirante:e.aspirante, estado:e.estado, dictamen:e.dictamen || ''})}>{copy.college.update}</button></div></article>)}</div> : <p className="empty-state">{copy.college.selectDecision}</p>}</div></div></div>
            )}

            {activeSection === 'bandeja' && (
              <div className="aspirante-section-card is-open">
                <div className="section-panel">
                      <div className="panel-card coord-queue"><div className="coord-queue-head"><h3>{copy.queue.title}</h3><div className="coord-filters">{FILTROS.map((item) => <button type="button" key={item.id} className={filtro === item.id ? 'is-active' : ''} onClick={() => setFiltro(item.id)}>{copy.filters[item.key]}</button>)}</div></div><div className="coord-list">{aspirantes.length === 0 ? <p className="empty-state">{copy.queue.empty}</p> : aspirantes.map((aspirante) => <button type="button" key={aspirante.id} className={`coord-item${seleccionado?.id === aspirante.id ? ' is-selected' : ''}`} onClick={() => { setSeleccionado(aspirante); setActiveSection('detalle'); }}><span><strong>{aspirante.nombre}</strong><small>{aspirante.programa} · {aspirante.unidad}</small></span><span className={`estado-badge estado-${aspirante.proceso_estado}`}>{etiquetaEstado(aspirante.proceso_estado, copy)}</span></button>)}</div></div>
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
                        <div className="coord-profile-photo">{seleccionado.profile_photo ? <img src={seleccionado.profile_photo.startsWith('http') ? seleccionado.profile_photo : `http://localhost:8000${seleccionado.profile_photo}`} alt={copy.detail.title} /> : <span>{(seleccionado.nombre || 'A').charAt(0).toUpperCase()}</span>}</div>
                        <div>
                          <p className="panel-kicker">{copy.detail.title}</p>
                          <h3>{seleccionado.nombre}</h3>
                          <p>{seleccionado.correo} · {seleccionado.telefono}</p>
                        </div>
                        <span className={`estado-badge estado-${seleccionado.proceso_estado}`}>{etiquetaEstado(seleccionado.proceso_estado, copy)}</span>
                      </div>

                      {detalleCargando && !detalle ? (
                        <div className="panel-card">{copy.loadingDetails}</div>
                      ) : detalle ? (
                        <div>
                          {saveError && <div className="api-error" role="alert">{saveError}</div>}
                          {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}

                          <div className="coord-action-row">
                                {detalle?.rol === 'aspirante' && <>
                                  <button type="button" className="qa-btn" onClick={() => cambiarEstado('revision')} disabled={actualizando}>{copy.detail.markReview}</button>
                                  <button type="button" className="qa-btn" onClick={() => cambiarEstado('aceptado')} disabled={actualizando}>{copy.detail.accept}</button>
                                  <button type="button" className="qa-btn" onClick={() => cambiarEstado('rechazado')} disabled={actualizando}>{copy.detail.reject}</button>
                                </>}
                            {/* Conversion actions: only available once the aspirante is an alumno */}
                            {detalle?.rol === 'aspirante' && detalle?.proceso_estado === 'aceptado' && (
                              <button type="button" className="qa-btn" onClick={async () => {
                                try {
                                  const resp = await fetch(`/api/coordinacion/aspirantes/${detalle.id}/convertir/`, {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`}});
                                  if (!resp.ok) throw new Error(copy.detail.convertError);
                                  const data = await resp.json();
                                  setDetalle((d) => ({...d, rol: data.rol}));
                                  setSaveSuccess(copy.detail.converted);
                                  cargarPanel(new AbortController().signal);
                                } catch (err) {
                                  setError(err.message || copy.detail.convertError);
                                }
                              }}>{copy.detail.convert}</button>
                            )}

                            {detalle?.rol === 'alumno' && (
                              <div>
                                <button type="button" className="qa-btn" onClick={handleDescargarCalificaciones}>{copy.detail.grades}</button>
                                <button type="button" className="qa-btn" onClick={handleDescargarAdscripcion}>{copy.detail.affiliation}</button>
                                <button type="button" className="qa-btn" onClick={handleDarBaja}>{copy.detail.dropout}</button>
                                <button type="button" className="qa-btn" onClick={handleGenerarCarga}>{copy.detail.generateLoad}</button>
                                <button type="button" className="qa-btn" onClick={handleCargarCursosClick}>{copy.detail.uploadCourses}</button>
                                <input ref={fileInputRef} type="file" accept=".csv" style={{display:'none'}} onChange={handleCargarCursosFile} />
                              </div>
                            )}
                          </div>

                          <div className="coord-data">
                            {detalle.expediente_digital?.id && <ExpedienteCentralizadoCard expedienteId={detalle.expediente_digital.id} session={session}/>} 
                            <div><span>{copy.detail.curp}</span><strong>{detalle.curp}</strong></div>
                            <div><span>{copy.directory.username}</span><strong>{detalle.usuario}</strong></div>
                            <div><span>{copy.detail.program}</span><strong>{detalle.programa || '—'}</strong></div>
                            <div><span>{copy.detail.unit}</span><strong>{detalle.unidad || '—'}</strong></div>
                            <div><span>{copy.detail.department}</span><strong>{detalle.departamento || '—'}</strong></div>
                            <div><span>{copy.detail.section}</span><strong>{detalle.seccion || '—'}</strong></div>
                            <div><span>{copy.detail.modality}</span><strong>{detalle.modalidad || '—'}</strong></div>
                            <div><span>{copy.detail.degree}</span><strong>{detalle.ultimo_grado || '—'}</strong></div>
                            <div><span>{copy.detail.institution}</span><strong>{detalle.institucion || '—'}</strong></div>
                            <div><span>{copy.detail.director}</span><strong>{detalle.director_tesis_nombre || copy.detail.unassigned}</strong></div>
                          </div>

                          <div className="coord-form">
                            <div className="coord-form-heading">
                              <div>
                                <h4>{copy.detail.dates}</h4>
                                <p>{copy.detail.datesIntro}</p>
                              </div>
                              <div className="coord-form-actions">
                                <button type="button" className="qa-btn coord-btn" onClick={handleGuardarCambios} disabled={guardando}>
                                  {guardando ? copy.detail.saving : copy.detail.saveChanges}
                                </button>
                              </div>
                            </div>
                            {saveError && <div className="api-error" role="alert">{saveError}</div>}
                            {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}
                            <div className="coord-form-grid">
                              <label className="coord-field">
                                <span>{copy.detail.examDate}</span>
                                <input
                                  type="datetime-local"
                                  value={formatoDateTimeLocal(editData?.fecha_examen_admision)}
                                  onChange={(event) => handleFieldChange('fecha_examen_admision', event.target.value)}
                                />
                              </label>
                              <label className="coord-field">
                                <span>{copy.detail.interviewDate}</span>
                                <input
                                  type="datetime-local"
                                  value={formatoDateTimeLocal(editData?.fecha_entrevista)}
                                  onChange={(event) => handleFieldChange('fecha_entrevista', event.target.value)}
                                />
                              </label>
                              <label className="coord-field">
                                <span>{copy.detail.courseStart}</span>
                                <input
                                  type="datetime-local"
                                  value={formatoDateTimeLocal(editData?.fecha_inicio_curso_propedeutico)}
                                  onChange={(event) => handleFieldChange('fecha_inicio_curso_propedeutico', event.target.value)}
                                />
                              </label>
                              <label className="coord-field">
                                <span>{copy.detail.courseGrade}</span>
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
                                <span>{copy.detail.director}</span>
                                <select
                                  value={editData?.director_tesis || ''}
                                  onChange={(event) => handleFieldChange('director_tesis', event.target.value ? Number(event.target.value) : null)}
                                >
                                  <option value="">{copy.detail.unassigned}</option>
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
                                {copy.detail.courseApproved}
                              </label>
                              <label className="coord-checkbox">
                                <input
                                  type="checkbox"
                                  checked={editData?.apoyo_autorizado || false}
                                  onChange={(event) => handleFieldChange('apoyo_autorizado', event.target.checked)}
                                />
                                {copy.detail.supportAuthorized}
                              </label>
                            </div>
                          </div>

                          <div className="coord-documents">
                            <h4>{copy.detail.docs}</h4>
                            {detalle.documentos?.length ? (
                              <ul>
                                {detalle.documentos.map((documento) => (
                                  <li key={documento.id}>
                                    <span>{documento.tipo_label}</span>
                                    <a href={documento.archivo} target="_blank" rel="noreferrer">{copy.detail.viewFile}</a>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <p className="empty-state">{copy.detail.noDocs}</p>
                            )}
                          </div>

                          <div className="coord-materias">
                            <h4>{copy.detail.availableSubjects}</h4>
                            <div>
                              <button type="button" className="qa-btn" onClick={cargarMateriasDisponibles} disabled={materiasCargando}>{materiasCargando ? copy.subjects.loading : copy.subjects.query}</button>
                            </div>
                            {materias ? (
                              <table className="admin-table" style={{marginTop:12}}>
                                <thead><tr><th>{copy.subjects.key}</th><th>{copy.subjects.subject}</th><th>{copy.subjects.teacher}</th><th>{copy.subjects.schedule}</th></tr></thead>
                                <tbody>
                                  {materias.map((m) => (
                                    <tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.profesor || '—'}</td><td>{m.horario || '—'}</td></tr>
                                  ))}
                                </tbody>
                              </table>
                            ) : <p className="empty-state">{copy.detail.noSubjects}</p>}
                          </div>

                          <div className="coord-timeline">
                            <h4>{copy.detail.timeline}</h4>
                            {detalle.seguimientos?.length ? (
                              detalle.seguimientos.map((evento) => (
                                <article className="coord-event" key={evento.id}>
                                  <div className="coord-event-head">
                                    <strong>{etiquetaEstado(evento.estado, copy)}</strong>
                                    <time>{formatearFecha(evento.created_at)}</time>
                                  </div>
                                  <p>{evento.detalle}</p>
                                  <small>{evento.origen}</small>
                                </article>
                              ))
                            ) : (
                              <p className="empty-state">{copy.detail.noTimeline}</p>
                            )}
                          </div>
                        </div>
                  ) : (
                    <div className="empty-state">
                      <h3>{copy.detail.selectRecord}</h3>
                      <p>{copy.detail.selectRecordText}</p>
                      <button type="button" className="qa-btn" onClick={() => setActiveSection('bandeja')}>{copy.detail.goQueue}</button>
                    </div>
                  )}
                    </div>
                  ) : (
                    <div className="coord-empty"><h3>{copy.detail.selectRequest}</h3><p>{copy.detail.selectRequestText}</p></div>
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
