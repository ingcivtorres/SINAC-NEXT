import React, {useCallback, useEffect, useState} from 'react';

const ETIQUETAS = {
  pendiente: 'Pre-registro recibido',
  iniciado: 'Proceso iniciado',
  revision: 'En revisión',
  aceptado: 'Aceptado',
};

function fecha(valor) {
  return new Intl.DateTimeFormat('es-MX', {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(valor));
}

export default function SeguimientoSolicitud({session}) {
  const [seguimiento, setSeguimiento] = useState(null);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async (signal) => {
    setError('');
    try {
      const response = await fetch('/api/preregistro/seguimiento/', {headers: {Authorization: `Bearer ${session.access}`}, signal});
      if (!response.ok) throw new Error('No se pudo consultar el seguimiento de tu solicitud.');
      setSeguimiento(await response.json());
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'No se pudo consultar el seguimiento.');
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [session.access]);

  useEffect(() => {
    const controller = new AbortController();
    cargar(controller.signal);
    return () => controller.abort();
  }, [cargar]);

  return <div id="panel-proceso" role="tabpanel" className="panel-grid">
    <div className="panel-card panel-card--wide">
      <div className="seguimiento-head">
        <div>
          <h3>Seguimiento de tu solicitud</h3>
          <p>Consulta los cambios registrados en tu proceso de admisión.</p>
        </div>
        <button type="button" className="qa-btn" onClick={() => cargar(new AbortController().signal)}>Actualizar</button>
      </div>
      {error && <div className="api-error" role="alert">{error}</div>}
      {cargando && !seguimiento ? (
        <p>Cargando seguimiento...</p>
      ) : (
        <div className="seguimiento-timeline">
          {(seguimiento?.eventos || []).length ? (
            (seguimiento.eventos || []).map((evento) => (
              <article className="seguimiento-evento" key={evento.id}>
                <span className={`seguimiento-dot estado-${evento.estado}`}/>
                <div>
                  <div className="seguimiento-evento-head"><strong>{ETIQUETAS[evento.estado] || evento.estado}</strong><time>{fecha(evento.created_at)}</time></div>
                  <p>{evento.detalle}</p>
                  <small>{evento.origen}</small>
                </div>
              </article>
            ))
          ) : (
            <p className="empty-state">Aún no hay movimientos registrados.</p>
          )}
        </div>
      )}
    </div>
    {seguimiento && (
      <div className="panel-card">
        <h3>Enlace LIDA</h3>
        <div className="lida-trace">
          <div className="trace-row"><span className="trace-key">Estado actual</span><span className={`estado-badge estado-${seguimiento.estado_actual}`}>{ETIQUETAS[seguimiento.estado_actual] || seguimiento.estado_actual}</span></div>
          <div className="trace-row"><span className="trace-key">Business Key</span><code className="trace-val">{seguimiento.business_key || '—'}</code></div>
          <div className="trace-row"><span className="trace-key">Instancia Camunda</span><code className="trace-val">{seguimiento.camunda_instance_id || 'Pendiente de asignación'}</code></div>
        </div>
      </div>
    )}
  </div>;
}
