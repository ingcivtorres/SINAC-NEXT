import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {useLanguage} from '../translations';
import './ExamenesGestionPanel.css';

const COPY = {
  es: {
    kicker: 'EVALUACIÓN', title: 'Exámenes en línea', intro: 'Crea exámenes de admisión, selección o diagnóstico, asígnalos a aspirantes y revisa sus resultados.',
    introReadOnly: 'Consulta los exámenes en línea de los aspirantes y sus resultados. La creación y edición corresponde a Coordinación Académica.',
    newExam: 'Nuevo examen', refresh: 'Actualizar', search: 'Buscar por título o aspirante', allStates: 'Todos los estados', allTypes: 'Todos los tipos',
    loading: 'Cargando...', empty: 'No hay exámenes que coincidan.', loadError: 'No se pudieron cargar los exámenes.',
    cols: {exam: 'Examen', applicant: 'Aspirante', date: 'Fecha programada', status: 'Estado', grade: 'Calificación', actions: 'Acciones'},
    questions: 'preguntas', minutes: 'min', attempts: 'Intentos', pending: 'Por definir',
    view: 'Ver', edit: 'Editar', cancel: 'Cancelar examen', remove: 'Eliminar', anotherAttempt: 'Otro intento', close: 'Cerrar', back: 'Volver',
    formNew: 'Nuevo examen', formEdit: 'Editar examen', type: 'Tipo', name: 'Título', description: 'Descripción (opcional)',
    date: 'Fecha y hora de disponibilidad', duration: 'Duración (minutos)', maxAttempts: 'Intentos permitidos',
    applicants: 'Aspirantes', applicantSearch: 'Buscar aspirante por nombre, usuario o correo', applicantHint: 'Se creará un examen individual para cada aspirante seleccionado.',
    noCandidates: 'Sin resultados.', selected: 'Seleccionados', removeApplicant: 'Quitar',
    questionsTitle: 'Preguntas', addQuestion: 'Agregar pregunta', questionText: 'Enunciado', multiple: 'Opción múltiple', open: 'Respuesta abierta',
    option: 'Opción', addOption: 'Agregar opción', correct: 'Correcta', correctAnswer: 'Respuesta correcta (se compara sin distinguir mayúsculas)', removeQuestion: 'Quitar pregunta',
    save: 'Guardar', saving: 'Guardando...', created: 'Examen(es) creado(s):', updated: 'Examen actualizado.', removed: 'Examen eliminado.',
    confirmCancel: '¿Cancelar este examen? El aspirante ya no podrá presentarlo.', confirmRemove: '¿Eliminar este examen definitivamente?', confirmAttempt: '¿Habilitar otro intento? Se borrarán las respuestas anteriores.',
    locked: 'Este examen ya fue iniciado: su contenido no se puede modificar.', detail: 'Detalle del examen', yourAnswer: 'Respuesta del aspirante', correctLabel: 'Respuesta correcta', noAnswer: 'Sin responder',
    rightWrong: {true: 'Correcta', false: 'Incorrecta'}, passNote: 'Aprobatoria mínima: 8.0', saveError: 'No se pudo guardar el examen.',
    states: {programado: 'Programado', iniciado: 'En curso', completado: 'Completado', aprobado: 'Aprobado', reprobado: 'Reprobado', cancelado: 'Cancelado'},
  },
  en: {
    kicker: 'ASSESSMENT', title: 'Online exams', intro: 'Create admission, selection or diagnostic exams, assign them to applicants and review their results.',
    introReadOnly: 'Review applicants\u2019 online exams and results. Creating and editing exams is handled by Academic Coordination.',
    newExam: 'New exam', refresh: 'Refresh', search: 'Search by title or applicant', allStates: 'All statuses', allTypes: 'All types',
    loading: 'Loading...', empty: 'No exams match.', loadError: 'Exams could not be loaded.',
    cols: {exam: 'Exam', applicant: 'Applicant', date: 'Scheduled date', status: 'Status', grade: 'Grade', actions: 'Actions'},
    questions: 'questions', minutes: 'min', attempts: 'Attempts', pending: 'To be defined',
    view: 'View', edit: 'Edit', cancel: 'Cancel exam', remove: 'Delete', anotherAttempt: 'Another attempt', close: 'Close', back: 'Back',
    formNew: 'New exam', formEdit: 'Edit exam', type: 'Type', name: 'Title', description: 'Description (optional)',
    date: 'Availability date and time', duration: 'Duration (minutes)', maxAttempts: 'Allowed attempts',
    applicants: 'Applicants', applicantSearch: 'Search applicant by name, username or email', applicantHint: 'An individual exam will be created for each selected applicant.',
    noCandidates: 'No results.', selected: 'Selected', removeApplicant: 'Remove',
    questionsTitle: 'Questions', addQuestion: 'Add question', questionText: 'Question text', multiple: 'Multiple choice', open: 'Open answer',
    option: 'Option', addOption: 'Add option', correct: 'Correct', correctAnswer: 'Correct answer (case-insensitive match)', removeQuestion: 'Remove question',
    save: 'Save', saving: 'Saving...', created: 'Exam(s) created:', updated: 'Exam updated.', removed: 'Exam deleted.',
    confirmCancel: 'Cancel this exam? The applicant will no longer be able to take it.', confirmRemove: 'Delete this exam permanently?', confirmAttempt: 'Allow another attempt? Previous answers will be erased.',
    locked: 'This exam has already been started: its content cannot be changed.', detail: 'Exam details', yourAnswer: 'Applicant answer', correctLabel: 'Correct answer', noAnswer: 'Unanswered',
    rightWrong: {true: 'Correct', false: 'Incorrect'}, passNote: 'Minimum passing grade: 8.0', saveError: 'The exam could not be saved.',
    states: {programado: 'Scheduled', iniciado: 'In progress', completado: 'Completed', aprobado: 'Passed', reprobado: 'Failed', cancelado: 'Cancelled'},
  },
};

