import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {useLanguage} from '../translations';
import {TablaHerramientas, TablaPaginacion, useTablaControl} from './TablaControles';
import './DocentesDirectorioPanel.css';

const COPY = {
  es: {
    title: 'DIRECTORIO DE DOCENTES', subtitle: 'Información detallada de docentes y directores de tesis.',
    search: 'Buscar por nombre, usuario o correo', allRoles: 'Todos los roles', docente: 'Docente', director: 'Director de tesis', investigador: 'Investigador',
    allStatus: 'Todos los estatus', active: 'Activo', inactive: 'Inactivo', allDepartments: 'Todos los departamentos', allPrograms: 'Todos los programas', line: 'Línea de investigación',
    name: 'Docente', role: 'Rol', department: 'Departamento', lines: 'Líneas', advisees: 'Tesistas', graduates: 'Graduados', subjects: 'Materias', status: 'Estatus', view: 'Ver ficha',
    loading: 'Cargando docentes...', empty: 'No hay docentes con esos filtros.', error: 'No se pudo cargar la información.', expired: 'Tu sesión expiró.', back: '← Volver al directorio',
    general: 'Datos generales', academic: 'Perfil académico', students: 'Tesistas', courses: 'Materias', committees: 'Comités', history: 'Historial',
    user: 'Usuario', email: 'Correo', phone: 'Teléfono', curp: 'CURP', unit: 'Unidad', program: 'Programa', since: 'Alta', degree: 'Último grado', institution: 'Institución',
    languages: 'Idiomas', publications: 'Publicaciones', experience: 'Experiencia', documents: 'Documentos', reviewed: 'Revisado', markReviewed: 'Marcar revisado', unmark: 'Quitar revisión', open: 'Abrir',
    noDocs: 'Sin documentos cargados.', current: 'Tesistas activos', graduated: 'Tesistas graduados', matricula: 'Matrícula', project: 'Proyecto', projectStatus: 'Estado del proyecto', egress: 'Egreso', thesis: 'Tesis',
    catalog: 'Materias asignadas en catálogo', loads: 'Participación en cargas académicas', key: 'Clave', subject: 'Materia', period: 'Periodo', schedule: 'Horario', credits: 'Créditos', loadStatus: 'Estado de la carga', room: 'Salón',
    juries: 'Jurados', requests: 'Solicitudes de dirección', interviews: 'Entrevistas', signatures: 'Firmas de expediente', pending: 'Solicitudes pendientes', student: 'Alumno', as: 'Como',
    date: 'Fecha', field: 'Campo', before: 'Anterior', after: 'Nuevo', by: 'Realizado por', none: 'Sin registros.', deactivate: 'Desactivar docente', activate: 'Activar docente', saved: 'Cambios guardados.', saveError: 'No se pudo guardar.',
    confirmDeactivate: '¿Desactivar a este docente? Dejará de tener acceso al sistema.',
    sni: 'Nivel SNI', specialty: 'Especialidad', declaredLines: 'Líneas de investigación (separadas por coma)', save: 'Guardar perfil',
    chooseOption: 'Selecciona una opción',
    otherOption: 'Otro (especificar)',
    enterValue: 'Escribe un valor',
  },
  en: {
    title: 'FACULTY DIRECTORY', subtitle: 'Detailed information on faculty and thesis directors.',
    search: 'Search by name, username or email', allRoles: 'All roles', docente: 'Faculty', director: 'Thesis director', investigador: 'Researcher',
    allStatus: 'All statuses', active: 'Active', inactive: 'Inactive', allDepartments: 'All departments', allPrograms: 'All programs', line: 'Research line',
    name: 'Faculty', role: 'Role', department: 'Department', lines: 'Lines', advisees: 'Advisees', graduates: 'Graduates', subjects: 'Subjects', status: 'Status', view: 'View profile',
    loading: 'Loading faculty...', empty: 'No faculty match the filters.', error: 'Could not load the information.', expired: 'Your session expired.', back: '← Back to directory',
    general: 'General data', academic: 'Academic profile', students: 'Advisees', courses: 'Subjects', committees: 'Committees', history: 'History',
    user: 'Username', email: 'Email', phone: 'Phone', curp: 'CURP', unit: 'Unit', program: 'Program', since: 'Created', degree: 'Highest degree', institution: 'Institution',
    languages: 'Languages', publications: 'Publications', experience: 'Experience', documents: 'Documents', reviewed: 'Reviewed', markReviewed: 'Mark reviewed', unmark: 'Remove review', open: 'Open',
    noDocs: 'No documents uploaded.', current: 'Active advisees', graduated: 'Graduated advisees', matricula: 'Student ID', project: 'Project', projectStatus: 'Project status', egress: 'Graduation', thesis: 'Thesis',
    catalog: 'Subjects assigned in catalog', loads: 'Participation in academic loads', key: 'Code', subject: 'Subject', period: 'Period', schedule: 'Schedule', credits: 'Credits', loadStatus: 'Load status', room: 'Room',
    juries: 'Juries', requests: 'Advising requests', interviews: 'Interviews', signatures: 'Record signatures', pending: 'Pending requests', student: 'Student', as: 'As',
    date: 'Date', field: 'Field', before: 'Previous', after: 'New', by: 'Performed by', none: 'No records.', deactivate: 'Deactivate', activate: 'Activate', saved: 'Changes saved.', saveError: 'Could not save.',
    confirmDeactivate: 'Deactivate this faculty member? They will lose system access.',
    sni: 'SNI level', specialty: 'Specialty', declaredLines: 'Research lines (comma separated)', save: 'Save profile',
    chooseOption: 'Choose an option',
    otherOption: 'Other (specify)',
    enterValue: 'Enter a value',
  },
  de: {
    title: 'LEHRKRÄFTEVERZEICHNIS', subtitle: 'Detaillierte Informationen zu Lehrkräften und Dissertationsbetreuern.',
    search: 'Nach Name, Benutzer oder E-Mail suchen', allRoles: 'Alle Rollen', docente: 'Lehrkraft', director: 'Dissertationsbetreuer/in', investigador: 'Forscher/in',
    allStatus: 'Alle Status', active: 'Aktiv', inactive: 'Inaktiv', allDepartments: 'Alle Abteilungen', allPrograms: 'Alle Studiengänge', line: 'Forschungslinie',
    name: 'Lehrkraft', role: 'Rolle', department: 'Abteilung', lines: 'Linien', advisees: 'Doktoranden', graduates: 'Absolventen', subjects: 'Fächer', status: 'Status', view: 'Profil ansehen',
    loading: 'Lehrkräfte werden geladen...', empty: 'Keine Lehrkräfte für diese Filter.', error: 'Die Informationen konnten nicht geladen werden.', expired: 'Ihre Sitzung ist abgelaufen.', back: '← Zurück zum Verzeichnis',
    general: 'Allgemeine Daten', academic: 'Akademisches Profil', students: 'Doktoranden', courses: 'Fächer', committees: 'Komitees', history: 'Verlauf',
    user: 'Benutzer', email: 'E-Mail', phone: 'Telefon', curp: 'CURP', unit: 'Einheit', program: 'Studiengang', since: 'Angelegt', degree: 'Höchster Abschluss', institution: 'Institution',
    languages: 'Sprachen', publications: 'Publikationen', experience: 'Erfahrung', documents: 'Dokumente', reviewed: 'Geprüft', markReviewed: 'Als geprüft markieren', unmark: 'Prüfung entfernen', open: 'Öffnen',
    noDocs: 'Keine Dokumente hochgeladen.', current: 'Aktive Doktoranden', graduated: 'Promovierte Doktoranden', matricula: 'Matrikelnummer', project: 'Projekt', projectStatus: 'Projektstatus', egress: 'Abschluss', thesis: 'Dissertation',
    catalog: 'Im Katalog zugewiesene Fächer', loads: 'Beteiligung an Lehrdeputaten', key: 'Kürzel', subject: 'Fach', period: 'Zeitraum', schedule: 'Stundenplan', credits: 'Credits', loadStatus: 'Status des Deputats', room: 'Raum',
    juries: 'Prüfungskomitees', requests: 'Betreuungsanfragen', interviews: 'Gespräche', signatures: 'Aktenunterschriften', pending: 'Offene Anfragen', student: 'Studierende/r', as: 'Als',
    date: 'Datum', field: 'Feld', before: 'Vorher', after: 'Neu', by: 'Durchgeführt von', none: 'Keine Einträge.', deactivate: 'Lehrkraft deaktivieren', activate: 'Lehrkraft aktivieren', saved: 'Änderungen gespeichert.', saveError: 'Speichern nicht möglich.',
    confirmDeactivate: 'Diese Lehrkraft deaktivieren? Sie verliert den Zugang zum System.',
    sni: 'SNI-Stufe', specialty: 'Fachgebiet', declaredLines: 'Forschungslinien (durch Komma getrennt)', save: 'Profil speichern',
    chooseOption: 'Option auswählen',
    otherOption: 'Andere (angeben)',
    enterValue: 'Wert eingeben',
  },
  zh: {
    title: '教师名录', subtitle: '教师和论文导师的详细信息。',
    search: '按姓名、用户名或邮箱搜索', allRoles: '所有角色', docente: '教师', director: '论文导师', investigador: '研究员',
    allStatus: '所有状态', active: '启用', inactive: '停用', allDepartments: '所有院系', allPrograms: '所有项目', line: '研究方向',
    name: '教师', role: '角色', department: '院系', lines: '研究方向', advisees: '指导学生', graduates: '毕业生', subjects: '课程', status: '状态', view: '查看档案',
    loading: '正在加载教师...', empty: '没有符合筛选条件的教师。', error: '无法加载信息。', expired: '你的会话已过期。', back: '← 返回名录',
    general: '基本信息', academic: '学术档案', students: '指导学生', courses: '课程', committees: '委员会', history: '历史记录',
    user: '用户名', email: '邮箱', phone: '电话', curp: 'CURP', unit: '单位', program: '项目', since: '创建时间', degree: '最高学位', institution: '机构',
    languages: '语言', publications: '出版物', experience: '经验', documents: '文件', reviewed: '已审核', markReviewed: '标记为已审核', unmark: '取消审核', open: '打开',
    noDocs: '尚未上传文件。', current: '在读指导学生', graduated: '已毕业指导学生', matricula: '学号', project: '项目', projectStatus: '项目状态', egress: '毕业', thesis: '论文',
    catalog: '课程目录中分配的课程', loads: '参与的教学安排', key: '代码', subject: '课程', period: '学期', schedule: '时间表', credits: '学分', loadStatus: '教学安排状态', room: '教室',
    juries: '评审委员会', requests: '指导申请', interviews: '面谈', signatures: '档案签署', pending: '待处理申请', student: '学生', as: '担任',
    date: '日期', field: '字段', before: '修改前', after: '修改后', by: '操作人', none: '无记录。', deactivate: '停用教师', activate: '启用教师', saved: '更改已保存。', saveError: '无法保存。',
    confirmDeactivate: '确定停用该教师吗？其将无法访问系统。',
    sni: 'SNI 级别', specialty: '专业', declaredLines: '研究方向（以逗号分隔）', save: '保存档案',
    chooseOption: '请选择一个选项',
    otherOption: '其他（请注明）',
    enterValue: '请输入数值',
  },
  pt: {
    title: 'DIRETÓRIO DE DOCENTES', subtitle: 'Informações detalhadas sobre docentes e orientadores de tese.',
    search: 'Buscar por nome, usuário ou e-mail', allRoles: 'Todas as funções', docente: 'Docente', director: 'Orientador de tese', investigador: 'Pesquisador',
    allStatus: 'Todos os status', active: 'Ativo', inactive: 'Inativo', allDepartments: 'Todos os departamentos', allPrograms: 'Todos os programas', line: 'Linha de pesquisa',
    name: 'Docente', role: 'Função', department: 'Departamento', lines: 'Linhas', advisees: 'Orientandos', graduates: 'Titulados', subjects: 'Disciplinas', status: 'Status', view: 'Ver ficha',
    loading: 'Carregando docentes...', empty: 'Nenhum docente com esses filtros.', error: 'Não foi possível carregar as informações.', expired: 'Sua sessão expirou.', back: '← Voltar ao diretório',
    general: 'Dados gerais', academic: 'Perfil acadêmico', students: 'Orientandos', courses: 'Disciplinas', committees: 'Comitês', history: 'Histórico',
    user: 'Usuário', email: 'E-mail', phone: 'Telefone', curp: 'CURP', unit: 'Unidade', program: 'Programa', since: 'Cadastro', degree: 'Último grau', institution: 'Instituição',
    languages: 'Idiomas', publications: 'Publicações', experience: 'Experiência', documents: 'Documentos', reviewed: 'Revisado', markReviewed: 'Marcar como revisado', unmark: 'Remover revisão', open: 'Abrir',
    noDocs: 'Nenhum documento enviado.', current: 'Orientandos ativos', graduated: 'Orientandos titulados', matricula: 'Matrícula', project: 'Projeto', projectStatus: 'Status do projeto', egress: 'Conclusão', thesis: 'Tese',
    catalog: 'Disciplinas atribuídas no catálogo', loads: 'Participação em cargas acadêmicas', key: 'Código', subject: 'Disciplina', period: 'Período', schedule: 'Horário', credits: 'Créditos', loadStatus: 'Status da carga', room: 'Sala',
    juries: 'Bancas', requests: 'Solicitações de orientação', interviews: 'Entrevistas', signatures: 'Assinaturas de expediente', pending: 'Solicitações pendentes', student: 'Aluno', as: 'Como',
    date: 'Data', field: 'Campo', before: 'Anterior', after: 'Novo', by: 'Realizado por', none: 'Sem registros.', deactivate: 'Desativar docente', activate: 'Ativar docente', saved: 'Alterações salvas.', saveError: 'Não foi possível salvar.',
    confirmDeactivate: 'Desativar este docente? Ele perderá o acesso ao sistema.',
    sni: 'Nível SNI', specialty: 'Especialidade', declaredLines: 'Linhas de pesquisa (separadas por vírgula)', save: 'Salvar perfil',
    chooseOption: 'Selecione uma opção',
    otherOption: 'Outro (especificar)',
    enterValue: 'Digite um valor',
  },
};

