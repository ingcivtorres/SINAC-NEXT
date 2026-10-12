import React, {useEffect, useState} from 'react';
import {fotoUrl} from './PerfilAspirante';

const ROLES = {director: 'Director de tesis', coordinacion: 'Coordinación académica', servicios: 'Servicios Escolares'};
const fechaHora = (value) => value ? new Intl.DateTimeFormat('es-MX', {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value)) : '—';

export default function ExpedienteCentralizadoCard({expedienteId, session}) {
  const [expediente, setExpediente] = useState(null);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');

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

  async function abrir(ruta, {descargar = false, nombre = 'expediente.pdf'} = {}) {
    setAviso('');
    try {
      const response = await fetch(ruta, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error('No se pudo abrir el archivo.');
      const url = URL.createObjectURL(new Blob([await response.blob()], {type: 'application/pdf'}));
      if (descargar) {
        const a = document.createElement('a');
        a.href = url; a.download = nombre; a.click();
      } else {
        window.open(url, '_blank', 'noopener');
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) { setAviso(err.message); }
  }

  if (!expedienteId) return <p className="form-hint">El alumno aún no cuenta con un expediente digital oficial.</p>;
  if (error) return <p className="api-error">{error}</p>;
  if (!expediente) return <p className="form-hint">Integrando expediente digital...</p>;

  const {alumno, firmas, documentos} = expediente;
  const foto = fotoUrl(alumno.profile_photo);
  return <section className="expediente-centralizado-card">
    <div className="expediente-centralizado-head">
      <div><p className="panel-kicker">EXPEDIENTE CENTRALIZADO</p><h4>{expediente.expediente.folio}</h4></div>
      <span>{expediente.expediente.estado}</span>
    </div>
    <div className="exp-alumno">
      {foto ? <img src={foto} alt={alumno.nombre} className="exp-foto"/> : <div className="exp-foto exp-foto-vacia">{(alumno.nombre || '?').charAt(0)}</div>}
      <div className="exp-alumno-datos"><strong>{alumno.nombre}</strong><small>{alumno.matricula || '—'} · {alumno.correo}</small><small>{alumno.programa || '—'}{alumno.unidad ? ` · ${alumno.unidad}` : ''}</small></div>
      <div className="exp-acciones">
        <button type="button" className="btn-primary" onClick={() => abrir(`/api/expedientes/${expedienteId}/pdf/?inline=1`)}>Ver PDF</button>
        <button type="button" className="btn-secondary" onClick={() => abrir(`/api/expedientes/${expedienteId}/pdf/`, {descargar: true, nombre: `${expediente.expediente.folio}.pdf`})}>Descargar PDF</button>
      </div>
    </div>
    {aviso && <p className="api-error">{aviso}</p>}
    <div className="expediente-centralizado-metrics"><div><strong>{documentos.length}</strong><span>Documentos</span></div><div><strong>{expediente.inscripciones.length}</strong><span>Inscripciones</span></div><div><strong>{firmas.length}</strong><span>Firmas</span></div><div><strong>{expediente.tesis.length}</strong><span>Tesis</span></div></div>

    <div className="expediente-centralizado-list"><strong>Firmas electrónicas</strong>
      {firmas.length ? firmas.map(firma => <div key={firma.id} className="exp-sello"><span className="exp-sello-check">✔</span><div><b>{firma.firmante_nombre}</b><small>{ROLES[firma.rol_firmante] || firma.rol_firmante} · {fechaHora(firma.firmado_at)}</small><code>Huella: {firma.huella}</code></div></div>) : <span>Sin firmas todavía.</span>}
    </div>

    <div className="expediente-centralizado-list"><strong>Documentos</strong>
      {documentos.length ? documentos.map(d => <div key={d.id} className="exp-doc"><span>{d.tipo_label}<small>{d.nombre_original}</small></span><button type="button" className="btn-secondary" onClick={() => abrir(`${d.archivo}?inline=1`)}>Ver</button></div>) : <span>Sin documentos cargados.</span>}
    </div>

    {expediente.tesis.length > 0 && <div className="expediente-centralizado-list"><strong>Trayectoria de tesis</strong>{expediente.tesis.map(proyecto => <span key={proyecto.id}>{proyecto.titulo} · {proyecto.estado_label}{proyecto.defensa ? ` · ${proyecto.defensa.estado_label}` : ''}</span>)}</div>}
  </section>;
}
