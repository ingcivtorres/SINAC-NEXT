import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {useLanguage} from '../translations';

const COPY = {
  es: {title: 'Histórico', subtitle: 'Bitácora de cambios de alumnos, docentes y directores de tesis.', search: 'Buscar por nombre, matrícula o usuario', all: 'Todos los roles', alumno: 'Alumnos', docente: 'Docentes', director: 'Directores de tesis', from: 'Desde', to: 'Hasta', date: 'Fecha', person: 'Persona', role: 'Rol', event: 'Evento', field: 'Campo', before: 'Anterior', after: 'Nuevo', by: 'Realizado por', created: 'Alta', change: 'Cambio', empty: 'Sin movimientos registrados.', loading: 'Cargando histórico...', error: 'No se pudo cargar el histórico.', expired: 'Tu sesión expiró.', truncated: 'Mostrando los 300 movimientos más recientes; afina los filtros.'},
  en: {title: 'History', subtitle: 'Change log for students, faculty and thesis directors.', search: 'Search by name, ID or username', all: 'All roles', alumno: 'Students', docente: 'Faculty', director: 'Thesis directors', from: 'From', to: 'To', date: 'Date', person: 'Person', role: 'Role', event: 'Event', field: 'Field', before: 'Previous', after: 'New', by: 'Performed by', created: 'Created', change: 'Change', empty: 'No recorded changes.', loading: 'Loading history...', error: 'Could not load the history.', expired: 'Your session expired.', truncated: 'Showing the 300 most recent entries; refine the filters.'},
  de: {title: 'Verlauf', subtitle: 'Änderungsprotokoll für Studierende, Lehrkräfte und Betreuende.', search: 'Nach Name, Matrikel oder Benutzer suchen', all: 'Alle Rollen', alumno: 'Studierende', docente: 'Lehrkräfte', director: 'Betreuende', from: 'Von', to: 'Bis', date: 'Datum', person: 'Person', role: 'Rolle', event: 'Ereignis', field: 'Feld', before: 'Vorher', after: 'Neu', by: 'Durchgeführt von', created: 'Anlage', change: 'Änderung', empty: 'Keine Änderungen erfasst.', loading: 'Verlauf wird geladen...', error: 'Verlauf konnte nicht geladen werden.', expired: 'Ihre Sitzung ist abgelaufen.', truncated: 'Es werden die 300 neuesten Einträge angezeigt; Filter verfeinern.'},
  zh: {title: '历史记录', subtitle: '学生、教师和论文导师的变更日志。', search: '按姓名、学号或用户名搜索', all: '所有角色', alumno: '学生', docente: '教师', director: '论文导师', from: '从', to: '至', date: '日期', person: '人员', role: '角色', event: '事件', field: '字段', before: '原值', after: '新值', by: '操作人', created: '新增', change: '变更', empty: '暂无变更记录。', loading: '正在加载历史记录...', error: '无法加载历史记录。', expired: '会话已过期。', truncated: '仅显示最近 300 条记录，请缩小筛选范围。'},
  pt: {title: 'Histórico', subtitle: 'Registro de alterações de alunos, docentes e orientadores de tese.', search: 'Buscar por nome, matrícula ou usuário', all: 'Todos os papéis', alumno: 'Alunos', docente: 'Docentes', director: 'Orientadores de tese', from: 'De', to: 'Até', date: 'Data', person: 'Pessoa', role: 'Papel', event: 'Evento', field: 'Campo', before: 'Anterior', after: 'Novo', by: 'Realizado por', created: 'Cadastro', change: 'Alteração', empty: 'Nenhuma alteração registrada.', loading: 'Carregando histórico...', error: 'Não foi possível carregar o histórico.', expired: 'Sua sessão expirou.', truncated: 'Exibindo os 300 registros mais recentes; refine os filtros.'},
};

function formatFecha(value, language) {
  try { return new Intl.DateTimeFormat(language, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value)); } catch (e) { return value; }
}

export default function HistoricoPanel({session, onLogout}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);
  const logoutRef = useRef(onLogout);
  logoutRef.current = onLogout;
  const [filters, setFilters] = useState({q: '', rol: '', desde: '', hasta: ''});
  const [datos, setDatos] = useState({eventos: [], truncado: false});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const cargar = useCallback(async signal => {
    setLoading(true);
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
      const response = await fetch(`/api/historico/?${params.toString()}`, {headers, signal});
      if (response.status === 401) { logoutRef.current(t.expired); return; }
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || t.error);
      setDatos(body);
      setError('');
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || t.error);
    } finally {
      if (!signal || !signal.aborted) setLoading(false);
    }
  }, [filters, headers, t]);

  useEffect(() => { const c = new AbortController(); cargar(c.signal); return () => c.abort(); }, [cargar]);

  return (
    <div className="panel-card">
      <div className="servicios-card-heading"><div><span className="panel-kicker">{t.title.toUpperCase()}</span><h3>{t.subtitle}</h3></div></div>
      <div className="servicios-toolbar" style={{marginBottom: 16}}>
        <input value={filters.q} onChange={e => setFilters({...filters, q: e.target.value})} placeholder={t.search}/>
        <select value={filters.rol} onChange={e => setFilters({...filters, rol: e.target.value})}>
          <option value="">{t.all}</option>
          {['alumno', 'docente', 'director'].map(r => <option key={r} value={r}>{t[r]}</option>)}
        </select>
        <label>{t.from} <input type="date" value={filters.desde} onChange={e => setFilters({...filters, desde: e.target.value})}/></label>
        <label>{t.to} <input type="date" value={filters.hasta} onChange={e => setFilters({...filters, hasta: e.target.value})}/></label>
      </div>
      {error && <div className="api-error" role="alert">{error}</div>}
      {datos.truncado && <p className="servicios-muted">{t.truncated}</p>}
      {loading && !datos.eventos.length ? <p>{t.loading}</p> : datos.eventos.length === 0 ? <p>{t.empty}</p> : (
        <div className="servicios-table-wrap">
          <table className="admin-table">
            <thead><tr><th>{t.date}</th><th>{t.person}</th><th>{t.role}</th><th>{t.event}</th><th>{t.field}</th><th>{t.before}</th><th>{t.after}</th><th>{t.by}</th></tr></thead>
            <tbody>
              {datos.eventos.map(e => (
                <tr key={e.id}>
                  <td>{formatFecha(e.fecha, language)}</td>
                  <td>{e.nombre}{e.matricula ? ` (${e.matricula})` : ''}</td>
                  <td>{t[e.rol] || e.rol}</td>
                  <td>{e.evento === 'alta' ? t.created : t.change}</td>
                  <td>{e.campo || '—'}</td>
                  <td>{e.valor_anterior || '—'}</td>
                  <td>{e.valor_nuevo || '—'}</td>
                  <td>{e.realizado_por || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