const TABS = ['general', 'academic', 'students', 'courses', 'committees', 'history'];
const PROFILE_SUGGESTIONS = {
  degrees: ['Licenciatura', 'Especialidad', 'Maestría', 'Doctorado', 'Posdoctorado'],
  institutions: [
    'Cinvestav',
    'Instituto Politécnico Nacional',
    'Universidad Nacional Autónoma de México',
    'Universidad Autónoma Metropolitana',
    'Universidad de Guadalajara',
  ],
  sniLevels: ['No aplica', 'Sin reconocimiento', 'Candidatura', 'Nivel I', 'Nivel II', 'Nivel III', 'Emérito'],
};
export const PERFIL_COPY = COPY;

function fmt(value, language) {
  if (!value) return '—';
  try { return new Intl.DateTimeFormat(language, {dateStyle: 'medium'}).format(new Date(value)); } catch (e) { return value; }
}

function Field({label, value}) {
  return <div className={`docdir-field${value ? '' : ' is-empty'}`}><span>{label}</span><strong>{value || '—'}</strong></div>;
}

function Bloque({titulo, total, children}) {
  return (
    <section className="docdir-block">
      <header className="docdir-block-head"><h4>{titulo}</h4>{total !== undefined && <span className="docdir-count">{total}</span>}</header>
      {children}
    </section>
  );
}

