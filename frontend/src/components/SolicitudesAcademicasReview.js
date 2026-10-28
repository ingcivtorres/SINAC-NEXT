import React, {useCallback, useEffect, useMemo, useState} from 'react';
import {useLanguage} from '../translations';
import './SolicitudesAcademicasReview.css';

const translations = {
  es: {title:'Solicitudes académicas', intro:'Revisa las solicitudes asignadas a tu área. Cada resolución requiere una respuesta para que el alumno conozca el resultado.', loading:'Cargando solicitudes...', retry:'Reintentar', refresh:'Actualizar', pending:'Pendiente', accepted:'Aceptada', rejected:'Rechazada', type:{historial:'Historial académico', reinscripcion:'Reinscripción', ajuste_materias:'Ajuste de materias'}, student:'Alumno', submitted:'Enviada', request:'Solicitud', response:'Respuesta al alumno', responseHint:'Escribe una respuesta clara (mínimo 5 caracteres, máximo 2000).', responsePlaceholder:'Explica la resolución y los pasos siguientes, si aplica.', approve:'Aceptar solicitud', reject:'Rechazar solicitud', saving:'Guardando...', empty:'No hay solicitudes académicas asignadas a tu área.', loadError:'No se pudieron cargar las solicitudes académicas.', saveError:'No se pudo resolver la solicitud.', required:'Escribe una respuesta de al menos 5 caracteres.', saved:'La respuesta quedó registrada y se notificó al alumno.', resolvedBy:'Resuelta por'},
  en: {title:'Academic requests', intro:'Review requests assigned to your department. A response is required so the student can understand the decision.', loading:'Loading requests...', retry:'Retry', refresh:'Refresh', pending:'Pending', accepted:'Accepted', rejected:'Rejected', type:{historial:'Academic transcript', reinscripcion:'Re-enrollment', ajuste_materias:'Course adjustment'}, student:'Student', submitted:'Submitted', request:'Request', response:'Response to student', responseHint:'Write a clear response (5–2000 characters).', responsePlaceholder:'Explain the decision and any next steps.', approve:'Accept request', reject:'Reject request', saving:'Saving...', empty:'There are no academic requests assigned to your department.', loadError:'Could not load academic requests.', saveError:'Could not resolve the request.', required:'Enter a response of at least 5 characters.', saved:'The response was recorded and the student was notified.', resolvedBy:'Resolved by'},
  de: {title:'Akademische Anträge', intro:'Prüfen Sie die Ihrem Bereich zugewiesenen Anträge. Eine Antwort ist erforderlich, damit Studierende die Entscheidung nachvollziehen können.', loading:'Anträge werden geladen...', retry:'Erneut versuchen', refresh:'Aktualisieren', pending:'Ausstehend', accepted:'Genehmigt', rejected:'Abgelehnt', type:{historial:'Akademischer Werdegang', reinscripcion:'Wiedereinschreibung', ajuste_materias:'Kursanpassung'}, student:'Studierende', submitted:'Eingereicht', request:'Anliegen', response:'Antwort an Studierende', responseHint:'Verfassen Sie eine klare Antwort (5–2000 Zeichen).', responsePlaceholder:'Erläutern Sie die Entscheidung und mögliche nächste Schritte.', approve:'Antrag genehmigen', reject:'Antrag ablehnen', saving:'Wird gespeichert...', empty:'Ihrem Bereich sind keine Anträge zugewiesen.', loadError:'Anträge konnten nicht geladen werden.', saveError:'Antrag konnte nicht bearbeitet werden.', required:'Geben Sie eine Antwort mit mindestens 5 Zeichen ein.', saved:'Die Antwort wurde gespeichert und die studierende Person benachrichtigt.', resolvedBy:'Bearbeitet von'},
  zh: {title:'学术申请', intro:'审核分配给您部门的申请。请填写答复，让学生了解处理结果。', loading:'正在加载申请...', retry:'重试', refresh:'刷新', pending:'待处理', accepted:'已批准', rejected:'已拒绝', type:{historial:'学业记录', reinscripcion:'重新注册', ajuste_materias:'课程调整'}, student:'学生', submitted:'提交时间', request:'申请内容', response:'给学生的答复', responseHint:'请填写清晰答复（5 至 2000 个字符）。', responsePlaceholder:'说明处理决定及后续步骤。', approve:'批准申请', reject:'拒绝申请', saving:'正在保存...', empty:'您的部门目前没有待处理的学术申请。', loadError:'无法加载学术申请。', saveError:'无法处理申请。', required:'答复至少需要 5 个字符。', saved:'答复已保存并通知学生。', resolvedBy:'处理人'},
  pt: {title:'Solicitações acadêmicas', intro:'Revise as solicitações atribuídas à sua área. É necessário responder para que o aluno conheça a decisão.', loading:'Carregando solicitações...', retry:'Tentar novamente', refresh:'Atualizar', pending:'Pendente', accepted:'Aceita', rejected:'Rejeitada', type:{historial:'Histórico acadêmico', reinscripcion:'Matrícula', ajuste_materias:'Ajuste de disciplinas'}, student:'Aluno', submitted:'Enviada', request:'Solicitação', response:'Resposta ao aluno', responseHint:'Escreva uma resposta clara (5 a 2000 caracteres).', responsePlaceholder:'Explique a decisão e os próximos passos, se houver.', approve:'Aceitar solicitação', reject:'Rejeitar solicitação', saving:'Salvando...', empty:'Não há solicitações acadêmicas atribuídas à sua área.', loadError:'Não foi possível carregar as solicitações.', saveError:'Não foi possível resolver a solicitação.', required:'Informe uma resposta com pelo menos 5 caracteres.', saved:'A resposta foi registrada e o aluno foi notificado.', resolvedBy:'Resolvida por'},
};

