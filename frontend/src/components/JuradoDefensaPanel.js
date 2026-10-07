import React, {useEffect, useState} from 'react';
import './JuradoDefensaPanel.css';

const ROLES = [['presidente', 'Presidente'], ['secretario', 'Secretario'], ['vocal', 'Vocal'], ['suplente', 'Suplente']];
const MODALIDADES = [['presencial', 'Presencial'], ['virtual', 'Virtual'], ['hibrida', 'Hibrida']];
const formatDateTime = (value) => value ? new Date(value).toLocaleString('es-MX', {dateStyle: 'medium', timeStyle: 'short'}) : 'Pendiente';

export default function JuradoDefensaPanel({session, proyectos, onUpdated, onMessage, onError}) {
  const [docentes, setDocentes] = useState([]);
  const [asignacion, setAsignacion] = useState({});
  const [defensaForm, setDefensaForm] = useState({});
  const [guardando, setGuardando] = useState(null);

  useEffect(() => {
    fetch('/api/jurados-disponibles/', {headers: {Authorization: `Bearer ${session.access}`}})
      .then(response => response.ok ? response.json() : Promise.reject(new Error('No se pudo cargar el catalogo de docentes.')))
      .then(setDocentes)
      .catch(error => onError(error.message));
  }, [session.access, onError]);

  const actualizarAsignacion = (proyectoId, campo, valor) => setAsignacion(actual => ({...actual, [proyectoId]: {...actual[proyectoId], [campo]: valor}}));
  const actualizarDefensa = (proyectoId, campo, valor) => setDefensaForm(actual => ({...actual, [proyectoId]: {...actual[proyectoId], [campo]: valor}}));

  async function asignarJurado(event, proyecto) {
    event.preventDefault();
    const form = asignacion[proyecto.id] || {};
    if (!form.jurado || !form.rol) return onError('Selecciona un docente y un rol para el jurado.');
    setGuardando(`jurado-${proyecto.id}`);
    try {
      const response = await fetch(`/api/proyectos-tesis/${proyecto.id}/jurado/`, {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({jurado: form.jurado, rol: form.rol, orden: Number(form.orden || 1)})});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || body.rol?.[0] || body.jurado?.[0] || 'No se pudo asignar el jurado.');
      onMessage('Jurado asignado correctamente.');
      onUpdated();
    } catch (error) { onError(error.message); } finally { setGuardando(null); }
  }

  async function guardarDefensa(event, proyecto) {
    event.preventDefault();
    const form = defensaForm[proyecto.id] || {};
    if (!form.fecha) return onError('Indica la fecha y hora de la defensa.');
    setGuardando(`defensa-${proyecto.id}`);
    try {
      const method = proyecto.defensa ? 'PATCH' : 'POST';
      const response = await fetch(`/api/proyectos-tesis/${proyecto.id}/defensa/`, {method, headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({fecha: new Date(form.fecha).toISOString(), lugar: form.lugar || '', modalidad: form.modalidad || 'presencial', estado: form.estado || 'programada', observaciones: form.observaciones || ''})});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || body.fecha?.[0] || 'No se pudo guardar la defensa.');
      onMessage(proyecto.defensa ? 'Defensa actualizada correctamente.' : 'Defensa programada correctamente.');
      onUpdated();
    } catch (error) { onError(error.message); } finally { setGuardando(null); }
  }

  return <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">TRIBUNAL Y DEFENSA</span><h2>Gestion de jurado</h2><p>Asigna integrantes y programa la defensa de cada proyecto aprobado.</p></div><span className="director-count">{proyectos.length} proyectos</span></div>{proyectos.length ? <div className="director-project-list">{proyectos.map(proyecto => { const currentDefense = defensaForm[proyecto.id] || (proyecto.defensa ? {fecha: proyecto.defensa.fecha ? proyecto.defensa.fecha.slice(0, 16) : '', lugar: proyecto.defensa.lugar || '', modalidad: proyecto.defensa.modalidad || 'presencial', estado: proyecto.defensa.estado || 'programada', observaciones: proyecto.defensa.observaciones || ''} : {modalidad: 'presencial', estado: 'programada'}); return <article key={proyecto.id}><div><strong>{proyecto.titulo}</strong><small>{proyecto.alumno_nombre} · {proyecto.estado_label}</small><p>{proyecto.jurados?.length ? proyecto.jurados.map(jurado => `${jurado.rol_label || jurado.rol}: ${jurado.jurado_nombre}`).join(' · ') : 'Sin jurado asignado.'}</p>{proyecto.defensa && <span className="director-project-meta">Defensa: {formatDateTime(proyecto.defensa.fecha)} · {proyecto.defensa.lugar || 'Lugar pendiente'} · {proyecto.defensa.estado_label || proyecto.defensa.estado}</span>}</div><div className="jury-management-forms"><form className="jury-inline-form" onSubmit={event => asignarJurado(event, proyecto)}><select aria-label="Docente jurado" value={asignacion[proyecto.id]?.jurado || ''} onChange={event => actualizarAsignacion(proyecto.id, 'jurado', event.target.value)}><option value="">Docente jurado</option>{docentes.map(docente => <option key={docente.id} value={docente.id}>{docente.nombre}</option>)}</select><select aria-label="Rol del jurado" value={asignacion[proyecto.id]?.rol || ''} onChange={event => actualizarAsignacion(proyecto.id, 'rol', event.target.value)}><option value="">Rol</option>{ROLES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button type="submit" className="btn-secondary" disabled={guardando === `jurado-${proyecto.id}`}>{guardando === `jurado-${proyecto.id}` ? 'Guardando...' : 'Asignar jurado'}</button></form><form className="jury-inline-form" onSubmit={event => guardarDefensa(event, proyecto)}><input aria-label="Fecha de defensa" type="datetime-local" value={currentDefense.fecha || ''} onChange={event => actualizarDefensa(proyecto.id, 'fecha', event.target.value)} /><input aria-label="Lugar de defensa" placeholder="Lugar o enlace" value={currentDefense.lugar || ''} onChange={event => actualizarDefensa(proyecto.id, 'lugar', event.target.value)} /><select aria-label="Modalidad de defensa" value={currentDefense.modalidad || 'presencial'} onChange={event => actualizarDefensa(proyecto.id, 'modalidad', event.target.value)}>{MODALIDADES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button type="submit" className="btn-primary" disabled={guardando === `defensa-${proyecto.id}`}>{guardando === `defensa-${proyecto.id}` ? 'Guardando...' : proyecto.defensa ? 'Actualizar defensa' : 'Programar defensa'}</button></form></div></article>; })}</div> : <div className="director-empty"><h3>No hay proyectos de tesis</h3><p>Los proyectos apareceran cuando un tesista los envie a revision.</p></div>}</div>;
}
