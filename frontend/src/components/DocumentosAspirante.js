import React, {useCallback, useEffect, useRef, useState} from 'react';
import {useApplicantCopy} from './aspirantPanelTranslations';

const TIPOS_REQUISITO = ['cv', 'titulo', 'carta_motivacion', 'carta_recomendacion'];

function tamano(bytes) {
  return bytes ? `${(bytes / (1024 * 1024)).toFixed(2)} MB` : '';
}

export default function DocumentosAspirante({session}) {
  const copy = useApplicantCopy();
  const text = copy.documents;
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
          throw new Error(`${text.unexpected} (${response.status}).`);
        }
      }
      if (!response.ok) throw new Error(data?.detail || text.loadError);
      if (!Array.isArray(data)) throw new Error(text.invalidResponse);
      setDocumentos(data);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'No se pudieron cargar tus documentos.');
    } finally {
      if (!signal.aborted) setCargando(false);
    }
  }, [session.access, text]);

  useEffect(() => {
    const controller = new AbortController();
    cargarDocumentos(controller.signal);
    return () => controller.abort();
  }, [cargarDocumentos]);

  async function subirArchivo(tipo, archivo) {
    if (!archivo) return;
    if (archivo.type !== 'application/pdf' && !archivo.name.toLowerCase().endsWith('.pdf')) {
      setError(text.pdfOnly);
      return;
    }
    if (archivo.size > 10 * 1024 * 1024) {
      setError(text.maxFile);
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
        const mensaje = data?.archivo || data?.tipo || data?.detail || texto;
        throw new Error(`${text.saveError}${response.status ? ` (${response.status})` : ''}${mensaje ? `. ${mensaje}` : ''}`);
      }
      if (!data) throw new Error(text.saveUnexpected);
      setDocumentos((actual) => [...actual.filter((documento) => documento.tipo !== tipo), data]);
    } catch (err) {
      setError(err.message || text.saveError);
    } finally {
      setSubiendo('');
      if (inputRefs.current[tipo]) inputRefs.current[tipo].value = '';
    }
  }

  async function eliminar(documento) {
    if (!window.confirm(`${text.deleteConfirm} ${documento.nombre_original}?`)) return;
    setError('');
    try {
      const response = await fetch(`/api/preregistro/documentos/${documento.id}/`, {method: 'DELETE', headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error(text.deleteError);
      setDocumentos((actual) => actual.filter((item) => item.id !== documento.id));
    } catch (err) {
      setError(err.message || text.deleteError);
    }
  }

  async function descargar(documento) {
    setError('');
    try {
      const response = await fetch(`${documento.archivo}`, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error(text.downloadError);
      const url = URL.createObjectURL(await response.blob());
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = documento.nombre_original;
      enlace.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setError(err.message || text.downloadError);
    }
  }

  return <div id="panel-documentos" role="tabpanel" className="documentos-panel">
    <div className="panel-card panel-card--wide"><h3>{text.title}</h3><p className="documentos-intro">{text.intro}</p>{error && <div className="api-error" role="alert">{error}</div>}{cargando ? <p>{copy.loading}</p> : <div className="documentos-grid">{TIPOS_REQUISITO.map((tipo, index) => {
      const [titulo, descripcion] = text.requirements[index];
      const requisito = {tipo, titulo, descripcion};
      const documento = documentos.find((item) => item.tipo === requisito.tipo);
      const ocupado = subiendo === requisito.tipo;
      return <article className="documento-card" key={requisito.tipo}><div><h4>{requisito.titulo}</h4><p>{requisito.descripcion}</p></div>{documento ? <div className="documento-cargado"><span className="documento-ok">{text.loaded}</span><button type="button" className="documento-link" onClick={() => descargar(documento)}>{documento.nombre_original}</button><small>{tamano(documento.tamano)} · {documento.lida_notificado ? text.notified : text.pendingNotice}</small><div><button type="button" className="link-btn" onClick={() => inputRefs.current[requisito.tipo]?.click()}>{text.replace}</button><button type="button" className="documento-delete" onClick={() => eliminar(documento)}>{text.delete}</button></div></div> : <button type="button" className="documento-upload" disabled={ocupado} onClick={() => inputRefs.current[requisito.tipo]?.click()}>{ocupado ? text.uploading : text.choosePdf}</button>}<input ref={(element) => { inputRefs.current[requisito.tipo] = element; }} type="file" accept="application/pdf,.pdf" hidden onChange={(event) => subirArchivo(requisito.tipo, event.target.files?.[0])}/></article>;
    })}</div>}</div>
  </div>;
}
