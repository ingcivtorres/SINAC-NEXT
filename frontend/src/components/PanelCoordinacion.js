import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import ExpedienteCentralizadoCard from './ExpedienteCentralizadoCard';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import EgresadosPanel from './EgresadosPanel';
import HistoricoPanel from './HistoricoPanel';
import ExamenesGestionPanel from './ExamenesGestionPanel';
import SolicitudesAcademicasReview from './SolicitudesAcademicasReview';
import {useCoordinationCopy} from './coordinationPanelTranslations';
import './PanelCoordinacion.css';

const FILTROS = [
  {id: 'todos', key: 'all'},
  {id: 'por-revisar', key: 'review'},
  {id: 'revision', key: 'inReview'},
  {id: 'aceptado', key: 'accepted'},
  {id: 'rechazado', key: 'rejected'},
];

const COORDINATION_NAV = [
  {label: 'overview', items: [['resumen', 'Resumen', '▦'], ['bandeja', 'Bandeja de solicitudes', '◷'], ['detalle', 'Detalle de expediente', '◉']]},
  {label: 'academic', items: [['materias', 'Materias y cursos', '▤'], ['cargas', 'Preparar carga académica', '↗'], ['solicitudesAcademicas', 'Solicitudes académicas', '✉'], ['inscripciones', 'Inscripciones regulares', '✓'], ['extemporanea', 'Inscripción extemporánea', '＋'], ['examenes', 'Exámenes en línea', '✎']]},
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
  es: {student:'Alumno', chooseStudent:'Selecciona un alumno', period:'Periodo de inscripción', choosePeriod:'Selecciona un periodo', subjects:'Materias disponibles', reason:'Motivo obligatorio', reasonHint:'Explica por qué se realiza fuera del periodo regular o la situación excepcional.', intro:'Para inscripciones fuera de plazo o por una situación excepcional, envía la solicitud a Servicios Escolares. Requiere autorización para hacerse efectiva.', submit:'Enviar solicitud a Servicios Escolares', saving:'Enviando solicitud...', saved:'Solicitud enviada a Servicios Escolares. La inscripción y el oficio estarán disponibles cuando sea aprobada.', loadError:'No se pudieron cargar los datos para la inscripción.', saveError:'No se pudo enviar la solicitud.', noStudents:'No hay alumnos disponibles.', noSubjects:'No hay materias disponibles en una carga publicada para ese periodo.', capacity:'Cupo', full:'Sin cupo', loading:'Cargando materias...', stepStudent:'Alumno y periodo', stepSubjects:'Materias', stepReason:'Motivo y envío', selected:'seleccionadas', credits:'créditos', available:'disponibles'},
  en: {student:'Student', chooseStudent:'Select a student', period:'Enrollment period', choosePeriod:'Select a period', subjects:'Available subjects', reason:'Required reason', reasonHint:'Explain why this is outside the regular enrollment period or describe the exceptional situation.', intro:'For late enrollment or an exceptional situation, send a request to School Services. Approval is required for it to take effect.', submit:'Send request to School Services', saving:'Sending request...', saved:'Request sent to School Services. Enrollment and the formal letter will be available after approval.', loadError:'Could not load enrollment data.', saveError:'Could not send the request.', noStudents:'There are no students available.', noSubjects:'No subjects are available in a published course load for this period.', capacity:'Seats', full:'Full', loading:'Loading subjects...', stepStudent:'Student and period', stepSubjects:'Subjects', stepReason:'Reason and submission', selected:'selected', credits:'credits', available:'available'},
  de: {student:'Studierende', chooseStudent:'Studierende auswählen', period:'Einschreibungszeitraum', choosePeriod:'Zeitraum auswählen', subjects:'Verfügbare Fächer', reason:'Begründung erforderlich', reasonHint:'Erläutern Sie die Einschreibung außerhalb des regulären Zeitraums oder beschreiben Sie die Ausnahmesituation.', intro:'Senden Sie den Antrag an die Studienverwaltung. Die Einschreibung wird erst nach Genehmigung wirksam.', submit:'Antrag an die Studienverwaltung senden', saving:'Antrag wird gesendet...', saved:'Der Antrag wurde an die Studienverwaltung gesendet. Einschreibung und Schreiben sind nach Genehmigung verfügbar.', loadError:'Einschreibungsdaten konnten nicht geladen werden.', saveError:'Der Antrag konnte nicht gesendet werden.', noStudents:'Keine Studierenden verfügbar.', noSubjects:'Keine Fächer in einem veröffentlichten Angebot verfügbar.', capacity:'Plätze', full:'Voll', loading:'Fächer werden geladen...', stepStudent:'Studierende und Zeitraum', stepSubjects:'Fächer', stepReason:'Begründung und Versand', selected:'ausgewählt', credits:'Credits', available:'verfügbar'},
  zh: {student:'学生', chooseStudent:'选择学生', period:'注册学期', choosePeriod:'选择学期', subjects:'可选课程', reason:'必须填写原因', reasonHint:'说明为何在常规注册期外办理，或描述特殊情况。', intro:'将申请发送给学务处。只有获批后才会正式注册课程。', submit:'发送给学务处审批', saving:'正在发送申请...', saved:'申请已发送给学务处。获批后可完成注册并下载正式文件。', loadError:'无法加载注册数据。', saveError:'无法发送申请。', noStudents:'没有可用学生。', noSubjects:'该学期没有已发布课程。', capacity:'名额', full:'已满', loading:'正在加载课程...', stepStudent:'学生和学期', stepSubjects:'课程', stepReason:'原因和提交', selected:'已选', credits:'学分', available:'可用'},
  pt: {student:'Aluno', chooseStudent:'Selecione um aluno', period:'Período de inscrição', choosePeriod:'Selecione um período', subjects:'Disciplinas disponíveis', reason:'Motivo obrigatório', reasonHint:'Explique por que a inscrição ocorre fora do prazo regular ou descreva a situação excepcional.', intro:'Envie a solicitação aos Serviços Escolares. A inscrição só será efetivada após aprovação.', submit:'Enviar solicitação aos Serviços Escolares', saving:'Enviando solicitação...', saved:'Solicitação enviada aos Serviços Escolares. A inscrição e o ofício estarão disponíveis após aprovação.', loadError:'Não foi possível carregar os dados da inscrição.', saveError:'Não foi possível enviar a solicitação.', noStudents:'Não há alunos disponíveis.', noSubjects:'Não há disciplinas em uma oferta publicada para esse período.', capacity:'Vagas', full:'Sem vagas', loading:'Carregando disciplinas...', stepStudent:'Aluno e período', stepSubjects:'Disciplinas', stepReason:'Motivo e envio', selected:'selecionadas', credits:'créditos', available:'disponíveis'},
};