const emptyQuestion = () => ({texto: '', abierta: false, opciones: ['', ''], correctIdx: 0, respuesta: ''});
const emptyForm = () => ({tipo: 'admision', titulo: '', descripcion: '', fecha_programada: '', duracion_minutos: 90, max_intentos: 1, aspirantes: [], preguntas: [emptyQuestion()]});

const toLocalInput = (value) => {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

function formatDate(value, locale, fallback) {
  if (!value) return fallback;
  try {
    return new Intl.DateTimeFormat(locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value));
  } catch (e) {
    return value;
  }
}

function errorText(data, fallback) {
  if (!data) return fallback;
  if (data.detail) return data.detail;
  const first = Object.values(data).find((v) => typeof v === 'string' || Array.isArray(v));
  return Array.isArray(first) ? first.join(' ') : first || fallback;
}

function QuestionEditor({question, index, t, onChange, onRemove, canRemove}) {
  const set = (patch) => onChange({...question, ...patch});
  const setOption = (i, value) => set({opciones: question.opciones.map((o, j) => (j === i ? value : o))});
  const removeOption = (i) => {
    const opciones = question.opciones.filter((_, j) => j !== i);
    let correctIdx = question.correctIdx;
    if (i === correctIdx) correctIdx = 0;
    else if (i < correctIdx) correctIdx -= 1;
    set({opciones, correctIdx});
  };
  return (
    <fieldset className="exg-question">
      <legend>{t.questionsTitle} {index + 1}</legend>
      <textarea rows="2" placeholder={t.questionText} value={question.texto} onChange={(e) => set({texto: e.target.value})} aria-label={t.questionText} />
      <div className="exg-segment" role="group">
        <button type="button" className={!question.abierta ? 'is-on' : ''} onClick={() => set({abierta: false})}>{t.multiple}</button>
        <button type="button" className={question.abierta ? 'is-on' : ''} onClick={() => set({abierta: true})}>{t.open}</button>
      </div>
      {question.abierta ? (
        <input type="text" maxLength={255} placeholder={t.correctAnswer} value={question.respuesta} onChange={(e) => set({respuesta: e.target.value})} aria-label={t.correctAnswer} />
      ) : (
        <div className="exg-options">
          {question.opciones.map((opcion, i) => (
            <div className="exg-option-row" key={i}>
              <input type="radio" name={`correct-${index}`} checked={question.correctIdx === i} onChange={() => set({correctIdx: i})} title={t.correct} aria-label={`${t.correct} ${i + 1}`} />
              <input type="text" maxLength={255} placeholder={`${t.option} ${i + 1}`} value={opcion} onChange={(e) => setOption(i, e.target.value)} aria-label={`${t.option} ${i + 1}`} />
              {question.opciones.length > 2 && <button type="button" className="exg-icon-btn" onClick={() => removeOption(i)} aria-label={t.removeApplicant}>×</button>}
            </div>
          ))}
          {question.opciones.length < 8 && <button type="button" className="qa-btn" onClick={() => set({opciones: [...question.opciones, '']})}>{t.addOption}</button>}
        </div>
      )}
      {canRemove && <button type="button" className="exg-link" onClick={onRemove}>{t.removeQuestion}</button>}
    </fieldset>
  );
}

