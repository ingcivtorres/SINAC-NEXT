import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {useLanguage} from '../translations';
import {TablaHerramientas, TablaPaginacion, useTablaControl} from './TablaControles';
import './HistoricoPanel.css';

const CATEGORIAS = ['cuenta', 'academico', 'tesis', 'documentos', 'egreso'];
const EVENTOS = ['alta', 'cambio', 'baja'];
const FILTROS_VACIOS = {q: '', rol: '', categoria: '', evento: '', programa: '', responsable: '', desde: '', hasta: ''};
const POR_TANDA = 40;

const COPY = {
  es: {
    title: 'Histórico', subtitle: 'Bitácora de alumnos, docentes y directores de tesis.', search: 'Buscar por nombre, matrícula, usuario o materia', searchTable: 'Buscar en los resultados',
    all: 'Todos', allRoles: 'Todos los roles', alumno: 'Alumno', docente: 'Docente', director: 'Director de tesis', aspirante: 'Aspirante',
    from: 'Desde', to: 'Hasta', date: 'Fecha', person: 'Persona', role: 'Rol', category: 'Categoría', event: 'Evento', movement: 'Movimiento', change: 'Cambio', by: 'Realizado por',
    program: 'Programa', responsible: 'Responsable', clear: 'Limpiar filtros',
    cat: {cuenta: 'Cuenta y datos', academico: 'Académico', tesis: 'Tesis', documentos: 'Documentos', egreso: 'Egreso'},
    ev: {alta: 'Alta', cambio: 'Cambio', baja: 'Baja'},
    total: 'Movimientos', people: 'Personas', activity: 'Actividad de los últimos 12 meses', movementsMonth: '{n} movimientos',
    empty: 'Sin movimientos registrados.', loading: 'Cargando histórico...', error: 'No se pudo cargar el histórico.', expired: 'Tu sesión expiró.', truncated: 'Mostrando los 300 movimientos más recientes; afina los filtros.',
    timeline: 'Línea de tiempo', back: 'Volver al histórico', openTimeline: 'Ver línea de tiempo de {nombre}', enrollment: 'Matrícula', user: 'Usuario', email: 'Correo', advisor: 'Director de tesis', period: 'Periodo actual', status: 'Estado', active: 'Cuenta activa', inactive: 'Cuenta inactiva', since: 'Registrado desde', showMore: 'Ver más movimientos', truncatedPerson: 'Se muestran los 1000 movimientos más recientes.', system: 'Sistema',
  },
  en: {
    title: 'History', subtitle: 'Log for students, faculty and thesis directors.', search: 'Search by name, ID, username or course', searchTable: 'Search within results',
    all: 'All', allRoles: 'All roles', alumno: 'Student', docente: 'Faculty', director: 'Thesis director', aspirante: 'Applicant',
    from: 'From', to: 'To', date: 'Date', person: 'Person', role: 'Role', category: 'Category', event: 'Event', movement: 'Entry', change: 'Change', by: 'Performed by',
    program: 'Program', responsible: 'Performed by', clear: 'Clear filters',
    cat: {cuenta: 'Account & data', academico: 'Academic', tesis: 'Thesis', documentos: 'Documents', egreso: 'Graduation'},
    ev: {alta: 'Created', cambio: 'Changed', baja: 'Removed'},
    total: 'Entries', people: 'People', activity: 'Activity over the last 12 months', movementsMonth: '{n} entries',
    empty: 'No recorded entries.', loading: 'Loading history...', error: 'Could not load the history.', expired: 'Your session expired.', truncated: 'Showing the 300 most recent entries; refine the filters.',
    timeline: 'Timeline', back: 'Back to history', openTimeline: 'View timeline of {nombre}', enrollment: 'Student ID', user: 'Username', email: 'Email', advisor: 'Thesis director', period: 'Current term', status: 'Status', active: 'Active account', inactive: 'Inactive account', since: 'Registered since', showMore: 'Show more entries', truncatedPerson: 'Showing the 1000 most recent entries.', system: 'System',
  },
  de: {
    title: 'Verlauf', subtitle: 'Protokoll für Studierende, Lehrkräfte und Betreuende.', search: 'Nach Name, Matrikel, Benutzer oder Fach suchen', searchTable: 'In Ergebnissen suchen',
    all: 'Alle', allRoles: 'Alle Rollen', alumno: 'Studierende/r', docente: 'Lehrkraft', director: 'Betreuer/in', aspirante: 'Bewerber/in',
    from: 'Von', to: 'Bis', date: 'Datum', person: 'Person', role: 'Rolle', category: 'Kategorie', event: 'Ereignis', movement: 'Eintrag', change: 'Änderung', by: 'Durchgeführt von',
    program: 'Studiengang', responsible: 'Verantwortlich', clear: 'Filter zurücksetzen',
    cat: {cuenta: 'Konto & Daten', academico: 'Akademisch', tesis: 'Abschlussarbeit', documentos: 'Dokumente', egreso: 'Abschluss'},
    ev: {alta: 'Angelegt', cambio: 'Geändert', baja: 'Entfernt'},
    total: 'Einträge', people: 'Personen', activity: 'Aktivität der letzten 12 Monate', movementsMonth: '{n} Einträge',
    empty: 'Keine Einträge erfasst.', loading: 'Verlauf wird geladen...', error: 'Verlauf konnte nicht geladen werden.', expired: 'Ihre Sitzung ist abgelaufen.', truncated: 'Es werden die 300 neuesten Einträge angezeigt; Filter verfeinern.',
    timeline: 'Zeitleiste', back: 'Zurück zum Verlauf', openTimeline: 'Zeitleiste von {nombre} anzeigen', enrollment: 'Matrikel', user: 'Benutzer', email: 'E-Mail', advisor: 'Betreuer/in', period: 'Aktuelles Semester', status: 'Status', active: 'Konto aktiv', inactive: 'Konto inaktiv', since: 'Registriert seit', showMore: 'Weitere Einträge anzeigen', truncatedPerson: 'Es werden die 1000 neuesten Einträge angezeigt.', system: 'System',
  },
  zh: {
    title: '历史记录', subtitle: '学生、教师和论文导师的日志。', search: '按姓名、学号、用户名或课程搜索', searchTable: '在结果中搜索',
    all: '全部', allRoles: '所有角色', alumno: '学生', docente: '教师', director: '论文导师', aspirante: '申请人',
    from: '从', to: '至', date: '日期', person: '人员', role: '角色', category: '类别', event: '事件', movement: '记录', change: '变更', by: '操作人',
    program: '项目', responsible: '操作人', clear: '清除筛选',
    cat: {cuenta: '账户与资料', academico: '学业', tesis: '论文', documentos: '文件', egreso: '毕业'},
    ev: {alta: '新增', cambio: '变更', baja: '移除'},
    total: '记录数', people: '人数', activity: '最近 12 个月的活动', movementsMonth: '{n} 条记录',
    empty: '暂无记录。', loading: '正在加载历史记录...', error: '无法加载历史记录。', expired: '会话已过期。', truncated: '仅显示最近 300 条记录，请缩小筛选范围。',
    timeline: '时间线', back: '返回历史记录', openTimeline: '查看 {nombre} 的时间线', enrollment: '学号', user: '用户名', email: '邮箱', advisor: '论文导师', period: '当前学期', status: '状态', active: '账户启用', inactive: '账户停用', since: '注册时间', showMore: '显示更多记录', truncatedPerson: '仅显示最近 1000 条记录。', system: '系统',
  },
  pt: {
    title: 'Histórico', subtitle: 'Registro de alunos, docentes e orientadores de tese.', search: 'Buscar por nome, matrícula, usuário ou disciplina', searchTable: 'Buscar nos resultados',
    all: 'Todos', allRoles: 'Todos os papéis', alumno: 'Aluno', docente: 'Docente', director: 'Orientador de tese', aspirante: 'Candidato',
    from: 'De', to: 'Até', date: 'Data', person: 'Pessoa', role: 'Papel', category: 'Categoria', event: 'Evento', movement: 'Movimento', change: 'Alteração', by: 'Realizado por',
    program: 'Programa', responsible: 'Responsável', clear: 'Limpar filtros',
    cat: {cuenta: 'Conta e dados', academico: 'Acadêmico', tesis: 'Tese', documentos: 'Documentos', egreso: 'Egresso'},
    ev: {alta: 'Cadastro', cambio: 'Alteração', baja: 'Remoção'},
    total: 'Movimentos', people: 'Pessoas', activity: 'Atividade dos últimos 12 meses', movementsMonth: '{n} movimentos',
    empty: 'Nenhum movimento registrado.', loading: 'Carregando histórico...', error: 'Não foi possível carregar o histórico.', expired: 'Sua sessão expirou.', truncated: 'Exibindo os 300 movimentos mais recentes; refine os filtros.',
    timeline: 'Linha do tempo', back: 'Voltar ao histórico', openTimeline: 'Ver linha do tempo de {nombre}', enrollment: 'Matrícula', user: 'Usuário', email: 'E-mail', advisor: 'Orientador de tese', period: 'Período atual', status: 'Status', active: 'Conta ativa', inactive: 'Conta inativa', since: 'Cadastrado desde', showMore: 'Ver mais movimentos', truncatedPerson: 'Exibindo os 1000 movimentos mais recentes.', system: 'Sistema',
  },
};

