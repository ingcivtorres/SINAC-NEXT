import React, {useEffect, useState} from 'react';

export default function ExpedienteCentralizadoCard({expedienteId, session}) {
  const [expediente, setExpediente] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!expedienteId) return undefined;
    const controller = new AbortController();
    setError('');
    fetch(`/api/expedientes/${expedienteId}/centralizado/`, {headers: {Authorization: `Bearer ${session.access}`}, signal: controller.signal})
      .then(response => response.ok ? response.json() : Promise.reject(new Error('No se pudo integrar el expediente centralizado.')))
      .then(setExpediente)
      .catch(err => { if (err.name !== 'AbortError') setError(err.message); });
    return () => controller.abort();
  }, [expedienteId, session.access]);

  if (!expedienteId) return <p className="form-hint">El alumno aún no cuenta con un expediente digital oficial.</p>;
  if (error) return <p className="api-error">{error}</p>;
  if (!expediente) return <p className="form-hint">Integrando expediente digital...</p>;

  return <section className="expediente-centralizado-card"><div className="expediente-centralizado-head"><div><p className="panel-kicker">EXPEDIENTE CENTRALIZADO</p><h4>{expediente.expediente.folio}</h4></div><span>{expediente.expediente.estado}</span></div><div className="expediente-centralizado-metrics"><div><strong>{expediente.documentos.length}</strong><span>Documentos</span></div><div><strong>{expediente.inscripciones.length}</strong><span>Inscripciones</span></div><div><strong>{expediente.firmas.length}</strong><span>Firmas</span></div><div><strong>{expediente.tesis.length}</strong><span>Tesis</span></div></div>{expediente.tesis.length > 0 && <div className="expediente-centralizado-list"><strong>Trayectoria de tesis</strong>{expediente.tesis.map(proyecto => <span key={proyecto.id}>{proyecto.titulo} · {proyecto.estado_label}{proyecto.defensa ? ` · ${proyecto.defensa.estado_label}` : ''}</span>)}</div>}</section>;
}
