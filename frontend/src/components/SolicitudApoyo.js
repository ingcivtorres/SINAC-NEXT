import React, {useEffect, useState} from 'react';
import leftLogo from '../assets/logociv.png';
import rightLogo from '../assets/6-removebg-preview.png';
import {useApplicantCopy} from './aspirantPanelTranslations';
import {BANCOS_MEXICO} from './bancosMexico';

function clabeValida(valor) {
  if (!/^\d{18}$/.test(valor)) return false;
  const pesos = [3, 7, 1];
  const suma = valor.slice(0, 17).split('').reduce((acc, d, i) => acc + ((Number(d) * pesos[i % 3]) % 10), 0);
  return (10 - (suma % 10)) % 10 === Number(valor[17]);
}

function fecha(valor, locale) {
  return valor ? new Intl.DateTimeFormat(locale, {dateStyle: 'long'}).format(new Date(valor)) : new Intl.DateTimeFormat(locale, {dateStyle: 'long'}).format(new Date());
}

export default function SolicitudApoyo({perfil, session, onActualizado}) {
  const copy = useApplicantCopy();
  const text = copy.support;
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
    if (!banco.trim() || !clabeValida(clabeLimpia)) {
      setError(text.validation);
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
      if (!response.ok) throw new Error(text.saveError);
      setMensaje(text.registered);
      onActualizado();
    } catch (err) {
      setError(err.message || text.saveError);
    } finally {
      setGuardando(false);
    }
  }

  return <>
    <div className="panel-card support-card">
      <h3>{text.title}</h3>
      {!habilitado ? <p className="support-locked">{text.locked}</p> : solicitudCompleta ? <><div className="api-success" role="status">{text.registered}</div><button type="button" className="qa-btn support-print-btn" onClick={() => window.print()}>{text.print}</button></> : <form className="support-form" onSubmit={guardar}><p>{text.intro}</p><label>{text.bank}<select value={banco} required onChange={(event) => setBanco(event.target.value)}><option value="">—</option>{banco && !BANCOS_MEXICO.includes(banco) && <option value={banco}>{banco}</option>}{BANCOS_MEXICO.map(nombre => <option key={nombre} value={nombre}>{nombre}</option>)}</select></label><label>{text.clabe}<span className="clabe-field"><input type="text" inputMode="numeric" value={clabe} maxLength="18" required onChange={(event) => setClabe(event.target.value.replace(/\D/g, ''))} placeholder={text.digits} className={clabe.length === 18 ? (clabeValida(clabe) ? 'clabe-ok' : 'clabe-bad') : ''}/>{clabeValida(clabe) && <span className="clabe-check" role="img" aria-label="CLABE válida">✔</span>}</span>{clabe.length === 18 && !clabeValida(clabe) && <small className="clabe-error">CLABE inválida: revisa los dígitos.</small>}</label>{error && <div className="api-error" role="alert">{error}</div>}{mensaje && <div className="api-success" role="status">{mensaje}</div>}<button type="submit" className="qa-btn" disabled={guardando}>{guardando ? text.saving : text.save}</button></form>}
    </div>

    {solicitudCompleta && <section className="support-print-sheet" aria-label={text.printTitle}>
      <header className="support-print-header">
        <img src={leftLogo} alt="CINVESTAV" className="support-print-logo left"/>
        <div className="support-print-title">
          <p>{text.institution}</p>
          <p>{text.institute}</p>
          <h1>{text.printTitle}</h1>
        </div>
        <img src={rightLogo} alt="Logo" className="support-print-logo right"/>
      </header>
      <div className="support-print-meta"><span>{text.requestDate}: {fecha(perfil.solicitud_apoyo_fecha, copy.locale)}</span><span>{text.folio}: {perfil.business_key || 'SINAC-NEXT'}</span></div>
      <p className="support-print-intro">{text.declaration}</p>
      <table className="support-print-table"><tbody><tr><th>{text.applicant}</th><td>{perfil.nombre}</td></tr><tr><th>CURP</th><td>{perfil.curp}</td></tr><tr><th>{copy.overview.program}</th><td>{perfil.programa}</td></tr><tr><th>{copy.overview.currentUnit}</th><td>{perfil.unidad}</td></tr><tr><th>{text.bank}</th><td>{perfil.banco_apoyo}</td></tr><tr><th>{text.clabe}</th><td>{perfil.clabe_interbancaria}</td></tr></tbody></table>
      <p className="support-print-declaration">{text.accuracy}</p>
      <div className="support-print-signatures"><div><span>________________________________</span><strong>{text.signature}</strong></div><div><span>________________________________</span><strong>{text.approval}</strong></div></div>
      <footer>{text.generated}</footer>
    </section>}
  </>;
}
