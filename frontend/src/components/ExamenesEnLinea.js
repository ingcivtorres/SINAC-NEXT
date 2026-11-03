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
    errStart: 'No se pudo iniciar el examen.', errSend: 'No se pudo enviar el examen.', errLoad: 'No se pudieron cargar los exámenes.', availableFrom: 'Disponible a partir de', retrySend: 'Reintentar envío',
    states: {programado: 'Programado', iniciado: 'En curso', completado: 'Completado', aprobado: 'Aprobado', reprobado: 'Reprobado', cancelado: 'Cancelado'},
    types: {admision: 'Examen de Admisión', seleccion: 'Examen de Selección', diagnostico: 'Examen de Diagnóstico', predoctoral: 'Examen predoctoral', otro: 'Otro'},
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
    errStart: 'The exam could not be started.', errSend: 'The exam could not be submitted.', errLoad: 'Exams could not be loaded.', availableFrom: 'Available from', retrySend: 'Retry submission',
    states: {programado: 'Scheduled', iniciado: 'In progress', completado: 'Completed', aprobado: 'Passed', reprobado: 'Failed', cancelado: 'Cancelled'},
    types: {admision: 'Admission exam', seleccion: 'Selection exam', diagnostico: 'Diagnostic exam', predoctoral: 'Predoctoral exam', otro: 'Other'},
  },
  de: {
    title: 'Online-Prüfungen', intro: 'Sehen Sie Ihre zugewiesenen Prüfungen ein, starten Sie sie, sobald sie verfügbar sind, und prüfen Sie Ihr Ergebnis.',
    empty: 'Ihnen wurden noch keine Prüfungen zugewiesen.', minutes: 'Minuten', date: 'Geplantes Datum', pending: 'Noch festzulegen',
    attempts: 'Versuche', questions: 'Fragen', start: 'Prüfung starten', starting: 'Wird gestartet...',
    confirmStart: 'Beim Start beginnt die Zeitmessung und einer Ihrer Versuche wird verbraucht. Möchten Sie fortfahren?',
    inProgress: 'Prüfung läuft', timeLeft: 'Verbleibende Zeit', answered: 'beantwortet', question: 'Frage',
    typeAnswer: 'Geben Sie Ihre Antwort ein', submit: 'Prüfung abgeben', submitting: 'Wird abgegeben...',
    confirmSubmit: 'Einige Fragen sind unbeantwortet. Prüfung trotzdem abgeben?',
    timeUp: 'Die Zeit ist abgelaufen; Ihre Prüfung wurde automatisch abgegeben.', sent: 'Prüfung abgegeben.',
    score: 'Note', feedback: 'Rückmeldung', passNote: 'Mindestnote zum Bestehen: 8,0',
    errStart: 'Die Prüfung konnte nicht gestartet werden.', errSend: 'Die Prüfung konnte nicht abgegeben werden.', errLoad: 'Die Prüfungen konnten nicht geladen werden.', availableFrom: 'Verfügbar ab', retrySend: 'Abgabe erneut versuchen',
    states: {programado: 'Geplant', iniciado: 'Läuft', completado: 'Abgeschlossen', aprobado: 'Bestanden', reprobado: 'Nicht bestanden', cancelado: 'Abgesagt'},
    types: {admision: 'Aufnahmeprüfung', seleccion: 'Auswahlprüfung', diagnostico: 'Diagnoseprüfung', predoctoral: 'Prädoktorale Prüfung', otro: 'Sonstige'},
  },
  zh: {
    title: '在线考试', intro: '查看分配给你的考试，在开放时开始作答并查看结果。',
    empty: '你还没有被分配考试。', minutes: '分钟', date: '计划日期', pending: '待定',
    attempts: '尝试次数', questions: '道题', start: '开始考试', starting: '正在开始...',
    confirmStart: '开始后将开始计时，并消耗一次尝试机会。是否继续？',
    inProgress: '考试进行中', timeLeft: '剩余时间', answered: '已作答', question: '题目',
    typeAnswer: '请输入你的答案', submit: '提交考试', submitting: '正在提交...',
    confirmSubmit: '还有题目未作答。仍要提交考试吗？',
    timeUp: '时间已到，考试已自动提交。', sent: '考试已提交。',
    score: '成绩', feedback: '反馈', passNote: '最低及格分：8.0',
    errStart: '无法开始考试。', errSend: '无法提交考试。', errLoad: '无法加载考试。', availableFrom: '开放时间', retrySend: '重新提交',
    states: {programado: '已安排', iniciado: '进行中', completado: '已完成', aprobado: '通过', reprobado: '未通过', cancelado: '已取消'},
    types: {admision: '入学考试', seleccion: '选拔考试', diagnostico: '诊断考试', predoctoral: '博士资格考试', otro: '其他'},
  },
  pt: {
    title: 'Exames on-line', intro: 'Consulte seus exames atribuídos, inicie-os quando estiverem disponíveis e veja seu resultado.',
    empty: 'Você ainda não tem exames atribuídos.', minutes: 'minutos', date: 'Data programada', pending: 'A definir',
    attempts: 'Tentativas', questions: 'perguntas', start: 'Iniciar exame', starting: 'Iniciando...',
    confirmStart: 'Ao iniciar, a contagem de tempo começará e uma de suas tentativas será usada. Deseja continuar?',
    inProgress: 'Exame em andamento', timeLeft: 'Tempo restante', answered: 'respondidas', question: 'Pergunta',
    typeAnswer: 'Escreva sua resposta', submit: 'Enviar exame', submitting: 'Enviando...',
    confirmSubmit: 'Há perguntas sem resposta. Enviar o exame mesmo assim?',
    timeUp: 'O tempo acabou; seu exame foi enviado automaticamente.', sent: 'Exame enviado.',
    score: 'Nota', feedback: 'Feedback', passNote: 'Nota mínima para aprovação: 8,0',
    errStart: 'Não foi possível iniciar o exame.', errSend: 'Não foi possível enviar o exame.', errLoad: 'Não foi possível carregar os exames.', availableFrom: 'Disponível a partir de', retrySend: 'Tentar enviar novamente',
    states: {programado: 'Programado', iniciado: 'Em andamento', completado: 'Concluído', aprobado: 'Aprovado', reprobado: 'Reprovado', cancelado: 'Cancelado'},
    types: {admision: 'Exame de admissão', seleccion: 'Exame de seleção', diagnostico: 'Exame de diagnóstico', predoctoral: 'Exame predoctoral', otro: 'Outro'},
  },
};

