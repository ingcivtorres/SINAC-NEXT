import React, {useEffect, useRef, useState} from 'react';
import {useApplicantCopy} from './aspirantPanelTranslations';

// Usar la misma base de origen permite que funcione tanto en desarrollo
// como detrás del proxy de nginx en Docker.
const API = '';

export function fotoUrl(value) {
  if (!value) return '';
  if (value.startsWith('http')) return value;
  const path = String(value).replace(/^\/+/, '');
  return path.startsWith('media/') ? `/${path}` : `/media/${path}`;
}

export default function PerfilAspirante({perfil, session, onActualizado}) {
  const copy = useApplicantCopy();
  const text = copy.profile;
  const [nombre, setNombre] = useState(perfil.nombre || '');
  const [correo, setCorreo] = useState(perfil.correo || '');
  const [telefono, setTelefono] = useState(perfil.telefono || '');
  const [foto, setFoto] = useState(null);
  const [preview, setPreview] = useState(fotoUrl(perfil.profile_photo));
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    setNombre(perfil.nombre || '');
    setCorreo(perfil.correo || '');
    setTelefono(perfil.telefono || '');
    setPreview(fotoUrl(perfil.profile_photo));
  }, [perfil.nombre, perfil.correo, perfil.telefono, perfil.profile_photo]);

  function seleccionarFoto(event) {
    const archivo = event.target.files?.[0];
    if (!archivo) return;
    if (!archivo.type.startsWith('image/')) return setError(text.selectImage);
    if (archivo.size > 5 * 1024 * 1024) return setError(text.maxPhoto);
    setError('');
    setFoto(archivo);
    setPreview(URL.createObjectURL(archivo));
  }

  async function guardar(event) {
    event.preventDefault();
    setGuardando(true); setError(''); setMensaje('');
    const form = new FormData();
    form.append('nombre', nombre);
    form.append('correo', correo);
    form.append('telefono', telefono);
    if (foto) form.append('profile_photo', foto);
    try {
      const response = await fetch(`${API}/api/preregistro/perfil/`, {method: 'PATCH', headers: {Authorization: `Bearer ${session.access}`}, body: form});
      const contentType = response.headers.get('content-type') || '';
      const data = contentType.includes('application/json') ? await response.json().catch(() => ({})) : {};
      if (!response.ok) throw new Error(`${text.saveError} (HTTP ${response.status}).`);
      if (!contentType.includes('application/json')) throw new Error(text.unexpected);
      if (fileRef.current) fileRef.current.value = '';
      setFoto(null); setMensaje(text.saved);
      onActualizado(data);
    } catch (err) { setError(err.message || text.saveError); }
    finally { setGuardando(false); }
  }

  return <div className="profile-editor panel-card">
    <div className="profile-editor-head"><div className="profile-avatar">{preview ? <img src={preview} alt={text.photo} onError={() => setPreview('')}/> : <span>{(nombre || 'A').charAt(0).toUpperCase()}</span>}</div><div><h3>{text.name}</h3><p>{text.update}</p></div></div>
    <form className="profile-form" onSubmit={guardar}><label>{text.photo}<input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={seleccionarFoto}/><small>{text.fileHelp}</small></label><label>{text.name}<input value={nombre} onChange={(event) => setNombre(event.target.value)} required/></label><label>{text.email}<input type="email" value={correo} onChange={(event) => setCorreo(event.target.value)} required/></label><label>{text.phone}<input value={telefono} onChange={(event) => setTelefono(event.target.value)} required/></label>{error && <div className="api-error" role="alert">{error}</div>}{mensaje && <div className="api-success" role="status">{mensaje}</div>}<button type="submit" className="qa-btn" disabled={guardando}>{guardando ? text.saving : text.save}</button></form>
  </div>;
}