function ExamForm({t, tipos, headers, initial, editingId, onSaved, onCancel}) {
  const [form, setForm] = useState(initial);
  const [candidates, setCandidates] = useState([]);
  const [query, setQuery] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (editingId) return undefined;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      fetch(`/api/examenes-gestion/candidatos/?q=${encodeURIComponent(query)}`, {headers, signal: controller.signal})
        .then((r) => (r.ok ? r.json() : {aspirantes: []})).then((d) => setCandidates(d.aspirantes || [])).catch(() => {});
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, headers, editingId]);

  const set = (patch) => setForm((prev) => ({...prev, ...patch}));
  const toggleApplicant = (a) => set({aspirantes: form.aspirantes.some((x) => x.id === a.id) ? form.aspirantes.filter((x) => x.id !== a.id) : [...form.aspirantes, a]});

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    const preguntas = form.preguntas.map((q) => (q.abierta
      ? {texto: q.texto, opciones: [], respuesta_correcta: q.respuesta}
      : {texto: q.texto, opciones: q.opciones, respuesta_correcta: q.opciones[q.correctIdx] || ''}));
    const body = {
      tipo: form.tipo, titulo: form.titulo, descripcion: form.descripcion,
      fecha_programada: form.fecha_programada ? new Date(form.fecha_programada).toISOString() : '',
      duracion_minutos: Number(form.duracion_minutos), max_intentos: Number(form.max_intentos), preguntas,
    };
    if (!editingId) body.aspirantes = form.aspirantes.map((a) => a.id);
    setSaving(true);
    try {
      const response = await fetch(editingId ? `/api/examenes-gestion/${editingId}/` : '/api/examenes-gestion/', {method: editingId ? 'PATCH' : 'POST', headers, body: JSON.stringify(body)});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) setError(errorText(data, t.saveError));
      else onSaved(editingId ? t.updated : `${t.created} ${data.creados}`);
    } catch (e) {
      setError(t.saveError);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="exg-form" onSubmit={submit}>
      <h4>{editingId ? t.formEdit : t.formNew}</h4>
      <div className="exg-grid">
        <label>{t.type}<select value={form.tipo} onChange={(e) => set({tipo: e.target.value})}>{tipos.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}</select></label>
        <label>{t.name}<input type="text" required maxLength={255} value={form.titulo} onChange={(e) => set({titulo: e.target.value})} /></label>
        <label>{t.date}<input type="datetime-local" required value={form.fecha_programada} onChange={(e) => set({fecha_programada: e.target.value})} /></label>
        <label>{t.duration}<input type="number" min="5" max="480" required value={form.duracion_minutos} onChange={(e) => set({duracion_minutos: e.target.value})} /></label>
        <label>{t.maxAttempts}<input type="number" min="1" max="5" required value={form.max_intentos} onChange={(e) => set({max_intentos: e.target.value})} /></label>
      </div>
      <label className="exg-full">{t.description}<textarea rows="2" value={form.descripcion} onChange={(e) => set({descripcion: e.target.value})} /></label>

      {!editingId && (
        <section className="exg-applicants">
          <h5>{t.applicants}</h5>
          <p className="exg-hint">{t.applicantHint}</p>
          <input type="search" placeholder={t.applicantSearch} value={query} onChange={(e) => setQuery(e.target.value)} aria-label={t.applicantSearch} />
          <div className="exg-candidate-list">
            {candidates.length ? candidates.map((a) => (
              <label key={a.id} className="exg-candidate">
                <input type="checkbox" checked={form.aspirantes.some((x) => x.id === a.id)} onChange={() => toggleApplicant(a)} />
                <span><strong>{a.nombre}</strong><small>{a.usuario} · {a.correo}</small></span>
              </label>
            )) : <p className="exg-hint">{t.noCandidates}</p>}
          </div>
          {form.aspirantes.length > 0 && (
            <div className="exg-chips" aria-label={t.selected}>
              {form.aspirantes.map((a) => <span key={a.id} className="exg-chip">{a.nombre}<button type="button" onClick={() => toggleApplicant(a)} aria-label={`${t.removeApplicant} ${a.nombre}`}>×</button></span>)}
            </div>
          )}
        </section>
      )}

      <section>
        <h5>{t.questionsTitle} ({form.preguntas.length})</h5>
        {form.preguntas.map((q, i) => (
          <QuestionEditor key={i} question={q} index={i} t={t} canRemove={form.preguntas.length > 1}
            onChange={(next) => set({preguntas: form.preguntas.map((x, j) => (j === i ? next : x))})}
            onRemove={() => set({preguntas: form.preguntas.filter((_, j) => j !== i)})} />
        ))}
        <button type="button" className="qa-btn" onClick={() => set({preguntas: [...form.preguntas, emptyQuestion()]})}>{t.addQuestion}</button>
      </section>

      {error && <p className="exg-error" role="alert">{error}</p>}
      <div className="exg-actions">
        <button type="submit" className="btn-primary" disabled={saving}>{saving ? t.saving : t.save}</button>
        <button type="button" className="qa-btn" onClick={onCancel}>{t.back}</button>
      </div>
    </form>
  );
}

