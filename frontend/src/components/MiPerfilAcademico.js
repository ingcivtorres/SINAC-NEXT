import React, {useEffect, useMemo, useState} from 'react';
import {useLanguage} from '../translations';
import {PerfilForm, PERFIL_COPY} from './DocentesDirectorioPanel';

export default function MiPerfilAcademico({session, docenteId, onLogout}) {
  const {language} = useLanguage();
  const t = PERFIL_COPY[language] || PERFIL_COPY.es;
  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`, 'Content-Type': 'application/json'}), [session.access]);
  const [perfil, setPerfil] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!docenteId) return undefined;
    const controller = new AbortController();
    fetch(`/api/servicios-escolares/docentes/${docenteId}/`, {headers, signal: controller.signal})
      .then(async response => {
        if (response.status === 401) { onLogout && onLogout(t.expired); return; }
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || t.error);
        setPerfil(body);
      })
      .catch(err => { if (err.name !== 'AbortError') setError(err.message || t.error); });
    return () => controller.abort();
  }, [docenteId, headers, onLogout, t]);

  async function guardar(cambios) {
    try {
      const response = await fetch(`/api/servicios-escolares/docentes/${docenteId}/`, {method: 'PATCH', headers, body: JSON.stringify(cambios)});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || t.saveError);
      setPerfil(body);
      setMessage(t.saved);
      setError('');
    } catch (err) { setError(err.message || t.saveError); setMessage(''); }
  }

  if (!docenteId) return null;
  return (
    <div className="panel-card" style={{marginTop: 16}}>
      <div className="servicios-card-heading"><div><span className="panel-kicker">{t.academic.toUpperCase()}</span></div></div>
      {message && <div className="api-success">{message}</div>}
      {error && <div className="api-error" role="alert">{error}</div>}
      {perfil ? <PerfilForm d={perfil} t={t} onSave={guardar}/> : !error && <p>{t.loading}</p>}
    </div>
  );
}
