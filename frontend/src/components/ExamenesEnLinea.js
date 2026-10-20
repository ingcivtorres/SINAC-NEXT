import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {useLanguage} from '../translations';
import './ExamenesEnLinea.css';

const COPY = {
  es: {
    title: 'Exámenes en línea', intro: 'Consulta tus exámenes asignados, inícialos cuando estén disponibles y revisa tu resultado.',
    empty: 'Aún no tienes exámenes asignados.', minutes: 'minutos', date: 'Fecha programada', pending: 'Por definir',
    attempts: 'Intentos', questions: 'preguntas', start: 'Iniciar examen', starting: 'Iniciando...',
    confirmStart: 'Al iniciar comenzará el conteo de tiempo y se usará uno de tus intentos. ¿Deseas continuar?',
    inProgress: 'Examen en curso', timeLeft: 'Tiempo restante', answered: 'respondidas', question: 'Pregunta',
    typeAnswer: 'Escribe tu respuesta', submit: 'Enviar examen', submitting: 'Enviando...',
    confirmSubmit: 'Tienes preguntas sin responder. ¿Enviar el examen de todos modos?',
    timeUp: 'Se agotó el tiempo; tu examen se envió automáticamente.', sent: 'Examen enviado.',
    score: 'Calificación', feedback: 'Retroalimentación', passNote: 'Aprobatoria mínima: 8.0',
    errStart: 'No se pudo iniciar el examen.', errSend: 'No se pudo enviar el examen.', errLoad: 'No se pudieron cargar los exámenes.',
    states: {programado: 'Programado', iniciado: 'En curso', completado: 'Completado', aprobado: 'Aprobado', reprobado: 'Reprobado', cancelado: 'Cancelado'},
  },
  en: {
    title: 'Online exams', intro: 'Review your assigned exams, start them when they are available and check your result.',
    empty: 'No exams have been assigned yet.', minutes: 'minutes', date: 'Scheduled date', pending: 'To be defined',
    attempts: 'Attempts', questions: 'questions', start: 'Start exam', starting: 'Starting...',
    confirmStart: 'Starting will begin the timer and use one of your attempts. Do you want to continue?',
    inProgress: 'Exam in progress', timeLeft: 'Time left', answered: 'answered', question: 'Question',
    typeAnswer: 'Type your answer', submit: 'Submit exam', submitting: 'Submitting...',
    confirmSubmit: 'Some questions are unanswered. Submit the exam anyway?',
    timeUp: 'Time is up; your exam was submitted automatically.', sent: 'Exam submitted.',
    score: 'Grade', feedback: 'Feedback', passNote: 'Minimum passing grade: 8.0',
    errStart: 'The exam could not be started.', errSend: 'The exam could not be submitted.', errLoad: 'Exams could not be loaded.',
    states: {programado: 'Scheduled', iniciado: 'In progress', completado: 'Completed', aprobado: 'Passed', reprobado: 'Failed', cancelado: 'Cancelled'},
  },
};

const pad = (n) => String(n).padStart(2, '0');

function formatRemaining(ms) {
  const total = Math.max(0, Math.floor(ms / 1000));
  return `${pad(Math.floor(total / 3600))}:${pad(Math.floor((total % 3600) / 60))}:${pad(total % 60)}`;
}

function formatDate(value, locale, fallback) {
  if (!value) return fallback;
  try {
    return new Intl.DateTimeFormat(locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value));
  } catch (e) {
    return value;
  }
}

