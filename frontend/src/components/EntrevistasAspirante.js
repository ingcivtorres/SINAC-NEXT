import React from 'react';
import {useApplicantCopy} from './aspirantPanelTranslations';

function fecha(valor, locale, fallback) {
  if (!valor) return fallback;
  try { return new Intl.DateTimeFormat(locale, {dateStyle: 'full', timeStyle: 'short'}).format(new Date(valor)); } catch (e) { return valor; }
}

const enlaceSeguro = url => /^https:\/\//i.test(url || '');

export default function EntrevistasAspirante({entrevistas, error}) {
  const copy = useApplicantCopy();
  const t = copy.interviews;
  return <div className="panel-card panel-card--wide">
    <h3>{t.title}</h3>
    <p>{t.intro}</p>
    {error && <div className="api-error" role="alert">{error}</div>}
    {!error && !entrevistas.length && <p className="empty-state">{t.empty}</p>}
    {entrevistas.length > 0 && <div className="request-list">
      {entrevistas.map(entrevista => {
        const enCurso = entrevista.estado === 'iniciada';
        return <article key={entrevista.id}>
          <strong>{entrevista.titulo || t.title}</strong>
          <p>{t.purposes[entrevista.proposito] || entrevista.proposito_label}</p>
          <p>{t.date}: {fecha(entrevista.fecha_programada, copy.locale, t.pending)} · {t.duration}: {entrevista.duracion_minutos} {t.minutes}</p>
          {entrevista.descripcion && <p>{entrevista.descripcion}</p>}
          <span className={`estado-badge estado-${entrevista.estado}`}>{t.states[entrevista.estado] || entrevista.estado_label}</span>
          {enCurso && enlaceSeguro(entrevista.jitsi_room_link) && <p><a className="qa-btn" href={entrevista.jitsi_room_link} target="_blank" rel="noopener noreferrer">{t.join}</a></p>}
          {entrevista.estado === 'programada' && <p><small>{t.waiting}</small></p>}
          {entrevista.retroalimentacion && <p><strong>{t.feedback}:</strong> {entrevista.retroalimentacion}</p>}
          {entrevista.estado === 'completada' && enlaceSeguro(entrevista.recording_link) && <p><a href={entrevista.recording_link} target="_blank" rel="noopener noreferrer">{t.recording}</a></p>}
        </article>;
      })}
    </div>}
  </div>;
}
