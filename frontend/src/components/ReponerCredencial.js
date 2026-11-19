import React, {useState} from 'react';
import {useLanguage} from '../translations';

const textos = {
  es: {kicker: 'CREDENCIAL DIGITAL', title: 'Reposición de credencial', intro: 'Úsala si el alumno perdió su credencial impresa o su teléfono. Las versiones anteriores dejarán de ser válidas y se le notificará por correo.', button: 'Reponer credencial', confirm: '¿Reponer la credencial? Las credenciales impresas anteriores quedarán invalidadas.', done: folio => `Credencial repuesta. Nuevo folio: ${folio}.`, error: 'No se pudo reponer la credencial.', expired: 'Tu sesión expiró.'},
  en: {kicker: 'DIGITAL ID CARD', title: 'Replace ID card', intro: 'Use it if the student lost the printed card or phone. Previous versions will no longer be valid and the student will be notified by email.', button: 'Replace ID card', confirm: 'Replace the ID card? Previously printed cards will be invalidated.', done: folio => `ID card replaced. New serial: ${folio}.`, error: 'The ID card could not be replaced.', expired: 'Your session expired.'},
  de: {kicker: 'DIGITALER AUSWEIS', title: 'Ausweis ersetzen', intro: 'Verwenden, wenn der gedruckte Ausweis oder das Telefon verloren ging. Frühere Versionen werden ungültig; die Person wird per E-Mail benachrichtigt.', button: 'Ausweis ersetzen', confirm: 'Ausweis ersetzen? Bisher gedruckte Ausweise werden ungültig.', done: folio => `Ausweis ersetzt. Neue Nummer: ${folio}.`, error: 'Der Ausweis konnte nicht ersetzt werden.', expired: 'Ihre Sitzung ist abgelaufen.'},
  zh: {kicker: '电子学生证', title: '补办学生证', intro: '学生遗失打印版学生证或手机时使用。旧版本将失效，并通过电子邮件通知学生。', button: '补办学生证', confirm: '确定补办学生证？之前打印的学生证将失效。', done: folio => `学生证已补办。新编号：${folio}。`, error: '无法补办学生证。', expired: '会话已过期。'},
  pt: {kicker: 'CARTEIRINHA DIGITAL', title: 'Reposição de carteirinha', intro: 'Use se o aluno perdeu a carteirinha impressa ou o telefone. As versões anteriores deixarão de valer e o aluno será avisado por e-mail.', button: 'Repor carteirinha', confirm: 'Repor a carteirinha? As carteirinhas impressas anteriores serão invalidadas.', done: folio => `Carteirinha reposta. Novo número: ${folio}.`, error: 'Não foi possível repor a carteirinha.', expired: 'Sua sessão expirou.'},
};

export default function ReponerCredencial({alumnoId, session, onLogout}) {
  const {language} = useLanguage();
  const copy = textos[language] || textos.es;
  const [estado, setEstado] = useState({enviando: false, mensaje: '', error: ''});

  async function reponer() {
    if (!window.confirm(copy.confirm)) return;
    setEstado({enviando: true, mensaje: '', error: ''});
    try {
      const respuesta = await fetch(`/api/servicios-escolares/alumnos/${alumnoId}/credencial/reponer/`, {
        method: 'POST', headers: {Authorization: `Bearer ${session.access}`},
      });
      if (respuesta.status === 401) return onLogout(copy.expired);
      const datos = await respuesta.json().catch(() => ({}));
      if (!respuesta.ok) throw new Error(datos.detail || copy.error);
      setEstado({enviando: false, mensaje: copy.done(datos.folio), error: ''});
    } catch (e) {
      setEstado({enviando: false, mensaje: '', error: e.message || copy.error});
    }
  }

  return <section className="servicios-card">
    <div className="servicios-card-heading">
      <div><span className="panel-kicker">{copy.kicker}</span><h3>{copy.title}</h3><p>{copy.intro}</p></div>
      <button type="button" className="btn-secondary" onClick={reponer} disabled={estado.enviando}>{copy.button}</button>
    </div>
    {estado.mensaje && <div className="api-success" role="status">{estado.mensaje}</div>}
    {estado.error && <div className="api-error" role="alert">{estado.error}</div>}
  </section>;
}
