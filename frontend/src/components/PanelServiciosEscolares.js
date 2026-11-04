import React, {useEffect, useMemo, useRef, useState} from "react";
import ExpedienteCentralizadoCard from "./ExpedienteCentralizadoCard";
import EgresadosPanel from "./EgresadosPanel";
import HistoricoPanel from "./HistoricoPanel";
import DocentesDirectorioPanel from "./DocentesDirectorioPanel";
import ExamenesGestionPanel from "./ExamenesGestionPanel";
import SolicitudesAcademicasReview from "./SolicitudesAcademicasReview";
import SchoolAcademicConfiguration from "./SchoolAcademicConfiguration";
import {useSchoolServicesCopy} from "./schoolServicesPanelTranslations";
import {TablaHerramientas, TablaPaginacion, useEtiquetasFiltro, useTablaControl} from "./TablaControles";

const buildMenu = (copy) => [
  {label: copy.groups.panorama, items: [["resumen", copy.menu.resumen, "▦"], ["alumnos", copy.menu.alumnos, "♙"], ["docentes", copy.menu.docentes, "♜"]]},
  {label: copy.groups.academicControl, items: [["planes", copy.menu.planes, "▧"], ["periodos", copy.menu.periodos, "◫"], ["cargas", copy.menu.cargas, "↗"], ["extemporaneas", copy.menu.extemporaneas, "⌁"], ["solicitudesAcademicas", copy.menu.solicitudesAcademicas, "✉"], ["inscripciones", copy.menu.inscripciones, "▣"], ["historial", copy.menu.historial, "▤"], ["calificaciones", copy.menu.calificaciones, "✓"], ["examenes", copy.menu.examenes || "Exámenes en línea", "✎"]]},
  {label: copy.groups.documentation, items: [["constancias", copy.menu.constancias, "▣"], ["egreso", copy.menu.egreso, "◆"], ["egresados", copy.menu.egresados, "♛"], ["historico", copy.menu.historico, "⟲"]]},
  {label: copy.groups.institutional, items: [["reportes", copy.menu.reportes, "▥"]]},
];

const ALTA_VACIA = {nombre: "", usuario: "", correo: "", curp: "", password: "", telefono: "", matricula: "", programa: "", departamento: ""};

const estadoTexto = (estado, copy) => ({
  activo: copy.status.activo,
  baja: copy.status.baja,
  inactivo: copy.status.inactivo,
  egresado: copy.status.egresado,
  reingreso: copy.movement.readmission,
  cursando: copy.status.cursando,
  aprobada: copy.status.aprobada,
  reprobada: copy.status.reprobada,
  pendiente: copy.status.pendiente,
  validada: copy.status.validada,
  observada: copy.status.observada,
}[estado] || estado || copy.status.pending);

function Estado({value, copy}) {
  const clase = String(value || "pendiente").toLowerCase().replace(/\s+/g, "-");
  const colorClase = value === "validada" ? "aprobada" : value === "observada" ? "reprobada" : clase;
  return <span className={`servicios-status servicios-status--${clase} servicios-status--${colorClase}`}>{estadoTexto(value, copy)}</span>;
}