const INSCRIPCION_REGULAR_TEXT = {
  es: {intro:'Registra la carga regular del alumno mientras Servicios Escolares mantenga abierto el periodo. La inscripción quedará pendiente de validación administrativa.', noPeriod:'No hay un periodo abierto. Solicita a Servicios Escolares que habilite el periodo de inscripción.', student:'Alumno', chooseStudent:'Selecciona un alumno', period:'Periodo vigente', subjects:'Materias disponibles', chooseStudentFirst:'Selecciona un alumno para consultar sus materias.', noSubjects:'No hay materias disponibles en la carga publicada de este periodo.', completed:'El alumno ya completó las cuatro materias de este periodo.', remaining:'materias por seleccionar para completar las 4 del periodo', submit:'Registrar inscripción regular', saving:'Registrando inscripción...', saved:'Inscripción registrada. Está pendiente de validación de Servicios Escolares.', loadError:'No se pudo cargar la información de inscripción.', saveError:'No se pudo registrar la inscripción.', noStudents:'No hay alumnos disponibles.', capacity:'Cupo', full:'Sin cupo', selected:'seleccionadas', credits:'créditos', available:'disponibles', pendingValidation:'La boleta formal estará disponible cuando Servicios Escolares valide todas las materias.', downloadSlip:'Descargar boleta formal', downloadError:'No se pudo descargar la boleta formal.', extRequests:'Solicitudes extemporáneas del alumno', pending:'Pendiente de autorización', approved:'Aprobada', rejected:'Rechazada', downloadOffice:'Descargar oficio formal'},
  en: {intro:'Register the student’s regular course load while School Services keeps enrollment open. The enrollment will remain pending administrative validation.', noPeriod:'There is no open enrollment period. Ask School Services to open one.', student:'Student', chooseStudent:'Select a student', period:'Current period', subjects:'Available subjects', chooseStudentFirst:'Select a student to view available subjects.', noSubjects:'No subjects are available in the published course load for this period.', completed:'The student has completed the four subjects for this period.', remaining:'subjects left to complete the 4 for this period', submit:'Register regular enrollment', saving:'Registering enrollment...', saved:'Enrollment registered. It is pending School Services validation.', loadError:'Could not load enrollment information.', saveError:'Could not register the enrollment.', noStudents:'There are no students available.', capacity:'Capacity', full:'Full', selected:'selected', credits:'credits', available:'available', pendingValidation:'The formal enrollment slip will be available after School Services validates all subjects.', downloadSlip:'Download formal enrollment slip', downloadError:'Could not download the formal enrollment slip.', extRequests:'Student late-enrollment requests', pending:'Pending approval', approved:'Approved', rejected:'Rejected', downloadOffice:'Download formal letter'},
  de: {intro:'Registrieren Sie die reguläre Kursbelegung, solange die Einschreibung durch die Studienverwaltung geöffnet ist. Die Einschreibung bleibt bis zur administrativen Prüfung ausstehend.', noPeriod:'Es gibt keinen offenen Einschreibungszeitraum. Bitten Sie die Studienverwaltung, einen Zeitraum zu öffnen.', student:'Studierende', chooseStudent:'Studierende auswählen', period:'Aktueller Zeitraum', subjects:'Verfügbare Fächer', chooseStudentFirst:'Wählen Sie Studierende aus, um verfügbare Fächer anzuzeigen.', noSubjects:'Im veröffentlichten Lehrangebot dieses Zeitraums sind keine Fächer verfügbar.', completed:'Die vier Fächer dieses Zeitraums wurden bereits abgeschlossen.', remaining:'Fächer fehlen, um die 4 für diesen Zeitraum zu vervollständigen', submit:'Reguläre Einschreibung registrieren', saving:'Einschreibung wird registriert...', saved:'Einschreibung registriert. Die administrative Prüfung durch die Studienverwaltung steht noch aus.', loadError:'Einschreibungsdaten konnten nicht geladen werden.', saveError:'Einschreibung konnte nicht registriert werden.', noStudents:'Keine Studierenden verfügbar.', capacity:'Kapazität', full:'Voll', selected:'ausgewählt', credits:'Credits', available:'verfügbar', pendingValidation:'Die formelle Einschreibebescheinigung ist nach der Prüfung aller Fächer durch die Studienverwaltung verfügbar.', downloadSlip:'Formelle Einschreibebescheinigung herunterladen', downloadError:'Die Bescheinigung konnte nicht heruntergeladen werden.', extRequests:'Anträge auf nachträgliche Einschreibung', pending:'Genehmigung ausstehend', approved:'Genehmigt', rejected:'Abgelehnt', downloadOffice:'Formelles Schreiben herunterladen'},
  zh: {intro:'在学务处开放注册期间，为学生登记常规课程。注册记录将等待学务处行政审核。', noPeriod:'当前没有开放的注册学期。请联系学务处开放注册。', student:'学生', chooseStudent:'选择学生', period:'当前学期', subjects:'可选课程', chooseStudentFirst:'选择学生以查看可选课程。', noSubjects:'本学期已发布的课程安排中没有可选课程。', completed:'该学生已完成本学期四门课程。', remaining:'门课程待选，以完成本学期4门课程', submit:'登记常规注册', saving:'正在登记...', saved:'注册已登记，等待学务处行政审核。', loadError:'无法加载注册信息。', saveError:'无法登记注册。', noStudents:'没有可用学生。', capacity:'名额', full:'已满', selected:'已选', credits:'学分', available:'可用', pendingValidation:'学务处审核全部课程后，可下载正式注册证明。', downloadSlip:'下载正式注册证明', downloadError:'无法下载正式注册证明。', extRequests:'学生的逾期注册申请', pending:'等待批准', approved:'已批准', rejected:'已拒绝', downloadOffice:'下载正式函件'},
  pt: {intro:'Registre a carga regular do aluno enquanto os Serviços Escolares mantiverem o período aberto. A inscrição ficará pendente de validação administrativa.', noPeriod:'Não há período de inscrição aberto. Solicite aos Serviços Escolares que o habilitem.', student:'Aluno', chooseStudent:'Selecione um aluno', period:'Período vigente', subjects:'Disciplinas disponíveis', chooseStudentFirst:'Selecione um aluno para consultar as disciplinas disponíveis.', noSubjects:'Não há disciplinas disponíveis na carga publicada deste período.', completed:'O aluno já completou as quatro disciplinas deste período.', remaining:'disciplinas restantes para completar as 4 do período', submit:'Registrar inscrição regular', saving:'Registrando inscrição...', saved:'Inscrição registrada. Está pendente de validação dos Serviços Escolares.', loadError:'Não foi possível carregar os dados da inscrição.', saveError:'Não foi possível registrar a inscrição.', noStudents:'Não há alunos disponíveis.', capacity:'Vagas', full:'Sem vagas', selected:'selecionadas', credits:'créditos', available:'disponíveis', pendingValidation:'O comprovante formal ficará disponível quando os Serviços Escolares validarem todas as disciplinas.', downloadSlip:'Baixar comprovante formal', downloadError:'Não foi possível baixar o comprovante formal.', extRequests:'Solicitações extemporâneas do aluno', pending:'Aguardando aprovação', approved:'Aprovada', rejected:'Rejeitada', downloadOffice:'Baixar ofício formal'},
};

