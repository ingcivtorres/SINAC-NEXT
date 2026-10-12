import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {useLanguage} from '../translations';
import {fotoUrl} from './PerfilAspirante';
import ExpedienteCentralizadoCard from './ExpedienteCentralizadoCard';

const COPY = {
  es: {title: 'Egresados', subtitle: 'Registro oficial de egresados con su expediente.', search: 'Buscar por nombre, matrícula o tesis', allPrograms: 'Todos los programas', allGenerations: 'Todas las generaciones', register: '+ Registrar egreso', cancel: 'Cancelar', save: 'Guardar egreso', student: 'Alumno', select: 'Selecciona un alumno', date: 'Fecha de egreso', generation: 'Generación', average: 'Promedio final', thesis: 'Título de tesis', notes: 'Observaciones', exception: 'Motivo de excepción', exceptionHint: 'El alumno no cumple la prevalidación. Para registrarlo indica un motivo de excepción:', empty: 'No hay egresados registrados.', loading: 'Cargando egresados...', back: '← Volver al listado', matricula: 'Matrícula', program: 'Programa', department: 'Departamento', email: 'Correo', phone: 'Teléfono', folio: 'Folio de expediente', registeredBy: 'Registrado por', noPhoto: 'Sin foto', saved: 'Egreso registrado correctamente.', updated: 'Datos actualizados.', edit: 'Guardar cambios', error: 'No se pudo cargar la información.', expired: 'Tu sesión expiró.', record: 'Expediente', details: 'Datos del egresado', exceptionLabel: 'Registrado por excepción'},
  en: {title: 'Graduates', subtitle: 'Official graduate registry with their record.', search: 'Search by name, ID or thesis', allPrograms: 'All programs', allGenerations: 'All cohorts', register: '+ Register graduation', cancel: 'Cancel', save: 'Save graduation', student: 'Student', select: 'Select a student', date: 'Graduation date', generation: 'Cohort', average: 'Final average', thesis: 'Thesis title', notes: 'Notes', exception: 'Exception reason', exceptionHint: 'The student does not meet the pre-validation. Provide an exception reason to register:', empty: 'No graduates registered.', loading: 'Loading graduates...', back: '← Back to list', matricula: 'Student ID', program: 'Program', department: 'Department', email: 'Email', phone: 'Phone', folio: 'Record number', registeredBy: 'Registered by', noPhoto: 'No photo', saved: 'Graduation registered.', updated: 'Data updated.', edit: 'Save changes', error: 'Could not load the information.', expired: 'Your session expired.', record: 'Record', details: 'Graduate details', exceptionLabel: 'Registered by exception'},
  de: {title: 'Absolventen', subtitle: 'Offizielles Absolventenregister mit Akte.', search: 'Nach Name, Matrikel oder Thesis suchen', allPrograms: 'Alle Programme', allGenerations: 'Alle Jahrgänge', register: '+ Abschluss registrieren', cancel: 'Abbrechen', save: 'Abschluss speichern', student: 'Studierende/r', select: 'Studierende/n auswählen', date: 'Abschlussdatum', generation: 'Jahrgang', average: 'Endnote', thesis: 'Thesis-Titel', notes: 'Anmerkungen', exception: 'Ausnahmegrund', exceptionHint: 'Die Vorprüfung ist nicht erfüllt. Geben Sie einen Ausnahmegrund an:', empty: 'Keine Absolventen registriert.', loading: 'Absolventen werden geladen...', back: '← Zurück zur Liste', matricula: 'Matrikel', program: 'Programm', department: 'Abteilung', email: 'E-Mail', phone: 'Telefon', folio: 'Aktennummer', registeredBy: 'Registriert von', noPhoto: 'Kein Foto', saved: 'Abschluss registriert.', updated: 'Daten aktualisiert.', edit: 'Änderungen speichern', error: 'Informationen konnten nicht geladen werden.', expired: 'Ihre Sitzung ist abgelaufen.', record: 'Akte', details: 'Daten der Absolventen', exceptionLabel: 'Ausnahmeregistrierung'},
  zh: {title: '毕业生', subtitle: '毕业生正式登记及其档案。', search: '按姓名、学号或论文搜索', allPrograms: '所有项目', allGenerations: '所有届别', register: '+ 登记毕业', cancel: '取消', save: '保存毕业登记', student: '学生', select: '选择学生', date: '毕业日期', generation: '届别', average: '最终平均分', thesis: '论文题目', notes: '备注', exception: '例外原因', exceptionHint: '该学生未通过预审。请填写例外原因后登记：', empty: '暂无毕业生。', loading: '正在加载毕业生...', back: '← 返回列表', matricula: '学号', program: '项目', department: '院系', email: '邮箱', phone: '电话', folio: '档案编号', registeredBy: '登记人', noPhoto: '无照片', saved: '毕业登记成功。', updated: '数据已更新。', edit: '保存更改', error: '无法加载信息。', expired: '会话已过期。', record: '档案', details: '毕业生信息', exceptionLabel: '例外登记'},
  pt: {title: 'Egressos', subtitle: 'Registro oficial de egressos com seu prontuário.', search: 'Buscar por nome, matrícula ou tese', allPrograms: 'Todos os programas', allGenerations: 'Todas as turmas', register: '+ Registrar egresso', cancel: 'Cancelar', save: 'Salvar egresso', student: 'Aluno', select: 'Selecione um aluno', date: 'Data de egresso', generation: 'Turma', average: 'Média final', thesis: 'Título da tese', notes: 'Observações', exception: 'Motivo da exceção', exceptionHint: 'O aluno não cumpre a pré-validação. Informe um motivo de exceção para registrar:', empty: 'Nenhum egresso registrado.', loading: 'Carregando egressos...', back: '← Voltar à lista', matricula: 'Matrícula', program: 'Programa', department: 'Departamento', email: 'E-mail', phone: 'Telefone', folio: 'Número do prontuário', registeredBy: 'Registrado por', noPhoto: 'Sem foto', saved: 'Egresso registrado.', updated: 'Dados atualizados.', edit: 'Salvar alterações', error: 'Não foi possível carregar as informações.', expired: 'Sua sessão expirou.', record: 'Prontuário', details: 'Dados do egresso', exceptionLabel: 'Registrado por exceção'},
};

