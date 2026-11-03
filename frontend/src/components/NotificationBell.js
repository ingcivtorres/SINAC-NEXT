import React, {useCallback, useEffect, useRef, useState} from 'react';
import './NotificationBell.css';
import notificIcon from '../assets/notific.png';
import {useLanguage} from '../translations';

const COPY = {
  es: {
    locale: 'es-MX', title: 'Notificaciones', unread: '({count} sin leer)', saving: 'Guardando...', markRead: 'Marcar leídas', retry: 'Reintentar',
    loadError: 'No se pudieron cargar las notificaciones.', markError: 'No se pudieron marcar las notificaciones como leídas.',
    unavailable: 'Las notificaciones están disponibles para aspirantes y alumnos.', loading: 'Cargando notificaciones...',
    empty: 'No tienes notificaciones.', more: 'Se muestran las 20 notificaciones más recientes.',
  },
  en: {
    locale: 'en-US', title: 'Notifications', unread: '({count} unread)', saving: 'Saving...', markRead: 'Mark as read', retry: 'Retry',
    loadError: 'Notifications could not be loaded.', markError: 'Notifications could not be marked as read.',
    unavailable: 'Notifications are available to applicants and students.', loading: 'Loading notifications...',
    empty: 'You have no notifications.', more: 'Showing the 20 most recent notifications.',
  },
  de: {
    locale: 'de-DE', title: 'Benachrichtigungen', unread: '({count} ungelesen)', saving: 'Wird gespeichert...', markRead: 'Als gelesen markieren', retry: 'Erneut versuchen',
    loadError: 'Die Benachrichtigungen konnten nicht geladen werden.', markError: 'Die Benachrichtigungen konnten nicht als gelesen markiert werden.',
    unavailable: 'Benachrichtigungen sind für Bewerber und Studierende verfügbar.', loading: 'Benachrichtigungen werden geladen...',
    empty: 'Sie haben keine Benachrichtigungen.', more: 'Es werden die 20 neuesten Benachrichtigungen angezeigt.',
  },
  zh: {
    locale: 'zh-CN', title: '通知', unread: '（{count} 条未读）', saving: '正在保存...', markRead: '标为已读', retry: '重试',
    loadError: '无法加载通知。', markError: '无法将通知标为已读。',
    unavailable: '通知仅对申请人和学生开放。', loading: '正在加载通知...',
    empty: '你没有通知。', more: '仅显示最近的 20 条通知。',
  },
  pt: {
    locale: 'pt-BR', title: 'Notificações', unread: '({count} não lidas)', saving: 'Salvando...', markRead: 'Marcar como lidas', retry: 'Tentar novamente',
    loadError: 'Não foi possível carregar as notificações.', markError: 'Não foi possível marcar as notificações como lidas.',
    unavailable: 'As notificações estão disponíveis para candidatos e alunos.', loading: 'Carregando notificações...',
    empty: 'Você não tem notificações.', more: 'Exibindo as 20 notificações mais recentes.',
  },
};

export default function NotificationBell({session}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const [eventos, setEventos] = useState([]);
  const [noLeidas, setNoLeidas] = useState(0);
  const [abierto, setAbierto] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [marcando, setMarcando] = useState(false);
  const [error, setError] = useState('');
  const [disponible, setDisponible] = useState(true);
  const solicitudActiva = useRef(false);

  const cargar = useCallback(async () => {
    if (solicitudActiva.current || !disponible) return;
    solicitudActiva.current = true;
    try {
      const respuesta = await fetch('/api/preregistro/seguimiento/', {
        headers: {Authorization: `Bearer ${session.access}`},
      });
      if (respuesta.status === 403) {
        setDisponible(false);
        return;
      }
      if (!respuesta.ok) throw new Error('loadError');
      const data = await respuesta.json();
      setEventos(Array.isArray(data.eventos) ? data.eventos : []);
      setNoLeidas(Number.isFinite(data.no_leidas) ? data.no_leidas : 0);
      setError('');
    } catch (err) {
      setError('loadError');
    } finally {
      solicitudActiva.current = false;
      setCargando(false);
    }
  }, [disponible, session.access]);

  useEffect(() => {
    cargar();
    const timer = setInterval(cargar, 30000);
    return () => clearInterval(timer);
  }, [cargar]);

  async function marcarLeidas() {
    setMarcando(true);
    setError('');
    try {
      const respuesta = await fetch('/api/preregistro/notificaciones/marcar-leidas/', {
        method: 'POST',
        headers: {Authorization: `Bearer ${session.access}`},
      });
      if (!respuesta.ok) throw new Error('markError');
      const data = await respuesta.json();
      setEventos(items => items.map(item => ({...item, leido: true})));
      setNoLeidas(count => Math.max(0, count - (data.updated || 0)));
    } catch (err) {
      setError('markError');
    } finally {
      setMarcando(false);
    }
  }

  return (
    <div className="notification-bell-wrap">
      <button
        type="button"
        className={`notification-bell ${noLeidas ? 'has-new' : ''}`}
        aria-label={t.title}
        aria-expanded={abierto}
        onClick={() => setAbierto(!abierto)}
      >
        <img src={notificIcon} alt="" className="bell-icon" aria-hidden="true" />
        {noLeidas > 0 && <span className="bell-count">{noLeidas > 99 ? '99+' : noLeidas}</span>}
      </button>
      {abierto && (
        <div className="notification-popover">
          <div className="notification-popover-head">
            <strong>{t.title} {noLeidas > 0 ? t.unread.replace('{count}', noLeidas) : ''}</strong>
            <button type="button" disabled={!disponible || !noLeidas || marcando} onClick={marcarLeidas}>
              {marcando ? t.saving : t.markRead}
            </button>
          </div>
          {error && <div className="notification-error" role="alert">{t[error]}<button type="button" onClick={cargar}>{t.retry}</button></div>}
          <div className="notification-items">
            {!disponible ? <p className="notification-empty">{t.unavailable}</p> : cargando ? <p className="notification-empty">{t.loading}</p> : eventos.length ? eventos.slice(0, 20).map(item => (
              <article key={item.id} className={!item.leido ? 'unread' : ''}>
                <div>
                  <strong>{item.origen || 'SINAC NEXT'}</strong>
                  <small>{item.created_at ? new Date(item.created_at).toLocaleString(t.locale) : ''}</small>
                </div>
                <p>{item.detalle}</p>
              </article>
            )) : <p className="notification-empty">{t.empty}</p>}
          </div>
          {eventos.length > 20 && <p className="notification-more">{t.more}</p>}
        </div>
      )}
    </div>
  );
}