function Stat({label, value}) {
  return <div className="docdir-stat"><strong>{value ?? 0}</strong><span>{label}</span></div>;
}

function iniciales(nombre) {
  return (nombre || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0].toUpperCase()).join('');
}

const textoCelda = row => row.filter(cell => typeof cell === 'string' || typeof cell === 'number');

function Table({head, rows, empty}) {
  const control = useTablaControl(rows, {campos: textoCelda});
  if (!rows.length) return <p className="servicios-muted docdir-empty">{empty}</p>;
  const extensa = rows.length > 10;
  return (
    <>
      {extensa && <TablaHerramientas control={control}/>}
      <div className="servicios-table-wrap tabla-scroll">
        <table className="admin-table">
          <thead><tr>{head.map(h => <th key={h}>{h}</th>)}</tr></thead>
          <tbody>{control.visibles.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell === '' || cell == null ? '—' : cell}</td>)}</tr>)}</tbody>
        </table>
      </div>
      {extensa && <TablaPaginacion control={control}/>}
    </>
  );
}

export function PerfilForm({d, t, onSave}) {
  const initialForm = {
    ultimo_grado: d.ultimo_grado || '', institucion: d.institucion || '', sni_nivel: d.sni_nivel || '', orcid: d.orcid || '',
    especialidad: d.especialidad || '', lineas_declaradas: d.lineas_declaradas || '', idiomas: d.idiomas || '',
    publicaciones: d.publicaciones || '', experiencia: d.experiencia || '',
  };
  const [form, setForm] = useState(initialForm);
  const [customAcademicValue, setCustomAcademicValue] = useState(() => ({
    ultimo_grado: Boolean(initialForm.ultimo_grado && !PROFILE_SUGGESTIONS.degrees.includes(initialForm.ultimo_grado)),
    institucion: Boolean(initialForm.institucion && !PROFILE_SUGGESTIONS.institutions.includes(initialForm.institucion)),
    sni_nivel: Boolean(initialForm.sni_nivel && !PROFILE_SUGGESTIONS.sniLevels.includes(initialForm.sni_nivel)),
  }));
  const bind = campo => ({value: form[campo], onChange: e => setForm({...form, [campo]: e.target.value})});
  const academicSelect = (campo, label, options) => (
    <label key={campo}>{label}
      <select
        value={customAcademicValue[campo] ? '__custom__' : form[campo]}
        onChange={event => {
          const custom = event.target.value === '__custom__';
          setCustomAcademicValue(previous => ({...previous, [campo]: custom}));
          if (!custom) setForm(previous => ({...previous, [campo]: event.target.value}));
          else if (!customAcademicValue[campo]) setForm(previous => ({...previous, [campo]: ''}));
        }}
      >
        <option value="">{t.chooseOption}</option>
        {options.map(value => <option key={value} value={value}>{value}</option>)}
        <option value="__custom__">{t.otherOption}</option>
      </select>
      {customAcademicValue[campo] && (
        <input
          aria-label={label}
          placeholder={t.enterValue}
          maxLength={campo === 'ultimo_grado' ? 80 : campo === 'institucion' ? 180 : 30}
          value={form[campo]}
          onChange={event => setForm(previous => ({...previous, [campo]: event.target.value}))}
        />
      )}
    </label>
  );
  return (
    <form className="servicios-form-grid" onSubmit={e => { e.preventDefault(); onSave(form); }}>
      {academicSelect('ultimo_grado', t.degree, PROFILE_SUGGESTIONS.degrees)}
      {academicSelect('institucion', t.institution, PROFILE_SUGGESTIONS.institutions)}
      {academicSelect('sni_nivel', t.sni, PROFILE_SUGGESTIONS.sniLevels)}
      <label>ORCID<input maxLength="40" {...bind('orcid')}/></label>
      <label>{t.specialty}<input maxLength="180" {...bind('especialidad')}/></label>
      <label>{t.declaredLines}<textarea rows="2" {...bind('lineas_declaradas')}/></label>
      <label>{t.languages}<textarea rows="2" {...bind('idiomas')}/></label>
      <label>{t.publications}<textarea rows="3" {...bind('publicaciones')}/></label>
      <label>{t.experience}<textarea rows="3" {...bind('experiencia')}/></label>
      <button type="submit" className="btn-primary">{t.save}</button>
    </form>
  );
}