const LOCALES = {es: 'es-MX', en: 'en-US', de: 'de-DE', zh: 'zh-CN', pt: 'pt-BR'};

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

const claveRespuestas = id => `sinac-examen-${id}`;

function leerRespuestas(id) {
  try { return JSON.parse(sessionStorage.getItem(claveRespuestas(id))) || {}; } catch (e) { return {}; }
}

function ExamTaker({examen, t, headers, onUpdated, onNotice}) {
  const [answers, setAnswers] = useState(() => leerRespuestas(examen.id));
  const [sending, setSending] = useState(false);
  const [now, setNow] = useState(Date.now());
  const submittedRef = useRef(false);
  const autoEnviadoRef = useRef(false);

  useEffect(() => {
    try { sessionStorage.setItem(claveRespuestas(examen.id), JSON.stringify(answers)); } catch (e) { /* almacenamiento no disponible */ }
  }, [answers, examen.id]);
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
        try { sessionStorage.removeItem(claveRespuestas(examen.id)); } catch (e) { /* almacenamiento no disponible */ }
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
    if (remaining <= 0 && !autoEnviadoRef.current) {
      autoEnviadoRef.current = true;
      submit(true);
    }
  }, [remaining, submit]);

  const tiempoAgotado = remaining <= 0;
  const handleSubmit = () => {
    if (!tiempoAgotado && answered < preguntas.length && !window.confirm(t.confirmSubmit)) return;
    submit(tiempoAgotado);
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
        {sending ? t.submitting : tiempoAgotado ? t.retrySend : t.submit}
      </button>
    </article>
  );
}

export default function ExamenesEnLinea({session, examenes, onChange}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const locale = LOCALES[language] || LOCALES.es;
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
            const futuro = examen.fecha_programada && new Date(examen.fecha_programada).getTime() > Date.now();
            const canStart = examen.estado === 'programado' && examen.tipo !== 'predoctoral' && !active && !futuro && examen.intentos < examen.max_intentos;
            return (
              <article key={examen.id}>
                <strong>{examen.titulo}</strong>
                <p>{t.types[examen.tipo] || examen.tipo_label} · {examen.duracion_minutos} {t.minutes}{examen.total_preguntas ? ` · ${examen.total_preguntas} ${t.questions}` : ''}</p>
                {examen.descripcion && <p>{examen.descripcion}</p>}
                <p>{t.date}: {formatDate(examen.fecha_programada, locale, t.pending)} · {t.attempts}: {examen.intentos}/{examen.max_intentos}</p>
                <span className={`estado-badge estado-${examen.estado}`}>{t.states[examen.estado] || examen.estado_label}</span>
                {finished && examen.calificacion !== null && examen.calificacion !== undefined && (
                  <p>{t.score}: <strong>{examen.calificacion}</strong> <small>({t.passNote})</small></p>
                )}
                {examen.retroalimentacion && <p><strong>{t.feedback}:</strong> {examen.retroalimentacion}</p>}
                {examen.estado === 'programado' && examen.tipo !== 'predoctoral' && futuro && (
                  <p><small>{t.availableFrom} {formatDate(examen.fecha_programada, locale, t.pending)}</small></p>
                )}
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