export default function SolicitudesAcademicasReview({session, onLogout}) {
  const {language} = useLanguage();
  const copy = translations[language] || translations.es;
  const [solicitudes, setSolicitudes] = useState([]);
  const [respuestas, setRespuestas] = useState({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);

  const cargarSolicitudes = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch('/api/preregistro/solicitudes-academicas/', {headers});
      if (response.status === 401) return onLogout(copy.loadError);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || copy.loadError);
      if (!Array.isArray(data)) throw new Error(copy.loadError);
      setSolicitudes(data);
    } catch (err) {
      setError(err.message || copy.loadError);
    } finally {
      setLoading(false);
    }
  }, [headers, onLogout, copy.loadError]);

  useEffect(() => { cargarSolicitudes(); }, [cargarSolicitudes]);

  async function resolverSolicitud(solicitud, estado) {
    const respuesta_revision = (respuestas[solicitud.id] || '').trim();
    if (respuesta_revision.length < 5) {
      setError(copy.required);
      return;
    }
    setSavingId(solicitud.id);
    setError('');
    setMessage('');
    try {
      const response = await fetch(`/api/preregistro/solicitudes-academicas/${solicitud.id}/`, {
        method: 'PATCH',
        headers: {...headers, 'Content-Type': 'application/json'},
        body: JSON.stringify({estado, respuesta_revision}),
      });
      if (response.status === 401) return onLogout(copy.saveError);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || data.respuesta_revision || data.estado || copy.saveError);
      setSolicitudes(items => items.map(item => item.id === data.id ? data : item));
      setRespuestas(items => ({...items, [solicitud.id]: ''}));
      setMessage(copy.saved);
    } catch (err) {
      setError(err.message || copy.saveError);
    } finally {
      setSavingId(null);
    }
  }

  const formatoFecha = value => value ? new Intl.DateTimeFormat(language, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value)) : '—';
  const pendientes = solicitudes.filter(item => item.estado === 'pendiente').length;

  return <section className="academic-requests-review">
    <header className="academic-requests-review-head">
      <div><p className="panel-kicker">{copy.title}</p><h2>{copy.title}</h2><p>{copy.intro}</p></div>
      <div className="academic-requests-review-actions"><span>{pendientes} {copy.pending.toLowerCase()}</span><button type="button" className="btn-secondary" onClick={cargarSolicitudes} disabled={loading}>{loading ? copy.loading : copy.refresh}</button></div>
    </header>
    {error && <div className="api-error" role="alert">{error}</div>}
    {message && <div className="academic-requests-review-success" role="status">{message}</div>}
    {loading ? <div className="academic-requests-review-empty" role="status">{copy.loading}</div> : error && !solicitudes.length ? <div className="academic-requests-review-empty"><button type="button" className="btn-secondary" onClick={cargarSolicitudes}>{copy.retry}</button></div> : solicitudes.length ? <div className="academic-requests-review-list">
      {solicitudes.map(solicitud => {
        const estado = solicitud.estado;
        const estadoLabel = copy[estado] || solicitud.estado_label || estado;
        return <article className="academic-request-review-card" key={solicitud.id}>
          <div className="academic-request-review-heading">
            <div><span className="academic-request-review-type">{copy.type[solicitud.tipo] || solicitud.tipo_label}</span><h3>{solicitud.aspirante?.nombre || solicitud.aspirante?.usuario || copy.student}</h3><small>{solicitud.aspirante?.usuario && `${copy.student}: ${solicitud.aspirante.usuario} · `}{copy.submitted}: {formatoFecha(solicitud.created_at)}</small></div>
            <span className={`academic-request-review-status is-${estado}`}>{estadoLabel}</span>
          </div>
          <div className="academic-request-review-message"><strong>{copy.request}</strong><p>{solicitud.comentario}</p></div>
          {estado === 'pendiente' ? <div className="academic-request-review-form">
            <label><span>{copy.response}</span><textarea rows="3" maxLength="2000" minLength="5" value={respuestas[solicitud.id] || ''} onChange={event => setRespuestas(items => ({...items, [solicitud.id]: event.target.value}))} placeholder={copy.responsePlaceholder}/><small>{copy.responseHint} · {(respuestas[solicitud.id] || '').length}/2000</small></label>
            <div><button type="button" className="btn-primary" disabled={savingId === solicitud.id} onClick={() => resolverSolicitud(solicitud, 'aceptado')}>{savingId === solicitud.id ? copy.saving : copy.approve}</button><button type="button" className="btn-secondary" disabled={savingId === solicitud.id} onClick={() => resolverSolicitud(solicitud, 'rechazado')}>{copy.reject}</button></div>
          </div> : <div className="academic-request-review-response"><strong>{copy.response}</strong><p>{solicitud.respuesta_revision}</p>{solicitud.resuelta_por_nombre && <small>{copy.resolvedBy}: {solicitud.resuelta_por_nombre}</small>}</div>}
        </article>;
      })}
    </div> : <div className="academic-requests-review-empty">{copy.empty}<button type="button" className="btn-secondary" onClick={cargarSolicitudes}>{copy.retry}</button></div>}
  </section>;
}
