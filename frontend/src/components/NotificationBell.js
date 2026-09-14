import React, {useEffect, useState} from 'react';
import './NotificationBell.css';
import notificIcon from '../assets/notific.png';

export default function NotificationBell({session}) {
  const [eventos, setEventos] = useState([]);
  const [abierto, setAbierto] = useState(false);

  async function cargar() {
    try {
      const respuesta = await fetch('/api/preregistro/seguimiento/', {
        headers: {Authorization: `Bearer ${session.access}`},
      });
      if (respuesta.ok) {
        const data = await respuesta.json();
        setEventos(data.eventos || []);
      }
    } catch (error) {
      // La campana no debe bloquear el panel si el servicio no responde.
    }
  }

  useEffect(() => {
    cargar();
    const timer = setInterval(cargar, 10000);
    return () => clearInterval(timer);
  }, [session.access]);

  async function marcarLeidas() {
    setEventos(items => items.map(item => ({...item, leido: true})));
    await fetch('/api/preregistro/notificaciones/marcar-leidas/', {
      method: 'POST',
      headers: {Authorization: `Bearer ${session.access}`},
    });
  }

  const pendientes = eventos.filter(item => !item.leido).length;

  return (
    <div className="notification-bell-wrap">
      <button
        type="button"
        className={`notification-bell ${pendientes ? 'has-new' : ''}`}
        aria-label="Notificaciones"
        aria-expanded={abierto}
        onClick={() => setAbierto(!abierto)}
      >
        <img src={notificIcon} alt="" className="bell-icon" aria-hidden="true" />
        {pendientes > 0 && <span className="bell-count">{pendientes > 99 ? '99+' : pendientes}</span>}
      </button>
      {abierto && (
        <div className="notification-popover">
          <div className="notification-popover-head">
            <strong>Notificaciones</strong>
            <button type="button" onClick={marcarLeidas}>Marcar leídas</button>
          </div>
          <div className="notification-items">
            {eventos.length ? eventos.slice(0, 8).map(item => (
              <article key={item.id} className={!item.leido ? 'unread' : ''}>
                <div>
                  <strong>{item.origen || 'SINAC NEXT'}</strong>
                  <small>{item.created_at ? new Date(item.created_at).toLocaleString('es-MX') : ''}</small>
                </div>
                <p>{item.detalle}</p>
              </article>
            )) : <p className="notification-empty">No tienes notificaciones.</p>}
          </div>
        </div>
      )}
    </div>
  );
}
