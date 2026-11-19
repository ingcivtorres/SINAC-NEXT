import React, {useCallback, useEffect, useRef, useState} from 'react';
import {fotoUrl} from './PerfilAspirante';
import {formatoFechaCorta, useCredencialCopy} from './credencialTranslations';
import cinvestavLogo from '../assets/logociv.png';
import './CredencialDigital.css';

function iniciales(nombre) {
  return String(nombre || '?').split(/\s+/).slice(0, 2).map(parte => parte.charAt(0)).join('').toUpperCase();
}

export default function CredencialDigital({session, onLogout, onIrPerfil}) {
  const copy = useCredencialCopy();
  const [credencial, setCredencial] = useState(null);
  const [error, setError] = useState('');
  const [restante, setRestante] = useState(0);
  const [descargando, setDescargando] = useState(false);
  const onLogoutRef = useRef(onLogout);
  onLogoutRef.current = onLogout;

  const cargar = useCallback(async () => {
    try {
      const respuesta = await fetch('/api/alumno/credencial/', {headers: {Authorization: `Bearer ${session.access}`}});
      if (respuesta.status === 401) return onLogoutRef.current(copy.expired);
      if (!respuesta.ok) throw new Error(copy.error);
      const datos = await respuesta.json();
      setCredencial(datos);
      setRestante(datos.renovar_en || 60);
      setError('');
    } catch (e) {
      setError(e.message || copy.error);
    }
  }, [session.access, copy]);

  useEffect(() => { cargar(); }, [cargar]);

  useEffect(() => {
    if (!credencial) return undefined;
    const intervalo = window.setInterval(() => setRestante(actual => Math.max(actual - 1, 0)), 1000);
    return () => window.clearInterval(intervalo);
  }, [credencial]);

  useEffect(() => {
    if (!credencial || restante > 0) return undefined;
    if (document.visibilityState === 'visible') {
      cargar();
      return undefined;
    }
    const alVolver = () => { if (document.visibilityState === 'visible') cargar(); };
    document.addEventListener('visibilitychange', alVolver);
    return () => document.removeEventListener('visibilitychange', alVolver);
  }, [credencial, restante, cargar]);

  async function descargarPdf() {
    setDescargando(true);
    setError('');
    try {
      const respuesta = await fetch('/api/alumno/credencial/pdf/', {headers: {Authorization: `Bearer ${session.access}`}});
      if (respuesta.status === 401) return onLogout(copy.expired);
      if (!respuesta.ok) {
        const datos = await respuesta.json().catch(() => ({}));
        throw new Error(datos.detail || copy.downloadError);
      }
      const url = URL.createObjectURL(await respuesta.blob());
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `credencial-${credencial.matricula || 'sinac'}.pdf`;
      enlace.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e.message || copy.downloadError);
    } finally {
      setDescargando(false);
    }
  }

  if (!credencial) {
    return <div className="panel-card">{error ? <div className="api-error" role="alert">{error}</div> : <p role="status">{copy.loading}</p>}</div>;
  }

  const vigencia = formatoFechaCorta(credencial.vigencia_hasta, copy.locale);
  return <div className="panel-card credencial-panel">
    <div className="alumno-section-title">
      <div><p className="panel-kicker">{copy.kicker}</p><h3>{copy.title}</h3></div>
      <span className={`credencial-estado ${credencial.vigente ? 'is-vigente' : 'is-no-vigente'}`}>{credencial.vigente ? copy.valid : copy.notValid}</span>
    </div>
    {!credencial.vigente && credencial.motivo && <p className="credencial-aviso" role="status">{copy.reasons[credencial.motivo]}</p>}
    {!credencial.foto && <p className="credencial-aviso">{copy.noPhoto} <button type="button" className="link-btn" onClick={onIrPerfil}>{copy.goProfile}</button></p>}
    {error && <div className="api-error" role="alert">{error}</div>}

    <div className="credencial-caras">
      <article className="credencial-tarjeta credencial-frente" aria-label={copy.front}>
        <header className="credencial-banda">
          <strong>{copy.cardTitle}</strong>
          <span>Cinvestav · SINAC NEXT</span>
        </header>
        <div className="credencial-cuerpo">
          <div className="credencial-foto">
            {credencial.foto
              ? <img src={fotoUrl(credencial.foto)} alt={copy.photoAlt(credencial.nombre)} />
              : <span aria-hidden="true">{iniciales(credencial.nombre)}</span>}
          </div>
          <dl className="credencial-datos">
            <dt className="a11y-sr-only">{copy.name}</dt>
            <dd className="credencial-nombre">{credencial.nombre}</dd>
            <dt>{copy.studentId}</dt><dd>{credencial.matricula || '—'}</dd>
            <dt>{copy.program}</dt><dd>{credencial.programa || '—'}</dd>
            {credencial.grado && <><dt>{copy.degree}</dt><dd>{credencial.grado}</dd></>}
            <dt>{copy.unit}</dt><dd>{credencial.unidad || '—'}</dd>
          </dl>
        </div>
        <footer className="credencial-pie">
          <strong>{copy.validUntil} {vigencia}</strong>
          <span>{copy.period} {credencial.periodo || '—'}</span>
        </footer>
      </article>

      <article className="credencial-tarjeta credencial-reverso" aria-label={copy.back}>
        <div className="credencial-reverso-cuerpo">
          <div className="credencial-reverso-texto">
            <img className="credencial-logo" src={cinvestavLogo} alt="Cinvestav" />
            <p>{copy.scan}</p>
            <small>{copy.folio}: <b>{credencial.folio}</b></small>
          </div>
          <img className="credencial-qr" src={credencial.qr} alt={copy.qrAlt} />
        </div>
        <footer className="credencial-pie credencial-pie--verde">
          <span aria-hidden="true">{copy.renew(restante)}</span>
        </footer>
      </article>
    </div>

    <div className="credencial-acciones">
      <button type="button" className="btn-primary" onClick={descargarPdf} disabled={!credencial.vigente || descargando}>{copy.download}</button>
      <a className="btn-secondary" href={credencial.url_verificacion} target="_blank" rel="noopener noreferrer">{copy.openVerify}</a>
    </div>
  </div>;
}