const EMPTY_FORM = {alumno_id: '', fecha_egreso: '', generacion: '', promedio_final: '', titulo_tesis: '', observaciones: '', excepcion_motivo: ''};

function Foto({item, size = 72}) {
  const url = fotoUrl(item.profile_photo);
  const iniciales = (item.nombre || '?').split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase();
  const style = {width: size, height: size, borderRadius: '50%', objectFit: 'cover', background: '#d7e3f4', color: '#17407a', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: size / 3, flexShrink: 0};
  return url ? <img src={url} alt={item.nombre} style={style}/> : <div style={style} aria-label={item.nombre}>{iniciales}</div>;
}

export default function EgresadosPanel({session, onLogout}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'}), [session.access]);
  const [datos, setDatos] = useState({egresados: [], filtros: {programas: [], generaciones: []}, candidatos: []});
  const [filters, setFilters] = useState({q: '', programa: '', generacion: ''});
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formAbierto, setFormAbierto] = useState(false);
  const [motivos, setMotivos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const logoutRef = React.useRef(onLogout);
  logoutRef.current = onLogout;
  const cargar = useCallback(async signal => {
    setLoading(true);
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
      const response = await fetch(`/api/egresados/?${params.toString()}`, {headers, signal});
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

  async function guardar(event) {
    event.preventDefault();
    setError(''); setMessage('');
    const response = await fetch('/api/egresados/', {method: 'POST', headers, body: JSON.stringify(form)});
    const body = await response.json().catch(() => ({}));
    if (response.status === 409 && body.codigo === 'prevalidacion_incompleta') { setMotivos(body.motivos || []); setError(body.detail); return; }
    if (!response.ok) { setError(body.detail || t.error); return; }
    setMessage(t.saved); setMotivos([]); setForm(EMPTY_FORM); setFormAbierto(false);
    cargar();
  }

  async function guardarCambios(event) {
    event.preventDefault();
    setError(''); setMessage('');
    const response = await fetch(`/api/egresados/${selected.id}/`, {method: 'PATCH', headers, body: JSON.stringify({fecha_egreso: selected.fecha_egreso, generacion: selected.generacion, promedio_final: selected.promedio_final ?? '', titulo_tesis: selected.titulo_tesis, observaciones: selected.observaciones})});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) { setError(body.detail || t.error); return; }
    setSelected(body); setMessage(t.updated); cargar();
  }

  const campo = (label, name, type = 'text', extra = {}) => (
    <label>{label}<input type={type} value={form[name]} onChange={e => setForm({...form, [name]: e.target.value})} {...extra}/></label>
  );

  if (selected) {
    const set = (name, value) => setSelected({...selected, [name]: value});
    return (
      <div className="panel-card">
        <button type="button" className="btn-secondary" onClick={() => { setSelected(null); setMessage(''); setError(''); }}>{t.back}</button>
        {message && <div className="api-success" role="status">{message}</div>}
        {error && <div className="api-error" role="alert">{error}</div>}
        <div style={{display: 'flex', gap: 20, alignItems: 'center', margin: '16px 0'}}>
          <Foto item={selected} size={120}/>
          <div>
            <h3 style={{margin: 0}}>{selected.nombre}</h3>
            <p style={{margin: '4px 0'}}>{t.matricula}: <strong>{selected.matricula || '—'}</strong> · {t.program}: <strong>{selected.programa || '—'}</strong></p>
            <p style={{margin: '4px 0'}}>{t.department}: {selected.departamento || '—'} · {t.email}: {selected.correo || '—'} · {t.phone}: {selected.telefono || '—'}</p>
            <p style={{margin: '4px 0'}}>{t.folio}: {selected.expediente_folio || '—'} · {t.registeredBy}: {selected.registrado_por || '—'}</p>
            {selected.excepcion_motivo && <p style={{margin: '4px 0'}}><strong>{t.exceptionLabel}:</strong> {selected.excepcion_motivo}</p>}
          </div>
        </div>
        <form onSubmit={guardarCambios} className="servicios-form-grid">
          <label>{t.date}<input type="date" value={selected.fecha_egreso} onChange={e => set('fecha_egreso', e.target.value)}/></label>
          <label>{t.generation}<input value={selected.generacion} onChange={e => set('generacion', e.target.value)}/></label>
          <label>{t.average}<input type="number" step="0.01" min="0" max="10" value={selected.promedio_final ?? ''} onChange={e => set('promedio_final', e.target.value)}/></label>
          <label>{t.thesis}<input value={selected.titulo_tesis} onChange={e => set('titulo_tesis', e.target.value)}/></label>
          <label>{t.notes}<textarea value={selected.observaciones} onChange={e => set('observaciones', e.target.value)}/></label>
          <button type="submit" className="btn-primary">{t.edit}</button>
        </form>
        <h4>{t.record}</h4>
        {selected.expediente_id ? <ExpedienteCentralizadoCard expedienteId={selected.expediente_id} session={session}/> : null}
      </div>
    );
  }

  return (
    <div className="panel-card">
      <div className="servicios-card-heading">
        <div><span className="panel-kicker">{t.title.toUpperCase()}</span><h3>{t.subtitle}</h3></div>
        <button type="button" className="btn-primary" onClick={() => setFormAbierto(!formAbierto)}>{formAbierto ? t.cancel : t.register}</button>
      </div>
      {message && <div className="api-success" role="status">{message}</div>}
      {error && <div className="api-error" role="alert">{error}{motivos.length > 0 && <ul>{motivos.map(m => <li key={m}>{m}</li>)}</ul>}</div>}
      {formAbierto && (
        <form onSubmit={guardar} className="servicios-form-grid" style={{marginBottom: 16}}>
          <label>{t.student}
            <select required value={form.alumno_id} onChange={e => { setForm({...form, alumno_id: e.target.value}); setMotivos([]); }}>
              <option value="">{t.select}</option>
              {datos.candidatos.map(c => <option key={c.id} value={c.id}>{c.nombre} {c.matricula ? `(${c.matricula})` : ''}</option>)}
            </select>
          </label>
          {campo(t.date, 'fecha_egreso', 'date', {required: true})}
          {campo(t.generation, 'generacion')}
          {campo(t.average, 'promedio_final', 'number', {step: '0.01', min: '0', max: '10'})}
          {campo(t.thesis, 'titulo_tesis')}
          <label>{t.notes}<textarea value={form.observaciones} onChange={e => setForm({...form, observaciones: e.target.value})}/></label>
          {motivos.length > 0 && <label>{t.exceptionHint}<textarea required value={form.excepcion_motivo} onChange={e => setForm({...form, excepcion_motivo: e.target.value})} placeholder={t.exception}/></label>}
          <button type="submit" className="btn-primary">{t.save}</button>
        </form>
      )}
      <div className="servicios-toolbar" style={{marginBottom: 16}}>
        <input value={filters.q} onChange={e => setFilters({...filters, q: e.target.value})} placeholder={t.search}/>
        <select value={filters.programa} onChange={e => setFilters({...filters, programa: e.target.value})}><option value="">{t.allPrograms}</option>{datos.filtros.programas.map(v => <option key={v} value={v}>{v}</option>)}</select>
        <select value={filters.generacion} onChange={e => setFilters({...filters, generacion: e.target.value})}><option value="">{t.allGenerations}</option>{datos.filtros.generaciones.map(v => <option key={v} value={v}>{v}</option>)}</select>
      </div>
      {loading && !datos.egresados.length ? <p>{t.loading}</p> : datos.egresados.length === 0 ? <p>{t.empty}</p> : (
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 14}}>
          {datos.egresados.map(item => (
            <button type="button" key={item.id} onClick={() => { setSelected(item); setMessage(''); setError(''); }} style={{display: 'flex', gap: 12, alignItems: 'center', textAlign: 'left', padding: 12, border: '1px solid #d0d7e2', borderRadius: 10, background: '#fff', cursor: 'pointer'}}>
              <Foto item={item}/>
              <span>
                <strong>{item.nombre}</strong><br/>
                <small>{item.matricula || '—'} · {item.programa || '—'}</small><br/>
                <small>{item.generacion || item.fecha_egreso}{item.promedio_final != null ? ` · ${item.promedio_final}` : ''}</small>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
