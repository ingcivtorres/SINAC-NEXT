import React, {useCallback, useEffect, useRef, useState} from 'react';

const REQUISITOS = [
  {tipo: 'cv', titulo: 'Currículum vitae', descripcion: 'PDF con formación, experiencia y publicaciones.'},
  {tipo: 'titulo', titulo: 'Título o comprobante de estudios', descripcion: 'Título, cédula o constancia académica.'},
  {tipo: 'carta_motivacion', titulo: 'Carta de motivos', descripcion: 'Explica tu interés por el programa.'},
  {tipo: 'carta_recomendacion', titulo: 'Carta de recomendación', descripcion: 'Carta firmada por una referencia académica o profesional.'},
];

function tamano(bytes) {
  return bytes ? `${(bytes / (1024 * 1024)).toFixed(2)} MB` : '';
}

export default function DocumentosAspirante({session}) {
  const [documentos, setDocumentos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [subiendo, setSubiendo] = useState('');
  const inputRefs = useRef({});

  const cargarDocumentos = useCallback(async (signal) => {
    try {
      const response = await fetch('/api/preregistro/documentos/', {headers: {Authorization: `Bearer ${session.access}`}, signal});
      const contentType = response.headers.get('content-type') || '';
      let data = null;
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        const texto = await response.text();
        if (texto) {
          throw new Error(`El servidor devolvió una respuesta inesperada (${response.status}).`);
        }
      }
      if (!response.ok) throw new Error(data?.detail || 'No se pudieron cargar tus documentos.');
      if (!Array.isArray(data)) throw new Error('La respuesta del servidor no fue válida.');
      setDocumentos(data);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'No se pudieron cargar tus documentos.');
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [session.access]);

  useEffect(() => {
    const controller = new AbortController();
    cargarDocumentos(controller.signal);
    return () => controller.abort();
  }, [cargarDocumentos]);

  async function subirArchivo(tipo, archivo) {
    if (!archivo) return;
    if (archivo.type !== 'application/pdf' && !archivo.name.toLowerCase().endsWith('.pdf')) {
      setError('Solo puedes cargar archivos PDF.');
      return;
    }
    if (archivo.size > 10 * 1024 * 1024) {
      setError('Cada archivo debe pesar como máximo 10 MB.');
      return;
    }
    setSubiendo(tipo);
    setError('');
    const form = new FormData();
    form.append('tipo', tipo);
    form.append('archivo', archivo);
    try {
      const response = await fetch('/api/preregistro/documentos/', {method: 'POST', headers: {Authorization: `Bearer ${session.access}`}, body: form});
      const contentType = response.headers.get('content-type') || '';
      let data = null;
      let texto = '';
      if (contentType.includes('application/json')) {
        data = await response.json();
      } else {
        texto = await response.text();
      }
      if (!response.ok) {
        const mensaje = data?.archivo || data?.tipo || data?.detail || texto || 'No se pudo guardar el documento.';
        throw new Error(`No se pudo guardar el documento${response.status ? ` (${response.status})` : ''}. ${mensaje}`);
      }
      if (!data) throw new Error('El servidor devolvió una respuesta inesperada. Intenta nuevamente.');
      setDocumentos((actual) => [...actual.filter((documento) => documento.tipo !== tipo), data]);
    } catch (err) {
      setError(err.message || 'No se pudo guardar el documento.');
    } finally {
      setSubiendo('');
      if (inputRefs.current[tipo]) inputRefs.current[tipo].value = '';
    }
  }

  async function eliminar(documento) {
    if (!window.confirm(`¿Eliminar ${documento.nombre_original}?`)) return;
    setError('');
    try {
      const response = await fetch(`/api/preregistro/documentos/${documento.id}/`, {method: 'DELETE', headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error('No se pudo eliminar el documento.');
      setDocumentos((actual) => actual.filter((item) => item.id !== documento.id));
    } catch (err) {
      setError(err.message || 'No se pudo eliminar el documento.');
    }
  }

  async function descargar(documento) {
    setError('');
    try {
      const response = await fetch(`${documento.archivo}`, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error('No se pudo descargar el documento.');
      const url = URL.createObjectURL(await response.blob());
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = documento.nombre_original;
      enlace.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err.message || 'No se pudo descargar el documento.');
    }
  }

  return <div id="panel-documentos" role="tabpanel" className="documentos-panel">
    <div className="panel-card panel-card--wide"><h3>Documentos requeridos</h3><p className="documentos-intro">Carga archivos PDF de hasta 10 MB. Cada carga queda registrada y se notifica al flujo LIDA.</p>{error && <div className="api-error" role="alert">{error}</div>}{cargando ? <p>Cargando documentos...</p> : <div className="documentos-grid">{REQUISITOS.map((requisito) => {
      const documento = documentos.find((item) => item.tipo === requisito.tipo);
      const ocupado = subiendo === requisito.tipo;
      return <article className="documento-card" key={requisito.tipo}><div><h4>{requisito.titulo}</h4><p>{requisito.descripcion}</p></div>{documento ? <div className="documento-cargado"><span className="documento-ok">Cargado</span><button type="button" className="documento-link" onClick={() => descargar(documento)}>{documento.nombre_original}</button><small>{tamano(documento.tamano)} · {documento.lida_notificado ? 'Notificado a LIDA' : 'Pendiente de notificación LIDA'}</small><div><button type="button" className="link-btn" onClick={() => inputRefs.current[requisito.tipo]?.click()}>Reemplazar</button><button type="button" className="documento-delete" onClick={() => eliminar(documento)}>Eliminar</button></div></div> : <button type="button" className="documento-upload" disabled={ocupado} onClick={() => inputRefs.current[requisito.tipo]?.click()}>{ocupado ? 'Cargando...' : 'Seleccionar PDF'}</button>}<input ref={(element) => { inputRefs.current[requisito.tipo] = element; }} type="file" accept="application/pdf,.pdf" hidden onChange={(event) => subirArchivo(requisito.tipo, event.target.files?.[0])}/></article>;
    })}</div>}</div>
  </div>;
}
