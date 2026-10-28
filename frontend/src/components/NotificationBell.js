import React, {useCallback, useEffect, useRef, useState} from 'react';
import './NotificationBell.css';
import notificIcon from '../assets/notific.png';

export default function NotificationBell({session}) {
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
      if (!respuesta.ok) throw new Error('No se pudieron cargar las notificaciones.');
      const data = await respuesta.json();
      setEventos(Array.isArray(data.eventos) ? data.eventos : []);
      setNoLeidas(Number.isFinite(data.no_leidas) ? data.no_leidas : 0);
      setError('');
    } catch (err) {
      setError(err.message || 'No se pudieron cargar las notificaciones.');
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
      if (!respuesta.ok) throw new Error('No se pudieron marcar las notificaciones como leídas.');
      const data = await respuesta.json();
      setEventos(items => items.map(item => ({...item, leido: true})));
      setNoLeidas(count => Math.max(0, count - (data.updated || 0)));
    } catch (err) {
      setError(err.message || 'No se pudieron marcar las notificaciones como leídas.');
    } finally {
      setMarcando(false);
    }
  }

  return (
    <div className="notification-bell-wrap">
      <button
        type="button"
        className={`notification-bell ${noLeidas ? 'has-new' : ''}`}
        aria-label="Notificaciones"
        aria-expanded={abierto}
        onClick={() => setAbierto(!abierto)}
      >
        <img src={notificIcon} alt="" className="bell-icon" aria-hidden="true" />
        {noLeidas > 0 && <span className="bell-count">{noLeidas > 99 ? '99+' : noLeidas}</span>}
      </button>
      {abierto && (
        <div className="notification-popover">
          <div className="notification-popover-head">
            <strong>Notificaciones {noLeidas > 0 ? `(${noLeidas} sin leer)` : ''}</strong>
            <button type="button" disabled={!disponible || !noLeidas || marcando} onClick={marcarLeidas}>
              {marcando ? 'Guardando...' : 'Marcar leídas'}
            </button>
          </div>
          {error && <div className="notification-error" role="alert">{error}<button type="button" onClick={cargar}>Reintentar</button></div>}
          <div className="notification-items">
            {!disponible ? <p className="notification-empty">Las notificaciones están disponibles para aspirantes y alumnos.</p> : cargando ? <p className="notification-empty">Cargando notificaciones...</p> : eventos.length ? eventos.slice(0, 20).map(item => (
              <article key={item.id} className={!item.leido ? 'unread' : ''}>
                <div>
                  <strong>{item.origen || 'SINAC NEXT'}</strong>
                  <small>{item.created_at ? new Date(item.created_at).toLocaleString('es-MX') : ''}</small>
                </div>
                <p>{item.detalle}</p>
              </article>
            )) : <p className="notification-empty">No tienes notificaciones.</p>}
          </div>
          {eventos.length > 20 && <p className="notification-more">Se muestran las 20 notificaciones más recientes.</p>}
        </div>
      )}
    </div>
  );
}
