import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import ExpedienteCentralizadoCard from './ExpedienteCentralizadoCard';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import EgresadosPanel from './EgresadosPanel';
import HistoricoPanel from './HistoricoPanel';
import ExamenesGestionPanel from './ExamenesGestionPanel';
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
  {label: 'academic', items: [['materias', 'Materias y cursos', '▤'], ['cargas', 'Aprobación de carga', '↗'], ['extemporanea', 'Inscripción extemporánea', '＋'], ['examenes', 'Exámenes en línea', '✎']]},
  {label: 'research', items: [['tesis', 'Proyectos de tesis', '◆'], ['asignaciones', 'Asignación de directores', '↔'], ['predoctoral', 'Examen predoctoral', '✦'], ['colegio', 'Colegio de Profesores', '◈']]},
  {label: 'community', items: [['alumnos', 'Alumnos', '♙'], ['aspirantes', 'Aspirantes', '◎'], ['egresados', 'Egresados', '♛'], ['historico', 'Histórico', '⟲'], ['personal', 'Docentes y Directores', '◇'], ['reportes', 'Reportes', '▥'], ['perfil', 'Mi perfil', '●']]},
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

const CARGA_FORM_TEXT = {
  es: {add: 'Agregar materia', remove: 'Quitar', room: 'Salón', capacity: 'Cupo', save: 'Guardar borrador', update: 'Actualizar borrador', edit: 'Editar', cancel: 'Cancelar edición', submit: 'Enviar a revisión', subject: 'Selecciona una materia', teacher: 'Selecciona un docente', count: 'Materias', detail: 'Ver detalle', hide: 'Ocultar detalle', reviewComment: 'Comentario de revisión (obligatorio)', reviewCommentHint: 'Explica el motivo de la decisión.', approveComment: 'Aprobar con comentario', rejectComment: 'Rechazar con comentario', noCourses: 'La carga no contiene materias.'},
  en: {add: 'Add subject', remove: 'Remove', room: 'Room', capacity: 'Capacity', save: 'Save draft', update: 'Update draft', edit: 'Edit', cancel: 'Cancel editing', submit: 'Submit for review', subject: 'Select a subject', teacher: 'Select an instructor', count: 'Subjects', detail: 'View details', hide: 'Hide details', reviewComment: 'Review comment (required)', reviewCommentHint: 'Explain the reason for your decision.', approveComment: 'Approve with comment', rejectComment: 'Reject with comment', noCourses: 'This course load has no subjects.'},
  de: {add: 'Fach hinzufügen', remove: 'Entfernen', room: 'Raum', capacity: 'Kapazität', save: 'Entwurf speichern', update: 'Entwurf aktualisieren', edit: 'Bearbeiten', cancel: 'Bearbeitung abbrechen', submit: 'Zur Prüfung senden', subject: 'Fach auswählen', teacher: 'Lehrkraft auswählen', count: 'Fächer', detail: 'Details anzeigen', hide: 'Details ausblenden', reviewComment: 'Prüfungskommentar (erforderlich)', reviewCommentHint: 'Begründen Sie Ihre Entscheidung.', approveComment: 'Mit Kommentar genehmigen', rejectComment: 'Mit Kommentar ablehnen', noCourses: 'Dieses Lehrangebot enthält keine Fächer.'},
  zh: {add: '添加课程', remove: '移除', room: '教室', capacity: '容量', save: '保存草稿', update: '更新草稿', edit: '编辑', cancel: '取消编辑', submit: '提交审核', subject: '选择课程', teacher: '选择教师', count: '门课程', detail: '查看详情', hide: '隐藏详情', reviewComment: '审核意见（必填）', reviewCommentHint: '请说明决定理由。', approveComment: '附意见批准', rejectComment: '附意见拒绝', noCourses: '此课程安排没有课程。'},
  pt: {add: 'Adicionar disciplina', remove: 'Remover', room: 'Sala', capacity: 'Vagas', save: 'Salvar rascunho', update: 'Atualizar rascunho', edit: 'Editar', cancel: 'Cancelar edição', submit: 'Enviar para revisão', subject: 'Selecione uma disciplina', teacher: 'Selecione um docente', count: 'Disciplinas', detail: 'Ver detalhes', hide: 'Ocultar detalhes', reviewComment: 'Comentário da revisão (obrigatório)', reviewCommentHint: 'Explique o motivo da decisão.', approveComment: 'Aprovar com comentário', rejectComment: 'Rejeitar com comentário', noCourses: 'A carga não contém disciplinas.'},
};

