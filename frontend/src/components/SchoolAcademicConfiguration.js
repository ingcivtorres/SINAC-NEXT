import React, {useEffect, useState} from "react";
import {PROGRAMAS, gradoDePrograma} from "./programasCatalogo";
import {useCoordinationCopy} from "./coordinationPanelTranslations";

const predeterminados = (grado, periodicidad) => (grado === "doctorado" ? 4 : 2) * (periodicidad === "cuatrimestral" ? 3 : 2);

function nuevoPlan() {
  return {
    id: null,
    programa: "",
    grado: "maestria",
    periodicidad: "semestral",
    periodos_requeridos: predeterminados("maestria", "semestral"),
    creditos_requeridos: 0,
    activo: true,
    materias_plan: [],
  };
}

function fechaLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export default function SchoolAcademicConfiguration({section, session, onLogout}) {
  const copy = useCoordinationCopy();
  const [periodos, setPeriodos] = useState([]);
  const [periodoForm, setPeriodoForm] = useState({id: null, nombre: "", apertura: "", cierre: "", activo: true});
  const [planes, setPlanes] = useState([]);
  const [materias, setMaterias] = useState([]);
  const [planForm, setPlanForm] = useState(nuevoPlan);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const endpoint = section === "periodos" ? "/api/periodos-inscripcion/?todos=1" : "/api/tesis/flujo/";
    fetch(endpoint, {headers: {Authorization: `Bearer ${session.access}`}, signal: controller.signal})
      .then(async response => {
        if (response.status === 401) {
          onLogout(copy.messages.expired);
          throw Object.assign(new Error(), {name: "AbortError"});
        }
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || (section === "periodos" ? copy.periods.createError : copy.plans.loadError));
        return body;
      })
      .then(body => {
        if (section === "periodos") {
          const lista = Array.isArray(body) ? body : [];
          setPeriodos(lista);
          if (lista.length) seleccionarPeriodo(lista[0]);
        } else {
          const lista = body.configuraciones || [];
          setPlanes(lista);
          setMaterias(body.materias || []);
          if (lista.length) seleccionarPlan(lista[0]);
        }
      })
      .catch(err => { if (err.name !== "AbortError") setError(err.message); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [copy.messages.expired, copy.periods.createError, copy.plans.loadError, onLogout, section, session.access]);

  function seleccionarPeriodo(periodo) {
    setPeriodoForm({
      id: periodo.id,
      nombre: periodo.nombre || "",
      apertura: fechaLocal(periodo.apertura),
      cierre: fechaLocal(periodo.cierre),
      activo: periodo.habilitado ?? periodo.activo,
    });
    setError("");
    setSuccess("");
  }

  function seleccionarPlan(plan) {
    setPlanForm({
      id: plan.id,
      programa: plan.programa || "",
      grado: plan.grado || "maestria",
      periodicidad: plan.periodicidad || "semestral",
      periodos_requeridos: plan.periodos_requeridos || 1,
      creditos_requeridos: plan.creditos_requeridos || 0,
      activo: Boolean(plan.activo),
      materias_plan: (plan.materias_plan || []).map(item => ({...item, slotId: `plan-${item.id}`})),
    });
    setError("");
    setSuccess("");
  }

  function cambiarDuracion(cambios) {
    setPlanForm(current => {
      const grado = cambios.grado || current.grado;
      const periodicidad = cambios.periodicidad || current.periodicidad;
      const periodos = Number(current.periodos_requeridos) === predeterminados(current.grado, current.periodicidad)
        ? predeterminados(grado, periodicidad)
        : Number(current.periodos_requeridos);
      return {
        ...current,
        ...cambios,
        periodos_requeridos: periodos,
        materias_plan: current.materias_plan.filter(item => Number(item.periodo_sugerido) <= periodos),
      };
    });
  }

  function prepararMateriasMinimas() {
    setPlanForm(current => {
      const filas = [...current.materias_plan];
      const cantidadPeriodos = Math.max(1, Number(current.periodos_requeridos) || 1);
      for (let periodo = 1; periodo <= cantidadPeriodos; periodo += 1) {
        const existentes = filas.filter(item => Number(item.periodo_sugerido) === periodo).length;
        for (let indice = existentes; indice < 4; indice += 1) {
          filas.push({slotId: `nuevo-${periodo}-${indice}-${Date.now()}-${Math.random()}`, materia: "", periodo_sugerido: periodo, obligatoria: true});
        }
      }
      return {...current, materias_plan: filas};
    });
  }

  async function guardarPeriodo(event) {
    event.preventDefault();
    if (saving) return;
    const editando = Boolean(periodoForm.id);
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const response = await fetch("/api/periodos-inscripcion/", {
        method: editando ? "PUT" : "POST",
        headers: {Authorization: `Bearer ${session.access}`, "Content-Type": "application/json"},
        body: JSON.stringify(periodoForm),
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (!response.ok) throw new Error(body.detail || copy.periods.createError);
      setPeriodos(previous => previous.some(item => item.id === body.id)
        ? previous.map(item => item.id === body.id ? body : item)
        : [body, ...previous]);
      seleccionarPeriodo(body);
      setSuccess(editando ? copy.periods.updated : copy.periods.saved);
    } catch (err) {
      setError(err.message || copy.periods.createError);
    } finally {
      setSaving(false);
    }
  }

  async function guardarPlan(event) {
    event.preventDefault();
    if (saving) return;
    const periodosRequeridos = Number(planForm.periodos_requeridos);
    const filas = planForm.materias_plan.filter(item => item.materia !== "" && item.materia != null);
    const cuentaPorPeriodo = Array.from({length: periodosRequeridos}, (_, index) =>
      filas.filter(item => Number(item.periodo_sugerido) === index + 1).length,
    );
    if (!planForm.programa.trim()) return setError(copy.plans.programRequired);
    if (!periodosRequeridos || periodosRequeridos < 1) return setError(copy.plans.periodsRequired);
    if (new Set(filas.map(item => Number(item.materia))).size !== filas.length) return setError(copy.plans.duplicateCourse);
    if (cuentaPorPeriodo.some(count => count < 4)) return setError(copy.plans.minimumFour);
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const response = await fetch("/api/tesis/flujo/", {
        method: "POST",
        headers: {Authorization: `Bearer ${session.access}`, "Content-Type": "application/json"},
        body: JSON.stringify({
          ...planForm,
          periodos_requeridos: periodosRequeridos,
          creditos_requeridos: Number(planForm.creditos_requeridos) || 0,
          materias_plan: filas.map(({materia, periodo_sugerido, obligatoria}) => ({
            materia: Number(materia),
            periodo_sugerido: Number(periodo_sugerido),
            obligatoria: Boolean(obligatoria),
          })),
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 401) return onLogout(copy.messages.expired);
      if (!response.ok) throw new Error(body.detail || copy.plans.saveError);
      setPlanes(previous => previous.some(item => item.id === body.id)
        ? previous.map(item => item.id === body.id ? body : item)
        : [...previous, body].sort((a, b) => a.programa.localeCompare(b.programa)));
      seleccionarPlan(body);
      setSuccess(copy.plans.saved);
    } catch (err) {
      setError(err.message || copy.plans.saveError);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="servicios-empty-card">{copy.loading}</div>;

  if (section === "periodos") {
    return (
      <section className="servicios-card">
        <div className="servicios-card-heading">
          <div><span className="panel-kicker">{copy.periods.kicker}</span><h3>{copy.periods.title}</h3><p>{copy.periods.intro}</p></div>
          <button type="button" className="btn-secondary" onClick={() => setPeriodoForm({id: null, nombre: "", apertura: "", cierre: "", activo: true})}>{copy.periods.createNew}</button>
        </div>
        {periodos.length > 0 && <label>{copy.periods.selectExisting}
          <select value={periodoForm.id || ""} onChange={event => {
            const seleccionado = periodos.find(item => String(item.id) === event.target.value);
            if (seleccionado) seleccionarPeriodo(seleccionado);
          }}>
            <option value="">{copy.periods.createNew}</option>
            {periodos.map(item => <option key={item.id} value={item.id}>{item.nombre}</option>)}
          </select>
        </label>}
        <form className="servicios-form" onSubmit={guardarPeriodo}>
          <div className="servicios-form-grid">
            <label>{copy.periods.name}<input maxLength="40" required value={periodoForm.nombre} onChange={event => setPeriodoForm({...periodoForm, nombre: event.target.value})}/></label>
            <label>{copy.periods.opening}<input type="datetime-local" required value={periodoForm.apertura} onChange={event => setPeriodoForm({...periodoForm, apertura: event.target.value})}/></label>
            <label>{copy.periods.closing}<input type="datetime-local" required value={periodoForm.cierre} onChange={event => setPeriodoForm({...periodoForm, cierre: event.target.value})}/></label>
            <label>{copy.periods.enabled}<select value={periodoForm.activo ? "true" : "false"} onChange={event => setPeriodoForm({...periodoForm, activo: event.target.value === "true"})}><option value="true">{copy.periods.yes}</option><option value="false">{copy.periods.no}</option></select></label>
          </div>
          <button type="submit" className="btn-primary" disabled={saving}>{saving ? copy.periods.saving : periodoForm.id ? copy.periods.update : copy.periods.save}</button>
        </form>
        {error && <div className="api-error" role="alert">{error}</div>}
        {success && <div className="api-success" role="status">{success}</div>}
      </section>
    );
  }

  return (
    <section className="servicios-card">
      <div className="servicios-card-heading">
        <div><span className="panel-kicker">{copy.plans.title}</span><h3>{copy.plans.intro}</h3></div>
        <button type="button" className="btn-secondary" onClick={() => setPlanForm(nuevoPlan())}>{copy.plans.new}</button>
      </div>
      {planes.length > 0 && <label>{copy.plans.choose}
        <select value={planForm.id || ""} onChange={event => {
          const seleccionado = planes.find(item => String(item.id) === event.target.value);
          if (seleccionado) seleccionarPlan(seleccionado);
          else setPlanForm(nuevoPlan());
        }}>
          <option value="">{copy.plans.new}</option>
          {planes.map(item => <option key={item.id} value={item.id}>{item.programa} · {item.grado_label}</option>)}
        </select>
      </label>}
      {materias.length === 0 && <p className="servicios-muted">{copy.plans.catalogEmpty}</p>}
      <form className="servicios-form" onSubmit={guardarPlan}>
        <div className="servicios-form-grid">
          <label>{copy.plans.program}<select required value={planForm.programa} onChange={event => {
            const programa = event.target.value;
            setPlanForm(current => ({...current, programa}));
            if (programa) cambiarDuracion({grado: gradoDePrograma(programa)});
          }}>
            <option value="">—</option>
            {planForm.programa && !PROGRAMAS.includes(planForm.programa) && <option value={planForm.programa}>{planForm.programa}</option>}
            {PROGRAMAS.map(item => <option key={item} value={item}>{item}</option>)}
          </select></label>
          <label>{copy.plans.degree}<select value={planForm.grado} onChange={event => cambiarDuracion({grado: event.target.value})}><option value="maestria">{copy.plans.masters}</option><option value="doctorado">{copy.plans.doctorate}</option></select></label>
          <label>{copy.plans.periodicity}<select value={planForm.periodicidad} onChange={event => cambiarDuracion({periodicidad: event.target.value})}><option value="semestral">{copy.plans.semesters}</option><option value="cuatrimestral">{copy.plans.quarters}</option></select></label>
          <label>{copy.plans.periods}<input type="number" min="1" max="24" required value={planForm.periodos_requeridos} onChange={event => {
            const count = Number(event.target.value);
            setPlanForm(current => ({...current, periodos_requeridos: count, materias_plan: current.materias_plan.filter(item => Number(item.periodo_sugerido) <= count)}));
          }}/></label>
          <label>{copy.plans.credits}<input type="number" min="0" value={planForm.creditos_requeridos} onChange={event => setPlanForm({...planForm, creditos_requeridos: Number(event.target.value)})}/></label>
          <label>{copy.plans.active}<select value={planForm.activo ? "true" : "false"} onChange={event => setPlanForm({...planForm, activo: event.target.value === "true"})}><option value="true">{copy.periods.yes}</option><option value="false">{copy.periods.no}</option></select></label>
        </div>
        <div className="servicios-card-heading">
          <div><h4>{copy.plans.courses}</h4><p>{copy.plans.minimumFour}</p></div>
          <button type="button" className="btn-secondary" disabled={!materias.length} onClick={prepararMateriasMinimas}>{copy.plans.generateSlots}</button>
        </div>
        {planForm.materias_plan.map((item, index) => (
          <div className="coord-plan-course-row" key={item.slotId || item.id || index}>
            <label>{copy.plans.course}<select value={item.materia || ""} onChange={event => setPlanForm(current => ({
              ...current,
              materias_plan: current.materias_plan.map((row, rowIndex) => rowIndex === index ? {...row, materia: event.target.value} : row),
            }))}>
              <option value="">{copy.subjects.subject}</option>
              {materias.map(materia => <option key={materia.id} value={materia.id} disabled={planForm.materias_plan.some((row, rowIndex) => rowIndex !== index && Number(row.materia) === materia.id)}>{materia.clave} · {materia.nombre}</option>)}
            </select></label>
            <label>{copy.plans.suggestedPeriod}<select value={item.periodo_sugerido || 1} onChange={event => setPlanForm(current => ({
              ...current,
              materias_plan: current.materias_plan.map((row, rowIndex) => rowIndex === index ? {...row, periodo_sugerido: Number(event.target.value)} : row),
            }))}>
              {Array.from({length: Math.max(1, Number(planForm.periodos_requeridos) || 1)}, (_, periodo) => <option key={periodo + 1} value={periodo + 1}>{periodo + 1}</option>)}
            </select></label>
            <label><input type="checkbox" checked={Boolean(item.obligatoria)} onChange={event => setPlanForm(current => ({
              ...current,
              materias_plan: current.materias_plan.map((row, rowIndex) => rowIndex === index ? {...row, obligatoria: event.target.checked} : row),
            }))}/>{copy.plans.mandatory}</label>
            <button type="button" className="btn-secondary" onClick={() => setPlanForm(current => ({...current, materias_plan: current.materias_plan.filter((_, rowIndex) => rowIndex !== index)}))}>{copy.plans.remove}</button>
          </div>
        ))}
        <div className="servicios-row-actions">
          <button type="button" className="btn-secondary" disabled={!materias.length} onClick={() => setPlanForm(current => ({
            ...current,
            materias_plan: [...current.materias_plan, {slotId: `manual-${Date.now()}-${Math.random()}`, materia: "", periodo_sugerido: 1, obligatoria: true}],
          }))}>{copy.plans.addCourse}</button>
          <button type="submit" className="btn-primary" disabled={saving || !materias.length}>{saving ? copy.plans.saving : copy.plans.save}</button>
        </div>
      </form>
      {error && <div className="api-error" role="alert">{error}</div>}
      {success && <div className="api-success" role="status">{success}</div>}
    </section>
  );
}