export default function DocentesDirectorioPanel({session, onLogout}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'}), [session.access]);
  const logoutRef = useRef(onLogout);
  logoutRef.current = onLogout;
  const [filters, setFilters] = useState({q: '', rol: '', estatus: '', departamento: '', programa: '', linea: ''});
  const [lista, setLista] = useState({docentes: [], filtros: {departamentos: [], programas: []}, puede_gestionar: false});
  const [detalle, setDetalle] = useState(null);
  const [tab, setTab] = useState('general');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const docentesTabla = useTablaControl(lista.docentes);

  const request = useCallback(async (url, options = {}) => {
    const response = await fetch(url, {headers, ...options});
    if (response.status === 401) { logoutRef.current(t.expired); throw new Error(t.expired); }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || t.error);
    return body;
  }, [headers, t]);

  const cargar = useCallback(async signal => {
    setLoading(true);
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
      setLista(await request(`/api/servicios-escolares/docentes/?${params.toString()}`, {signal}));
      setError('');
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || t.error);
    } finally {
      if (!signal || !signal.aborted) setLoading(false);
    }
  }, [filters, request, t]);

  useEffect(() => { const c = new AbortController(); cargar(c.signal); return () => c.abort(); }, [cargar]);

  async function abrir(id) {
    try {
      setDetalle(await request(`/api/servicios-escolares/docentes/${id}/`));
      setTab('general');
      setMessage('');
      setError('');
    } catch (err) { setError(err.message || t.error); }
  }

  async function guardar(cambios) {
    try {
      setDetalle(await request(`/api/servicios-escolares/docentes/${detalle.id}/`, {method: 'PATCH', body: JSON.stringify(cambios)}));
      setMessage(t.saved);
      setError('');
    } catch (err) { setError(err.message || t.saveError); setMessage(''); }
  }

  const estado = activo => <span className={`servicios-status servicios-status--${activo ? 'activo' : 'inactivo'}`}>{activo ? t.active : t.inactive}</span>;
  const lineas = d => (d.lineas_investigacion || []).join(', ');

  if (detalle) {
    const d = detalle;
    const c = d.comites;
    return (
      <div className="panel-card docdir-detail">
        <button type="button" className="link-btn docdir-back" onClick={() => { setDetalle(null); cargar(); }}>{t.back}</button>
        <div className="docdir-hero">
          <div className="docdir-avatar" aria-hidden="true">{iniciales(d.nombre)}</div>
          <div className="docdir-hero-info">
            <span className="panel-kicker">{t[d.rol] || d.rol}</span>
            <h3>{d.nombre}</h3>
            <p className="docdir-hero-meta">{[d.correo, d.departamento, d.programa].filter(Boolean).map(v => <span key={v}>{v}</span>)}</p>
          </div>
          {estado(d.is_active)}
        </div>
        {message && <div className="api-success">{message}</div>}
        {error && <div className="api-error" role="alert">{error}</div>}
        <div className="docdir-tabs" role="tablist">
          {TABS.map(k => <button type="button" role="tab" aria-selected={tab === k} key={k} className={`docdir-tab${tab === k ? ' is-active' : ''}`} onClick={() => setTab(k)}>{t[k]}</button>)}
        </div>

        {tab === 'general' && (
          <>
            <Bloque titulo={t.general}>
              <div className="docdir-fields">
                <Field label={t.user} value={d.usuario}/><Field label={t.email} value={d.correo}/><Field label={t.phone} value={d.telefono}/>
                <Field label={t.curp} value={d.curp}/><Field label={t.unit} value={d.unidad}/><Field label={t.department} value={d.departamento}/>
                <Field label={t.program} value={d.programa}/><Field label={t.since} value={fmt(d.created_at, language)}/>
              </div>
            </Bloque>
            {lista.puede_gestionar && (
              <div className="docdir-actions">
                <button type="button" className={`btn-secondary${d.is_active ? ' is-danger' : ''}`} onClick={() => { if (!d.is_active || window.confirm(t.confirmDeactivate)) guardar({is_active: !d.is_active}); }}>
                  {d.is_active ? t.deactivate : t.activate}
                </button>
              </div>
            )}
          </>
        )}

        {tab === 'academic' && (
          <>
            <Bloque titulo={t.academic}>
              {d.puede_editar_perfil ? <PerfilForm key={d.id + (d.updated_key || '')} d={d} t={t} onSave={guardar}/> : (
                <div className="docdir-fields">
                  <Field label={t.degree} value={d.ultimo_grado}/><Field label={t.institution} value={d.institucion}/><Field label={t.line} value={lineas(d)}/>
                  <Field label={t.sni} value={d.sni_nivel}/><Field label="ORCID" value={d.orcid}/><Field label={t.specialty} value={d.especialidad}/>
                  <Field label={t.languages} value={d.idiomas}/><Field label={t.publications} value={d.publicaciones}/><Field label={t.experience} value={d.experiencia}/>
                </div>
              )}
            </Bloque>
            <Bloque titulo={t.documents} total={d.documentos.length}>
              <Table
                head={[t.documents, t.reviewed, '']}
                empty={t.noDocs}
                rows={d.documentos.map(doc => [
                  doc.url ? <a href={doc.url} target="_blank" rel="noreferrer">{doc.tipo_texto} · {doc.nombre}</a> : doc.tipo_texto,
                  doc.revisado ? `✓ ${fmt(doc.revisado_en, language)}` : '—',
                  lista.puede_gestionar ? <button type="button" className="btn-secondary" onClick={() => guardar({documento_id: doc.id, revisado: !doc.revisado})}>{doc.revisado ? t.unmark : t.markReviewed}</button> : '',
                ])}
              />
            </Bloque>
          </>
        )}

        {tab === 'students' && (
          <>
            <Bloque titulo={t.current} total={d.tesistas.length}>
              <Table head={[t.student, t.matricula, t.program, t.project, t.projectStatus]} empty={t.none}
                rows={d.tesistas.map(a => [a.nombre, a.matricula, a.programa, a.proyecto, a.estado_proyecto])}/>
            </Bloque>
            <Bloque titulo={t.graduated} total={d.graduados.length}>
              <Table head={[t.student, t.matricula, t.egress, t.thesis]} empty={t.none}
                rows={d.graduados.map(a => [a.nombre, a.matricula, fmt(a.fecha_egreso, language), a.titulo_tesis])}/>
            </Bloque>
          </>
        )}

        {tab === 'courses' && (
          <>
            <Bloque titulo={t.catalog} total={d.materias_catalogo.length}>
              <Table head={[t.key, t.subject, t.schedule, t.credits]} empty={t.none}
                rows={d.materias_catalogo.map(m => [m.clave, m.nombre, m.horario, m.creditos])}/>
            </Bloque>
            <Bloque titulo={t.loads} total={d.materias_cargas.length}>
              <Table head={[t.key, t.subject, t.period, t.schedule, t.room, t.loadStatus]} empty={t.none}
                rows={d.materias_cargas.map(m => [m.clave, m.materia, m.periodo, m.horario, m.salon, m.estado_carga])}/>
            </Bloque>
          </>
        )}

        {tab === 'committees' && (
          <>
            <div className="docdir-stats">
              <Stat label={t.interviews} value={c.entrevistas}/><Stat label={t.signatures} value={c.firmas}/><Stat label={t.pending} value={c.solicitudes_pendientes}/>
            </div>
            <Bloque titulo={t.juries} total={c.jurados.length}>
              <Table head={[t.project, t.student, t.role, t.status]} empty={t.none} rows={c.jurados.map(j => [j.proyecto, j.alumno, j.rol, j.estado])}/>
            </Bloque>
            <Bloque titulo={t.requests} total={c.solicitudes.length}>
              <Table head={[t.student, t.as, t.status]} empty={t.none} rows={c.solicitudes.map(s => [s.alumno, s.como, s.estado])}/>
            </Bloque>
          </>
        )}

        {tab === 'history' && (
          <Bloque titulo={t.history} total={d.historial.length}>
            <Table head={[t.date, t.field, t.before, t.after, t.by]} empty={t.none}
              rows={d.historial.map(h => [fmt(h.fecha, language), h.campo || h.evento, h.valor_anterior, h.valor_nuevo, h.realizado_por])}/>
          </Bloque>
        )}
      </div>
    );
  }

  const set = campo => e => setFilters({...filters, [campo]: e.target.value});
  return (
    <div className="panel-card">
      <div className="servicios-card-heading"><div><span className="panel-kicker">{t.title}</span><h3>{t.subtitle}</h3></div></div>
      <div className="servicios-toolbar" style={{marginBottom: 16}}>
        <input value={filters.q} onChange={set('q')} placeholder={t.search}/>
        <select value={filters.rol} onChange={set('rol')}>
          <option value="">{t.allRoles}</option>
          {['docente', 'director', 'investigador'].map(r => <option key={r} value={r}>{t[r]}</option>)}
        </select>
        <select value={filters.estatus} onChange={set('estatus')}>
          <option value="">{t.allStatus}</option><option value="activo">{t.active}</option><option value="inactivo">{t.inactive}</option>
        </select>
        <select value={filters.departamento} onChange={set('departamento')}>
          <option value="">{t.allDepartments}</option>
          {lista.filtros.departamentos.map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={filters.programa} onChange={set('programa')}>
          <option value="">{t.allPrograms}</option>
          {lista.filtros.programas.map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <input value={filters.linea} onChange={set('linea')} placeholder={t.line}/>
      </div>
      {error && <div className="api-error" role="alert">{error}</div>}
      {loading && !lista.docentes.length ? <p>{t.loading}</p> : lista.docentes.length === 0 ? <p>{t.empty}</p> : (<>
        <div className="servicios-table-wrap tabla-scroll">
          <table className="admin-table">
            <thead><tr><th>{t.name}</th><th>{t.role}</th><th>{t.department}</th><th>{t.lines}</th><th>{t.advisees}</th><th>{t.graduates}</th><th>{t.subjects}</th><th>{t.status}</th><th/></tr></thead>
            <tbody>
              {docentesTabla.visibles.map(d => (
                <tr key={d.id}>
                  <td><strong>{d.nombre}</strong><br/><small>{d.correo}</small></td>
                  <td>{t[d.rol] || d.rol}</td>
                  <td>{d.departamento || '—'}</td>
                  <td>{lineas(d) || '—'}</td>
                  <td>{d.tesistas_activos}</td>
                  <td>{d.tesistas_graduados}</td>
                  <td>{d.total_materias}</td>
                  <td>{estado(d.is_active)}</td>
                  <td><button type="button" className="btn-secondary" onClick={() => abrir(d.id)}>{t.view}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <TablaPaginacion control={docentesTabla}/>
      </>)}
    </div>
  );
}
