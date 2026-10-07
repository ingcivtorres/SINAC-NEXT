import React, {useEffect, useMemo, useRef, useState} from "react";
import ExpedienteCentralizadoCard from "./ExpedienteCentralizadoCard";
import {useSchoolServicesCopy} from "./schoolServicesPanelTranslations";

const buildMenu = (copy) => [
  {label: copy.groups.panorama, items: [["resumen", copy.menu.resumen, "▦"], ["alumnos", copy.menu.alumnos, "♙"]]},
  {label: copy.groups.academicControl, items: [["inscripciones", copy.menu.inscripciones, "◫"], ["historial", copy.menu.historial, "▤"], ["calificaciones", copy.menu.calificaciones, "✓"]]},
  {label: copy.groups.documentation, items: [["constancias", copy.menu.constancias, "▣"], ["egreso", copy.menu.egreso, "◆"]]},
  {label: copy.groups.institutional, items: [["reportes", copy.menu.reportes, "▥"]]},
];

const estadoTexto = (estado, copy) => ({
  activo: copy.status.activo,
  baja: copy.status.baja,
  inactivo: copy.status.inactivo,
  egresado: copy.status.egresado,
  cursando: copy.status.cursando,
  aprobada: copy.status.aprobada,
  reprobada: copy.status.reprobada,
  pendiente: copy.status.pendiente,
  validada: copy.status.validada,
  observada: copy.status.observada,
}[estado] || estado || copy.status.pending);