export default function PanelCoordinacion({session, onLogout: onLogoutProp}) {
  const onLogoutRef = useRef(onLogoutProp);
  onLogoutRef.current = onLogoutProp;
  const onLogout = useCallback((...args) => onLogoutRef.current?.(...args), []);
  const copy = useCoordinationCopy();
  const extText = EXTEMPORANEO_TEXT[copy.locale.slice(0, 2)] || EXTEMPORANEO_TEXT.es;
  const regularText = INSCRIPCION_REGULAR_TEXT[copy.locale.slice(0, 2)] || INSCRIPCION_REGULAR_TEXT.es;
  const cargaText = CARGA_FORM_TEXT[(document.documentElement.lang || 'es').slice(0, 2)] || CARGA_FORM_TEXT.es;
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);
  const [filtro, setFiltro] = useState('por-revisar');
  const [notificacionGrupo, setNotificacionGrupo] = useState('por-revisar');
  const [notificacionSeleccionados, setNotificacionSeleccionados] = useState(null);
  const [notificacionMensaje, setNotificacionMensaje] = useState('');
  const [notificacionIncluirFechas, setNotificacionIncluirFechas] = useState(true);
  const [notificacionEnviando, setNotificacionEnviando] = useState(false);
  const [notificacionError, setNotificacionError] = useState('');
  const [notificacionResultado, setNotificacionResultado] = useState(null);
  const [seleccionado, setSeleccionado] = useState(null);
  const [detalle, setDetalle] = useState(null);
  const [detalleCargando, setDetalleCargando] = useState(false);
  const [editData, setEditData] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState('');
  const [materias, setMaterias] = useState(null);
  const [materiasCargando, setMateriasCargando] = useState(false);
  const [materiasError, setMateriasError] = useState('');
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
  const [alumnoRegularId, setAlumnoRegularId] = useState('');
  const [inscripcionRegular, setInscripcionRegular] = useState(null);
  const [materiasRegularesSeleccionadas, setMateriasRegularesSeleccionadas] = useState([]);
  const [cargandoRegular, setCargandoRegular] = useState(false);
  const [guardandoRegular, setGuardandoRegular] = useState(false);
  const [recargaRegular, setRecargaRegular] = useState(0);
  const [alumnoExtemporaneoId, setAlumnoExtemporaneoId] = useState('');
  const [periodoExtemporaneoId, setPeriodoExtemporaneoId] = useState('');
  const [periodosExtemporaneos, setPeriodosExtemporaneos] = useState([]);
  const [materiasExtemporaneas, setMateriasExtemporaneas] = useState([]);
  const [solicitudesExtemporaneasAlumno, setSolicitudesExtemporaneasAlumno] = useState([]);
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
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || `${copy.messages.loadCharges} (HTTP ${r.status})`);
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

  async function enviarCargaRevision(id) {
    setError('');
    setSaveSuccess('');
    try {
      const response = await fetch(`/api/cargas-academicas/${id}/`, {
        method: 'PATCH',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({estado: 'en_revision'}),
      });
      const data = await response.json().catch(() => ({}));
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (!response.ok) throw new Error(data.detail || copy.loads.updateError);
      setSaveSuccess(copy.loads.sent);
      await cargarFlujoCargas();
    } catch (error) {
      setError(error.message || copy.loads.updateError);
    }
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
  useEffect(() => {
    if (activeSection !== 'inscripciones') return undefined;
    const controller = new AbortController();
    setCargandoRegular(true);
    setError('');
    const endpoint = alumnoRegularId
      ? `/api/coordinacion/alumnos/${alumnoRegularId}/inscripciones-regulares/`
      : '/api/periodos-inscripcion/';
    fetch(endpoint, {headers: {Authorization: `Bearer ${session.access}`}, signal: controller.signal})
      .then(async response => {
        const body = await response.json().catch(() => ({}));
        if (response.status === 401) {
          onLogout(copy.messages.expired);
          throw Object.assign(new Error(), {name: 'AbortError'});
        }
        if (!response.ok) throw new Error(body.detail || regularText.loadError);
        return body;
      })
      .then(body => {
        if (alumnoRegularId) {
          setInscripcionRegular(body);
        } else {
          setInscripcionRegular({periodo: body?.activo ? body : null, materias: [], faltantes: 0, registradas: 0});
        }
        setMateriasRegularesSeleccionadas([]);
      })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message || regularText.loadError); })
      .finally(() => { if (!controller.signal.aborted) setCargandoRegular(false); });
    return () => controller.abort();
  }, [activeSection, alumnoRegularId, recargaRegular, session.access, onLogout, copy.messages.expired, regularText.loadError]);
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
    if (activeSection !== 'extemporanea' || !alumnoExtemporaneoId) {
      setMateriasExtemporaneas([]);
      setPeriodosExtemporaneos([]);
      setSolicitudesExtemporaneasAlumno([]);
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
        setSolicitudesExtemporaneasAlumno(body.solicitudes || []);
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

  async function registrarInscripcionRegular(event) {
    event.preventDefault();
    const faltantes = inscripcionRegular?.faltantes || 0;
    if (!alumnoRegularId || !inscripcionRegular?.periodo?.activo || !faltantes || materiasRegularesSeleccionadas.length !== faltantes) {
      setError(regularText.saveError);
      return;
    }
    setGuardandoRegular(true);
    setError('');
    setSaveSuccess('');
    try {
      const response = await fetch(`/api/coordinacion/alumnos/${alumnoRegularId}/inscripciones-regulares/`, {
        method: 'POST',
        headers: {Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({materias: materiasRegularesSeleccionadas}),
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (!response.ok) throw new Error(body.detail || body.materias || regularText.saveError);
      setMateriasRegularesSeleccionadas([]);
      setSaveSuccess(regularText.saved);
      setRecargaRegular(value => value + 1);
    } catch (err) {
      setError(err.message || regularText.saveError);
    } finally {
      setGuardandoRegular(false);
    }
  }

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
  const aspirantesNotificables = useMemo(() => aspirantesRegistrados.filter(aspirante => {
    if (notificacionGrupo === 'por-revisar') return ['pendiente', 'iniciado'].includes(aspirante.proceso_estado);
    return notificacionGrupo === 'todos' || aspirante.proceso_estado === notificacionGrupo;
  }), [aspirantesRegistrados, notificacionGrupo]);
  const notificacionDestinatarios = useMemo(() => notificacionSeleccionados === null
    ? aspirantesNotificables
    : aspirantesNotificables.filter(aspirante => notificacionSeleccionados.includes(aspirante.id)),
  [aspirantesNotificables, notificacionSeleccionados]);
  const notificacionConCorreo = useMemo(
    () => notificacionDestinatarios.filter(aspirante => Boolean(aspirante.correo?.trim())),
    [notificacionDestinatarios],
  );
  const notificacionSinCorreo = notificacionDestinatarios.length - notificacionConCorreo.length;
  const alumnos = useMemo(() => (datos?.personas || []).filter(a => a.rol === 'alumno'), [datos]);
  const docentes = useMemo(() => (datos?.personas || []).filter(a => ['docente','director'].includes(a.rol)), [datos]);
  const directores = useMemo(() => (datos?.personas || []).filter(a => a.rol === 'director' && a.is_active !== false), [datos]);
  const filtrarPersonas = (lista) => lista.filter(a => !busqueda.trim() || `${a.nombre} ${a.usuario} ${a.correo}`.toLowerCase().includes(busqueda.toLowerCase()));
  const analitica = useMemo(() => { const lista=datos?.personas||[]; const total=lista.length||1; const estados=['pendiente','revision','aceptado','rechazado']; return {total:lista.length, aspirantes:lista.filter(a=>a.rol==='aspirante').length, alumnos:lista.filter(a=>a.rol==='alumno').length, personal:lista.filter(a=>['docente','director'].includes(a.rol)).length, estados:estados.map(e=>({key:e,label:etiquetaEstado(e, copy),count:lista.filter(a=>a.rol==='aspirante'&&a.proceso_estado===e).length,pct:Math.round(lista.filter(a=>a.rol==='aspirante'&&a.proceso_estado===e).length*100/Math.max(1,lista.filter(a=>a.rol==='aspirante').length))}))}; }, [copy, datos]);
  const evaluacionesVisibles = useMemo(() => evaluacionFiltro === 'todas' ? evaluacionesColegio : evaluacionesColegio.filter(e => e.estado === evaluacionFiltro), [evaluacionesColegio, evaluacionFiltro]);

  async function enviarNotificacionesMasivas() {
    if (!notificacionConCorreo.length) {
      setNotificacionError(copy.notifications.selectRecipients);
      return;
    }
    const confirmar = `${copy.notifications.confirm} ${notificacionConCorreo.length} ${copy.notifications.recipients}?`;
    if (!window.confirm(confirmar)) return;

    setNotificacionEnviando(true);
    setNotificacionError('');
    setNotificacionResultado(null);
    try {
      const response = await fetch('/api/coordinacion/notificaciones-masivas/', {
        method: 'POST',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({
          grupo: notificacionGrupo,
          ids: notificacionConCorreo.map(aspirante => aspirante.id),
          mensaje: notificacionMensaje,
          incluir_fechas: notificacionIncluirFechas,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || body.ids || body.grupo || copy.notifications.sendError);
      setNotificacionResultado({
        ...body,
        sin_correo_seleccionados: notificacionDestinatarios
          .filter(aspirante => !aspirante.correo?.trim())
          .map(aspirante => ({id: aspirante.id, nombre: aspirante.nombre})),
      });
      setNotificacionSeleccionados(null);
      setNotificacionMensaje('');
    } catch (err) {
      setNotificacionError(err.message || copy.notifications.sendError);
    } finally {
      setNotificacionEnviando(false);
    }
  }

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
  async function downloadBlob(url, filename, errorMessage = copy.detail.downloadError) {
    try {
      const resp = await fetch(url, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}));
        throw new Error(body.detail || errorMessage);
      }
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
      setError(err.message || errorMessage);
    }
  }

  async function descargarBoletaRegular() {
    if (!alumnoRegularId || !inscripcionRegular?.periodo?.id) return;
    const persona = (datos.personas || []).find(item => String(item.id) === String(alumnoRegularId));
    await downloadBlob(
      `/api/coordinacion/alumnos/${alumnoRegularId}/inscripciones-regulares/boleta/?periodo=${inscripcionRegular.periodo.id}`,
      `${persona?.matricula || persona?.usuario || alumnoRegularId}_boleta_inscripcion_regular.pdf`,
      regularText.downloadError,
    );
  }

  async function descargarOficioExtemporaneo(solicitud) {
    await downloadBlob(
      `/api/coordinacion/solicitudes-extemporaneas/${solicitud.id}/oficio/`,
      `${solicitud.folio}_oficio_inscripcion_extemporanea.pdf`,
      regularText.downloadError,
    );
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

  const cargarMateriasDisponibles = useCallback(async () => {
    setMateriasCargando(true);
    setMateriasError('');
    try {
      const resp = await fetch('/api/coordinacion/materias/', {headers: {Authorization: `Bearer ${session.access}`}});
      if (resp.status === 401) {
        onLogout(copy.messages.expired);
        return;
      }
      if (!resp.ok) {
        let detail = '';
        if (resp.headers.get('content-type')?.includes('application/json')) {
          try {
            const body = await resp.json();
            detail = body.detail || '';
          } catch {
            detail = '';
          }
        }
        throw new Error(`${copy.subjects.noSubjects} (HTTP ${resp.status})${detail ? `: ${detail}` : ''}`);
      }
      const data = await resp.json();
      if (!Array.isArray(data)) throw new Error(copy.subjects.noSubjects);
      setMaterias(data);
    } catch (err) {
      setMaterias(null);
      setMateriasError(err.message || copy.subjects.noSubjects);
    } finally {
      setMateriasCargando(false);
    }
  }, [copy.messages.expired, copy.subjects.noSubjects, onLogout, session.access]);

  useEffect(() => {
    if (activeSection === 'materias') cargarMateriasDisponibles();
  }, [activeSection, cargarMateriasDisponibles]);

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

            {activeSection === 'inscripciones' && (
              <section className="panel-card coord-plan-panel coord-inscripciones-regulares">
                <header className="admin-card-head coord-extemporanea-header">
                  <div><p className="panel-kicker">{copy.groups.academic}</p><h3>{copy.nav.inscripciones}</h3><p>{regularText.intro}</p></div>
                </header>
                {error && <div className="api-error" role="alert">{error}</div>}
                {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}
                <form className="coord-plan-form" onSubmit={registrarInscripcionRegular}>
                  <div className="coord-plan-fields coord-extemporanea-fields">
                    <label className="coord-extemporanea-field"><span>{regularText.student}</span>
                      <select value={alumnoRegularId} onChange={event => {
                        setAlumnoRegularId(event.target.value);
                        setMateriasRegularesSeleccionadas([]);
                        setSaveSuccess('');
                      }} required>
                        <option value="">{regularText.chooseStudent}</option>
                        {(datos.personas || []).filter(persona => persona.rol === 'alumno').map(persona => (
                          <option key={persona.id} value={persona.id}>{persona.nombre} · {persona.matricula || persona.programa || ''}</option>
                        ))}
                      </select>
                    </label>
                    <div className="coord-regular-period">
                      <span>{regularText.period}</span>
                      {inscripcionRegular?.periodo?.activo
                        ? <strong>{inscripcionRegular.periodo.nombre} · {formatearFecha(inscripcionRegular.periodo.apertura, copy.locale)} – {formatearFecha(inscripcionRegular.periodo.cierre, copy.locale)}</strong>
                        : <strong>{regularText.noPeriod}</strong>}
                    </div>
                  </div>
                  {cargandoRegular ? <p className="coord-plan-notice">{extText.loading}</p> : !inscripcionRegular?.periodo?.activo ? (
                    <p className="coord-plan-notice" role="status">{regularText.noPeriod}</p>
                  ) : !alumnoRegularId ? (
                    <p className="coord-plan-notice">{regularText.chooseStudentFirst}</p>
                  ) : inscripcionRegular.faltantes === 0 ? (
                    <p className="coord-regular-complete" role="status">{regularText.completed}</p>
                  ) : inscripcionRegular.materias.length ? (
                    <section className="coord-extemporanea-subjects" aria-labelledby="coord-regular-subjects-title">
                      <div className="coord-plan-course-heading coord-extemporanea-subject-heading">
                        <div><h4 id="coord-regular-subjects-title">{regularText.subjects}</h4><p>{inscripcionRegular.faltantes} {regularText.remaining}</p></div>
                        <span className="coord-extemporanea-count">{materiasRegularesSeleccionadas.length}/{inscripcionRegular.faltantes} {regularText.selected}</span>
                      </div>
                      <div className="coord-plan-course-list coord-extemporanea-course-list">
                        {inscripcionRegular.materias.map(materia => {
                          const sinCupo = materia.inscritos >= materia.capacidad;
                          const marcada = materiasRegularesSeleccionadas.includes(materia.id);
                          const bloqueadaPorLimite = materiasRegularesSeleccionadas.length >= inscripcionRegular.faltantes && !marcada;
                          const lugaresDisponibles = Math.max(0, materia.capacidad - materia.inscritos);
                          return (
                            <label className={`coord-plan-course-row coord-extemporanea-course${marcada ? ' is-selected' : ''}${sinCupo ? ' is-full' : ''}`} key={materia.id}>
                              <input type="checkbox" checked={marcada} disabled={sinCupo || bloqueadaPorLimite} onChange={event => setMateriasRegularesSeleccionadas(current => (
                                event.target.checked ? [...current, materia.id] : current.filter(id => id !== materia.id)
                              ))}/>
                              <span className="coord-extemporanea-course-info"><strong>{materia.clave} · {materia.nombre}</strong><small>{materia.creditos} {copy.plans.credits} · {materia.horario || copy.subjects.define}</small></span>
                              <span className="coord-extemporanea-capacity"><span><strong>{lugaresDisponibles}</strong> {regularText.available} · {regularText.capacity} {materia.inscritos}/{materia.capacidad}{sinCupo ? ` · ${regularText.full}` : ''}</span></span>
                            </label>
                          );
                        })}
                      </div>
                    </section>
                  ) : <p className="coord-plan-notice">{regularText.noSubjects}</p>}
                  {datos && !(datos.personas || []).some(persona => persona.rol === 'alumno') && <p className="coord-plan-notice">{regularText.noStudents}</p>}
                  <div className="coord-extemporanea-footer">
                    <p>{materiasRegularesSeleccionadas.length}/{inscripcionRegular?.faltantes || 0} {regularText.selected}</p>
                    <button type="submit" className="qa-btn" disabled={guardandoRegular || cargandoRegular || !alumnoRegularId || !inscripcionRegular?.periodo?.activo || !inscripcionRegular.faltantes || materiasRegularesSeleccionadas.length !== inscripcionRegular.faltantes}>{guardandoRegular ? regularText.saving : regularText.submit}</button>
                  </div>
                </form>
                {alumnoRegularId && inscripcionRegular?.periodo?.id && (inscripcionRegular.validacion_servicios || []).length > 0 && (
                  <div className="coord-enrollment-document">
                    {(inscripcionRegular.validacion_servicios || []).every(value => value === 'validada')
                      ? <button type="button" className="qa-btn" onClick={descargarBoletaRegular}>{regularText.downloadSlip}</button>
                      : <p role="status">{regularText.pendingValidation}</p>}
                  </div>
                )}
              </section>
            )}

            {activeSection === 'solicitudesAcademicas' && <SolicitudesAcademicasReview session={session} onLogout={onLogout}/>}

            {activeSection === 'extemporanea' && (
              <section className="panel-card coord-plan-panel coord-extemporanea">
                <header className="admin-card-head coord-extemporanea-header">
                  <div><p className="panel-kicker">{copy.groups.academic}</p><h3>{copy.nav.extemporanea}</h3><p>{extText.intro}</p></div>
                  <span className="coord-extemporanea-badge">{extText.stepReason}</span>
                </header>
                <ol className="coord-extemporanea-steps" aria-label={copy.nav.extemporanea}>
                  {[extText.stepStudent, extText.stepSubjects, extText.stepReason].map((step, index) => (
                    <li className={`coord-extemporanea-step${index === 0 && alumnoExtemporaneoId || index === 1 && materiasExtemporaneasSeleccionadas.length || index === 2 && motivoExtemporaneo.trim() ? ' is-complete' : ''}`} key={step}>
                      <span>{index + 1}</span><strong>{step}</strong>
                    </li>
                  ))}
                </ol>
                <form className="coord-plan-form coord-extemporanea-form" onSubmit={registrarInscripcionExtemporanea}>
                  <div className="coord-plan-fields coord-extemporanea-fields">
                    <label className="coord-extemporanea-field"><span>{extText.student}</span>
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
                    <label className="coord-extemporanea-field"><span>{extText.period}</span>
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
                  <section className="coord-extemporanea-subjects" aria-labelledby="coord-extemporanea-subjects-title">
                    <div className="coord-plan-course-heading coord-extemporanea-subject-heading">
                      <div><h4 id="coord-extemporanea-subjects-title">{extText.subjects}</h4><p>{extText.capacity} {extText.available}</p></div>
                      <span className="coord-extemporanea-count">{materiasExtemporaneasSeleccionadas.length} {extText.selected}</span>
                    </div>
                    {cargandoExtemporanea ? <p className="coord-plan-notice">{extText.loading}</p> : materiasExtemporaneas.length ? (
                    <div className="coord-plan-course-list coord-extemporanea-course-list">
                      {materiasExtemporaneas.map(materia => {
                        const sinCupo = materia.inscritos >= materia.capacidad;
                        const marcada = materiasExtemporaneasSeleccionadas.includes(materia.id);
                        const lugaresDisponibles = Math.max(0, materia.capacidad - materia.inscritos);
                        const porcentajeOcupacion = materia.capacidad > 0 ? Math.min(100, Math.round(materia.inscritos * 100 / materia.capacidad)) : 100;
                        return (
                          <label className={`coord-plan-course-row coord-extemporanea-course${marcada ? ' is-selected' : ''}${sinCupo ? ' is-full' : ''}`} key={materia.id}>
                            <input type="checkbox" checked={marcada} disabled={sinCupo} onChange={event => setMateriasExtemporaneasSeleccionadas(current => (
                              event.target.checked
                                ? [...current, materia.id]
                                : current.filter(id => id !== materia.id)
                            ))}/>
                            <span className="coord-extemporanea-course-info"><strong>{materia.clave} · {materia.nombre}</strong><small>{materia.creditos} {copy.plans.credits} · {materia.horario || copy.subjects.define}</small></span>
                            <span className="coord-extemporanea-capacity">
                              <span><strong>{lugaresDisponibles}</strong> {extText.available} · {extText.capacity} {materia.inscritos}/{materia.capacidad}{sinCupo ? ` · ${extText.full}` : ''}</span>
                              <span className="coord-extemporanea-capacity-track" role="progressbar" aria-label={`${extText.capacity}: ${materia.inscritos}/${materia.capacidad}`} aria-valuemin="0" aria-valuemax={materia.capacidad} aria-valuenow={Math.min(materia.inscritos, materia.capacidad)}><i style={{width: `${porcentajeOcupacion}%`}}/></span>
                            </span>
                          </label>
                        );
                      })}
                    </div>
                    ) : <p className="coord-plan-notice">{alumnoExtemporaneoId && periodoExtemporaneoId ? extText.noSubjects : extText.chooseStudent}</p>}
                  </section>
                  <label className="coord-plan-reason coord-extemporanea-reason"><span>{extText.reason}</span>
                    <textarea rows="4" value={motivoExtemporaneo} onChange={event => setMotivoExtemporaneo(event.target.value)} placeholder={extText.reasonHint} required maxLength="2000" aria-describedby="coord-extemporanea-reason-count"/>
                    <small id="coord-extemporanea-reason-count" className="coord-extemporanea-character-count">{motivoExtemporaneo.length}/2000</small>
                  </label>
                  <div className="coord-extemporanea-footer">
                    <p>{materiasExtemporaneasSeleccionadas.length} {extText.selected}</p>
                    <button type="submit" className="qa-btn" disabled={guardandoExtemporanea || !alumnoExtemporaneoId || !periodoExtemporaneoId || !materiasExtemporaneasSeleccionadas.length || !motivoExtemporaneo.trim()}>{guardandoExtemporanea ? extText.saving : extText.submit}</button>
                  </div>
                  {error && <div className="api-error" role="alert">{error}</div>}
                  {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}
                  {!alumnoExtemporaneoId && !(datos.personas || []).some(persona => persona.rol === 'alumno') && <p className="coord-plan-notice">{extText.noStudents}</p>}
                </form>
                {alumnoExtemporaneoId && solicitudesExtemporaneasAlumno.length > 0 && (
                  <section className="coord-extemporanea-documents" aria-label={regularText.extRequests}>
                    <h4>{regularText.extRequests}</h4>
                    {solicitudesExtemporaneasAlumno.map(solicitud => (
                      <div className="coord-extemporanea-document-row" key={solicitud.id}>
                        <span><strong>{solicitud.folio}</strong><small>{solicitud.periodo}</small></span>
                        <span className={`estado-badge estado-${solicitud.estado}`}>{regularText[solicitud.estado] || solicitud.estado}</span>
                        {solicitud.estado === 'aprobada' && <button type="button" className="qa-btn" onClick={() => descargarOficioExtemporaneo(solicitud)}>{regularText.downloadOffice}</button>}
                      </div>
                    ))}
                  </section>
                )}
              </section>
            )}

            {activeSection === 'materias' && <div className="panel-card coord-directory coord-materias-card"><div className="admin-card-head"><div><p className="panel-kicker">{copy.subjects.kicker}</p><h3>{copy.subjects.title}</h3><p>{copy.subjects.intro}</p></div><div className="coord-action-row"><button type="button" className="qa-btn" onClick={cargarMateriasDisponibles} disabled={materiasCargando}>{materiasCargando ? copy.subjects.loading : materiasError ? copy.retry : copy.subjects.query}</button></div></div>{materiasError && <div className="api-error coord-catalog-error" role="alert">{materiasError}</div>}{materiasCargando ? <p className="empty-state" role="status">{copy.subjects.loading}</p> : materias !== null ? materias.length ? <><div className="coord-catalog-summary"><span>{materias.length} {copy.directory.subjects}</span><span>{copy.subjects.readOnly}</span></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.subjects.key}</th><th>{copy.subjects.subject}</th><th>{copy.subjects.credits}</th><th>{copy.subjects.teacher}</th><th>{copy.subjects.schedule}</th></tr></thead><tbody>{materias.map(m=><tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.creditos ?? '—'}</td><td>{m.profesor || copy.subjects.assign}</td><td>{m.horario || copy.subjects.define}</td></tr>)}</tbody></table></div></> : <p className="empty-state">{copy.detail.noSubjects}</p> : !materiasError && <p className="empty-state">{copy.subjects.noCatalog}</p>}</div>}
            {activeSection === 'cargas' && <div className="panel-card coord-directory">
              <div className="admin-card-head"><div><p className="panel-kicker">{copy.loads.kicker}</p><h3>{copy.loads.title}</h3><p>{copy.loads.intro}</p></div><button type="button" className="qa-btn" onClick={cargarFlujoCargas}>{copy.refresh}</button></div>
              <form className="coord-carga-form" onSubmit={guardarCargaBorrador}>
                <label><span>{copy.loads.period}</span><input className="coord-search" required placeholder={copy.loads.example} value={periodoCarga} onChange={event => setPeriodoCarga(event.target.value)} /></label>
                <div className="coord-carga-rows">
                  {materiasCarga.map((item, index) => {
                    const usada = materiasCarga.some((otra, otroIndex) => otroIndex !== index && String(otra.materia) === String(item.materia));
                    return <div className="coord-carga-row" key={`carga-${index}`}>
                      <label><span>{copy.subjects.subject}</span><select required value={item.materia} onChange={event => {
                        const materia = catalogoCarga.materias.find(subject => String(subject.id) === event.target.value);
                        const docente = materia?.profesor ? catalogoCarga.docentes.find(teacher => teacher.nombre.toLowerCase() === materia.profesor.toLowerCase()) : null;
                        setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, materia: event.target.value, docente: docente ? String(docente.id) : '', horario: materia?.horario || '', salon: materia?.salon || catalogoCarga.salones[0]?.id || '', capacidad: materia?.capacidad || 42} : row));
                      }}>
                        <option value="">{cargaText.subject}</option>
                        {catalogoCarga.materias.map(subject => <option key={subject.id} value={subject.id} disabled={usada && String(item.materia) !== String(subject.id)}>{subject.clave} - {subject.nombre} ({subject.creditos} {copy.plans.credits})</option>)}
                      </select></label>
                      <label><span>{copy.subjects.teacher}</span><select required value={item.docente} onChange={event => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, docente: event.target.value} : row))}>
                        <option value="">{cargaText.teacher}</option>{catalogoCarga.docentes.map(teacher => <option key={teacher.id} value={teacher.id}>{teacher.nombre}</option>)}
                      </select></label>
                      <label><span>{copy.subjects.schedule}</span><input required maxLength="120" value={item.horario} onChange={event => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, horario: event.target.value} : row))}/></label>
                      <label><span>{cargaText.room}</span><select required value={item.salon} onChange={event => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, salon: event.target.value} : row))}>
                        <option value="">{copy.detail.unassigned}</option>{catalogoCarga.salones.map(room => <option key={room.id} value={room.id}>{room.nombre}</option>)}
                      </select></label>
                      <label><span>{cargaText.capacity}</span><input type="number" min="1" max="32767" required value={item.capacidad} onChange={event => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, capacidad: event.target.value} : row))}/></label>
                      <label><span>{copy.detail.modality}</span><select required value={item.modalidad} onChange={event => setMateriasCarga(items => items.map((row, rowIndex) => rowIndex === index ? {...row, modalidad: event.target.value} : row))}>
                        {catalogoCarga.modalidades.map(modality => <option key={modality.id} value={modality.id}>{modality.nombre}</option>)}
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
              <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>{copy.loads.period}</th><th>{copy.detail.state}</th><th>{cargaText.count}</th><th>{copy.loads.created}</th><th>{copy.loads.actions}</th></tr></thead><tbody>
                {cargas.length ? cargas.map(carga => <tr key={carga.id}><td>{carga.periodo || '-'}<small>{carga.creador_nombre}</small></td><td><span className={`estado-badge estado-${carga.estado}`}>{etiquetaEstado(carga.estado, copy)}</span></td><td>{carga.materias.length}</td><td>{formatearFecha(carga.created_at, copy.locale)}</td><td><div className="coord-action-row">
                  {carga.estado === 'borrador' && <><button type="button" className="qa-btn qa-btn-secondary" onClick={() => editarCarga(carga)}>{cargaText.edit}</button><button type="button" className="qa-btn" disabled={!carga.materias.length} onClick={() => enviarCargaRevision(carga.id)}>{cargaText.submit}</button></>}
                </div></td></tr>) : <tr><td colSpan="5">{copy.loads.noLoads}</td></tr>}
              </tbody></table></div>
            </div>}
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
                  <div className="panel-card coord-bulk-notification">
                    <div className="coord-bulk-heading">
                      <div>
                        <p className="panel-kicker">{copy.notifications.title}</p>
                        <p>{copy.notifications.intro}</p>
                      </div>
                      <span className="coord-bulk-count">{notificacionDestinatarios.length} / {aspirantesNotificables.length} {copy.notifications.recipients}</span>
                    </div>
                    <div className="coord-bulk-controls">
                      <label>
                        <span>{copy.notifications.target}</span>
                        <select value={notificacionGrupo} onChange={event => {
                          setNotificacionGrupo(event.target.value);
                          setNotificacionSeleccionados(null);
                          setNotificacionResultado(null);
                          setNotificacionError('');
                        }}>
                          <option value="por-revisar">{copy.filters.review}</option>
                          <option value="revision">{copy.filters.inReview}</option>
                          <option value="aceptado">{copy.filters.accepted}</option>
                          <option value="rechazado">{copy.filters.rejected}</option>
                          <option value="todos">{copy.filters.all}</option>
                        </select>
                      </label>
                      <label className="coord-bulk-message">
                        <span>{copy.notifications.message}</span>
                        <textarea
                          rows="2"
                          maxLength="1000"
                          value={notificacionMensaje}
                          placeholder={copy.notifications.messagePlaceholder}
                          onChange={event => setNotificacionMensaje(event.target.value)}
                        />
                      </label>
                    </div>
                    <label className="coord-bulk-checkbox">
                      <input
                        type="checkbox"
                        checked={notificacionIncluirFechas}
                        onChange={event => setNotificacionIncluirFechas(event.target.checked)}
                      />
                      <span><strong>{copy.notifications.includeDates}</strong><small>{copy.notifications.dateInfo}</small></span>
                    </label>
                    <details className="coord-bulk-recipients">
                      <summary>{copy.notifications.chooseRecipients} ({notificacionDestinatarios.length}/{aspirantesNotificables.length})</summary>
                      <div className="coord-bulk-recipient-actions">
                        <button type="button" className="qa-btn qa-btn-secondary" onClick={() => setNotificacionSeleccionados(null)}>{copy.notifications.selectAll}</button>
                        <button type="button" className="qa-btn qa-btn-secondary" onClick={() => setNotificacionSeleccionados([])}>{copy.notifications.selectNone}</button>
                      </div>
                      {aspirantesNotificables.length ? (
                        <div className="coord-bulk-recipient-list">
                          {aspirantesNotificables.map(aspirante => (
                            <label key={aspirante.id}>
                              <input
                                type="checkbox"
                                checked={notificacionSeleccionados === null || notificacionSeleccionados.includes(aspirante.id)}
                                onChange={event => setNotificacionSeleccionados(current => {
                                  const selected = current === null ? aspirantesNotificables.map(item => item.id) : current;
                                  return event.target.checked
                                    ? [...selected, aspirante.id]
                                    : selected.filter(id => id !== aspirante.id);
                                })}
                              />
                              <span><strong>{aspirante.nombre}</strong><small>{aspirante.correo || copy.notifications.noEmail} · {etiquetaEstado(aspirante.proceso_estado, copy)}</small></span>
                            </label>
                          ))}
                        </div>
                      ) : <p className="empty-state">{copy.notifications.noRecipients}</p>}
                    </details>
                    <details className="coord-bulk-preview">
                      <summary>{copy.notifications.preview}</summary>
                      <p>{notificacionMensaje.trim() || copy.notifications.defaultMessage}</p>
                      <div>
                        {notificacionDestinatarios.map(aspirante => {
                          const fechas = notificacionIncluirFechas ? [
                            [copy.notifications.examDate, aspirante.fecha_examen_admision],
                            [copy.notifications.interviewDate, aspirante.fecha_entrevista],
                            [copy.notifications.courseDate, aspirante.fecha_inicio_curso_propedeutico],
                          ].filter(([, value]) => value) : [];
                          return (
                            <article key={aspirante.id}>
                              <strong>{aspirante.nombre}</strong>
                              <span>{etiquetaEstado(aspirante.proceso_estado, copy)}</span>
                              {notificacionIncluirFechas && (
                                <small>{fechas.length
                                  ? fechas.map(([label, value]) => `${label}: ${formatearFecha(value, copy.locale)}`).join(' · ')
                                  : copy.notifications.noDates}</small>
                              )}
                            </article>
                          );
                        })}
                      </div>
                    </details>
                    {notificacionError && <div className="api-error" role="alert">{notificacionError}</div>}
                    {notificacionResultado && (
                      <div className="coord-bulk-result" role="status" aria-live="polite">
                        <strong>
                          {copy.notifications.result}: {notificacionResultado.enviados} {copy.notifications.sent} · {notificacionResultado.avisos_internos || 0} {copy.notifications.internalSaved}
                          {(notificacionResultado.correos_desactivados || 0) > 0
                            ? ` · ${notificacionResultado.correos_desactivados} ${copy.notifications.disabledEmail}`
                            : ''}
                          {' · '}{notificacionResultado.fallidos.length} {copy.notifications.failed}
                          {(notificacionResultado.sin_correo.length + notificacionResultado.sin_correo_seleccionados.length) > 0
                            ? ` · ${notificacionResultado.sin_correo.length + notificacionResultado.sin_correo_seleccionados.length} ${copy.notifications.noEmail}`
                            : ''}.
                        </strong>
                        {(notificacionResultado.fallidos.length || notificacionResultado.sin_correo.length || notificacionResultado.sin_correo_seleccionados.length) > 0 && (
                          <ul>
                            {[...notificacionResultado.fallidos, ...notificacionResultado.sin_correo, ...notificacionResultado.sin_correo_seleccionados].map(item => <li key={item.id}>{item.nombre}</li>)}
                          </ul>
                        )}
                        {notificacionResultado.fallidos.length > 0 && (
                          <button
                            type="button"
                            className="qa-btn qa-btn-secondary coord-bulk-retry"
                            onClick={() => {
                              setNotificacionSeleccionados(notificacionResultado.fallidos.map(item => item.id));
                              setNotificacionResultado(null);
                              setNotificacionError('');
                            }}
                          >
                            {copy.notifications.retry}
                          </button>
                        )}
                      </div>
                    )}
                    <div className="coord-bulk-footer">
                      <span>
                        {notificacionResultado
                          ? copy.notifications.success
                          : `${notificacionConCorreo.length} ${copy.notifications.recipients}`}
                        {notificacionSinCorreo > 0 && <small className="coord-bulk-no-email">{notificacionSinCorreo} {copy.notifications.excludedNoEmail}</small>}
                      </span>
                      <button type="button" className="qa-btn" disabled={notificacionEnviando || !notificacionConCorreo.length} onClick={enviarNotificacionesMasivas}>
                        {notificacionEnviando ? copy.notifications.sending : copy.notifications.send}
                      </button>
                    </div>
                  </div>

                  <div className="panel-card coord-queue">
                    <div className="coord-queue-head">
                      <h3>{copy.queue.title}</h3>
                      <div className="coord-filters">{FILTROS.map(item => (
                        <button type="button" key={item.id} className={filtro === item.id ? 'is-active' : ''} onClick={() => setFiltro(item.id)}>{copy.filters[item.key]}</button>
                      ))}</div>
                    </div>
                    <div className="coord-list">
                      {aspirantes.length === 0 ? <p className="empty-state">{copy.queue.empty}</p> : aspirantes.map(aspirante => (
                        <button type="button" key={aspirante.id} className={`coord-item${seleccionado?.id === aspirante.id ? ' is-selected' : ''}`} onClick={() => { setSeleccionado(aspirante); setActiveSection('detalle'); }}>
                          <span><strong>{aspirante.nombre}</strong><small>{aspirante.programa} · {aspirante.unidad}</small></span>
                          <span className={`estado-badge estado-${aspirante.proceso_estado}`}>{etiquetaEstado(aspirante.proceso_estado, copy)}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeSection === 'detalle' && (
              <div className="aspirante-section-card is-open">
                <div className="section-panel">
                  <div className="panel-card coord-detail">
                  {seleccionado ? (
                    <div className="coord-record">
                      <div className="coord-detail-head coord-record-header">
                        <div className="coord-profile-photo">{seleccionado.profile_photo ? <img src={seleccionado.profile_photo.startsWith('http') ? seleccionado.profile_photo : `http://localhost:8000${seleccionado.profile_photo}`} alt={copy.detail.title} /> : <span>{(seleccionado.nombre || 'A').charAt(0).toUpperCase()}</span>}</div>
                        <div className="coord-record-identity">
                          <p className="panel-kicker">{copy.detail.title}</p>
                          <h3>{seleccionado.nombre}</h3>
                          <p><span>{seleccionado.correo || '—'}</span><span>{seleccionado.telefono || '—'}</span></p>
                        </div>
                        <span className={`estado-badge estado-${seleccionado.proceso_estado} coord-record-status`}>{etiquetaEstado(seleccionado.proceso_estado, copy)}</span>
                      </div>

                      {detalleCargando && !detalle ? (
                        <div className="panel-card">{copy.loadingDetails}</div>
                      ) : detalle ? (
                        <div>
                          {saveError && <div className="api-error" role="alert">{saveError}</div>}
                          {saveSuccess && <div className="api-success" role="status">{saveSuccess}</div>}

                          <div className="coord-action-row coord-record-actions">
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
                              <div className="coord-student-actions">
                                <button type="button" className="qa-btn" onClick={handleDescargarCalificaciones}>{copy.detail.grades}</button>
                                <button type="button" className="qa-btn" onClick={handleDescargarAdscripcion}>{copy.detail.affiliation}</button>
                                <button type="button" className="qa-btn" onClick={handleDarBaja}>{copy.detail.dropout}</button>
                                <button type="button" className="qa-btn" onClick={handleGenerarCarga}>{copy.detail.generateLoad}</button>
                              </div>
                            )}
                          </div>

                          {detalle.expediente_digital?.id && (
                            <div className="coord-digital-record">
                              <ExpedienteCentralizadoCard expedienteId={detalle.expediente_digital.id} session={session}/>
                            </div>
                          )}

                          <div className="coord-data">
                            <div><span>{copy.detail.curp}</span><strong>{detalle.curp || '—'}</strong></div>
                            <div><span>{copy.directory.username}</span><strong>{detalle.usuario || '—'}</strong></div>
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
                              <div className="coord-subjects-table">
                              <table className="admin-table">
                                <thead><tr><th>{copy.subjects.key}</th><th>{copy.subjects.subject}</th><th>{copy.subjects.teacher}</th><th>{copy.subjects.schedule}</th></tr></thead>
                                <tbody>
                                  {materias.map((m) => (
                                    <tr key={m.id}><td>{m.clave}</td><td>{m.nombre}</td><td>{m.profesor || '—'}</td><td>{m.horario || '—'}</td></tr>
                                  ))}
                                </tbody>
                              </table>
                              </div>
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