const formatear = (texto, valores) => Object.entries(valores).reduce((acc, [k, v]) => acc.replace(`{${k}}`, v), texto);

function formatFecha(value, language, opciones = {dateStyle: 'medium', timeStyle: 'short'}) {
  try { return new Intl.DateTimeFormat(language, opciones).format(new Date(value)); } catch (e) { return value; }
}

function mesLocal(isoMes, language, mes = 'short') {
  const [anio, numero] = isoMes.split('-').map(Number);
  return formatFecha(new Date(anio, numero - 1, 1), language, {month: mes, year: mes === 'short' ? '2-digit' : 'numeric'});
}

const iniciales = nombre => String(nombre || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0]).join('').toUpperCase();

function useApi(headers, onLogout, t) {
  const logoutRef = useRef(onLogout);
  logoutRef.current = onLogout;
  return useCallback(async (url, signal) => {
    const response = await fetch(url, {headers, signal});
    if (response.status === 401) { logoutRef.current(t.expired); return null; }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || t.error);
    return body;
  }, [headers, t]);
}

function Cambio({e}) {
  if (!e.valor_anterior && !e.valor_nuevo) return <span className="hist-muted">—</span>;
  return <span className="hist-cambio">
    {e.valor_anterior && <del>{e.valor_anterior}</del>}
    {e.valor_anterior && e.valor_nuevo && <span aria-hidden="true">→</span>}
    {e.valor_nuevo && <strong>{e.valor_nuevo}</strong>}
  </span>;
}

