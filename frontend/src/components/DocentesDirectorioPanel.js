import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {useLanguage} from '../translations';

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
  },
};

const TABS = ['general', 'academic', 'students', 'courses', 'committees', 'history'];
export const PERFIL_COPY = COPY;

function fmt(value, language) {
  if (!value) return '—';
  try { return new Intl.DateTimeFormat(language, {dateStyle: 'medium'}).format(new Date(value)); } catch (e) { return value; }
}

function Field({label, value}) {
  return <div><span>{label}</span><strong>{value || '—'}</strong></div>;
}

function Table({head, rows, empty}) {
  if (!rows.length) return <p className="servicios-muted">{empty}</p>;
  return (
    <div className="servicios-table-wrap">
      <table className="admin-table">
        <thead><tr>{head.map(h => <th key={h}>{h}</th>)}</tr></thead>
        <tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell === '' || cell == null ? '—' : cell}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export function PerfilForm({d, t, onSave}) {
  const [form, setForm] = useState({
    ultimo_grado: d.ultimo_grado || '', institucion: d.institucion || '', sni_nivel: d.sni_nivel || '', orcid: d.orcid || '',
    especialidad: d.especialidad || '', lineas_declaradas: d.lineas_declaradas || '', idiomas: d.idiomas || '',
    publicaciones: d.publicaciones || '', experiencia: d.experiencia || '',
  });
  const bind = campo => ({value: form[campo], onChange: e => setForm({...form, [campo]: e.target.value})});
  return (
    <form className="servicios-form-grid" onSubmit={e => { e.preventDefault(); onSave(form); }}>
      <label>{t.degree}<input maxLength="80" {...bind('ultimo_grado')}/></label>
      <label>{t.institution}<input maxLength="180" {...bind('institucion')}/></label>
      <label>{t.sni}<input maxLength="30" {...bind('sni_nivel')}/></label>
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
      <div className="panel-card">
        <button type="button" className="link-btn" onClick={() => { setDetalle(null); cargar(); }}>{t.back}</button>
        <div className="servicios-card-heading">
          <div><span className="panel-kicker">{t[d.rol] || d.rol}</span><h3>{d.nombre}</h3></div>
          <div>{estado(d.is_active)}</div>
        </div>
        {message && <div className="api-success">{message}</div>}
        {error && <div className="api-error" role="alert">{error}</div>}
        <div className="servicios-toolbar" style={{marginBottom: 16}}>
          {TABS.map(k => <button type="button" key={k} className={tab === k ? 'btn-primary' : 'btn-secondary'} onClick={() => setTab(k)}>{t[k]}</button>)}
        </div>

        {tab === 'general' && (
          <>
            <div className="servicios-detail-grid">
              <Field label={t.user} value={d.usuario}/><Field label={t.email} value={d.correo}/><Field label={t.phone} value={d.telefono}/>
              <Field label={t.curp} value={d.curp}/><Field label={t.unit} value={d.unidad}/><Field label={t.department} value={d.departamento}/>
              <Field label={t.program} value={d.programa}/><Field label={t.since} value={fmt(d.created_at, language)}/>
            </div>
            {lista.puede_gestionar && (
              <p style={{marginTop: 16}}>
                <button type="button" className="btn-secondary" onClick={() => { if (!d.is_active || window.confirm(t.confirmDeactivate)) guardar({is_active: !d.is_active}); }}>
                  {d.is_active ? t.deactivate : t.activate}
                </button>
              </p>
            )}
          </>
        )}

        {tab === 'academic' && (
          <>
            {d.puede_editar_perfil ? <PerfilForm key={d.id + (d.updated_key || '')} d={d} t={t} onSave={guardar}/> : (
              <div className="servicios-detail-grid">
                <Field label={t.degree} value={d.ultimo_grado}/><Field label={t.institution} value={d.institucion}/><Field label={t.line} value={lineas(d)}/>
                <Field label={t.sni} value={d.sni_nivel}/><Field label="ORCID" value={d.orcid}/><Field label={t.specialty} value={d.especialidad}/>
                <Field label={t.languages} value={d.idiomas}/><Field label={t.publications} value={d.publicaciones}/><Field label={t.experience} value={d.experiencia}/>
              </div>
            )}
            <h4 style={{marginTop: 16}}>{t.documents}</h4>
            {d.documentos.length === 0 ? <p className="servicios-muted">{t.noDocs}</p> : (
              <Table
                head={[t.documents, t.reviewed, '']}
                empty={t.noDocs}
                rows={d.documentos.map(doc => [
                  doc.url ? <a href={doc.url} target="_blank" rel="noreferrer">{doc.tipo_texto} · {doc.nombre}</a> : doc.tipo_texto,
                  doc.revisado ? `✓ ${fmt(doc.revisado_en, language)}` : '—',
                  lista.puede_gestionar ? <button type="button" className="btn-secondary" onClick={() => guardar({documento_id: doc.id, revisado: !doc.revisado})}>{doc.revisado ? t.unmark : t.markReviewed}</button> : '',
                ])}
              />
            )}
          </>
        )}

        {tab === 'students' && (
          <>
            <h4>{t.current} ({d.tesistas.length})</h4>
            <Table head={[t.student, t.matricula, t.program, t.project, t.projectStatus]} empty={t.none}
              rows={d.tesistas.map(a => [a.nombre, a.matricula, a.programa, a.proyecto, a.estado_proyecto])}/>
            <h4 style={{marginTop: 16}}>{t.graduated} ({d.graduados.length})</h4>
            <Table head={[t.student, t.matricula, t.egress, t.thesis]} empty={t.none}
              rows={d.graduados.map(a => [a.nombre, a.matricula, fmt(a.fecha_egreso, language), a.titulo_tesis])}/>
          </>
        )}

        {tab === 'courses' && (
          <>
            <h4>{t.catalog}</h4>
            <Table head={[t.key, t.subject, t.schedule, t.credits]} empty={t.none}
              rows={d.materias_catalogo.map(m => [m.clave, m.nombre, m.horario, m.creditos])}/>
            <h4 style={{marginTop: 16}}>{t.loads}</h4>
            <Table head={[t.key, t.subject, t.period, t.schedule, t.room, t.loadStatus]} empty={t.none}
              rows={d.materias_cargas.map(m => [m.clave, m.materia, m.periodo, m.horario, m.salon, m.estado_carga])}/>
          </>
        )}

        {tab === 'committees' && (
          <>
            <div className="servicios-detail-grid">
              <Field label={t.interviews} value={String(c.entrevistas)}/><Field label={t.signatures} value={String(c.firmas)}/><Field label={t.pending} value={String(c.solicitudes_pendientes)}/>
            </div>
            <h4 style={{marginTop: 16}}>{t.juries}</h4>
            <Table head={[t.project, t.student, t.role, t.status]} empty={t.none} rows={c.jurados.map(j => [j.proyecto, j.alumno, j.rol, j.estado])}/>
            <h4 style={{marginTop: 16}}>{t.requests}</h4>
            <Table head={[t.student, t.as, t.status]} empty={t.none} rows={c.solicitudes.map(s => [s.alumno, s.como, s.estado])}/>
          </>
        )}

        {tab === 'history' && (
          <Table head={[t.date, t.field, t.before, t.after, t.by]} empty={t.none}
            rows={d.historial.map(h => [fmt(h.fecha, language), h.campo || h.evento, h.valor_anterior, h.valor_nuevo, h.realizado_por])}/>
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
      {loading && !lista.docentes.length ? <p>{t.loading}</p> : lista.docentes.length === 0 ? <p>{t.empty}</p> : (
        <div className="servicios-table-wrap">
          <table className="admin-table">
            <thead><tr><th>{t.name}</th><th>{t.role}</th><th>{t.department}</th><th>{t.lines}</th><th>{t.advisees}</th><th>{t.graduates}</th><th>{t.subjects}</th><th>{t.status}</th><th/></tr></thead>
            <tbody>
              {lista.docentes.map(d => (
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
      )}
    </div>
  );
}