function ExamTaker({examen, t, headers, onUpdated, onNotice}) {
  const [answers, setAnswers] = useState({});
  const [sending, setSending] = useState(false);
  const [now, setNow] = useState(Date.now());
  const submittedRef = useRef(false);
  const deadline = useMemo(() => {
    const start = examen.fecha_inicio ? new Date(examen.fecha_inicio).getTime() : Date.now();
    return start + examen.duracion_minutos * 60000;
  }, [examen.fecha_inicio, examen.duracion_minutos]);
  const remaining = deadline - now;
  const preguntas = examen.preguntas || [];
  const answered = preguntas.filter((p) => String(answers[p.id] || '').trim()).length;

  const submit = useCallback(async (auto = false) => {
    if (submittedRef.current) return;
    submittedRef.current = true;
    setSending(true);
    try {
      const response = await fetch('/api/preregistro/examenes/', {
        method: 'PUT', headers, body: JSON.stringify({id: examen.id, respuestas: answers}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        submittedRef.current = false;
        onNotice({type: 'error', text: data.detail || t.errSend});
      } else {
        onUpdated(data);
        onNotice({type: 'success', text: `${auto ? t.timeUp : t.sent} ${t.score}: ${data.calificacion}`});
      }
    } catch (e) {
      submittedRef.current = false;
      onNotice({type: 'error', text: t.errSend});
    } finally {
      setSending(false);
    }
  }, [answers, examen.id, headers, onNotice, onUpdated, t]);

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (remaining <= 0) submit(true);
  }, [remaining, submit]);

  const handleSubmit = () => {
    if (answered < preguntas.length && !window.confirm(t.confirmSubmit)) return;
    submit(false);
  };

  return (
    <article className="exam-taker" aria-live="polite">
      <header className="exam-taker-header">
        <div><strong>{examen.titulo}</strong><p>{t.inProgress} · {answered}/{preguntas.length} {t.answered}</p></div>
        <div className={`exam-timer${remaining < 300000 ? ' is-low' : ''}`} role="timer">
          <span>{t.timeLeft}</span><strong>{formatRemaining(remaining)}</strong>
        </div>
      </header>
      <ol className="exam-questions">
        {preguntas.map((pregunta, index) => (
          <li key={pregunta.id} className="exam-question">
            <p><strong>{t.question} {index + 1}.</strong> {pregunta.texto}</p>
            {Array.isArray(pregunta.opciones) && pregunta.opciones.length ? (
              <div className="exam-options" role="radiogroup">
                {pregunta.opciones.map((opcion) => (
                  <label key={opcion} className="exam-option">
                    <input
                      type="radio" name={`pregunta-${pregunta.id}`} value={opcion}
                      checked={answers[pregunta.id] === opcion}
                      onChange={() => setAnswers((prev) => ({...prev, [pregunta.id]: opcion}))}
                      disabled={sending}
                    />
                    <span>{opcion}</span>
                  </label>
                ))}
              </div>
            ) : (
              <input
                type="text" className="exam-text" placeholder={t.typeAnswer} value={answers[pregunta.id] || ''}
                onChange={(event) => setAnswers((prev) => ({...prev, [pregunta.id]: event.target.value}))}
                disabled={sending} maxLength={255}
              />
            )}
          </li>
        ))}
      </ol>
      <button type="button" className="btn-primary" onClick={handleSubmit} disabled={sending}>
        {sending ? t.submitting : t.submit}
      </button>
    </article>
  );
}

export default function ExamenesEnLinea({session, examenes, onChange}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const locale = language === 'en' ? 'en-US' : 'es-MX';
  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'}), [session.access]);
  const [notice, setNotice] = useState(null);
  const [startingId, setStartingId] = useState(null);

  const replaceExam = useCallback((updated) => {
    onChange((items) => items.map((item) => (item.id === updated.id ? {...item, ...updated} : item)));
  }, [onChange]);

  const startExam = async (examen) => {
    if (!window.confirm(t.confirmStart)) return;
    setNotice(null);
    setStartingId(examen.id);
    try {
      const response = await fetch('/api/preregistro/examenes/', {method: 'POST', headers, body: JSON.stringify({id: examen.id})});
      const data = await response.json().catch(() => ({}));
      if (!response.ok) setNotice({type: 'error', text: data.detail || t.errStart});
      else replaceExam(data);
    } catch (e) {
      setNotice({type: 'error', text: t.errStart});
    } finally {
      setStartingId(null);
    }
  };

  const active = examenes.find((examen) => examen.estado === 'iniciado' && examen.tipo !== 'predoctoral');
  const others = examenes.filter((examen) => examen !== active);

  return (
    <div className="panel-card exam-panel">
      <h3>{t.title}</h3>
      <p>{t.intro}</p>
      {notice && <p className={`exam-notice exam-notice--${notice.type}`} role={notice.type === 'error' ? 'alert' : 'status'}>{notice.text}</p>}
      {active && <ExamTaker key={active.id} examen={active} t={t} headers={headers} onUpdated={replaceExam} onNotice={setNotice} />}
      {!examenes.length && <p className="empty-state">{t.empty}</p>}
      {others.length > 0 && (
        <div className="request-list">
          {others.map((examen) => {
            const finished = ['aprobado', 'reprobado', 'completado'].includes(examen.estado);
            const canStart = examen.estado === 'programado' && examen.tipo !== 'predoctoral' && !active;
            return (
              <article key={examen.id}>
                <strong>{examen.titulo}</strong>
                <p>{examen.tipo_label} · {examen.duracion_minutos} {t.minutes}{examen.total_preguntas ? ` · ${examen.total_preguntas} ${t.questions}` : ''}</p>
                {examen.descripcion && <p>{examen.descripcion}</p>}
                <p>{t.date}: {formatDate(examen.fecha_programada, locale, t.pending)} · {t.attempts}: {examen.intentos}/{examen.max_intentos}</p>
                <span className={`estado-badge estado-${examen.estado}`}>{t.states[examen.estado] || examen.estado_label}</span>
                {finished && examen.calificacion !== null && examen.calificacion !== undefined && (
                  <p>{t.score}: <strong>{examen.calificacion}</strong> <small>({t.passNote})</small></p>
                )}
                {examen.retroalimentacion && <p><strong>{t.feedback}:</strong> {examen.retroalimentacion}</p>}
                {canStart && (
                  <button type="button" className="btn-primary" onClick={() => startExam(examen)} disabled={startingId === examen.id}>
                    {startingId === examen.id ? t.starting : t.start}
                  </button>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