function Avatar({foto, nombre, grande}) {
  return foto
    ? <img className={`hist-avatar${grande ? ' is-large' : ''}`} src={foto} alt=""/>
    : <span className={`hist-avatar${grande ? ' is-large' : ''}`} aria-hidden="true">{iniciales(nombre)}</span>;
}

function Resumen({datos, filtros, setFiltros, t, language}) {
  const {resumen, total} = datos;
  if (!resumen) return null;
  const maximo = Math.max(1, ...resumen.actividad.map(m => m.total));
  const alternar = categoria => setFiltros(f => ({...f, categoria: f.categoria === categoria ? '' : categoria}));
  return <section className="hist-resumen">
    <div className="hist-stats">
      <div className="hist-stat is-main"><strong>{total}</strong><span>{t.total}</span></div>
      <div className="hist-stat"><strong>{resumen.personas}</strong><span>{t.people}</span></div>
      {EVENTOS.map(ev => <div key={ev} className={`hist-stat ev-${ev}`}><strong>{resumen.por_evento[ev]}</strong><span>{t.ev[ev]}</span></div>)}
    </div>
    <div className="hist-categorias" role="group" aria-label={t.category}>
      {CATEGORIAS.map(c => <button type="button" key={c} className={`hist-chip cat-${c}${filtros.categoria === c ? ' is-active' : ''}`} aria-pressed={filtros.categoria === c} onClick={() => alternar(c)}>
        <span className="hist-chip-dot" aria-hidden="true"/>{t.cat[c]}<b>{resumen.por_categoria[c]}</b>
      </button>)}
    </div>
    <div className="hist-actividad">
      <h4>{t.activity}</h4>
      <div className="hist-barras">
        {resumen.actividad.map(m => {
          const etiqueta = `${mesLocal(m.mes, language, 'long')}: ${formatear(t.movementsMonth, {n: m.total})}`;
          return <div key={m.mes} className="hist-barra" title={etiqueta} aria-label={etiqueta}>
            <span className="hist-barra-valor">{m.total || ''}</span>
            <span className="hist-barra-fill" style={{height: `${Math.max(m.total ? 6 : 2, (m.total / maximo) * 100)}%`}}/>
            <span className="hist-barra-mes">{mesLocal(m.mes, language)}</span>
          </div>;
        })}
      </div>
    </div>
  </section>;
}