function fecha(value, incluirHora = false, copy) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(copy.locale, incluirHora ? {dateStyle: "short", timeStyle: "short"} : {dateStyle: "medium"}).format(new Date(value));
}

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
  const [alta, setAlta] = useState({nombre: "", usuario: "", correo: "", curp: "", password: "", telefono: "", matricula: "", programa: "", departamento: ""});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const cargaId = useRef(0);

  const headers = useMemo(() => ({Authorization: `Bearer ${session.access}`}), [session.access]);
  const alumno = useMemo(() => datos.alumnos.find(item => item.id === selectedId) || null, [datos.alumnos, selectedId]);
  const inscripciones = useMemo(() => datos.alumnos.flatMap(item => (item.inscripciones || []).map(inscripcion => ({...inscripcion, alumno: item}))), [datos.alumnos]);

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
      .then(response => response.ok ? response.json() : Promise.reject(new Error(copy.messages.loadReports)))
      .then(data => setReportes(data))
      .catch(err => { if (err.name !== "AbortError") setError(err.message); });
    return () => controller.abort();
  }, [active, session.access]);

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
    if (!alumno || !formAlumno) return;
    setError("");
    try {
      const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/`, {method: "PATCH", headers: {...headers, "Content-Type": "application/json"}, body: JSON.stringify(formAlumno)});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.dataSaveError);
      setMessage(copy.messages.movementSaved);
      await cargar();
    } catch (err) { setError(err.message || copy.messages.dataSaveError); }
  }

  async function darDeAlta(event) {
    event.preventDefault();
    try {
      const response = await fetch("/api/servicios-escolares/panel/", {method: "POST", headers: {...headers, "Content-Type": "application/json"}, body: JSON.stringify(alta)});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.studentCreated);
      setAlta({nombre: "", usuario: "", correo: "", curp: "", password: "", telefono: "", matricula: "", programa: "", departamento: ""});
      setAltaAbierta(false);
      setMessage(copy.messages.studentCreated);
      await cargar();
    } catch (err) { setError(err.message || copy.messages.studentCreated); }
  }

  async function registrarMovimiento(event) {
    event.preventDefault();
    if (!alumno || !movimiento.detalle.trim()) return setError(copy.messages.describeMovement);
    try {
      const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/`, {method: "POST", headers: {...headers, "Content-Type": "application/json"}, body: JSON.stringify(movimiento)});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || body.detalle || copy.messages.movementError);
      setMovimiento({estado: "", detalle: ""});
      setMessage(copy.messages.movementSaved);
      await cargar();
    } catch (err) { setError(err.message || copy.messages.movementError); }
  }

  async function validarInscripcion(inscripcionId, validar = true) {
    if (!alumno) return;
    try {
      const response = await fetch(`/api/servicios-escolares/alumnos/${alumno.id}/validar-inscripcion/`, {method: "POST", headers: {...headers, "Content-Type": "application/json"}, body: JSON.stringify({inscripcion_id: inscripcionId, validar})});
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || copy.messages.invalidInscription);
      setMessage(validar ? copy.messages.validInscription : copy.messages.invalidForReview);
      await cargar();
    } catch (err) { setError(err.message || copy.messages.invalidInscription); }
  }

  async function descargar(tipo, id = selectedId) {
    if (!id) return setError(copy.messages.noStudentSelected);
    try {
      const response = await fetch(`/api/servicios-escolares/alumnos/${id}/documentos/${tipo}/`, {headers});
      if (!response.ok) throw new Error(copy.messages.documentError);
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

  const label = buildMenu(copy).flatMap(group => group.items).find(item => item[0] === active)?.[1] || copy.menu.resumen;
  const mostrarDetalle = Boolean(alumno);

  function tablaAlumnos() {
    return (
      <div className="servicios-table-wrap">
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
            {datos.alumnos.length ? datos.alumnos.map(item => (
              <tr key={item.id}>
                <td><strong>{item.nombre}</strong><small>{item.correo}</small></td>
                <td>{item.matricula || copy.common.noEnrollment}</td>
                <td>{item.programa || copy.common.noProgram}</td>
                <td>{item.departamento || copy.common.noDepartment}</td>
                <td><Estado copy={copy} value={item.is_active ? item.proceso_estado || "activo" : "inactivo"} /></td>
                <td><button type="button" className="servicios-link" onClick={() => seleccionar(item)}>{copy.table.consult}</button></td>
              </tr>
            )) : <tr><td colSpan="6" className="servicios-empty">{copy.common.noResults}</td></tr>}
          </tbody>
        </table>
      </div>
    );
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
            <button type="submit" className="btn-primary">{copy.common.save}</button>
          </div>
          <div className="servicios-form-grid">
            <label>{copy.academic.name}<input value={formAlumno?.nombre || ""} onChange={e => setFormAlumno({...formAlumno, nombre: e.target.value})}/></label>
            <label>{copy.academic.matricula}<input value={formAlumno?.matricula || ""} onChange={e => setFormAlumno({...formAlumno, matricula: e.target.value})}/></label>
            <label>{copy.academic.program}<input value={formAlumno?.programa || ""} onChange={e => setFormAlumno({...formAlumno, programa: e.target.value})}/></label>
            <label>{copy.academic.department}<input value={formAlumno?.departamento || ""} onChange={e => setFormAlumno({...formAlumno, departamento: e.target.value})}/></label>
            <label>{copy.academic.email}<input type="email" value={formAlumno?.correo || ""} onChange={e => setFormAlumno({...formAlumno, correo: e.target.value})}/></label>
            <label>{copy.academic.phone}<input value={formAlumno?.telefono || ""} onChange={e => setFormAlumno({...formAlumno, telefono: e.target.value})}/></label>
            <label>{copy.academic.unit}<input value={formAlumno?.unidad || ""} onChange={e => setFormAlumno({...formAlumno, unidad: e.target.value})}/></label>
            <label>{copy.academic.average}<input value={formAlumno?.promedio_academico ?? formAlumno?.promedio ?? ""} onChange={e => setFormAlumno({...formAlumno, promedio_academico: e.target.value})}/></label>
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
                <label>{copy.academic.curp}<input required maxLength="18" value={alta.curp} onChange={e => setAlta({...alta, curp: e.target.value})}/></label>
                <label>{copy.academic.phone}<input value={alta.telefono} onChange={e => setAlta({...alta, telefono: e.target.value})}/></label>
                <label>{copy.academic.matricula}<input value={alta.matricula} onChange={e => setAlta({...alta, matricula: e.target.value})}/></label>
                <label>{copy.academic.program}<input value={alta.programa} onChange={e => setAlta({...alta, programa: e.target.value})}/></label>
                <label>{copy.academic.department}<input value={alta.departamento} onChange={e => setAlta({...alta, departamento: e.target.value})}/></label>
              </div>
              <button type="submit" className="btn-primary">{copy.common.save}</button>
            </form>
          )}
        </>
      );
    }

    if (active === "inscripciones") {
      return (
        <div className="servicios-card">
          <div className="servicios-card-heading">
            <div><span className="panel-kicker">{copy.enrollment.title.toUpperCase()}</span><h3>{alumno ? `${copy.table.viewStudentData} ${alumno.nombre}` : copy.common.registeredStudents}</h3></div>
            {alumno && <button className="btn-secondary" onClick={() => setSelectedId(null)}>{copy.enrollment.review}</button>}
          </div>
          {alumno ? (
            <div className="servicios-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>{copy.table.key}</th>
                    <th>{copy.table.subject}</th>
                    <th>{copy.table.credits}</th>
                    <th>{copy.table.professor}</th>
                    <th>{copy.table.final}</th>
                    <th>{copy.table.status}</th>
                    <th>{copy.table.validation}</th>
                  </tr>
                </thead>
                <tbody>
                  {alumno.inscripciones.length ? alumno.inscripciones.map(item => (
                    <tr key={item.id}>
                      <td>{item.materia_clave}</td>
                      <td>{item.materia_nombre}</td>
                      <td>{item.materia_creditos ?? "—"}</td>
                      <td>{item.materia_profesor || copy.common.registered}</td>
                      <td>{item.calificacion ?? copy.status.pending}</td>
                      <td><Estado copy={copy} value={item.estado}/></td>
                      <td>
                        <div>
                          <Estado copy={copy} value={item.validacion_servicios || "pendiente"}/>
                          <div className="servicios-row-actions">
                            <button type="button" className="servicios-link" onClick={() => validarInscripcion(item.id, true)} disabled={item.validacion_servicios === "validada"}>{copy.table.validate}</button>
                            <button type="button" className="servicios-link" onClick={() => validarInscripcion(item.id, false)} disabled={item.validacion_servicios === "observada"}>{copy.table.observe}</button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )) : <tr><td colSpan="7" className="servicios-empty">{copy.enrollment.noInscriptions}</td></tr>}
                </tbody>
              </table>
            </div>
          ) : <><p className="servicios-muted">{copy.enrollment.selectStudent}</p>{tablaAlumnos()}</>}
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
              <div className="servicios-table-wrap">
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
                    {alumno.inscripciones.length ? alumno.inscripciones.map(item => (
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
          <button type="button" className="btn-secondary" onClick={cargar}>{copy.refresh}</button>
        </header>
        {message && <div className="api-success">{message}</div>}
        {error && <div className="api-error" role="alert">{error}<button type="button" className="link-btn" onClick={() => setError(copy.common.close)}>{copy.common.close}</button></div>}
        {loading && !datos.alumnos.length ? <div className="servicios-empty-card">{copy.loading}</div> : contenido()}
      </main>
    </section>
  );
}
