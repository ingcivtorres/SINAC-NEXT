import React, {useEffect, useState} from 'react';
import JuradoDefensaPanel from './JuradoDefensaPanel';
import DashboardAnalitico from './DashboardAnalitico';
import PerfilAspirante, {fotoUrl} from './PerfilAspirante';
import {useDirectorCopy} from './directorPanelTranslations';

export default function PanelDirector({session, onLogout}) {
  const copy = useDirectorCopy();
  const sectionGroups = [
    {label: copy.groups.panorama, items: [['resumen', copy.menu.resumen, '▦'], ['analitica', copy.menu.analitica, '▥']]},
    {label: copy.groups.followup, items: [['tesistas', copy.menu.tesistas, '♙'], ['avances', copy.menu.avances, '◴']]},
    {label: copy.groups.evaluation, items: [['predoctoral', copy.menu.predoctoral, '✦'], ['evaluaciones', copy.menu.evaluaciones, '✓'], ['jurado', copy.menu.jurado, '⚖']]},
    {label: copy.groups.academic, items: [['expedientes', copy.menu.expedientes, '▤'], ['proyectos', copy.menu.proyectos, '✦']]},
    {label: copy.groups.account, items: [['perfil', copy.menu.perfil, '●']]},
  ];
  const sections = sectionGroups.flatMap(group => group.items);

  const formatDate = (value) => value ? new Intl.DateTimeFormat(copy.locale, {dateStyle: 'medium'}).format(new Date(value)) : copy.common.pending;

  function estadoMateria(materia) {
    if (materia.calificacion == null) return copy.status.cursando;
    if (materia.calificacion < 7) return copy.status.reprobada;
    if (materia.calificacion < 8) return copy.status.aprobadaSeguimiento;
    return copy.status.aprobada;
  }

  const [active, setActive] = useState('resumen');
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [firmaMsg, setFirmaMsg] = useState('');
  const [examenesPredoctorales, setExamenesPredoctorales] = useState([]);
  const [predoctoralForm, setPredoctoralForm] = useState({aspirante_id: '', titulo: copy.menu.predoctoral, descripcion: '', fecha_programada: '', duracion_minutos: 120});

  const cargarPanel = async () => {
    setCargando(true);
    setError('');
    try {
      const response = await fetch('/api/director/panel/', {headers: {Authorization: `Bearer ${session.access}`}});
      const body = await response.json().catch(() => ({}));
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (!response.ok) throw new Error(body.detail || copy.messages.loadPanel);
      setDatos(body);
      const examenesResponse = await fetch('/api/predoctoral/examenes/', {headers: {Authorization: `Bearer ${session.access}`}});
      const examenesBody = await examenesResponse.json().catch(() => ({}));
      if (examenesResponse.ok) setExamenesPredoctorales(examenesBody.examenes || []);
    } catch (err) {
      setError(err.message || copy.messages.loadPanel);
    } finally {
      setCargando(false);
    }
  };

  useEffect(() => { cargarPanel(); }, [session.access]);

  const director = datos?.director || {};
  const tesistas = datos?.tesistas || [];
  const expedientes = datos?.expedientes || [];
  const proyectos = datos?.proyectos_tesis || [];
  const resumen = datos?.resumen || {};
  const evaluaciones = tesistas.flatMap((tesista) => (tesista.materias || []).map((materia) => ({...materia, tesista: tesista.nombre})));
  const menuCounts = {
    tesistas: resumen.tesistas_asignados || 0,
    avances: resumen.avances_por_revisar || 0,
    predoctoral: examenesPredoctorales.length,
    evaluaciones: evaluaciones.length,
    expedientes: expedientes.length,
    proyectos: proyectos.length,
  };

  async function firmar(expediente) {
    setFirmaMsg('');
    try {
      const response = await fetch(`/api/expedientes/${expediente.id}/firma/`, {
        method: 'POST',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({rol_firmante: 'director'}),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.signError);
      setFirmaMsg(copy.messages.expedienteSigned);
      await cargarPanel();
    } catch (err) { setFirmaMsg(err.message || copy.messages.signError); }
  }

  async function actualizarProyecto(proyecto, estado) {
    const comentario = window.prompt(copy.messages.commentPrompt, proyecto.comentarios_revision || '');
    if (comentario === null) return;
    try {
      const response = await fetch(`/api/proyectos-tesis/${proyecto.id}/`, {
        method: 'PATCH',
        headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'},
        body: JSON.stringify({estado, comentarios_revision: comentario}),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.projectUpdate);
      setFirmaMsg(`${copy.messages.projectUpdated} ${body.estado_label || estado}.`);
      await cargarPanel();
    } catch (err) { setError(err.message || copy.messages.projectUpdate); }
  }

  async function programarPredoctoral(event) {
    event.preventDefault();
    if (!predoctoralForm.aspirante_id) return setError(copy.messages.selectionRequired);
    if (!predoctoralForm.fecha_programada) return setError(copy.messages.dateRequired);
    try {
      const response = await fetch('/api/predoctoral/examenes/', {method: 'POST', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify({...predoctoralForm, fecha_programada: new Date(predoctoralForm.fecha_programada).toISOString()})});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || body.fecha_programada || copy.messages.examProgram);
      setExamenesPredoctorales(items => [body, ...items]);
      setPredoctoralForm({aspirante_id: '', titulo: copy.menu.predoctoral, descripcion: '', fecha_programada: '', duracion_minutos: 120});
      setFirmaMsg(copy.messages.examScheduled);
    } catch (err) { setError(err.message || copy.messages.examProgram); }
  }

  async function actualizarPredoctoral(examen, cambios) {
    try {
      const response = await fetch(`/api/predoctoral/examenes/${examen.id}/`, {method: 'PATCH', headers: {'Authorization': `Bearer ${session.access}`, 'Content-Type': 'application/json'}, body: JSON.stringify(cambios)});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.updateExam);
      setExamenesPredoctorales(items => items.map(item => item.id === body.id ? body : item));
    } catch (err) { setError(err.message || copy.messages.updateExam); }
  }

  const nombre = director.nombre || copy.common.defaultDirector;
  const titulo = sections.find((section) => section[0] === active)?.[1] || copy.menu.panel;

  return (
    <section className="admin-dashboard docente-dashboard director-dashboard" aria-label={copy.panel}>
      <aside className="admin-sidebar">
        <div className="admin-sidebar-header">
          <div className="admin-brand-mark director-brand-mark">{director.profile_photo ? <img src={fotoUrl(director.profile_photo)} alt={copy.common.profilePhoto} /> : nombre.charAt(0)}</div>
          <div><p className="panel-kicker">{copy.kicker}</p><h2>{copy.title}</h2><small>{copy.subtitle}</small></div>
        </div>
        <nav className="admin-menu" aria-label={copy.panel}>
          {sectionGroups.map(group => <div className="docente-nav-group" key={group.label}><p>{group.label}</p>{group.items.map(([id, label, icon]) => <button key={id} type="button" className={`admin-menu-item ${active === id ? 'is-active' : ''}`} onClick={() => setActive(id)}><i aria-hidden="true">{icon}</i><span>{label}</span>{menuCounts[id] != null && <small>{menuCounts[id]}</small>}</button>)}</div>)}
        </nav>
        <div className="admin-side-card"><p>{copy.cards.followUp}</p><strong>{resumen.tesistas_asignados || 0}</strong><span>{copy.welcome.assigned}</span></div>
        <button type="button" className="admin-logout" onClick={() => onLogout(copy.messages.sessionClosed)}>{copy.logout}</button>
      </aside>

      <main className="admin-main-panel">
        <header className="admin-topbar"><div><p className="panel-kicker">{copy.menu.panel}</p><h1>{titulo}</h1></div><div className="admin-top-actions"><button type="button" className="btn-secondary" onClick={cargarPanel}>{copy.refresh}</button></div></header>
        {error && <div className="api-error" role="alert">{error}</div>}
        {cargando && <div className="director-empty"><div>◌</div><h3>{copy.loading}</h3><p>{copy.loadingText}</p></div>}
        {!cargando && active === 'analitica' && <DashboardAnalitico title={copy.dashboard.title} description={copy.dashboard.description} metrics={[{label: copy.dashboard.students, value:resumen.tesistas_asignados || 0}, {label: copy.dashboard.activeFiles, value:resumen.expedientes_activos || 0}, {label: copy.dashboard.projects, value:proyectos.length}, {label: copy.dashboard.average, value:tesistas.length ? (tesistas.reduce((total, item) => total + (Number(item.promedio) || 0), 0) / tesistas.length).toFixed(2) : '0.00'}]} distribution={[{label: copy.dashboard.approvedSubjects, value:tesistas.reduce((total, item) => total + (item.materias_aprobadas || 0), 0)}, {label: copy.dashboard.inProgressSubjects, value:tesistas.reduce((total, item) => total + (item.materias_cursando || 0), 0)}, {label: copy.dashboard.failedSubjects, value:tesistas.reduce((total, item) => total + (item.materias_reprobadas || 0), 0)}, {label: copy.dashboard.projectReview, value:resumen.avances_por_revisar || 0}]} />}
        {!cargando && active === 'jurado' && <JuradoDefensaPanel session={session} proyectos={proyectos} onUpdated={cargarPanel} onMessage={setFirmaMsg} onError={setError} />}

        {!cargando && active === 'predoctoral' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">EVALUACIÓN DOCTORAL</span><h2>Examen predoctoral</h2><p>Programa, evalúa y registra el dictamen de tus tesistas.</p></div><span className="director-count">{examenesPredoctorales.length} exámenes</span></div><form className="tesis-form" onSubmit={programarPredoctoral}><label>Tesista<select required value={predoctoralForm.aspirante_id} onChange={event => setPredoctoralForm({...predoctoralForm, aspirante_id: event.target.value})}><option value="">Selecciona un tesista</option>{tesistas.map(tesista => <option key={tesista.id} value={tesista.id}>{tesista.nombre} · {tesista.matricula || 'Sin matrícula'}</option>)}</select></label><label>Fecha y hora<input type="datetime-local" value={predoctoralForm.fecha_programada} onChange={event => setPredoctoralForm({...predoctoralForm, fecha_programada: event.target.value})}/></label><label>Duración (minutos)<input type="number" min="15" value={predoctoralForm.duracion_minutos} onChange={event => setPredoctoralForm({...predoctoralForm, duracion_minutos: event.target.value})}/></label><label>Descripción<textarea rows="2" value={predoctoralForm.descripcion} onChange={event => setPredoctoralForm({...predoctoralForm, descripcion: event.target.value})} placeholder="Objetivo y alcance de la evaluación"/></label><button type="submit" className="btn-primary">Programar examen</button></form>{firmaMsg && <p className="api-success">{firmaMsg}</p>}{examenesPredoctorales.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>Tesista</th><th>Fecha</th><th>Estado</th><th>Calificación</th><th>Acciones</th></tr></thead><tbody>{examenesPredoctorales.map(examen => <tr key={examen.id}><td><strong>{examen.alumno?.nombre || 'Alumno'}</strong><small>{examen.alumno?.matricula || ''}</small></td><td>{formatDate(examen.fecha_programada)}</td><td><span className={`director-status-badge ${examen.color || 'neutral'}`}>{examen.estado_label}</span></td><td>{examen.calificacion ?? 'Pendiente'}</td><td><button type="button" className="btn-secondary" onClick={() => actualizarPredoctoral(examen, {estado: 'iniciado'})}>Iniciar</button><button type="button" className="btn-primary" onClick={() => { const value = window.prompt('Calificación final (0 a 10):', examen.calificacion ?? ''); if (value !== null) actualizarPredoctoral(examen, {calificacion: value}); }}>Registrar resultado</button></td></tr>)}</tbody></table></div> : <div className="director-empty"><h3>No hay exámenes programados</h3><p>Selecciona un tesista para iniciar su evaluación predoctoral.</p></div>}</div>}

        {!cargando && active === 'resumen' && <>
          <div className="director-welcome"><div><small>{copy.welcome.panelTitle}</small><h2>{copy.welcome.greeting}, {nombre.split(' ')[0]}</h2><p>{copy.welcome.intro}</p></div><div className="director-welcome-mark">DT</div></div>
          <div className="director-stats"><article><span>{copy.welcome.assigned}</span><strong>{resumen.tesistas_asignados || 0}</strong><small>{copy.common.assignedToYou}</small></article><article><span>{copy.welcome.activeFiles}</span><strong>{resumen.expedientes_activos || 0}</strong><small>{resumen.expedientes_sin_firma || 0} {copy.cards.pendingReview}</small></article><article><span>{copy.welcome.evaluations}</span><strong>{resumen.evaluaciones || 0}</strong><small>{copy.cards.registeredSubjects}</small></article><article><span>{copy.welcome.advances}</span><strong>{resumen.avances_por_revisar || 0}</strong><small>{datos?.avance_tesis_disponible ? copy.cards.pendingFollowUp : copy.cards.modulePending}</small></article></div>
          {tesistas.length ? <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.welcome.followUp}</span><h2>{copy.tables.studentProgress}</h2></div><button type="button" className="btn-secondary" onClick={() => setActive('tesistas')}>{copy.welcome.visible}</button></div><div className="director-mini-grid">{tesistas.slice(0, 3).map((tesista) => <article key={tesista.id}><strong>{tesista.nombre}</strong><span>{tesista.matricula || copy.common.noEnrollment} · {tesista.programa || copy.common.noProgram}</span><b>{tesista.materias_aprobadas}/{tesista.total_materias} {copy.tables.approved} {copy.tables.matters}</b></article>)}</div></div> : <div className="director-empty"><div>◈</div><h3>{copy.welcome.noAssignmentsTitle}</h3><p>{copy.welcome.noAssignmentsText}</p></div>}
        </>}

        {!cargando && active === 'tesistas' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.welcome.academicAssign}</span><h2>{copy.menu.tesistas}</h2></div><span className="director-count">{tesistas.length} {copy.common.records}</span></div>{tesistas.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>{copy.tables.students}</th><th>{copy.tables.enrollment}</th><th>{copy.tables.program}</th><th>{copy.tables.subjects}</th><th>{copy.tables.approved}</th><th>{copy.tables.average}</th></tr></thead><tbody>{tesistas.map((tesista) => <tr key={tesista.id}><td><strong>{tesista.nombre}</strong><small>{tesista.correo}</small></td><td>{tesista.matricula || copy.common.pending}</td><td>{tesista.programa || copy.common.noProgram}</td><td>{tesista.total_materias}</td><td>{tesista.materias_aprobadas}</td><td>{tesista.promedio == null ? '—' : tesista.promedio.toFixed(2)}</td></tr>)}</tbody></table></div> : <div className="director-empty"><h3>{copy.records.noTesistasTitle}</h3><p>{copy.records.noTesistasText}</p></div>}</div>}

        {!cargando && active === 'expedientes' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.menu.expedientes}</span><h2>{copy.menu.expedientes}</h2></div><span className="director-count">{expedientes.length} {copy.common.records}</span></div>{firmaMsg && <p className="api-success">{firmaMsg}</p>}{expedientes.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>{copy.tables.students}</th><th>{copy.tables.file}</th><th>{copy.tables.created}</th><th>{copy.tables.state}</th><th>{copy.tables.firm}</th><th>{copy.tables.action}</th></tr></thead><tbody>{expedientes.map((expediente) => { const firmado = (expediente.firmas || []).some((firma) => firma.rol_firmante === 'director'); return <tr key={expediente.id}><td><strong>{expediente.aspirante_nombre}</strong><small>{expediente.matricula || expediente.usuario}</small></td><td>{expediente.folio}</td><td>{formatDate(expediente.fecha_creacion)}</td><td>{expediente.estado}</td><td>{firmado ? `${copy.common.signed} ${formatDate((expediente.firmas || []).find((firma) => firma.rol_firmante === 'director')?.firmado_at)}` : copy.common.pending}</td><td><button type="button" className="btn-primary" onClick={() => firmar(expediente)} disabled={firmado}>{firmado ? copy.common.signed : copy.common.sign}</button></td></tr>; })}</tbody></table></div> : <div className="director-empty"><h3>{copy.records.noExpedientesTitle}</h3><p>{copy.records.noExpedientesText}</p></div>}</div>}

        {!cargando && active === 'proyectos' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.dashboard.projectTitle}</span><h2>{copy.dashboard.projectTitle}</h2><p>{copy.dashboard.projectDescription}</p></div><span className="director-count">{proyectos.length} {copy.dashboard.projects}</span></div>{proyectos.length ? <div className="director-project-list">{proyectos.map((proyecto) => <article key={proyecto.id}><div><strong>{proyecto.titulo}</strong><small>{proyecto.alumno_nombre} · {proyecto.alumno_matricula || copy.common.noEnrollment} · {proyecto.alumno_programa || copy.common.noProgram}</small><p>{proyecto.resumen}</p><span className="director-project-meta">{proyecto.linea_investigacion || copy.tables.linePending} · {copy.tables.updated} {formatDate(proyecto.updated_at)}</span>{proyecto.comentarios_revision && <blockquote>{proyecto.comentarios_revision}</blockquote>}</div><div className="director-project-actions"><span className={`director-status-badge ${proyecto.estado === 'aprobado' ? 'success' : proyecto.estado === 'rechazado' ? 'danger' : proyecto.estado === 'observado' ? 'warning' : 'neutral'}`}>{proyecto.estado_label}</span>{['en_revision','observado'].includes(proyecto.estado) && <><button type="button" className="btn-primary" onClick={() => actualizarProyecto(proyecto, 'aprobado')}>{copy.tables.approval}</button><button type="button" className="btn-secondary" onClick={() => actualizarProyecto(proyecto, 'observado')}>{copy.tables.requestChanges}</button><button type="button" className="btn-secondary" onClick={() => actualizarProyecto(proyecto, 'rechazado')}>{copy.tables.reject}</button></>}</div></article>)}</div> : <div className="director-empty"><h3>{copy.records.noProjectsTitle}</h3><p>{copy.records.noProjectsText}</p></div>}</div>}

        {!cargando && active === 'avances' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.dashboard.reviewPanel}</span><h2>{copy.dashboard.academicProgress}</h2></div></div>{tesistas.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>{copy.tables.student}</th><th>{copy.tables.subjects}</th><th>{copy.tables.approved}</th><th>{copy.tables.state}</th><th>{copy.common.grade}</th><th>{copy.tables.average}</th></tr></thead><tbody>{tesistas.map((tesista) => <tr key={tesista.id}><td><strong>{tesista.nombre}</strong></td><td>{tesista.total_materias}</td><td><span className="director-status-badge success">{tesista.materias_aprobadas}</span></td><td><span className="director-status-badge danger">{tesista.materias_reprobadas}</span></td><td>{tesista.creditos_aprobados}</td><td>{tesista.promedio == null ? '—' : tesista.promedio.toFixed(2)}</td></tr>)}</tbody></table></div> : <div className="director-empty"><h3>{copy.cards.noAcademicProgress}</h3><p>{copy.cards.noAcademicProgressText}</p></div>}<p className="director-note">{datos?.avance_tesis_mensaje}</p></div>}

        {!cargando && active === 'evaluaciones' && <div className="director-card"><div className="director-card-head"><div><span className="panel-kicker">{copy.dashboard.evaluationTitle}</span><h2>{copy.dashboard.academicTrajectory}</h2></div><span className="director-count">{evaluaciones.length} {copy.tables.matters}</span></div>{evaluaciones.length ? <div className="director-table-wrap"><table className="director-table"><thead><tr><th>{copy.tables.student}</th><th>{copy.tables.subjects}</th><th>{copy.tables.partials}</th><th>{copy.common.grade}</th><th>{copy.tables.state}</th></tr></thead><tbody>{evaluaciones.map((materia) => <tr key={`${materia.id}-${materia.tesista}`}><td>{materia.tesista}</td><td><strong>{materia.materia_clave}</strong><small>{materia.materia_nombre}</small></td><td>{[materia.parcial_1, materia.parcial_2, materia.parcial_3].map((value) => value ?? '—').join(' / ')}</td><td>{materia.calificacion ?? '—'}</td><td><span className={`director-status-badge ${materia.color || 'neutral'}`}>{estadoMateria(materia)}</span></td></tr>)}</tbody></table></div> : <div className="director-empty"><h3>{copy.records.noEvaluationsTitle}</h3><p>{copy.records.noEvaluationsText}</p></div>}</div>}

        {!cargando && active === 'perfil' && <PerfilAspirante perfil={{...director, telefono: director.telefono || ''}} session={session} onActualizado={(actualizado) => setDatos(actual => ({...actual, director: {...actual.director, ...actualizado}}))} />}
      </main>
    </section>
  );
}