function LineaTiempo({personaId, api, t, language, onBack}) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');
  const [categoria, setCategoria] = useState('');
  const [mostrados, setMostrados] = useState(POR_TANDA);

  useEffect(() => {
    const control = new AbortController();
    setDatos(null);
    setError('');
    api(`/api/historico/personas/${personaId}/`, control.signal)
      .then(body => { if (body) setDatos(body); })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message || t.error); });
    return () => control.abort();
  }, [api, personaId, t]);

  useEffect(() => { setMostrados(POR_TANDA); }, [categoria]);

  const filtrados = useMemo(() => (datos ? datos.eventos.filter(e => !categoria || e.categoria === categoria) : []), [datos, categoria]);
  const grupos = useMemo(() => {
    const mapa = new Map();
    filtrados.slice(0, mostrados).forEach(e => {
      const clave = e.fecha.slice(0, 7);
      if (!mapa.has(clave)) mapa.set(clave, []);
      mapa.get(clave).push(e);
    });
    return [...mapa.entries()];
  }, [filtrados, mostrados]);

  const volver = <button type="button" className="btn-secondary hist-back" onClick={onBack}>← {t.back}</button>;
  if (error) return <div className="panel-card hist-panel">{volver}<div className="api-error" role="alert">{error}</div></div>;
  if (!datos) return <div className="panel-card hist-panel">{volver}<p>{t.loading}</p></div>;

  const {persona} = datos;
  const meta = [
    [t.enrollment, persona.matricula], [t.user, persona.usuario], [t.email, persona.correo], [t.program, persona.programa],
    [t.advisor, persona.director_tesis], [t.period, persona.periodo_actual], [t.status, persona.estado],
  ].filter(([, valor]) => valor !== '' && valor != null);

  return <div className="panel-card hist-panel">
    {volver}
    <section className="hist-hero">
      <Avatar foto={persona.profile_photo} nombre={persona.nombre} grande/>
      <div className="hist-hero-info">
        <span className="panel-kicker">{t.timeline.toUpperCase()} · {t[persona.rol] || persona.rol}</span>
        <h3>{persona.nombre}</h3>
        <p className="hist-hero-meta">{meta.map(([etiqueta, valor]) => <span key={etiqueta}><b>{etiqueta}:</b> {valor}</span>)}</p>
      </div>
      <div className="hist-hero-side">
        <span className={`hist-estado ${persona.activo ? 'is-on' : 'is-off'}`}>{persona.activo ? t.active : t.inactive}</span>
        <small>{t.since} {formatFecha(persona.alta, language, {dateStyle: 'medium'})}</small>
      </div>
    </section>

    <div className="hist-categorias" role="group" aria-label={t.category}>
      <button type="button" className={`hist-chip${!categoria ? ' is-active' : ''}`} aria-pressed={!categoria} onClick={() => setCategoria('')}>{t.all}<b>{datos.total}</b></button>
      {CATEGORIAS.map(c => <button type="button" key={c} disabled={!datos.por_categoria[c]} className={`hist-chip cat-${c}${categoria === c ? ' is-active' : ''}`} aria-pressed={categoria === c} onClick={() => setCategoria(c)}>
        <span className="hist-chip-dot" aria-hidden="true"/>{t.cat[c]}<b>{datos.por_categoria[c]}</b>
      </button>)}
    </div>

    {datos.truncado && <p className="hist-muted">{t.truncatedPerson}</p>}
    {!filtrados.length ? <p className="hist-empty">{t.empty}</p> : <ol className="hist-timeline">
      {grupos.map(([mes, eventos]) => <li key={mes} className="hist-mes">
        <h4 className="hist-mes-titulo">{mesLocal(mes, language, 'long')}</h4>
        <ol>
          {eventos.map(e => <li key={e.id} className={`hist-item cat-${e.categoria}`}>
            <span className="hist-item-dot" aria-hidden="true"/>
            <div className="hist-item-card">
              <div className="hist-item-head">
                <span className={`hist-badge cat-${e.categoria}`}>{t.cat[e.categoria] || e.categoria}</span>
                <span className={`hist-badge ev-${e.evento}`}>{t.ev[e.evento] || e.evento}</span>
                <time dateTime={e.fecha}>{formatFecha(e.fecha, language)}</time>
              </div>
              <strong className="hist-item-titulo">{e.campo || t.ev[e.evento]}</strong>
              {e.detalle && <p className="hist-item-detalle">{e.detalle}</p>}
              <Cambio e={e}/>
              <small className="hist-muted">{t.by}: {e.realizado_por || t.system}</small>
            </div>
          </li>)}
        </ol>
      </li>)}
    </ol>}
    {filtrados.length > mostrados && <button type="button" className="btn-secondary hist-mas" onClick={() => setMostrados(n => n + POR_TANDA)}>{t.showMore}</button>}
  </div>;
}