const EXTEMPORANEO_TEXT = {
  es: {student:'Alumno', chooseStudent:'Selecciona un alumno', period:'Periodo de inscripción', choosePeriod:'Selecciona un periodo', subjects:'Materias disponibles', reason:'Motivo obligatorio', reasonHint:'Explica por qué se realiza fuera del periodo regular.', submit:'Registrar inscripción', saving:'Registrando...', saved:'Inscripción extemporánea registrada.', loadError:'No se pudieron cargar los datos para la inscripción.', saveError:'No se pudo registrar la inscripción.', noStudents:'No hay alumnos disponibles.', noSubjects:'No hay materias disponibles en una carga publicada para ese periodo.', capacity:'Cupo', full:'Sin cupo', loading:'Cargando materias...'},
  en: {student:'Student', chooseStudent:'Select a student', period:'Enrollment period', choosePeriod:'Select a period', subjects:'Available subjects', reason:'Required reason', reasonHint:'Explain why this is outside the regular enrollment period.', submit:'Register enrollment', saving:'Registering...', saved:'Late enrollment registered.', loadError:'Could not load enrollment data.', saveError:'Could not register the enrollment.', noStudents:'There are no students available.', noSubjects:'No subjects are available in a published course load for this period.', capacity:'Seats', full:'Full', loading:'Loading subjects...'},
  de: {student:'Studierende', chooseStudent:'Studierende auswählen', period:'Einschreibungszeitraum', choosePeriod:'Zeitraum auswählen', subjects:'Verfügbare Fächer', reason:'Begründung erforderlich', reasonHint:'Erläutern Sie die Einschreibung außerhalb des regulären Zeitraums.', submit:'Einschreibung registrieren', saving:'Wird registriert...', saved:'Nachträgliche Einschreibung registriert.', loadError:'Einschreibungsdaten konnten nicht geladen werden.', saveError:'Einschreibung konnte nicht registriert werden.', noStudents:'Keine Studierenden verfügbar.', noSubjects:'Keine Fächer in einem veröffentlichten Angebot verfügbar.', capacity:'Plätze', full:'Voll', loading:'Fächer werden geladen...'},
  zh: {student:'学生', chooseStudent:'选择学生', period:'注册学期', choosePeriod:'选择学期', subjects:'可选课程', reason:'必须填写原因', reasonHint:'说明为何在常规注册期外办理。', submit:'登记注册', saving:'正在登记...', saved:'已登记逾期注册。', loadError:'无法加载注册数据。', saveError:'无法登记注册。', noStudents:'没有可用学生。', noSubjects:'该学期没有已发布课程。', capacity:'名额', full:'已满', loading:'正在加载课程...'},
  pt: {student:'Aluno', chooseStudent:'Selecione um aluno', period:'Período de inscrição', choosePeriod:'Selecione um período', subjects:'Disciplinas disponíveis', reason:'Motivo obrigatório', reasonHint:'Explique por que a inscrição ocorre fora do prazo regular.', submit:'Registrar inscrição', saving:'Registrando...', saved:'Inscrição fora do prazo registrada.', loadError:'Não foi possível carregar os dados da inscrição.', saveError:'Não foi possível registrar a inscrição.', noStudents:'Não há alunos disponíveis.', noSubjects:'Não há disciplinas em uma oferta publicada para esse período.', capacity:'Vagas', full:'Sem vagas', loading:'Carregando disciplinas...'},
};