function ExamDetail({exam, t, locale, canManage, onBack, onEdit, onCancelExam, onAnotherAttempt, onRemove}) {
  const finished = ['aprobado', 'reprobado', 'completado'].includes(exam.estado);
  return (
    <div className="exg-detail">
      <div className="exg-detail-head">
        <div><h4>{exam.titulo}</h4><p>{exam.tipo_label} · {exam.duracion_minutos} {t.minutes} · {t.attempts}: {exam.intentos}/{exam.max_intentos}</p></div>
        <span className={`estado-badge estado-${exam.estado}`}>{t.states[exam.estado] || exam.estado_label}</span>
      </div>
      <p><strong>{exam.aspirante.nombre}</strong> · {exam.aspirante.correo}</p>
      <p>{formatDate(exam.fecha_programada, locale, t.pending)}</p>
      {exam.descripcion && <p>{exam.descripcion}</p>}
      {finished && exam.calificacion !== null && <p>{t.cols.grade}: <strong>{exam.calificacion}</strong> <small>({t.passNote})</small></p>}
      {!exam.editable && canManage && <p className="exg-hint">{t.locked}</p>}
      <ol className="exg-detail-questions">
        {(exam.preguntas || []).map((p) => (
          <li key={p.id}>
            <p>{p.texto}</p>
            {p.opciones?.length > 0 && <ul>{p.opciones.map((o) => <li key={o}>{o}</li>)}</ul>}
            {canManage && <p className="exg-hint">{t.correctLabel}: <strong>{p.respuesta_correcta}</strong></p>}
            {canManage && finished && (
              <p className={`exg-hint ${p.es_correcta ? 'is-ok' : 'is-bad'}`}>
                {t.yourAnswer}: <strong>{p.respuesta_aspirante ?? t.noAnswer}</strong>{p.es_correcta !== null && p.es_correcta !== undefined ? ` — ${t.rightWrong[String(p.es_correcta)]}` : ''}
              </p>
            )}
          </li>
        ))}
      </ol>
      <div className="exg-actions">
        <button type="button" className="qa-btn" onClick={onBack}>{t.back}</button>
        {canManage && exam.editable && <button type="button" className="btn-primary" onClick={onEdit}>{t.edit}</button>}
        {canManage && ['reprobado', 'cancelado', 'iniciado'].includes(exam.estado) && <button type="button" className="qa-btn" onClick={onAnotherAttempt}>{t.anotherAttempt}</button>}
        {canManage && !finished && exam.estado !== 'cancelado' && <button type="button" className="qa-btn" onClick={onCancelExam}>{t.cancel}</button>}
        {canManage && exam.intentos === 0 && <button type="button" className="qa-btn exg-danger" onClick={onRemove}>{t.remove}</button>}
      </div>
    </div>
  );
}