export default function HistoricoPanel({session, onLogout}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);
  const api = useApi(headers, onLogout, t);
  const [filtros, setFiltros] = useState(FILTROS_VACIOS);
  const [consulta, setConsulta] = useState(FILTROS_VACIOS);
  const [datos, setDatos] = useState({eventos: [], truncado: false, total: 0, resumen: null, opciones: {programas: [], responsables: []}});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [personaId, setPersonaId] = useState(null);

  useEffect(() => {
    const espera = setTimeout(() => setConsulta(filtros), filtros.q === consulta.q ? 0 : 350);
    return () => clearTimeout(espera);
  }, [filtros, consulta.q]);

  const eventosTabla = useTablaControl(datos.eventos, {
    campos: e => [e.nombre, e.matricula, e.campo, e.detalle, e.valor_anterior, e.valor_nuevo, e.realizado_por],
  });

  useEffect(() => {
    const control = new AbortController();
    setLoading(true);
    const params = new URLSearchParams(Object.entries(consulta).filter(([, v]) => v));
    api(`/api/historico/?${params.toString()}`, control.signal)
      .then(body => { if (body) { setDatos(body); setError(''); } })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message || t.error); })
      .finally(() => { if (!control.signal.aborted) setLoading(false); });
    return () => control.abort();
  }, [api, consulta, t]);

  if (personaId) return <LineaTiempo personaId={personaId} api={api} t={t} language={language} onBack={() => setPersonaId(null)}/>;

  const cambiar = campo => event => setFiltros(f => ({...f, [campo]: event.target.value}));
  const hayFiltros = Object.values(filtros).some(Boolean);

  return (
    <div className="panel-card hist-panel">
      <div className="servicios-card-heading"><div><span className="panel-kicker">{t.title.toUpperCase()}</span><h3>{t.subtitle}</h3></div></div>
      <Resumen datos={datos} filtros={filtros} setFiltros={setFiltros} t={t} language={language}/>

      <div className="hist-filtros">
        <input className="hist-filtro-busqueda" type="search" value={filtros.q} onChange={cambiar('q')} placeholder={t.search} aria-label={t.search}/>
        <label><span>{t.role}</span><select value={filtros.rol} onChange={cambiar('rol')}>
          <option value="">{t.allRoles}</option>
          {['alumno', 'docente', 'director'].map(r => <option key={r} value={r}>{t[r]}</option>)}
        </select></label>
        <label><span>{t.category}</span><select value={filtros.categoria} onChange={cambiar('categoria')}>
          <option value="">{t.all}</option>
          {CATEGORIAS.map(c => <option key={c} value={c}>{t.cat[c]}</option>)}
        </select></label>
        <label><span>{t.event}</span><select value={filtros.evento} onChange={cambiar('evento')}>
          <option value="">{t.all}</option>
          {EVENTOS.map(ev => <option key={ev} value={ev}>{t.ev[ev]}</option>)}
        </select></label>
        <label><span>{t.program}</span><select value={filtros.programa} onChange={cambiar('programa')}>
          <option value="">{t.all}</option>
          {datos.opciones.programas.map(p => <option key={p} value={p}>{p}</option>)}
        </select></label>
        <label><span>{t.responsible}</span><select value={filtros.responsable} onChange={cambiar('responsable')}>
          <option value="">{t.all}</option>
          {datos.opciones.responsables.map(r => <option key={r} value={r}>{r}</option>)}
        </select></label>
        <label><span>{t.from}</span><input type="date" value={filtros.desde} max={filtros.hasta || undefined} onChange={cambiar('desde')}/></label>
        <label><span>{t.to}</span><input type="date" value={filtros.hasta} min={filtros.desde || undefined} onChange={cambiar('hasta')}/></label>
        {hayFiltros && <button type="button" className="tabla-limpiar" onClick={() => setFiltros(FILTROS_VACIOS)}>{t.clear}</button>}
      </div>

      {error && <div className="api-error" role="alert">{error}</div>}
      {datos.truncado && <p className="hist-muted">{t.truncated}</p>}
      {loading && !datos.eventos.length ? <p>{t.loading}</p> : datos.eventos.length === 0 ? <p className="hist-empty">{t.empty}</p> : (<>
        <TablaHerramientas control={eventosTabla} placeholder={t.searchTable}/>
        <div className={`servicios-table-wrap tabla-scroll hist-tabla${loading ? ' is-loading' : ''}`}>
          <table className="admin-table">
            <thead><tr><th>{t.date}</th><th>{t.person}</th><th>{t.category}</th><th>{t.movement}</th><th>{t.change}</th><th>{t.by}</th></tr></thead>
            <tbody>
              {eventosTabla.visibles.map(e => (
                <tr key={e.id}>
                  <td className="hist-nowrap">{formatFecha(e.fecha, language)}</td>
                  <td>
                    <button type="button" className="hist-persona" onClick={() => setPersonaId(e.persona_id)} title={formatear(t.openTimeline, {nombre: e.nombre})}>
                      <Avatar foto={e.profile_photo} nombre={e.nombre}/>
                      <span><strong>{e.nombre}</strong><small>{[e.matricula, t[e.rol] || e.rol].filter(Boolean).join(' · ')}</small></span>
                    </button>
                  </td>
                  <td><span className={`hist-badge cat-${e.categoria}`}>{t.cat[e.categoria] || e.categoria}</span></td>
                  <td>
                    <span className={`hist-badge ev-${e.evento}`}>{t.ev[e.evento] || e.evento}</span>{' '}
                    <strong>{e.campo || '—'}</strong>
                    {e.detalle && <small className="hist-detalle">{e.detalle}</small>}
                  </td>
                  <td><Cambio e={e}/></td>
                  <td>{e.realizado_por || t.system}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <TablaPaginacion control={eventosTabla}/>
      </>)}
    </div>
  );
}
