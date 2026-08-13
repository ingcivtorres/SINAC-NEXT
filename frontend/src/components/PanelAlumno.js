import React, {useCallback, useEffect, useMemo, useState} from 'react';

function InfoRow({label, value}) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <strong>{value || '—'}</strong>
    </div>
  );
}

function Badge({children, tone = 'neutral'}) {
  return <span className={`badge badge--${tone}`}>{children}</span>;
}

function MateriaRow({materia}) {
  return (
    <article className="subject-row">
      <div>
        <strong>{materia.materia_clave}</strong> {materia.materia_nombre}
        <p>{materia.materia_profesor || 'Profesor no asignado'}</p>
      </div>
      <div className="subject-meta">
        <Badge tone={materia.color}>{materia.estado_label}</Badge>
        <span>{materia.calificacion ?? 'Sin calif.'}</span>
      </div>
    </article>
  );
}

export default function PanelAlumno({session, onLogout}) {
  const [perfil, setPerfil] = useState(null);
  const [inscripciones, setInscripciones] = useState([]);
  const [solicitudes, setSolicitudes] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  const apiHeaders = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);

  const cargarDatos = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const [perfilResp, inscripcionesResp, solicitudesResp] = await Promise.all([
        fetch('/api/preregistro/me/', {headers: apiHeaders, signal}),
        fetch('/api/preregistro/inscripciones/', {headers: apiHeaders, signal}),
        fetch('/api/preregistro/solicitudes-academicas/', {headers: apiHeaders, signal}),
      ]);

      if (perfilResp.status === 401 || inscripcionesResp.status === 401 || solicitudesResp.status === 401) {
        onLogout('Tu sesión ha caducado. Inicia sesión de nuevo.');
        return;
      }

      if (!perfilResp.ok || !inscripcionesResp.ok || !solicitudesResp.ok) {
        throw new Error('No se pudo cargar los datos del alumno.');
      }

      setPerfil(await perfilResp.json());
      setInscripciones(await inscripcionesResp.json());
      setSolicitudes(await solicitudesResp.json());
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'No se pudo cargar el panel del alumno.');
      }
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [apiHeaders, onLogout]);

  useEffect(() => {
    const controller = new AbortController();
    cargarDatos(controller.signal);
    return () => controller.abort();
  }, [cargarDatos]);

  const promedioGeneral = useMemo(() => {
    if (!inscripciones.length) return null;
    const calificaciones = inscripciones
      .map(item => Number(item.calificacion))
      .filter(value => !Number.isNaN(value));
    if (!calificaciones.length) return null;
    const sum = calificaciones.reduce((total, val) => total + val, 0);
    return (sum / calificaciones.length).toFixed(2);
  }, [inscripciones]);

  const descargarArchivo = useCallback(async (ruta, nombre) => {
    try {
      const response = await fetch(ruta, {headers: apiHeaders});
      if (!response.ok) throw new Error('No se pudo generar el archivo.');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = nombre;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setMessage(`${nombre} descargado con éxito.`);
    } catch (err) {
      setError(err.message || 'Error descargando el archivo.');
    }
  }, [apiHeaders]);

  return (
    <section className="panel-section" aria-label="Panel del alumno">
      <div className="panel-hero">
        <div>
          <p className="panel-kicker">Alumno</p>
          <h1>Panel del alumno</h1>
          <p className="panel-sub">Consulta tu información académica, solicitudes y horario.</p>
        </div>
        <button type="button" className="btn-outline-danger" onClick={() => onLogout('Se cerró la sesión correctamente.')}>Cerrar sesión</button>
      </div>

      {message && (
        <div className="api-success" role="status">
          {message}
          <button type="button" className="link-btn" onClick={() => setMessage('')}>Cerrar</button>
        </div>
      )}

      {error && (
        <div className="api-error" role="alert">
          {error}
          <button type="button" className="link-btn" onClick={() => cargarDatos(new AbortController().signal)}>
            Reintentar
          </button>
        </div>
      )}

      {loading && !perfil && <div className="panel-card">Cargando tu información de alumno...</div>}

      {perfil && (
        <div className="panel-grid">
          <div className="panel-card panel-card--wide">
            <h3>Bienvenido, {perfil.nombre || 'Alumno'}</h3>
            <p>Usuario: <strong>{perfil.usuario || perfil.correo || '—'}</strong></p>
            <div className="info-grid">
              <InfoRow label="Programa" value={perfil.programa} />
              <InfoRow label="Unidad" value={perfil.unidad} />
              <InfoRow label="Modalidad" value={perfil.modalidad} />
              <InfoRow label="Estado actual" value={perfil.proceso_estado || 'Pendiente'} />
              <InfoRow label="Promedio" value={perfil.promedio ? Number(perfil.promedio).toFixed(2) : '—'} />
              <InfoRow label="Promedio académico" value={promedioGeneral || 'Sin calificaciones'} />
            </div>
          </div>

          <div className="panel-card">
            <h3>Materias inscritas</h3>
            {inscripciones.length ? (
              <div className="subject-list">
                {inscripciones.map(materia => <MateriaRow key={materia.id} materia={materia} />)}
              </div>
            ) : (
              <p>No tienes materias inscritas aún.</p>
            )}
          </div>

          <div className="panel-card">
            <h3>Acciones académicas</h3>
            <div className="action-grid">
              <button type="button" className="btn-secondary" onClick={() => descargarArchivo('/api/preregistro/horario/download/', 'horario.txt')}>Descargar horario</button>
              <button type="button" className="btn-secondary" onClick={() => descargarArchivo('/api/preregistro/reinscripcion/download/', 'reinscripcion.txt')}>Descargar reinscripción</button>
              <button type="button" className="btn-secondary" onClick={() => setError('Funcionalidad de solicitud de ajuste de materias disponible pronto.')}>Solicitar ajuste de materias</button>
            </div>
          </div>

          <div className="panel-card">
            <h3>Solicitudes académicas</h3>
            {solicitudes.length ? (
              <ul className="request-list">
                {solicitudes.map(item => (
                  <li key={item.id}>
                    <strong>{item.tipo_label}</strong>
                    <p>{item.comentario || 'Sin comentario.'}</p>
                    <span>{item.estado_label}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No hay solicitudes académicas registradas.</p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