export default function ExamenesGestionPanel({session}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const locale = language === 'en' ? 'en-US' : 'es-MX';
  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'}), [session.access]);
  const [data, setData] = useState({examenes: [], resumen: {}, tipos: [], puede_crear: false});
  const [filters, setFilters] = useState({q: '', estado: '', tipo: ''});
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [view, setView] = useState({mode: 'list'});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
      const response = await fetch(`/api/examenes-gestion/?${params}`, {headers});
      if (!response.ok) throw new Error();
      setData(await response.json());
    } catch (e) {
      setMessage({type: 'error', text: t.loadError});
    } finally {
      setLoading(false);
    }
  }, [filters, headers, t.loadError]);

  useEffect(() => {
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
  }, [load]);

  const openDetail = async (id, mode = 'detail') => {
    const response = await fetch(`/api/examenes-gestion/${id}/`, {headers});
    const exam = await response.json().catch(() => ({}));
    if (!response.ok) return setMessage({type: 'error', text: errorText(exam, t.loadError)});
    setView({mode, exam});
  };

  const act = async (exam, request, confirmText, success) => {
    if (confirmText && !window.confirm(confirmText)) return;
    const response = await fetch(`/api/examenes-gestion/${exam.id}/`, {headers, ...request});
    const body = response.status === 204 ? {} : await response.json().catch(() => ({}));
    if (!response.ok) return setMessage({type: 'error', text: errorText(body, t.saveError)});
    setMessage({type: 'success', text: success});
    setView({mode: 'list'});
    load();
  };

  const editInitial = (exam) => ({
    tipo: exam.tipo, titulo: exam.titulo, descripcion: exam.descripcion, fecha_programada: toLocalInput(exam.fecha_programada),
    duracion_minutos: exam.duracion_minutos, max_intentos: exam.max_intentos, aspirantes: [],
    preguntas: (exam.preguntas || []).map((p) => {
      const abierta = !p.opciones?.length;
      const idx = abierta ? 0 : p.opciones.findIndex((o) => o.toLowerCase() === String(p.respuesta_correcta).toLowerCase());
      return {texto: p.texto, abierta, opciones: abierta ? ['', ''] : p.opciones, correctIdx: Math.max(0, idx), respuesta: abierta ? p.respuesta_correcta : ''};
    }),
  });

  const onSaved = (text) => { setMessage({type: 'success', text}); setView({mode: 'list'}); load(); };

  return (
    <div className="panel-card exg-panel">
      <div className="admin-card-head">
        <div>
          <p className="panel-kicker">{t.kicker}</p>
          <h3>{t.title}</h3>
          <p>{data.puede_crear ? t.intro : t.introReadOnly}</p>
        </div>
        {view.mode === 'list' && (
          <div className="exg-actions">
            <button type="button" className="qa-btn" onClick={load}>{t.refresh}</button>
            {data.puede_crear && <button type="button" className="btn-primary" onClick={() => setView({mode: 'new'})}>{t.newExam}</button>}
          </div>
        )}
      </div>
      {message && <p className={`exg-notice exg-notice--${message.type}`} role={message.type === 'error' ? 'alert' : 'status'}>{message.text}</p>}

      {view.mode === 'new' && <ExamForm t={t} tipos={data.tipos} headers={headers} initial={emptyForm()} onSaved={onSaved} onCancel={() => setView({mode: 'list'})} />}
      {view.mode === 'edit' && <ExamForm t={t} tipos={data.tipos} headers={headers} initial={editInitial(view.exam)} editingId={view.exam.id} onSaved={onSaved} onCancel={() => setView({mode: 'detail', exam: view.exam})} />}
      {view.mode === 'detail' && (
        <ExamDetail exam={view.exam} t={t} locale={locale} canManage={data.puede_crear} onBack={() => setView({mode: 'list'})}
          onEdit={() => setView({mode: 'edit', exam: view.exam})}
          onCancelExam={() => act(view.exam, {method: 'PATCH', body: JSON.stringify({accion: 'cancelar'})}, t.confirmCancel, t.updated)}
          onAnotherAttempt={() => act(view.exam, {method: 'PATCH', body: JSON.stringify({accion: 'otro_intento'})}, t.confirmAttempt, t.updated)}
          onRemove={() => act(view.exam, {method: 'DELETE'}, t.confirmRemove, t.removed)} />
      )}

      {view.mode === 'list' && (
        <>
          <div className="exg-summary">
            {Object.entries(t.states).map(([estado, label]) => (
              <button type="button" key={estado} className={`exg-stat${filters.estado === estado ? ' is-on' : ''}`} onClick={() => setFilters((f) => ({...f, estado: f.estado === estado ? '' : estado}))}>
                <strong>{data.resumen?.[estado] ?? 0}</strong><span>{label}</span>
              </button>
            ))}
          </div>
          <div className="exg-filters">
            <input type="search" placeholder={t.search} value={filters.q} onChange={(e) => setFilters((f) => ({...f, q: e.target.value}))} aria-label={t.search} />
            <select value={filters.tipo} onChange={(e) => setFilters((f) => ({...f, tipo: e.target.value}))} aria-label={t.allTypes}>
              <option value="">{t.allTypes}</option>
              {data.tipos.map((x) => <option key={x.value} value={x.value}>{x.label}</option>)}
            </select>
            <select value={filters.estado} onChange={(e) => setFilters((f) => ({...f, estado: e.target.value}))} aria-label={t.allStates}>
              <option value="">{t.allStates}</option>
              {Object.entries(t.states).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </div>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>{t.cols.exam}</th><th>{t.cols.applicant}</th><th>{t.cols.date}</th><th>{t.cols.status}</th><th>{t.cols.grade}</th><th>{t.cols.actions}</th></tr></thead>
              <tbody>
                {loading && !data.examenes.length ? <tr><td colSpan="6">{t.loading}</td></tr> : data.examenes.length ? data.examenes.map((exam) => (
                  <tr key={exam.id}>
                    <td><strong>{exam.titulo}</strong><small>{exam.tipo_label} · {exam.total_preguntas} {t.questions} · {exam.duracion_minutos} {t.minutes}</small></td>
                    <td><strong>{exam.aspirante.nombre}</strong><small>{exam.aspirante.usuario}</small></td>
                    <td>{formatDate(exam.fecha_programada, locale, t.pending)}</td>
                    <td><span className={`estado-badge estado-${exam.estado}`}>{t.states[exam.estado] || exam.estado_label}</span></td>
                    <td>{exam.calificacion ?? '—'}</td>
                    <td><button type="button" className="qa-btn" onClick={() => openDetail(exam.id)}>{t.view}</button></td>
                  </tr>
                )) : <tr><td colSpan="6">{t.empty}</td></tr>}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
