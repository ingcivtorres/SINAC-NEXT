import React, {useEffect, useState} from 'react';
import {useDirectorCopy} from './directorPanelTranslations';
import './JuradoDefensaPanel.css';

const ROLES = ['presidente', 'secretario', 'vocal', 'suplente'];
const MODALIDADES = ['presencial', 'virtual', 'hibrida'];
const ESTADOS_DEFENSA = ['programada', 'realizada', 'cancelada'];

function aFechaLocal(valor) {
  if (!valor) return '';
  const fecha = new Date(valor);
  if (Number.isNaN(fecha.getTime())) return '';
  return new Date(fecha.getTime() - fecha.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function primerErrorApi(data, fallback) {
  if (!data || typeof data !== 'object') return fallback;
  if (typeof data.detail === 'string') return data.detail;
  const valor = Object.values(data).find(item => typeof item === 'string' || (Array.isArray(item) && typeof item[0] === 'string'));
  return (Array.isArray(valor) ? valor[0] : valor) || fallback;
}

export default function JuradoDefensaPanel({solicitar, proyectos, onUpdated, onMessage, onError}) {
  const copy = useDirectorCopy();
  const t = copy.extra.jury;
  const [candidatos, setCandidatos] = useState([]);
  const [asignacion, setAsignacion] = useState({});
  const [defensaForm, setDefensaForm] = useState({});
  const [resultadoForm, setResultadoForm] = useState({});
  const [guardando, setGuardando] = useState(null);
  const formatDateTime = (value) => value ? new Intl.DateTimeFormat(copy.locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value)) : t.pending;

  useEffect(() => {
    let vigente = true;
    solicitar('/api/jurados-disponibles/')
      .then(({response, data}) => {
        if (!response.ok) throw new Error(primerErrorApi(data, t.loadError));
        if (vigente) setCandidatos(Array.isArray(data) ? data : []);
      })
      .catch(error => { if (vigente && error.message) onError(error.message); });
    return () => { vigente = false; };
  }, [solicitar, onError, t.loadError]);

  const defensaInicial = (proyecto) => proyecto.defensa
    ? {fecha: aFechaLocal(proyecto.defensa.fecha), lugar: proyecto.defensa.lugar || '', modalidad: proyecto.defensa.modalidad || 'presencial', estado: proyecto.defensa.estado || 'programada', observaciones: proyecto.defensa.observaciones || ''}
    : {fecha: '', lugar: '', modalidad: 'presencial', estado: 'programada', observaciones: ''};
  const defensaActual = (proyecto) => defensaForm[proyecto.id] || defensaInicial(proyecto);

  const actualizarAsignacion = (proyectoId, campo, valor) => setAsignacion(actual => ({...actual, [proyectoId]: {...actual[proyectoId], [campo]: valor}}));
  const actualizarDefensa = (proyecto, campo, valor) => setDefensaForm(actual => ({...actual, [proyecto.id]: {...(actual[proyecto.id] || defensaInicial(proyecto)), [campo]: valor}}));

  async function asignarJurado(event, proyecto) {
    event.preventDefault();
    const form = asignacion[proyecto.id] || {};
    if (!form.jurado || !form.rol) return onError(t.selectRequired);
    setGuardando(`jurado-${proyecto.id}`);
    try {
      const {response, data} = await solicitar(`/api/proyectos-tesis/${proyecto.id}/jurado/`, {method: 'POST', body: {jurado: form.jurado, rol: form.rol, orden: Number(form.orden || 1)}});
      if (!response.ok) throw new Error(primerErrorApi(data, t.assignError));
      setAsignacion(actual => ({...actual, [proyecto.id]: {}}));
      onMessage(t.assigned);
      await onUpdated();
    } catch (error) { if (error.message) onError(error.message); } finally { setGuardando(null); }
  }

  async function guardarDefensa(event, proyecto) {
    event.preventDefault();
    const form = defensaActual(proyecto);
    if (!form.fecha) return onError(t.dateRequired);
    setGuardando(`defensa-${proyecto.id}`);
    try {
      const method = proyecto.defensa ? 'PATCH' : 'POST';
      const {response, data} = await solicitar(`/api/proyectos-tesis/${proyecto.id}/defensa/`, {method, body: {fecha: new Date(form.fecha).toISOString(), lugar: form.lugar || '', modalidad: form.modalidad || 'presencial', estado: form.estado || 'programada', observaciones: form.observaciones || ''}});
      if (!response.ok) throw new Error(primerErrorApi(data, t.saveError));
      setDefensaForm(actual => { const siguiente = {...actual}; delete siguiente[proyecto.id]; return siguiente; });
      onMessage(proyecto.defensa ? t.updated : t.scheduled);
      await onUpdated();
    } catch (error) { if (error.message) onError(error.message); } finally { setGuardando(null); }
  }

  const resultadoActual = (proyecto) => resultadoForm[proyecto.id] || {calificacion_final: '', acta_url: proyecto.defensa?.acta_url || '', observaciones: proyecto.defensa?.observaciones || ''};
  const actualizarResultado = (proyecto, campo, valor) => setResultadoForm(actual => ({...actual, [proyecto.id]: {...resultadoActual(proyecto), [campo]: valor}}));

  async function guardarResultado(event, proyecto) {
    event.preventDefault();
    const form = resultadoActual(proyecto);
    const conResultado = proyecto.defensa.calificacion_final !== null && proyecto.defensa.calificacion_final !== undefined;
    const body = {acta_url: form.acta_url || '', observaciones: form.observaciones || ''};
    if (!conResultado) {
      const nota = Number(form.calificacion_final);
      if (form.calificacion_final === '' || Number.isNaN(nota) || nota < 0 || nota > 10) return onError(t.gradeRange);
      body.calificacion_final = nota;
    }
    setGuardando(`resultado-${proyecto.id}`);
    try {
      const {response, data} = await solicitar(`/api/proyectos-tesis/${proyecto.id}/defensa/`, {method: 'PATCH', body});
      if (!response.ok) throw new Error(primerErrorApi(data, t.saveError));
      setResultadoForm(actual => { const siguiente = {...actual}; delete siguiente[proyecto.id]; return siguiente; });
      onMessage(conResultado ? t.actaSaved : t.resultSaved);
      await onUpdated();
    } catch (error) { if (error.message) onError(error.message); } finally { setGuardando(null); }
  }

  return <div className="director-card">
    <div className="director-card-head"><div><span className="panel-kicker">{t.kicker}</span><h2>{t.title}</h2><p>{t.description}</p></div><span className="director-count">{proyectos.length} {t.count}</span></div>
    {proyectos.length ? <div className="director-project-list">{proyectos.map(proyecto => {
      const defensa = defensaActual(proyecto);
      const resultado = resultadoActual(proyecto);
      const asignados = new Set((proyecto.jurados || []).map(jurado => jurado.jurado));
      const conResultado = proyecto.defensa && proyecto.defensa.calificacion_final !== null && proyecto.defensa.calificacion_final !== undefined;
      const puedeCalificar = proyecto.defensa && !conResultado && proyecto.defensa.estado !== 'cancelada' && new Date(proyecto.defensa.fecha) <= new Date();
      return <article key={proyecto.id}>
        <div>
          <strong>{proyecto.titulo}</strong>
          <small>{proyecto.alumno_nombre} · {proyecto.estado_label}</small>
          <p>{proyecto.jurados?.length ? proyecto.jurados.map(jurado => `${t.roles[jurado.rol] || jurado.rol_label || jurado.rol}: ${jurado.jurado_nombre}`).join(' · ') : t.none}</p>
          {proyecto.defensa && <span className="director-project-meta">{t.defense}: {formatDateTime(proyecto.defensa.fecha)} · {proyecto.defensa.lugar || t.placePending} · {t.statuses[proyecto.defensa.estado] || proyecto.defensa.estado_label || proyecto.defensa.estado}</span>}
          {conResultado && <span className="director-project-meta">{t.finalGrade}: {proyecto.defensa.calificacion_final} · {t.resultRecorded}</span>}
        </div>
        <div className="jury-management-forms">
          <form className="jury-inline-form" onSubmit={event => asignarJurado(event, proyecto)}>
            <select aria-label={t.member} value={asignacion[proyecto.id]?.jurado || ''} onChange={event => actualizarAsignacion(proyecto.id, 'jurado', event.target.value)}>
              <option value="">{t.member}</option>
              {candidatos.filter(persona => !asignados.has(persona.id) && persona.id !== proyecto.alumno).map(persona => <option key={persona.id} value={persona.id}>{persona.nombre}{persona.rol ? ` · ${t.memberRoles[persona.rol] || persona.rol}` : ''}</option>)}
            </select>
            <select aria-label={t.role} value={asignacion[proyecto.id]?.rol || ''} onChange={event => actualizarAsignacion(proyecto.id, 'rol', event.target.value)}>
              <option value="">{t.role}</option>
              {ROLES.map(value => <option key={value} value={value}>{t.roles[value]}</option>)}
            </select>
            <button type="submit" className="btn-secondary" disabled={guardando === `jurado-${proyecto.id}`}>{guardando === `jurado-${proyecto.id}` ? t.saving : t.assign}</button>
          </form>
          {!conResultado && <form className="jury-inline-form" onSubmit={event => guardarDefensa(event, proyecto)}>
            <input aria-label={t.date} type="datetime-local" value={defensa.fecha || ''} onChange={event => actualizarDefensa(proyecto, 'fecha', event.target.value)} />
            <input aria-label={t.place} placeholder={t.place} value={defensa.lugar || ''} onChange={event => actualizarDefensa(proyecto, 'lugar', event.target.value)} />
            <select aria-label={t.modality} value={defensa.modalidad || 'presencial'} onChange={event => actualizarDefensa(proyecto, 'modalidad', event.target.value)}>
              {MODALIDADES.map(value => <option key={value} value={value}>{t.modalities[value]}</option>)}
            </select>
            {proyecto.defensa && <select aria-label={t.defenseStatus} value={defensa.estado || 'programada'} onChange={event => actualizarDefensa(proyecto, 'estado', event.target.value)}>
              {ESTADOS_DEFENSA.map(value => <option key={value} value={value}>{t.statuses[value]}</option>)}
            </select>}
            <button type="submit" className="btn-primary" disabled={guardando === `defensa-${proyecto.id}`}>{guardando === `defensa-${proyecto.id}` ? t.saving : proyecto.defensa ? t.update : t.schedule}</button>
          </form>}
          {(puedeCalificar || conResultado) && <form className="jury-inline-form" onSubmit={event => guardarResultado(event, proyecto)}>
            {puedeCalificar && <input aria-label={t.finalGrade} placeholder={t.finalGrade} type="number" min="0" max="10" step="0.1" required value={resultado.calificacion_final} onChange={event => actualizarResultado(proyecto, 'calificacion_final', event.target.value)} />}
            <input aria-label={t.actaUrl} placeholder={t.actaUrl} type="url" value={resultado.acta_url} onChange={event => actualizarResultado(proyecto, 'acta_url', event.target.value)} />
            <input aria-label={t.observations} placeholder={t.observations} value={resultado.observaciones} onChange={event => actualizarResultado(proyecto, 'observaciones', event.target.value)} />
            <button type="submit" className="btn-primary" disabled={guardando === `resultado-${proyecto.id}`}>{guardando === `resultado-${proyecto.id}` ? t.saving : conResultado ? t.saveActa : t.recordResult}</button>
          </form>}
        </div>
      </article>;
    })}</div> : <div className="director-empty"><h3>{t.emptyTitle}</h3><p>{t.emptyText}</p></div>}
  </div>;
}