export default function PanelServiciosEscolares({session, onLogout}) {
  const copy = useSchoolServicesCopy();
  const [active, setActive] = useState("resumen");
  const [datos, setDatos] = useState({alumnos: [], filtros: {programas: [], departamentos: []}, resumen: {}});
  const [reportes, setReportes] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [filters, setFilters] = useState({q: "", programa: "", departamento: "", estado: ""});
  const [formAlumno, setFormAlumno] = useState(null);
  const [movimiento, setMovimiento] = useState({estado: "", detalle: ""});
  const [altaAbierta, setAltaAbierta] = useState(false);
  const [alta, setAlta] = useState(ALTA_VACIA);
  const [guardando, setGuardando] = useState(false);
  const [observacion, setObservacion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [solicitudesExtemporaneas, setSolicitudesExtemporaneas] = useState([]);
  const [comentariosExtemporaneas, setComentariosExtemporaneas] = useState({});
  const [recargaExtemporaneas, setRecargaExtemporaneas] = useState(0);
  const cargaId = useRef(0);

  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);
  const alumno = useMemo(() => datos.alumnos.find(item => item.id === selectedId) || null, [datos.alumnos, selectedId]);
  const inscripciones = useMemo(() => datos.alumnos.flatMap(item => (item.inscripciones || []).map(inscripcion => ({...inscripcion, alumno: item}))), [datos.alumnos]);
  const etiquetasFiltro = useEtiquetasFiltro();
  const estadoAlumno = item => item.is_active ? item.proceso_estado || "activo" : "inactivo";
  const alumnosTabla = useTablaControl(datos.alumnos, {
    campos: item => [item.nombre, item.correo, item.matricula, item.usuario, item.programa, item.departamento],
    filtros: {programa: item => item.programa, departamento: item => item.departamento, estado: estadoAlumno},
    sinFiltros: active === "alumnos",
  });
  const materiasAlumnoTabla = useTablaControl(alumno?.inscripciones, {
    campos: item => [item.materia_clave, item.materia_nombre, item.materia_profesor, item.periodo],
    filtros: {estado: item => item.estado, validacion: item => item.validacion_servicios || "pendiente", tipo: item => item.extemporanea ? "extemporanea" : "regular"},
  });
  const extemporaneasTabla = useTablaControl(solicitudesExtemporaneas, {
    campos: item => [item.alumno_nombre, item.alumno_matricula, item.folio, item.periodo, item.programa, item.motivo],
    filtros: {estado: item => item.estado, periodo: item => item.periodo, programa: item => item.programa},
  });

  async function cargar(signal) {
    const id = ++cargaId.current;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
      const response = await fetch(`/api/servicios-escolares/panel/?${params.toString()}`, {headers, signal});
      if (response.status === 401) { onLogout(copy.messages.sessionExpired); return; }
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.loadPanel);
      if (id === cargaId.current) setDatos(body);
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message || copy.messages.loadPanel);
    } finally {
      if (!signal || !signal.aborted) setLoading(false);
    }
  }

  useEffect(() => { const controller = new AbortController(); cargar(controller.signal); return () => controller.abort(); }, [session.access, filters.q, filters.programa, filters.departamento, filters.estado]);

  useEffect(() => {
    if (active !== "reportes") return;
    const controller = new AbortController();
    const params = new URLSearchParams(Object.entries(filters).filter(([, value]) => value));
    fetch(`/api/servicios-escolares/reportes/?${params.toString()}`, {headers, signal: controller.signal})
      .then(response => {
        if (response.status === 401) { onLogout(copy.messages.sessionExpired); return null; }
        return response.ok ? response.json() : Promise.reject(new Error(copy.messages.loadReports));
      })
      .then(data => { if (data) setReportes(data); })
      .catch(err => { if (err.name !== "AbortError") setError(err.message); });
    return () => controller.abort();
  }, [active, session.access]);

  useEffect(() => { setMessage(""); setError(""); }, [active]);

  useEffect(() => {
    if (active !== "extemporaneas") return;
    const controller = new AbortController();
    fetch("/api/servicios-escolares/solicitudes-extemporaneas/", {headers, signal: controller.signal})
      .then(async response => {
        const body = await response.json().catch(() => ({}));
        if (response.status === 401) { onLogout(copy.messages.sessionExpired); return []; }
        if (!response.ok) throw new Error(body.detail || copy.extemporaneas.loadError);
        return body;
      })
      .then(data => { if (Array.isArray(data)) setSolicitudesExtemporaneas(data); })
      .catch(err => { if (err.name !== "AbortError") setError(err.message || copy.extemporaneas.loadError); });
    return () => controller.abort();
  }, [active, headers, onLogout, copy.messages.sessionExpired, copy.extemporaneas.loadError, recargaExtemporaneas]);

  function seleccionar(item) {
    setSelectedId(item.id);
    setFormAlumno({
      nombre: item.nombre || "", matricula: item.matricula || "", correo: item.correo || "",
      telefono: item.telefono || "", programa: item.programa || "", departamento: item.departamento || "",
      unidad: item.unidad || "", modalidad: item.modalidad || "Presencial", proceso_estado: item.proceso_estado || "activo",
      is_active: Boolean(item.is_active),
    });
  }

  async function guardarAlumno(event) {
    event.preventDefault();
    if (!alumno || !formAlumno || guardando) return;
    setError(""); setMessage("");
    setGuardando(true);
    try {
      const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/`, {method: "PATCH", headers: {...headers, "Content-Type": "application/json"}, body: JSON.stringify(formAlumno)});
      if (response.status === 401) return onLogout(copy.messages.sessionExpired);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.dataSaveError);
      setMessage(copy.messages.dataSaved);
      await cargar();
    } catch (err) { setError(err.message || copy.messages.dataSaveError); }
    finally { setGuardando(false); }
  }

  async function darDeAlta(event) {
    event.preventDefault();
    if (guardando) return;
    setError(""); setMessage("");
    setGuardando(true);
    try {
      const response = await fetch("/api/servicios-escolares/panel/", {method: "POST", headers: {...headers, "Content-Type": "application/json"}, body: JSON.stringify(alta)});
      if (response.status === 401) return onLogout(copy.messages.sessionExpired);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.studentCreateError);
      setAlta(ALTA_VACIA);
      setAltaAbierta(false);
      setMessage(copy.messages.studentCreated);
      await cargar();
    } catch (err) { setError(err.message || copy.messages.studentCreateError); }
    finally { setGuardando(false); }
  }

  async function registrarMovimiento(event) {
    event.preventDefault();
    if (!alumno || !movimiento.detalle.trim()) return setError(copy.messages.describeMovement);
    if (guardando) return;
    setError(""); setMessage("");
    setGuardando(true);
    try {
      const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/`, {method: "POST", headers: {...headers, "Content-Type": "application/json"}, body: JSON.stringify({...movimiento, detalle: movimiento.detalle.trim()})});
      if (response.status === 401) return onLogout(copy.messages.sessionExpired);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || body.detalle || copy.messages.movementError);
      setMovimiento({estado: "", detalle: ""});
      setMessage(copy.messages.movementSaved);
      await cargar();
      if (body.alumno) seleccionar(body.alumno);
    } catch (err) { setError(err.message || copy.messages.movementError); }
    finally { setGuardando(false); }
  }

  async function validarInscripcion(inscripcionId, validar = true, comentario = "") {
    if (!alumno) return;
    if (!validar && !comentario.trim()) return setError(copy.enrollment.observeReasonRequired);
    try {
      setError(""); setMessage("");
      const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/validar-inscripcion/`, {method: "POST", headers: {...headers, "Content-Type": "application/json"}, body: JSON.stringify({inscripcion_id: inscripcionId, validar, ...(validar ? {} : {comentario: comentario.trim()})})});
      if (response.status === 401) return onLogout(copy.messages.sessionExpired);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || body.comentario || copy.messages.invalidInscription);
      setObservacion(null);
      setMessage(validar ? copy.messages.validInscription : copy.messages.invalidForReview);
      await cargar();
    } catch (err) { setError(err.message || copy.messages.invalidInscription); }
  }

  async function descargar(tipo, id = selectedId) {
    if (!id) return setError(copy.messages.noStudentSelected);
    try {
      const response = await fetch(`/api/servicios-escolares/alumnos/${id}/documentos/${tipo}/`, {headers});
      if (response.status === 401) return onLogout(copy.messages.sessionExpired);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || copy.messages.documentError);
      }
      const url = URL.createObjectURL(await response.blob());
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = `${tipo}_${id}.pdf`;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err.message || copy.messages.documentError); }
  }

  async function resolverSolicitudExtemporanea(solicitud, estado) {
    const comentario_revision = comentariosExtemporaneas[solicitud.id]?.trim() || "";
    if (estado === "rechazada" && !comentario_revision) {
      setError(copy.extemporaneas.rejectCommentRequired);
      return;
    }
    setError("");
    try {
      const response = await fetch(`/api/servicios-escolares/solicitudes-extemporaneas/${solicitud.id}/`, {
        method: "PATCH",
        headers: {...headers, "Content-Type": "application/json"},
        body: JSON.stringify({estado, comentario_revision}),
      });
      if (response.status === 401) return onLogout(copy.messages.sessionExpired);
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.extemporaneas.updateError);
      setSolicitudesExtemporaneas(items => items.map(item => item.id === body.id ? body : item));
      setMessage(estado === "aprobada" ? copy.extemporaneas.approved : copy.extemporaneas.rejected);
      setComentariosExtemporaneas(items => ({...items, [solicitud.id]: ""}));
    } catch (err) { setError(err.message || copy.extemporaneas.updateError); }
  }

  async function descargarOficioExtemporanea(solicitud) {
    try {
      const response = await fetch(`/api/servicios-escolares/solicitudes-extemporaneas/${solicitud.id}/oficio/`, {headers});
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || copy.extemporaneas.officeError);
      }
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${solicitud.folio}_oficio.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err.message || copy.extemporaneas.officeError); }
  }

  const label = buildMenu(copy).flatMap(group => group.items).find(item => item[0] === active)?.[1] || copy.menu.resumen;
  const mostrarDetalle = Boolean(alumno);

  function tablaAlumnos() {
    return (<>
      {active !== "alumnos" && <TablaHerramientas control={alumnosTabla} placeholder={copy.table.searchPlaceholder} filtros={[
        {clave: "programa", etiqueta: copy.table.program},
        {clave: "departamento", etiqueta: copy.table.department},
        {clave: "estado", etiqueta: copy.table.status, formato: value => estadoTexto(value, copy)},
      ]} />}
      <div className="servicios-table-wrap tabla-scroll">
        <table className="admin-table servicios-table">
          <thead>
            <tr>
              <th>{copy.table.student}</th>
              <th>{copy.table.enrollment}</th>
              <th>{copy.table.program}</th>
              <th>{copy.table.department}</th>
              <th>{copy.table.status}</th>
              <th>{copy.table.actions}</th>
            </tr>
          </thead>
          <tbody>
            {alumnosTabla.visibles.length ? alumnosTabla.visibles.map(item => (
              <tr key={item.id}>
                <td><strong>{item.nombre}</strong><small>{item.correo}</small></td>
                <td>{item.matricula || copy.common.noEnrollment}</td>
                <td>{item.programa || copy.common.noProgram}</td>
                <td>{item.departamento || copy.common.noDepartment}</td>
                <td><Estado copy={copy} value={estadoAlumno(item)} /></td>
                <td><button type="button" className="servicios-link" onClick={() => { seleccionar(item); if (active === "resumen") setActive("alumnos"); }}>{copy.table.consult}</button></td>
              </tr>
            )) : <tr><td colSpan="6" className="servicios-empty">{copy.common.noResults}</td></tr>}
          </tbody>
        </table>
      </div>
      <TablaPaginacion control={alumnosTabla} />
    </>);
  }

  function detalleAlumnoBase() {
    if (!mostrarDetalle) {
      return <div className="servicios-empty-card"><span>◉</span><h3>{copy.academic.selectStudent}</h3><p>{copy.academic.alert}</p></div>;
    }

    return (
      <div className="servicios-detail-grid">
        <article className="servicios-card servicios-profile-card">
          <div className="servicios-profile-head">
            <div className="servicios-avatar">{alumno.nombre.charAt(0).toUpperCase()}</div>
            <div>
              <h3>{alumno.nombre}</h3>
              <p>{alumno.matricula || copy.common.noEnrollment} · {alumno.programa || copy.common.noProgram}</p>
            </div>
            <Estado copy={copy} value={alumno.is_active ? alumno.proceso_estado || "activo" : "inactivo"} />
          </div>
          <div className="servicios-info-grid">
            <div><span>{copy.academic.email}</span><strong>{alumno.correo || "—"}</strong></div>
            <div><span>{copy.academic.phone}</span><strong>{alumno.telefono || "—"}</strong></div>
            <div><span>{copy.academic.department}</span><strong>{alumno.departamento || "—"}</strong></div>
            <div><span>{copy.academic.unit}</span><strong>{alumno.unidad || "—"}</strong></div>
            <div><span>{copy.academic.average}</span><strong>{alumno.promedio_academico ?? alumno.promedio ?? "—"}</strong></div>
            <div><span>{copy.academic.record}</span><strong>{alumno.expediente?.folio || copy.common.pendingDocuments}</strong></div>
          </div>
        </article>

        <form className="servicios-card servicios-form" onSubmit={guardarAlumno}>
          <div className="servicios-card-heading">
            <div><span className="panel-kicker">{copy.academic.management}</span><h3>{copy.academic.administrativeData}</h3></div>
            <button type="submit" className="btn-primary" disabled={guardando}>{copy.common.save}</button>
          </div>
          <div className="servicios-form-grid">
            <label>{copy.academic.name}<input value={formAlumno?.nombre || ""} onChange={e => setFormAlumno({...formAlumno, nombre: e.target.value})}/></label>
            <label>{copy.academic.matricula}<input value={formAlumno?.matricula || ""} onChange={e => setFormAlumno({...formAlumno, matricula: e.target.value})}/></label>
            <label>{copy.academic.program}<input value={formAlumno?.programa || ""} onChange={e => setFormAlumno({...formAlumno, programa: e.target.value})}/></label>
            <label>{copy.academic.department}<input value={formAlumno?.departamento || ""} onChange={e => setFormAlumno({...formAlumno, departamento: e.target.value})}/></label>
            <label>{copy.academic.email}<input type="email" value={formAlumno?.correo || ""} onChange={e => setFormAlumno({...formAlumno, correo: e.target.value})}/></label>
            <label>{copy.academic.phone}<input value={formAlumno?.telefono || ""} onChange={e => setFormAlumno({...formAlumno, telefono: e.target.value})}/></label>
            <label>{copy.academic.unit}<input value={formAlumno?.unidad || ""} onChange={e => setFormAlumno({...formAlumno, unidad: e.target.value})}/></label>
          </div>
        </form>

        <form className="servicios-card servicios-form" onSubmit={registrarMovimiento}>
          <div className="servicios-card-heading">
            <div><span className="panel-kicker">{copy.movement.kicker}</span><h3>{copy.movement.title}</h3></div>
            <button type="submit" className="btn-primary" disabled={guardando || !movimiento.detalle.trim()}>{copy.movement.submit}</button>
          </div>
          <div className="servicios-form-grid">
            <label>{copy.movement.state}<select value={movimiento.estado} onChange={e => setMovimiento({...movimiento, estado: e.target.value})}>
              <option value="">{copy.movement.noChange}</option>
              <option value="activo">{copy.status.activo}</option>
              <option value="reingreso">{copy.movement.readmission}</option>
              <option value="inactivo">{copy.status.inactivo}</option>
              <option value="baja">{copy.status.baja}</option>
            </select><small>{copy.movement.graduationHint}</small></label>
            <label>{copy.movement.detail}<textarea required rows="3" maxLength="2000" value={movimiento.detalle} placeholder={copy.movement.placeholder} onChange={e => setMovimiento({...movimiento, detalle: e.target.value})}/></label>
          </div>
        </form>
      </div>
    );
  }

  function detalleAlumno() {
    if (!alumno) return detalleAlumnoBase();
    return <><ExpedienteCentralizadoCard expedienteId={alumno.expediente?.id} session={session}/>{detalleAlumnoBase()}</>;
  }

  function contenido() {
    if (active === "planes" || active === "periodos" || active === "cargas") {
      return <SchoolAcademicConfiguration key={active} section={active} session={session} onLogout={onLogout}/>;
    }
    if (active === "solicitudesAcademicas") return <SolicitudesAcademicasReview session={session} onLogout={onLogout}/>;

    if (active === "resumen") {
      return (
        <>
          <div className="servicios-kpi-grid">
            <article><span>{copy.common.activeStudents}</span><strong>{datos.resumen.activos || 0}</strong><small>{copy.common.activeAccount}</small></article>
            <article><span>{copy.common.totalStudents}</span><strong>{datos.resumen.total || 0}</strong><small>{copy.common.officialRecord}</small></article>
            <article><span>{copy.common.academicPrevalidations}</span><strong>{datos.resumen.candidatos_egreso || 0}</strong><small>{copy.academic.graduateSubtitle}</small></article>
            <article><span>{copy.common.institutionalAverage}</span><strong>{datos.resumen.promedio_institucional ?? "—"}</strong><small>{copy.academic.studentProfile}</small></article>
          </div>
          <div className="servicios-card">
            <div className="servicios-card-heading">
              <div><span className="panel-kicker">{copy.common.quickConsult}</span><h3>{copy.common.registeredStudents}</h3></div>
              <button className="btn-secondary" onClick={() => setActive("alumnos")}>{copy.common.viewAllStudents}</button>
            </div>
            {tablaAlumnos()}
          </div>
        </>
      );
    }

    if (active === "alumnos") {
      return (
        <>
          <div className="servicios-toolbar">
            <input value={filters.q} onChange={e => setFilters({...filters, q: e.target.value})} placeholder={copy.table.searchPlaceholder}/>
            <select value={filters.programa} onChange={e => setFilters({...filters, programa: e.target.value})}><option value="">{copy.common.allPrograms}</option>{datos.filtros.programas.map(value => <option key={value} value={value}>{value}</option>)}</select>
            <select value={filters.departamento} onChange={e => setFilters({...filters, departamento: e.target.value})}><option value="">{copy.common.allDepartments}</option>{datos.filtros.departamentos.map(value => <option key={value} value={value}>{value}</option>)}</select>
            <select value={filters.estado} onChange={e => setFilters({...filters, estado: e.target.value})}><option value="">{copy.common.allStatuses}</option><option value="activo">{copy.status.activo}</option><option value="inactivo">{copy.status.inactivo}</option><option value="egresado">{copy.status.egresado}</option><option value="baja">{copy.status.baja}</option></select>
            <button type="button" className="btn-primary" onClick={() => setAltaAbierta(!altaAbierta)}>+ {copy.common.registered}</button>
          </div>
          {altaAbierta && (
            <form className="servicios-card servicios-alta-card" onSubmit={darDeAlta}>
              <div className="servicios-card-heading">
                <div><span className="panel-kicker">{copy.messages.newStudent.toUpperCase()}</span><h3>{copy.common.registered}</h3></div>
                <button type="button" className="btn-secondary" onClick={() => setAltaAbierta(false)}>{copy.common.cancel}</button>
              </div>
              <div className="servicios-form-grid">
                <label>{copy.academic.studentName}<input required value={alta.nombre} onChange={e => setAlta({...alta, nombre: e.target.value})}/></label>
                <label>{copy.academic.institutionUser}<input required value={alta.usuario} onChange={e => setAlta({...alta, usuario: e.target.value})}/></label>
                <label>{copy.academic.institutionalEmail}<input required type="email" value={alta.correo} onChange={e => setAlta({...alta, correo: e.target.value})}/></label>
                <label>{copy.academic.curp}<input required minLength="18" maxLength="18" value={alta.curp} onChange={e => setAlta({...alta, curp: e.target.value.toUpperCase()})}/></label>
                <label>{copy.academic.password}<input required type="password" autoComplete="new-password" minLength="8" pattern="(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}" title={copy.academic.passwordHint} value={alta.password} onChange={e => setAlta({...alta, password: e.target.value})}/><small>{copy.academic.passwordHint}</small></label>
                <label>{copy.academic.phone}<input value={alta.telefono} onChange={e => setAlta({...alta, telefono: e.target.value})}/></label>
                <label>{copy.academic.matricula}<input value={alta.matricula} onChange={e => setAlta({...alta, matricula: e.target.value})}/></label>
                <label>{copy.academic.program}<input value={alta.programa} onChange={e => setAlta({...alta, programa: e.target.value})}/></label>
                <label>{copy.academic.department}<input value={alta.departamento} onChange={e => setAlta({...alta, departamento: e.target.value})}/></label>
              </div>
              <button type="submit" className="btn-primary" disabled={guardando}>{copy.common.save}</button>
            </form>
          )}
          {alumno && <>
            <div className="servicios-row-actions"><button type="button" className="btn-secondary" onClick={() => setSelectedId(null)}>{copy.movement.close}</button></div>
            {detalleAlumno()}
          </>}
          {tablaAlumnos()}
        </>
      );
    }

    if (active === "extemporaneas") {
      const etiquetasEstado = {
        pendiente: copy.extemporaneas.pending,
        aprobada: copy.extemporaneas.approvedStatus,
        rechazada: copy.extemporaneas.rejectedStatus,
      };
      return (
        <section className="servicios-card">
          <div className="servicios-card-heading">
            <div><span className="panel-kicker">{copy.extemporaneas.kicker}</span><h3>{copy.extemporaneas.title}</h3><p>{copy.extemporaneas.intro}</p></div>
            <button type="button" className="btn-secondary" onClick={() => setRecargaExtemporaneas(count => count + 1)}>{copy.refresh}</button>
          </div>
          {solicitudesExtemporaneas.length > 0 && <TablaHerramientas control={extemporaneasTabla} filtros={[
            {clave: "estado", etiqueta: copy.table.status, formato: value => etiquetasEstado[value] || value},
            {clave: "periodo", etiqueta: etiquetasFiltro.period},
            {clave: "programa", etiqueta: copy.table.program},
          ]} />}
          <div className="tabla-scroll-lista">
          {extemporaneasTabla.visibles.length ? extemporaneasTabla.visibles.map(solicitud => (
            <article className="servicios-card" key={solicitud.id}>
              <div className="servicios-card-heading">
                <div><h4>{solicitud.alumno_nombre} · {solicitud.alumno_matricula || copy.common.noEnrollment}</h4><p>{copy.extemporaneas.folio}: {solicitud.folio} · {solicitud.periodo} · {solicitud.programa}</p></div>
                <Estado value={etiquetasEstado[solicitud.estado] || solicitud.estado} copy={copy}/>
              </div>
              <p><strong>{copy.extemporaneas.reason}:</strong> {solicitud.motivo}</p>
              <ul>{solicitud.materias.map(materia => <li key={materia.id}>{materia.clave} · {materia.nombre} · {materia.horario || "—"} · {materia.salon}</li>)}</ul>
              {solicitud.comentario_revision && <p><strong>{copy.extemporaneas.reviewComment}:</strong> {solicitud.comentario_revision}</p>}
              {solicitud.estado === "pendiente" && <>
                <label>{copy.extemporaneas.reviewComment}<textarea rows="2" maxLength="2000" value={comentariosExtemporaneas[solicitud.id] || ""} onChange={event => setComentariosExtemporaneas(items => ({...items, [solicitud.id]: event.target.value}))}/></label>
                <div className="servicios-row-actions">
                  <button type="button" className="btn-primary" onClick={() => resolverSolicitudExtemporanea(solicitud, "aprobada")}>{copy.extemporaneas.approve}</button>
                  <button type="button" className="btn-secondary" disabled={!comentariosExtemporaneas[solicitud.id]?.trim()} onClick={() => resolverSolicitudExtemporanea(solicitud, "rechazada")}>{copy.extemporaneas.reject}</button>
                </div>
              </>}
              {solicitud.estado === "aprobada" && <button type="button" className="btn-primary" onClick={() => descargarOficioExtemporanea(solicitud)}>{copy.extemporaneas.downloadOffice}</button>}
            </article>
          )) : <p className="servicios-muted">{copy.extemporaneas.empty}</p>}
          </div>
          <TablaPaginacion control={extemporaneasTabla} />
        </section>
      );
    }

    if (active === "inscripciones") {
      return (
        <div className="servicios-card">
          <div className="servicios-card-heading">
            <div><span className="panel-kicker">{copy.enrollment.title.toUpperCase()}</span><h3>{alumno ? `${copy.table.viewStudentData} ${alumno.nombre}` : copy.common.registeredStudents}</h3></div>
            {alumno && <button className="btn-secondary" onClick={() => setSelectedId(null)}>{copy.enrollment.review}</button>}
          </div>
          {alumno ? (<>
            <TablaHerramientas control={materiasAlumnoTabla} filtros={[
              {clave: "estado", etiqueta: copy.table.status, formato: value => estadoTexto(value, copy)},
              {clave: "validacion", etiqueta: copy.table.validation, formato: value => estadoTexto(value, copy)},
              {clave: "tipo", etiqueta: copy.enrollment.enrollmentType, opciones: [{value: "regular", label: copy.enrollment.regular}, {value: "extemporanea", label: copy.enrollment.extemporaneous}]},
            ]} />
            <div className="servicios-table-wrap tabla-scroll">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{copy.table.key}</th>
                    <th>{copy.table.subject}</th>
                    <th>{copy.table.credits}</th>
                    <th>{copy.enrollment.enrollmentType}</th>
                    <th>{copy.table.professor}</th>
                    <th>{copy.table.final}</th>
                    <th>{copy.table.status}</th>
                    <th>{copy.table.validation}</th>
                  </tr>
                </thead>
                <tbody>
                  {materiasAlumnoTabla.visibles.length ? materiasAlumnoTabla.visibles.map(item => (
                    <tr key={item.id}>
                      <td>{item.materia_clave}</td>
                      <td>{item.materia_nombre}</td>
                      <td>{item.materia_creditos ?? "—"}</td>
                      <td>{item.extemporanea ? <><strong>{copy.enrollment.extemporaneous}</strong><small>{item.motivo_extemporanea}</small></> : copy.enrollment.regular}</td>
                      <td>{item.materia_profesor || copy.common.registered}</td>
                      <td>{item.calificacion ?? copy.status.pending}</td>
                      <td><Estado copy={copy} value={item.estado}/></td>
                      <td>
                        <div>
                          <Estado copy={copy} value={item.validacion_servicios || "pendiente"}/>
                          <div className="servicios-row-actions">
                            <button type="button" className="servicios-link" onClick={() => validarInscripcion(item.id, true)} disabled={item.validacion_servicios === "validada"}>{copy.table.validate}</button>
                            <button type="button" className="servicios-link" onClick={() => setObservacion({id: item.id, comentario: ""})} disabled={item.validacion_servicios === "observada"}>{copy.table.observe}</button>
                          </div>
                          {observacion?.id === item.id && (
                            <div className="servicios-form">
                              <label>{copy.enrollment.observeReason}<textarea rows="2" maxLength="1000" required autoFocus value={observacion.comentario} placeholder={copy.enrollment.observeReasonHint} onChange={e => setObservacion({...observacion, comentario: e.target.value})}/></label>
                              <div className="servicios-row-actions">
                                <button type="button" className="btn-primary" disabled={!observacion.comentario.trim()} onClick={() => validarInscripcion(item.id, false, observacion.comentario)}>{copy.table.observe}</button>
                                <button type="button" className="btn-secondary" onClick={() => setObservacion(null)}>{copy.common.cancel}</button>
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )) : <tr><td colSpan="8" className="servicios-empty">{copy.enrollment.noInscriptions}</td></tr>}
                </tbody>
              </table>
            </div>
            <TablaPaginacion control={materiasAlumnoTabla} />
          </>) : <><p className="servicios-muted">{copy.enrollment.selectStudent}</p>{tablaAlumnos()}</>}
        </div>
      );
    }

    if (active === "historial" || active === "calificaciones") {
      return (
        <div className="servicios-card">
          <div className="servicios-card-heading">
            <div>
              <span className="panel-kicker">{active === "historial" ? copy.table.academicTrajectory.toUpperCase() : copy.table.institutionalGrades.toUpperCase()}</span>
              <h3>{alumno ? `${active === "historial" ? copy.table.subjectHistory : copy.table.institutionalGrades} · ${alumno.nombre}` : active === "historial" ? copy.table.subjectHistory : copy.table.institutionalGrades}</h3>
            </div>
            {alumno && <button className="btn-secondary" onClick={() => descargar(active === "historial" ? "historial" : "calificaciones")}>{copy.common.generatePdf}</button>}
          </div>
          {alumno ? (
            <>
              <div className="servicios-history-summary">
                <div><strong>{alumno.materias_aprobadas}</strong><span>{copy.table.approvedSubjects}</span></div>
                <div><strong>{alumno.creditos_obtenidos}</strong><span>{copy.table.creditsEarned}</span></div>
                <div><strong>{alumno.promedio_academico ?? "—"}</strong><span>{copy.table.finalAverage}</span></div>
              </div>
              <TablaHerramientas control={materiasAlumnoTabla} filtros={[{clave: "estado", etiqueta: copy.table.status, formato: value => estadoTexto(value, copy)}]} />
              <div className="servicios-table-wrap tabla-scroll">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>{copy.table.key}</th>
                      <th>{copy.table.subject}</th>
                      <th>{copy.table.credits}</th>
                      <th>{copy.table.partial1}</th>
                      <th>{copy.table.partial2}</th>
                      <th>{copy.table.partial3}</th>
                      <th>{copy.table.final}</th>
                      <th>{copy.table.status}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {materiasAlumnoTabla.visibles.length ? materiasAlumnoTabla.visibles.map(item => (
                      <tr key={item.id}>
                        <td>{item.materia_clave}</td>
                        <td>{item.materia_nombre}</td>
                        <td>{item.materia_creditos ?? "—"}</td>
                        <td>{item.parcial_1 ?? "—"}</td>
                        <td>{item.parcial_2 ?? "—"}</td>
                        <td>{item.parcial_3 ?? "—"}</td>
                        <td>{item.calificacion ?? copy.status.pending}</td>
                        <td><Estado copy={copy} value={item.estado}/></td>
                      </tr>
                    )) : <tr><td colSpan="8" className="servicios-empty">{copy.common.noGrades}</td></tr>}
                  </tbody>
                </table>
              </div>
              <TablaPaginacion control={materiasAlumnoTabla} />
              <p className="servicios-note">{copy.academic.noteAcademicValidation}</p>
            </>
          ) : <><p className="servicios-muted">{copy.messages.noAcademicData}</p>{tablaAlumnos()}</>}
        </div>
      );
    }

    if (active === "constancias") {
      return (
        <div className="servicios-card">
          <div className="servicios-card-heading">
            <div><span className="panel-kicker">{copy.documents.title.toUpperCase()}</span><h3>{copy.documents.title}</h3></div>
          </div>
          {alumno ? (
            <div className="servicios-doc-grid">
              <div className="servicios-doc-student">
                <div className="servicios-avatar">{alumno.nombre.charAt(0).toUpperCase()}</div>
                <strong>{alumno.nombre}</strong>
                <span>{alumno.matricula || copy.common.noEnrollment}</span>
              </div>
              {[
                ["constancia", copy.documents.studentName, copy.documents.descriptions.studies],
                ["calificaciones", copy.documents.grades, copy.documents.descriptions.grades],
                ["historial", copy.documents.academicHistory, copy.documents.descriptions.history],
                ["inscripcion", copy.documents.inscription, copy.documents.descriptions.inscription],
                ["egreso", copy.documents.graduation, copy.documents.descriptions.graduation],
              ].map(([tipo, titulo, descripcion]) => (
                <article key={tipo}>
                  <h4>{titulo}</h4>
                  <p>{descripcion}</p>
                  <button className="btn-secondary" onClick={() => descargar(tipo)}>{copy.common.generatePdf}</button>
                </article>
              ))}
            </div>
          ) : <><p className="servicios-muted">{copy.messages.noDocumentSelection}</p>{tablaAlumnos()}</>}
        </div>
      );
    }

    if (active === "egreso") {
      if (!alumno) {
        return (
          <div className="servicios-card">
            <div className="servicios-card-heading">
              <div><span className="panel-kicker">{copy.academic.graduateControl}</span><h3>{copy.academic.title}</h3></div>
            </div>
            <p className="servicios-muted">{copy.messages.noAcademicData}</p>
            {tablaAlumnos()}
          </div>
        );
      }

      const prevalidacion = alumno.prevalidacion_egreso;
      const resumen = prevalidacion?.resumen || {};
      const creditosCompletos = resumen.creditos_requeridos > 0 && resumen.creditos_aprobados >= resumen.creditos_requeridos;
      const periodosCompletos = resumen.periodos_requeridos > 0 && resumen.periodos_cursados >= resumen.periodos_requeridos;
      return (
        <div className="servicios-card">
          <div className="servicios-card-heading">
            <div><span className="panel-kicker">{copy.academic.graduateControl}</span><h3>{copy.academic.title} · {alumno.nombre}</h3></div>
            <Estado copy={copy} value={prevalidacion?.completa ? "validada" : "pendiente"}/>
          </div>
          <p className="servicios-note">{copy.academic.graduateSubtitle}</p>
          <div className="servicios-egreso">
            <div className="servicios-check-list">
              <div className={resumen.materias_obligatorias > 0 ? "ok" : "pending"}><span>{resumen.materias_obligatorias > 0 ? "✓" : "!"}</span>{copy.academic.mandatoryPlan}</div>
              <div className={resumen.materias_obligatorias > 0 && resumen.materias_pendientes?.length === 0 ? "ok" : "pending"}><span>{resumen.materias_obligatorias > 0 && resumen.materias_pendientes?.length === 0 ? "✓" : "!"}</span>{copy.academic.mandatoryApproved}: {resumen.materias_obligatorias_aprobadas || 0} / {resumen.materias_obligatorias || 0}</div>
              <div className={creditosCompletos ? "ok" : "pending"}><span>{creditosCompletos ? "✓" : "!"}</span>{copy.academic.creditsApproved}: {resumen.creditos_aprobados || 0} / {resumen.creditos_requeridos || copy.common.noThreshold}</div>
              <div className={periodosCompletos ? "ok" : "pending"}><span>{periodosCompletos ? "✓" : "!"}</span>{copy.academic.completedPeriods}: {resumen.periodos_cursados || 0} / {resumen.periodos_requeridos || 0}</div>
              <div className={alumno.matricula ? "ok" : "pending"}><span>{alumno.matricula ? "✓" : "!"}</span>{copy.academic.enrollmentAssigned}</div>
              <div className={alumno.documentos?.length ? "ok" : "pending"}><span>{alumno.documentos?.length ? "✓" : "!"}</span>{copy.academic.documentsLoaded}</div>
            </div>
            {prevalidacion?.motivos?.length > 0 && (
              <div className="servicios-note">
                <strong>{copy.academic.pendingAcademic}</strong>
                <ul>{prevalidacion.motivos.map(motivo => <li key={motivo}>{motivo}</li>)}</ul>
              </div>
            )}
            <button type="button" className="btn-secondary" onClick={() => descargar("egreso")}>{copy.common.generatePdf}</button>
          </div>
        </div>
      );
    }

    if (active === "reportes") {
      return (
        <div className="servicios-card">
          <div className="servicios-card-heading">
            <div><span className="panel-kicker">{copy.table.reportes.toUpperCase()}</span><h3>{copy.menu.reportes}</h3></div>
          </div>
          {reportes ? (
            <>
              <div className="servicios-kpi-grid servicios-kpi-grid--reports">
                <article><span>{copy.table.enrollment}</span><strong>{reportes.inscripciones}</strong></article>
                <article><span>{copy.status.aprobada}</span><strong>{reportes.aprobadas}</strong></article>
                <article><span>{copy.status.reprobada}</span><strong>{reportes.reprobadas}</strong></article>
                <article><span>{copy.status.cursando}</span><strong>{reportes.en_curso}</strong></article>
              </div>
              <div className="servicios-report-columns">
                <div>
                  <h4>{copy.table.byAcademicProgram}</h4>
                  {reportes.por_programa.map(item => <div className="servicios-bar-row" key={item.programa || "sin-programa"}><span>{item.programa || copy.common.noProgram}</span><strong>{item.total}</strong><i style={{width: `${Math.min(100, item.total * 12)}%`}} /></div>)}
                </div>
                <div>
                  <h4>{copy.table.byDepartment}</h4>
                  {reportes.por_departamento.map(item => <div className="servicios-bar-row" key={item.departamento || "sin-departamento"}><span>{item.departamento || copy.common.noDepartment}</span><strong>{item.total}</strong><i style={{width: `${Math.min(100, item.total * 12)}%`}} /></div>)}
                </div>
              </div>
            </>
          ) : <p className="servicios-muted">{copy.messages.loadingReports}</p>}
        </div>
      );
    }

    if (active === "egresados") return <EgresadosPanel session={session} onLogout={onLogout}/>;
    if (active === "docentes") return <DocentesDirectorioPanel session={session} onLogout={onLogout}/>;
    if (active === "examenes") return <ExamenesGestionPanel session={session}/>;
    if (active === "historico") return <HistoricoPanel session={session} onLogout={onLogout}/>;

    return null;
  }

  const MENU = buildMenu(copy);
  return (
    <section className="servicios-shell" aria-label={copy.panel}>
      <aside className="servicios-sidebar">
        <div className="servicios-identity">
          <div className="servicios-mark">SE</div>
          <div>
            <small>{copy.operations}</small>
            <strong>{copy.title}</strong>
            <span>{copy.subtitle}</span>
          </div>
        </div>

        <nav className="servicios-nav" aria-label={copy.panel}>
          {MENU.map(group => (
            <div className="servicios-nav-group" key={group.label}>
              <p>{group.label}</p>
              {group.items.map(([id, text, icon]) => (
                <button type="button" key={id} className={active === id ? "is-active" : ""} onClick={() => setActive(id)}>
                  <span className="servicios-nav-icon">{icon}</span>
                  <span>{text}</span>
                  {id === "alumnos" && <b>{datos.resumen.total || 0}</b>}
                  {id === "inscripciones" && <b>{inscripciones.length}</b>}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="servicios-sidebar-note">
          <strong>{copy.role}</strong>
          <span>{copy.roleText}</span>
        </div>

        <button type="button" className="servicios-logout" onClick={() => onLogout(copy.messages.logout)}>{copy.logout}</button>
      </aside>

      <main className="servicios-main">
        <header className="servicios-heading">
          <div>
            <span>{copy.title.toUpperCase()}</span>
            <h1>{label}</h1>
            <p>{copy.common.institutionalManagement}</p>
          </div>
          <button type="button" className="btn-secondary" onClick={() => cargar()}>{copy.refresh}</button>
        </header>
        {message && <div className="api-success" role="status">{message}</div>}
        {error && <div className="api-error" role="alert">{error}<button type="button" className="link-btn" onClick={() => setError("")}>{copy.common.close}</button></div>}
        {loading && !datos.alumnos.length ? <div className="servicios-empty-card">{copy.loading}</div> : contenido()}
      </main>
    </section>
  );
}
