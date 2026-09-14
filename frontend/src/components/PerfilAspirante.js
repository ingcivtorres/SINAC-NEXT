import React, {useEffect, useRef, useState} from 'react';

// Usar la misma base de origen permite que funcione tanto en desarrollo
// como detrás del proxy de nginx en Docker.
const API = '';

function fotoUrl(value) {
  if (!value) return '';
  return value.startsWith('http') ? value : `${API}${value}`;
}

export default function PerfilAspirante({perfil, session, onActualizado}) {
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
    if (!archivo.type.startsWith('image/')) return setError('Selecciona una imagen válida.');
    if (archivo.size > 5 * 1024 * 1024) return setError('La foto no debe superar 5 MB.');
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
      const data = await response.json();
      if (!response.ok) throw new Error(data.profile_photo || data.correo || data.detail || 'No se pudo actualizar el perfil.');
      setFoto(null); setMensaje('Perfil actualizado correctamente.');
      onActualizado(data);
    } catch (err) { setError(err.message || 'No se pudo actualizar el perfil.'); }
    finally { setGuardando(false); }
  }

  return <div className="profile-editor panel-card">
    <div className="profile-editor-head"><div className="profile-avatar">{preview ? <img src={preview} alt="Foto de perfil"/> : <span>{(nombre || 'A').charAt(0).toUpperCase()}</span>}</div><div><h3>Mi perfil</h3><p>Actualiza tus datos de contacto y tu foto.</p></div></div>
    <form className="profile-form" onSubmit={guardar}><label>Foto de perfil<input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={seleccionarFoto}/><small>JPG, PNG o WebP · máximo 5 MB</small></label><label>Nombre completo<input value={nombre} onChange={(event) => setNombre(event.target.value)} required/></label><label>Correo electrónico<input type="email" value={correo} onChange={(event) => setCorreo(event.target.value)} required/></label><label>Teléfono<input value={telefono} onChange={(event) => setTelefono(event.target.value)} required/></label>{error && <div className="api-error" role="alert">{error}</div>}{mensaje && <div className="api-success" role="status">{mensaje}</div>}<button type="submit" className="qa-btn" disabled={guardando}>{guardando ? 'Guardando...' : 'Guardar cambios'}</button></form>
  </div>;
}
