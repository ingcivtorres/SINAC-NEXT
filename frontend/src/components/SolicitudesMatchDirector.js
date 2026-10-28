import React, {useState} from 'react';
import thesisWorkflowTranslations from './tesisWorkflowTranslations';
import {useDirectorCopy} from './directorPanelTranslations';

export default function SolicitudesMatchDirector({solicitudes, session, onUpdated, onMessage, onError}) {
  const copy = useDirectorCopy();
  const text = thesisWorkflowTranslations[copy.locale.split('-')[0]]?.director || thesisWorkflowTranslations.es.director;
  const [savingId, setSavingId] = useState(null);
  const [message, setMessage] = useState('');

  async function responder(solicitud, estado) {
    setSavingId(solicitud.id);
    setMessage('');
    try {
      const response = await fetch(`/api/tesis/solicitudes/${solicitud.id}/`, {
        method: 'PATCH',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({estado}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || text.saveError);
      setMessage(text.saved);
      await onUpdated();
    } catch (error) {
      onError(error.message || text.saveError);
    } finally {
      setSavingId(null);
    }
  }

  return <section className="director-card director-thesis-match-requests">
    <div className="director-card-head"><div><span className="panel-kicker">{copy.menu.avances}</span><h2>{text.title}</h2><p>{text.intro}</p></div><span className="director-count">{solicitudes.length}</span></div>
    {message && <p className="api-success" role="status">{message}</p>}
    {solicitudes.length ? <div className="director-project-list">{solicitudes.map(solicitud => <article key={solicitud.id}>
      <div>
        <strong>{solicitud.alumno?.nombre || text.student}</strong>
        <small>{solicitud.alumno?.matricula || copy.common.noEnrollment} · {solicitud.alumno?.programa || copy.common.noProgram}</small>
        <p><b>{text.line}:</b> {solicitud.linea_investigacion || '—'}</p>
        <p><b>{text.topic}:</b> {solicitud.justificacion || '—'}</p>
      </div>
      <div className="director-project-actions">
        <button type="button" className="btn-primary" disabled={savingId === solicitud.id} onClick={() => responder(solicitud, 'aprobada')}>{text.accept}</button>
        <button type="button" className="btn-secondary" disabled={savingId === solicitud.id} onClick={() => responder(solicitud, 'rechazada')}>{text.reject}</button>
      </div>
    </article>)}</div> : <div className="director-empty"><p>{text.empty}</p></div>}
  </section>;
}
