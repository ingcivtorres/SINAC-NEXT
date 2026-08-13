import React, {useEffect, useState} from 'react';
import leftLogo from '../assets/logociv.png';
import rightLogo from '../assets/6-removebg-preview.png';

function fecha(valor) {
  return valor ? new Intl.DateTimeFormat('es-MX', {dateStyle: 'long'}).format(new Date(valor)) : new Intl.DateTimeFormat('es-MX', {dateStyle: 'long'}).format(new Date());
}

export default function SolicitudApoyo({perfil, session, onActualizado}) {
  const [banco, setBanco] = useState(perfil.banco_apoyo || '');
  const [clabe, setClabe] = useState(perfil.clabe_interbancaria || '');
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [guardando, setGuardando] = useState(false);
  const habilitado = perfil.curso_propedeutico_aprobado && Number(perfil.curso_propedeutico_nota) >= 8;
  const solicitudCompleta = perfil.apoyo_solicitado && perfil.banco_apoyo && perfil.clabe_interbancaria;

  useEffect(() => {
    setBanco(perfil.banco_apoyo || '');
    setClabe(perfil.clabe_interbancaria || '');
  }, [perfil.banco_apoyo, perfil.clabe_interbancaria]);

  async function guardar(event) {
    event.preventDefault();
    const clabeLimpia = clabe.replace(/\D/g, '');
    if (!banco.trim() || clabeLimpia.length !== 18) {
      setError('Captura el banco y una CLABE interbancaria de 18 dígitos.');
      return;
    }
    setGuardando(true);
    setError('');
    setMensaje('');
    try {
      const response = await fetch('/api/preregistro/apoyo/solicitar/', {
        method: 'POST',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({banco: banco.trim(), clabe_interbancaria: clabeLimpia}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.banco || data.clabe_interbancaria || data.detail || 'No se pudo guardar la solicitud.');
      setMensaje(data.detail);
      onActualizado();
    } catch (err) {
      setError(err.message || 'No se pudo guardar la solicitud.');
    } finally {
      setGuardando(false);
    }
  }

  return <>
    <div className="panel-card support-card">
      <h3>Solicitud de apoyo</h3>
      {!habilitado ? <p className="support-locked">Este formulario se habilitará cuando Coordinación Académica registre que aprobaste el curso propedéutico con una calificación mínima de 8.</p> : solicitudCompleta ? <><div className="api-success" role="status">Tu solicitud de apoyo está registrada. Ya puedes imprimir la hoja formal.</div><button type="button" className="qa-btn support-print-btn" onClick={() => window.print()}>Imprimir solicitud de apoyo</button></> : <form className="support-form" onSubmit={guardar}><p>Captura los datos bancarios para registrar tu solicitud de apoyo académico.</p><label>Nombre del banco<input type="text" value={banco} maxLength="120" required onChange={(event) => setBanco(event.target.value)} placeholder="Ej. BBVA México"/></label><label>CLABE interbancaria<input type="text" inputMode="numeric" value={clabe} maxLength="18" required onChange={(event) => setClabe(event.target.value.replace(/\D/g, ''))} placeholder="18 dígitos"/></label>{error && <div className="api-error" role="alert">{error}</div>}{mensaje && <div className="api-success" role="status">{mensaje}</div>}<button type="submit" className="qa-btn" disabled={guardando}>{guardando ? 'Guardando...' : 'Guardar datos y solicitar apoyo'}</button></form>}
    </div>

    {solicitudCompleta && <section className="support-print-sheet" aria-label="Solicitud imprimible de apoyo académico">
      <header className="support-print-header">
        <img src={leftLogo} alt="CINVESTAV" className="support-print-logo left"/>
        <div className="support-print-title">
          <p>CENTRO DE INVESTIGACIÓN Y DE ESTUDIOS AVANZADOS</p>
          <p>DEL INSTITUTO POLITÉCNICO NACIONAL</p>
          <h1>Solicitud de apoyo académico</h1>
        </div>
        <img src={rightLogo} alt="Logo" className="support-print-logo right"/>
      </header>
      <div className="support-print-meta"><span>Fecha de solicitud: {fecha(perfil.solicitud_apoyo_fecha)}</span><span>Folio: {perfil.business_key || 'SINAC-NEXT'}</span></div>
      <p className="support-print-intro">Por medio de la presente, solicito el apoyo académico correspondiente y proporciono los datos bancarios para los fines administrativos aplicables.</p>
      <table className="support-print-table"><tbody><tr><th>Nombre del aspirante</th><td>{perfil.nombre}</td></tr><tr><th>CURP</th><td>{perfil.curp}</td></tr><tr><th>Programa</th><td>{perfil.programa}</td></tr><tr><th>Unidad</th><td>{perfil.unidad}</td></tr><tr><th>Banco</th><td>{perfil.banco_apoyo}</td></tr><tr><th>CLABE interbancaria</th><td>{perfil.clabe_interbancaria}</td></tr></tbody></table>
      <p className="support-print-declaration">Declaro que los datos proporcionados son correctos y autorizo su uso exclusivamente para la gestión administrativa del apoyo solicitado.</p>
      <div className="support-print-signatures"><div><span>________________________________</span><strong>Firma del aspirante</strong></div><div><span>________________________________</span><strong>Vo. Bo. Coordinación Académica</strong></div></div>
      <footer>Documento generado por SINAC NEXT · Cinvestav</footer>
    </section>}
  </>;
}
