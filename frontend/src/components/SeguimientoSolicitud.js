import React from 'react';
import {useApplicantCopy} from './aspirantPanelTranslations';

function fecha(valor, locale) {
  try { return new Intl.DateTimeFormat(locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(valor)); } catch (e) { return valor; }
}

export default function SeguimientoSolicitud({seguimiento, evaluaciones = [], cargando = false, onActualizar}) {
  const copy = useApplicantCopy();
  const labelEstado = (estado) => copy.stages[estado] || estado;
  const dictamen = evaluaciones[0];
  return <div id="panel-proceso" role="tabpanel" className="panel-grid">
    <div className="panel-card panel-card--wide">
      <div className="seguimiento-head">
        <div>
          <h3>{copy.followup.title}</h3>
          <p>{copy.followup.intro}</p>
        </div>
        <button type="button" className="qa-btn" onClick={onActualizar}>{copy.followup.update}</button>
      </div>
      {cargando && !seguimiento ? (
        <p>{copy.followup.loading}</p>
      ) : (
        <div className="seguimiento-timeline">
          {(seguimiento?.eventos || []).length ? (
            (seguimiento.eventos || []).map((evento) => (
              <article className="seguimiento-evento" key={evento.id}>
                <span className={`seguimiento-dot estado-${evento.estado}`}/>
                <div>
                  <div className="seguimiento-evento-head"><strong>{labelEstado(evento.estado)}</strong><time>{fecha(evento.created_at, copy.locale)}</time></div>
                  <p>{evento.detalle}</p>
                  <small>{evento.origen}</small>
                </div>
              </article>
            ))
          ) : (
            <p className="empty-state">{copy.followup.empty}</p>
          )}
        </div>
      )}
    </div>
    {dictamen && (
      <div className="panel-card colegio-dictamen">
        <h3>{copy.colegio.title}</h3>
        <p><span className={`estado-badge estado-${dictamen.estado}`}>{copy.colegio.states[dictamen.estado] || dictamen.estado_label}</span></p>
        {dictamen.fecha_evaluacion && <p><small>{copy.colegio.date}: {fecha(dictamen.fecha_evaluacion, copy.locale)}</small></p>}
        {dictamen.dictamen && <p>{dictamen.dictamen}</p>}
      </div>
    )}
    {seguimiento && (
      <div className="panel-card">
        <h3>{copy.followup.lida}</h3>
        <div className="lida-trace">
          <div className="trace-row"><span className="trace-key">{copy.followup.currentState}</span><span className={`estado-badge estado-${seguimiento.estado_actual}`}>{labelEstado(seguimiento.estado_actual)}</span></div>
          <div className="trace-row"><span className="trace-key">{copy.followup.businessKey}</span><code className="trace-val">{seguimiento.business_key || '—'}</code></div>
          <div className="trace-row"><span className="trace-key">{copy.followup.instance}</span><code className="trace-val">{seguimiento.camunda_instance_id || copy.followup.pendingAssignment}</code></div>
        </div>
      </div>
    )}
  </div>;
}
