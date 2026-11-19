import React, {useEffect, useState} from 'react';
import {fotoUrl} from './PerfilAspirante';
import {formatoFechaCorta, useCredencialCopy} from './credencialTranslations';
import './CredencialDigital.css';

export default function VerificarCredencial({token, onHome}) {
  const copy = useCredencialCopy();
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const control = new AbortController();
    fetch(`/api/credencial/verificar/${encodeURIComponent(token)}/`, {signal: control.signal})
      .then(respuesta => respuesta.ok ? respuesta.json() : Promise.reject(new Error(copy.error)))
      .then(setDatos)
      .catch(e => { if (e.name !== 'AbortError') setError(e.message); });
    return () => control.abort();
  }, [token, copy.error]);

  const titulo = {vigente: copy.resultValid, no_vigente: copy.resultNotValid, invalida: copy.resultInvalid};
  return <section className="verificacion-credencial" aria-labelledby="verificacion-titulo">
    <h1 id="verificacion-titulo">{copy.verifyTitle}</h1>
    <p>{copy.verifyIntro}</p>
    {!datos && !error && <p role="status">{copy.verifying}</p>}
    {error && <div className="api-error" role="alert">{error}</div>}
    {datos && <article className="verificacion-tarjeta">
      <div className={`verificacion-resultado is-${datos.resultado}`} role="status">
        <strong>{titulo[datos.resultado]}</strong>
        {datos.motivo && <span>{copy.reasons[datos.motivo]}</span>}
      </div>
      {datos.nombre && <div className="verificacion-cuerpo">
        <div className="credencial-foto">
          {datos.foto ? <img src={fotoUrl(datos.foto)} alt={copy.photoAlt(datos.nombre)} /> : <span aria-hidden="true">{datos.nombre.charAt(0)}</span>}
        </div>
        <dl className="credencial-datos">
          <dt>{copy.name}</dt><dd className="credencial-nombre">{datos.nombre}</dd>
          <dt>{copy.studentId}</dt><dd>{datos.matricula || '—'}</dd>
          <dt>{copy.program}</dt><dd>{datos.programa || '—'}{datos.grado ? ` · ${datos.grado}` : ''}</dd>
          <dt>{copy.validUntil}</dt><dd>{formatoFechaCorta(datos.vigencia_hasta, copy.locale)} · {copy.period} {datos.periodo || '—'}</dd>
        </dl>
      </div>}
      <p className="verificacion-pie">{copy.checkedAt} {new Date(datos.verificado_en).toLocaleString(copy.locale)}</p>
    </article>}
    <p><button type="button" className="btn-secondary" onClick={onHome}>{copy.home}</button></p>
  </section>;
}