export default function PanelCoordinacion({session, onLogout: onLogoutProp}) {
  const onLogoutRef = useRef(onLogoutProp);
  onLogoutRef.current = onLogoutProp;
  const onLogout = useCallback((...args) => onLogoutRef.current?.(...args), []);
  const copy = useCoordinationCopy();
  const extText = EXTEMPORANEO_TEXT[copy.locale.slice(0, 2)] || EXTEMPORANEO_TEXT.es;
  const cargaText = CARGA_FORM_TEXT[(document.documentElement.lang || 'es').slice(0, 2)] || CARGA_FORM_TEXT.es;
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
  const [catalogoCarga, setCatalogoCarga] = useState({materias: [], docentes: [], salones: [], modalidades: []});
  const [cargaEditando, setCargaEditando] = useState(null);
  const [materiasCarga, setMateriasCarga] = useState([]);
  const [guardandoCarga, setGuardandoCarga] = useState(false);
  const [cargaDetalleId, setCargaDetalleId] = useState(null);
  const [comentarioRevision, setComentarioRevision] = useState('');
  const [cargaRevisionGuardando, setCargaRevisionGuardando] = useState(false);
  const [periodosPublicacionCarga, setPeriodosPublicacionCarga] = useState({});
  const [periodosInscripcion, setPeriodosInscripcion] = useState([]);
  const [alumnoExtemporaneoId, setAlumnoExtemporaneoId] = useState('');
  const [periodoExtemporaneoId, setPeriodoExtemporaneoId] = useState('');
  const [periodosExtemporaneos, setPeriodosExtemporaneos] = useState([]);
  const [materiasExtemporaneas, setMateriasExtemporaneas] = useState([]);
  const [materiasExtemporaneasSeleccionadas, setMateriasExtemporaneasSeleccionadas] = useState([]);
  const [motivoExtemporaneo, setMotivoExtemporaneo] = useState('');
  const [guardandoExtemporanea, setGuardandoExtemporanea] = useState(false);
  const [cargandoExtemporanea, setCargandoExtemporanea] = useState(false);
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
      const data = await r.json();
      setCargas(data.cargas || []);
      setCatalogoCarga({
        materias: data.materias_catalogo || [],
        docentes: data.docentes_catalogo || [],
        salones: data.salones || [],
        modalidades: data.modalidades || [],
      });
    } catch (e) { setError(e.message || copy.messages.loadCharges); }
  }, [copy, onLogout, session.access]);

  function agregarMateriaCarga() {
    setMateriasCarga(items => [...items, {materia: '', docente: '', horario: '', salon: '', capacidad: 42, modalidad: 'presencial'}]);
  }

  function editarCarga(carga) {
    setCargaEditando(carga.id);
    setPeriodoCarga(carga.periodo);
    setMateriasCarga(carga.materias.map(item => ({
      materia: String(item.materia),
      docente: item.docente ? String(item.docente) : '',
      horario: item.horario,
      salon: item.salon,
      capacidad: item.capacidad,
      modalidad: item.modalidad,
    })));
    setError('');
    setSaveSuccess('');
  }

  function cancelarEdicionCarga() {
    setCargaEditando(null);
    setPeriodoCarga('');
    setMateriasCarga([]);
  }

  async function guardarCargaBorrador(event) {
    event.preventDefault();
    setError('');
    setSaveSuccess('');
    setGuardandoCarga(true);
    try {
      const method = cargaEditando ? 'PATCH' : 'POST';
      const url = cargaEditando ? `/api/cargas-academicas/${cargaEditando}/` : '/api/cargas-academicas/';
      const payload = {
        periodo: periodoCarga.trim(),
        materias: materiasCarga.map(item => ({
          ...item,
          materia: item.materia ? Number(item.materia) : null,
          docente: item.docente ? Number(item.docente) : null,
          capacidad: Number(item.capacidad),
        })),
      };
      const r = await fetch(url, {
        method,
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || copy.loads.saveError);
      setSaveSuccess(cargaEditando ? copy.loads.draftUpdated : copy.loads.draftSaved);
      cancelarEdicionCarga();
      await cargarFlujoCargas();
    } catch (e) {
      setError(e.message || copy.loads.saveError);
    } finally {
      setGuardandoCarga(false);
    }
  }

  async function crearCargaRevision() {
    try {
      const r = await fetch('/api/cargas-academicas/', {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({periodo: periodoCarga})});
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || copy.loads.sendError);
      setSaveSuccess(copy.loads.sent); setPeriodoCarga(''); cargarFlujoCargas();
    } catch (e) { setError(e.message || copy.loads.sendError); }
  }

  async function actualizarEstadoCarga(id, estado, comentario = '', periodoInscripcion = null) {
    setError('');
    setSaveSuccess('');
    setCargaRevisionGuardando(true);
    try {
      const r = await fetch(`/api/cargas-academicas/${id}/`, {method: 'PATCH', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({estado, comentario, ...(estado === 'publicada' ? {periodo_inscripcion: Number(periodoInscripcion)} : {})})});
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || copy.loads.updateError);
      setSaveSuccess(`${copy.loads.updated} ${etiquetaEstado(estado, copy)}.`);
      setComentarioRevision('');
      setCargaDetalleId(null);
      await cargarFlujoCargas();
    } catch (e) { setError(e.message || copy.loads.updateError); }
    finally { setCargaRevisionGuardando(false); }
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

  useEffect(() => { if (['cargas', 'materias'].includes(activeSection)) cargarFlujoCargas(); }, [activeSection, cargarFlujoCargas]);
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
    if (!['cargas', 'materias'].includes(activeSection)) return;
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
      })
      .catch(error => { if (error.name !== 'AbortError') setError(error.message); });
    return () => controller.abort();
  }, [activeSection, copy.messages.expired, copy.periods.createError, onLogout, session.access]);

  useEffect(() => {
    if (activeSection !== 'extemporanea' || !alumnoExtemporaneoId) {
      setMateriasExtemporaneas([]);
      setPeriodosExtemporaneos([]);
      return undefined;
    }
    const controller = new AbortController();
    const query = periodoExtemporaneoId ? `?periodo=${periodoExtemporaneoId}` : '';
    setCargandoExtemporanea(true);
    setError('');
    fetch(`/api/coordinacion/alumnos/${alumnoExtemporaneoId}/inscripciones-extemporaneas/${query}`, {
      headers: {Authorization: `Bearer ${session.access}`},
      signal: controller.signal,
    })
      .then(async response => {
        const body = await response.json().catch(() => ({}));
        if (response.status === 401) {
          onLogout(copy.messages.expired);
          throw Object.assign(new Error(), {name: 'AbortError'});
        }
        if (!response.ok) throw new Error(body.detail || extText.loadError);
        return body;
      })
      .then(body => {
        const listaPeriodos = body.periodos || [];
        setPeriodosExtemporaneos(listaPeriodos);
        if (!periodoExtemporaneoId && listaPeriodos.length) {
          const periodoPreferido = listaPeriodos.find(periodo => periodo.activo || periodo.habilitado) || listaPeriodos[0];
          setPeriodoExtemporaneoId(String(periodoPreferido.id));
        }
        setMateriasExtemporaneas(body.materias || []);
        setMateriasExtemporaneasSeleccionadas([]);
      })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message || extText.loadError); })
      .finally(() => { if (!controller.signal.aborted) setCargandoExtemporanea(false); });
    return () => controller.abort();
  }, [activeSection, alumnoExtemporaneoId, periodoExtemporaneoId, session.access, onLogout, copy.messages.expired, extText.loadError]);

  async function registrarInscripcionExtemporanea(event) {
    event.preventDefault();
    if (!alumnoExtemporaneoId || !periodoExtemporaneoId || materiasExtemporaneasSeleccionadas.length === 0 || !motivoExtemporaneo.trim()) {
      setError(extText.saveError);
      return;
    }
    setGuardandoExtemporanea(true);
    setError('');
    setSaveSuccess('');
    try {
      const response = await fetch(`/api/coordinacion/alumnos/${alumnoExtemporaneoId}/inscripciones-extemporaneas/`, {
        method: 'POST',
        headers: {Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({
          periodo_inscripcion: Number(periodoExtemporaneoId),
          materias: materiasExtemporaneasSeleccionadas,
          motivo: motivoExtemporaneo.trim(),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (!response.ok) throw new Error(body.detail || body.motivo || body.materias || extText.saveError);
      setMateriasExtemporaneasSeleccionadas([]);
      setMotivoExtemporaneo('');
      setSaveSuccess(extText.saved);
      setMateriasExtemporaneas(current => current.map(materia => (
        materiasExtemporaneasSeleccionadas.includes(materia.id)
          ? {...materia, inscritos: materia.inscritos + 1}
          : materia
      )));
    } catch (err) {
      setError(err.message || extText.saveError);
    } finally {
      setGuardandoExtemporanea(false);
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
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || copy.detail.updateError);
      }
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

  async function revisarDocumento(documento, revisado) {
    if (actualizando) return;
    setActualizando(true);
    setError('');
    try {
      const response = await fetch(`/api/coordinacion/documentos/${documento.id}/revision/`, {
        method: 'PATCH',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({revisado}),
      });
      if (!response.ok) throw new Error(copy.detail.updateError);
      const actualizado = await response.json();
      setDetalle((actual) => ({...actual, documentos: actualizado.documentos}));
    } catch (err) {
      setError(err.message || copy.detail.updateError);
    } finally {
      setActualizando(false);
    }
  }

  async function verDocumento(documento) {
    const ventana = window.open('', '_blank');
    try {
      const response = await fetch(`${documento.archivo}?inline=1`, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error(copy.detail.downloadError);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(new Blob([blob], {type: 'application/pdf'}));
      if (ventana) ventana.location.href = url;
      else window.location.assign(url);
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60000);
    } catch (err) {
      if (ventana) ventana.close();
      setError(err.message || copy.detail.downloadError);
    }
  }

  function intentarAceptar() {
    const documentos = detalle?.documentos || [];
    if (!documentos.length || documentos.some((documento) => !documento.revisado)) {
      setSaveSuccess('');
      setSaveError(copy.detail.reviewDocsFirst);
      return;
    }
    setSaveError('');
    cambiarEstado('aceptado');
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

            {activeSection === 'extemporanea' && (
              <section className="panel-card coord-plan-panel">
                <header className="admin-card-head">
                  <div><p className="panel-kicker">{copy.groups.academic}</p><h3>{copy.nav.extemporanea}</h3><p>{extText.intro}</p></div>
                </header>
                <form className="coord-plan-form" onSubmit={registrarInscripcionExtemporanea}>
                  <div className="coord-plan-fields">
                    <label><span>{extText.student}</span>
                      <select value={alumnoExtemporaneoId} onChange={event => {
                        setAlumnoExtemporaneoId(event.target.value);
                        setPeriodoExtemporaneoId('');
                        setMateriasExtemporaneasSeleccionadas([]);
                        setMotivoExtemporaneo('');
                        setSaveSuccess('');
                      }} required>
                        <option value="">{extText.chooseStudent}</option>
                        {(datos.personas || []).filter(persona => persona.rol === 'alumno').map(persona => (
                          <option key={persona.id} value={persona.id}>{persona.nombre} · {persona.matricula || persona.programa || ''}</option>
                        ))}
                      </select>
                    </label>
                    <label><span>{extText.period}</span>
                      <select value={periodoExtemporaneoId} disabled={!alumnoExtemporaneoId || !periodosExtemporaneos.length} onChange={event => {
                        setPeriodoExtemporaneoId(event.target.value);
                        setMateriasExtemporaneasSeleccionadas([]);
                        setSaveSuccess('');
                      }} required>
                        <option value="">{extText.choosePeriod}</option>
                        {periodosExtemporaneos.map(periodo => <option key={periodo.id} value={periodo.id}>{periodo.nombre} · {formatearFecha(periodo.apertura, copy.locale)}</option>)}
                      </select>
                    </label>
                  </div>
                  <div className="coord-plan-course-heading"><div><h4>{extText.subjects}</h4></div></div>
                  {cargandoExtemporanea ? <p className="coord-plan-notice">{extText.loading}</p> : materiasExtemporaneas.length ? (
                    <div className="coord-plan-course-list">
                      {materiasExtemporaneas.map(materia => {
                        const sinCupo = materia.inscritos >= materia.capacidad;
                        const marcada = materiasExtemporaneasSeleccionadas.includes(materia.id);
                        return (
                          <label className="coord-plan-course-row" key={materia.id}>
                            <input type="checkbox" checked={marcada} disabled={sinCupo} onChange={event => setMateriasExtemporaneasSeleccionadas(current => (
                              event.target.checked
                                ? [...current, materia.id]
                                : current.filter(id => id !== materia.id)
                            ))}/>
                            <span><strong>{materia.clave} · {materia.nombre}</strong><small>{materia.creditos} {copy.plans.credits} · {materia.horario || copy.subjects.define}</small></span>
                            <span>{extText.capacity}: {Math.max(0, materia.capacidad - materia.inscritos)} / {materia.capacidad}{sinCupo ? ` · ${extText.full}` : ''}</span>
                          </label>
                        );
                      })}
                    </div>
                  ) : <p className="coord-plan-notice">{alumnoExtemporaneoId && periodoExtemporaneoId ? extText.noSubjects : extText.chooseStudent}</p>}
                  <label className="coord-plan-reason"><span>{extText.reason}</span>
                    <textarea rows="4" value={motivoExtemporaneo} onChange={event => setMotivoExtemporaneo(event.target.value)} placeholder={extText.reasonHint} required maxLength="2000"/>
                  </label>
                  <div className="periodo-form-actions">
                    <button type="submit" className="qa-btn" disabled={guardandoExtemporanea || !alumnoExtemporaneoId || !periodoExtemporaneoId || !materiasExtemporaneasSeleccionadas.length || !motivoExtemporaneo.trim()}>{guardandoExtemporanea ? extText.saving : extText.submit}</button>
                  </div>
                  {error && <div className="api-error" role="alert">{error}</div>}
                  {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}
                  {!alumnoExtemporaneoId && !(datos.personas || []).some(persona => persona.rol === 'alumno') && <p className="coord-plan-notice">{extText.noStudents}</p>}
                </form>
              </section>
            )}

            {activeSection === 'materias' && <div className="panel-card coord-directory coord-materias-card"><div className="admin-card-head"><div><p className="panel-kicker">{copy.subjects.kicker}</p><h3>{copy.subjects.title}</h3><p>{copy.subjects.intro}</p></div><div className="coord-action-row"><button type="button" className="qa-btn" onClick={handleCargarCursosClick}>{copy.subjects.upload}</button><input ref={fileInputRef} type="file" accept=".csv" style={{display:'none'}} onChange={handleCargarCursosFile}/><button type="button" className="qa-btn" onClick={cargarMateriasDisponibles} disabled={materiasCargando}>{materiasCargando ? copy.subjects.loading : copy.subjects.query}</button></div></div>{materias ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.subjects.key}</th><th>{copy.subjects.subject}</th><th>{copy.subjects.credits}</th><th>{copy.subjects.teacher}</th><th>{copy.subjects.schedule}</th></tr></thead><tbody>{materias.map(m=><tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.creditos ?? '—'}</td><td>{m.profesor || copy.subjects.assign}</td><td>{m.horario || copy.subjects.define}</td></tr>)}</tbody></table></div> : <p className="empty-state">{copy.subjects.noCatalog}</p>}</div>}
            {activeSection === 'cargas' && <div className="panel-card coord-directory">
              <div className="admin-card-head"><div><p className="panel-kicker">{copy.loads.kicker}</p><h3>{copy.loads.title}</h3><p>{copy.loads.intro}</p></div><button type="button" className="qa-btn" onClick={cargarFlujoCargas}>{copy.refresh}</button></div>
              <form className="coord-carga-form" onSubmit={guardarCargaBorrador}>
                <label><span>{copy.loads.period}</span><input className="coord-search" required placeholder={copy.loads.example} value={periodoCarga} onChange={e => setPeriodoCarga(e.target.value)} /></label>
                <div className="coord-carga-rows">
                  {materiasCarga.map((item, index) => {
                    const usada = materiasCarga.some((otra, otroIndex) => otroIndex !== index && String(otra.materia) === String(item.materia));
                    return <div className="coord-carga-row" key={`carga-${index}`}>
                      <label><span>{copy.subjects.subject}</span><select required value={item.materia} onChange={e => {
                        const materia = catalogoCarga.materias.find(m => String(m.id) === e.target.value);
                        const docente = materia?.profesor ? catalogoCarga.docentes.find(d => d.nombre.toLowerCase() === materia.profesor.toLowerCase()) : null;
                        setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, materia: e.target.value, docente: docente ? String(docente.id) : '', horario: materia?.horario || '', salon: materia?.salon || catalogoCarga.salones[0]?.id || '', capacidad: materia?.capacidad || 42} : row));
                      }}>
                        <option value="">{cargaText.subject}</option>
                        {catalogoCarga.materias.map(m => <option key={m.id} value={m.id} disabled={usada && String(item.materia) !== String(m.id)}>{m.clave} · {m.nombre} ({m.creditos} {copy.plans.credits})</option>)}
                      </select></label>
                      <label><span>{copy.subjects.teacher}</span><select required value={item.docente} onChange={e => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, docente: e.target.value} : row))}>
                        <option value="">{cargaText.teacher}</option>{catalogoCarga.docentes.map(d => <option key={d.id} value={d.id}>{d.nombre}</option>)}
                      </select></label>
                      <label><span>{copy.subjects.schedule}</span><input required maxLength="120" value={item.horario} onChange={e => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, horario: e.target.value} : row))}/></label>
                      <label><span>{cargaText.room}</span><select required value={item.salon} onChange={e => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, salon: e.target.value} : row))}>
                        <option value="">{copy.detail.unassigned}</option>{catalogoCarga.salones.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
                      </select></label>
                      <label><span>{cargaText.capacity}</span><input type="number" min="1" max="32767" required value={item.capacidad} onChange={e => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, capacidad: e.target.value} : row))}/></label>
                      <label><span>{copy.detail.modality}</span><select required value={item.modalidad} onChange={e => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, modalidad: e.target.value} : row))}>
                        {catalogoCarga.modalidades.map(m => <option key={m.id} value={m.id}>{m.nombre}</option>)}
                      </select></label>
                      <button type="button" className="qa-btn qa-btn-secondary" onClick={() => setMateriasCarga(items => items.filter((_, rowIndex) => rowIndex !== index))}>{cargaText.remove}</button>
                    </div>;
                  })}
                </div>
                <div className="coord-action-row">
                  <button type="button" className="qa-btn qa-btn-secondary" disabled={!catalogoCarga.materias.length} onClick={agregarMateriaCarga}>{cargaText.add}</button>
                  <button type="submit" className="qa-btn" disabled={guardandoCarga || !periodoCarga.trim() || !materiasCarga.length}>{guardandoCarga ? copy.plans.saving : cargaEditando ? cargaText.update : cargaText.save}</button>
                  {cargaEditando && <button type="button" className="qa-btn qa-btn-secondary" onClick={cancelarEdicionCarga}>{cargaText.cancel}</button>}
                </div>
              </form>
              <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.loads.period}</th><th>{copy.detail.state}</th><th>{cargaText.count}</th><th>{copy.loads.created}</th><th>{copy.loads.camunda}</th><th>{copy.loads.actions}</th></tr></thead><tbody>
                {cargas.length ? cargas.map(c => <React.Fragment key={c.id}>
                  <tr><td>{c.periodo || '—'}<small>{c.creador_nombre}</small></td><td><span className={`estado-badge estado-${c.estado}`}>{etiquetaEstado(c.estado, copy)}</span></td><td>{c.materias.length}</td><td>{formatearFecha(c.created_at, copy.locale)}</td><td>{c.camunda_instance_id ? copy.loads.connected : copy.loads.pending}</td><td><div className="coord-action-row">
                    <button type="button" className="qa-btn qa-btn-secondary" onClick={() => {setCargaDetalleId(cargaDetalleId === c.id ? null : c.id); setComentarioRevision('');}}>{cargaDetalleId === c.id ? cargaText.hide : cargaText.detail}</button>
                    {c.estado === 'borrador' && <><button type="button" className="qa-btn qa-btn-secondary" onClick={() => editarCarga(c)}>{cargaText.edit}</button><button type="button" className="qa-btn" onClick={() => actualizarEstadoCarga(c.id, 'en_revision')}>{cargaText.submit}</button></>}
                    {c.estado === 'aprobada' && <div className="coord-carga-publicacion">
                      <label><span>{copy.periods.title}</span><select value={periodosPublicacionCarga[c.id] || ''} onChange={event => setPeriodosPublicacionCarga(current => ({...current, [c.id]: event.target.value}))}>
                        <option value="">—</option>{periodosInscripcion.filter(periodo => periodo.habilitado).map(periodo => <option key={periodo.id} value={periodo.id}>{periodo.nombre} · {formatearFecha(periodo.apertura, copy.locale)}</option>)}
                      </select></label>
                      <button type="button" className="qa-btn" disabled={!periodosPublicacionCarga[c.id] || cargaRevisionGuardando} onClick={() => actualizarEstadoCarga(c.id, 'publicada', '', periodosPublicacionCarga[c.id])}>{copy.loads.publish}</button>
                    </div>}
                    {c.estado === 'publicada' && <small>{c.periodo_inscripcion_nombre || c.periodo}</small>}
                  </div></td></tr>
                  {cargaDetalleId === c.id && <tr><td colSpan="6">
                    <div className="coord-carga-review">
                      <h4>{copy.loads.period}: {c.periodo} · {cargaText.count}: {c.materias.length}</h4>
                      {c.materias.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.subjects.key}</th><th>{copy.subjects.subject}</th><th>{copy.plans.credits}</th><th>{copy.subjects.teacher}</th><th>{copy.subjects.schedule}</th><th>{cargaText.room}</th><th>{cargaText.capacity}</th><th>{copy.detail.modality}</th></tr></thead><tbody>
                        {c.materias.map(m => <tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.creditos}</td><td>{m.docente_nombre || '—'}</td><td>{m.horario || '—'}</td><td>{m.salon_label}</td><td>{m.capacidad}</td><td>{m.modalidad_label}</td></tr>)}
                      </tbody></table></div> : <p className="form-hint">{cargaText.noCourses}</p>}
                      {c.comentario && c.estado !== 'en_revision' && <p className="api-success"><strong>{cargaText.reviewComment}:</strong> {c.comentario}</p>}
                      {c.estado === 'en_revision' && <>
                        <label className="coord-carga-comment"><span>{cargaText.reviewComment}</span><textarea rows="3" maxLength="2000" value={comentarioRevision} placeholder={cargaText.reviewCommentHint} onChange={e => setComentarioRevision(e.target.value)}/></label>
                        <div className="coord-action-row">
                          <button type="button" className="qa-btn" disabled={cargaRevisionGuardando || !comentarioRevision.trim()} onClick={() => actualizarEstadoCarga(c.id, 'aprobada', comentarioRevision)}>{cargaText.approveComment}</button>
                          <button type="button" className="qa-btn qa-btn-secondary" disabled={cargaRevisionGuardando || !comentarioRevision.trim()} onClick={() => actualizarEstadoCarga(c.id, 'rechazada', comentarioRevision)}>{cargaText.rejectComment}</button>
                        </div>
                      </>}
                    </div>
                  </td></tr>}
                </React.Fragment>) : <tr><td colSpan="6">{copy.loads.noLoads}</td></tr>}
              </tbody></table></div>
            </div>}
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

            {activeSection === 'egresados' && <EgresadosPanel session={session} onLogout={onLogout}/>}
            {activeSection === 'historico' && <HistoricoPanel session={session} onLogout={onLogout}/>}
            {activeSection === 'examenes' && <ExamenesGestionPanel session={session}/>}

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
                                  <button type="button" className="qa-btn" onClick={intentarAceptar} disabled={actualizando}>{copy.detail.accept}</button>
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
                            {detalle.rol === 'aspirante' && detalle.proceso_estado !== 'aceptado' && (!detalle.documentos?.length || detalle.documentos.some((documento) => !documento.revisado)) && (
                              <div className="api-error" role="alert">{copy.detail.reviewDocsFirst}</div>
                            )}
                            {detalle.documentos?.length ? (
                              <ul>
                                {detalle.documentos.map((documento) => (
                                  <li key={documento.id}>
                                    <span>{documento.tipo_label}</span>
                                    <button type="button" className="link-btn" onClick={() => verDocumento(documento)}>{copy.detail.viewFile}</button>
                                    <label className="coord-checkbox">
                                      <input
                                        type="checkbox"
                                        checked={Boolean(documento.revisado)}
                                        disabled={actualizando}
                                        onChange={(event) => revisarDocumento(documento, event.target.checked)}
                                      />
                                      {documento.revisado ? copy.detail.docReviewed : copy.detail.markDocReviewed}
                                    </label>
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
