import React, {useEffect} from 'react';
import {useLanguage} from '../translations';

const COPY = {
  es: {title: '¿Cerrar sesión?', text: 'Tu sesión actual se cerrará y volverás al inicio.', cancel: 'Cancelar', confirm: 'Sí, cerrar sesión'},
  en: {title: 'Log out?', text: 'Your current session will end and you will return to the home page.', cancel: 'Cancel', confirm: 'Yes, log out'},
  de: {title: 'Abmelden?', text: 'Ihre aktuelle Sitzung wird beendet und Sie kehren zur Startseite zurück.', cancel: 'Abbrechen', confirm: 'Ja, abmelden'},
  zh: {title: '退出登录？', text: '当前会话将结束，您将返回首页。', cancel: '取消', confirm: '是，退出登录'},
  pt: {title: 'Sair da sessão?', text: 'Sua sessão atual será encerrada e você voltará ao início.', cancel: 'Cancelar', confirm: 'Sim, sair'},
};

export default function LogoutModal({onCancel, onConfirm}) {
  const {language} = useLanguage();
  const text = COPY[language] || COPY.es;

  useEffect(() => {
    const onKey = (event) => { if (event.key === 'Escape') onCancel(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);

  return <div className="modal-backdrop" role="presentation" onClick={onCancel}>
    <div className="modal-card" role="alertdialog" aria-modal="true" aria-labelledby="logout-modal-title" onClick={(event) => event.stopPropagation()}>
      <h3 id="logout-modal-title">{text.title}</h3>
      <p>{text.text}</p>
      <div className="modal-actions">
        <button type="button" className="btn-secondary" onClick={onCancel}>{text.cancel}</button>
        <button type="button" className="qa-btn" autoFocus onClick={onConfirm}>{text.confirm}</button>
      </div>
    </div>
  </div>;
}
