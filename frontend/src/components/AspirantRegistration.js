import React, {useMemo, useState} from 'react';

const DRAFT_KEY = 'sinac_preregistro_draft_v2';
const DEPARTAMENTOS = ['Biología Celular','Biomedicina Molecular','Bioquímica','Biotecnología y Bioingeniería','Computación','Control Automático','Farmacología','Física','Fisiología, Biofísica y Neurociencias','Genética y Biología Molecular','Infectómica y Patogénesis Molecular','Ingeniería Eléctrica','Investigación y Estudios Multidisciplinarios','Matemática Educativa','Matemáticas','Química','Toxicología'];
const PROGRAMAS = ['Maestría — Teoría de la Computación (2 años)','Maestría — Inteligencia Artificial (2 años)','Maestría — Sistemas de Cómputo (2 años)','Maestría — Sistemas de Información (2 años)','Maestría — Ciencias de la Computación (2 años)','Doctorado — Teoría de la Computación (4 años)','Doctorado — Inteligencia Artificial (4 años)','Doctorado — Sistemas de Cómputo (4 años)','Doctorado — Sistemas de Información (4 años)','Doctorado — Ciencias de la Computación (4 años)'];
const SECCIONES = Array.from({length:65},(_,i)=>String(i+1));

const initialForm = {
  nombre: '', usuario: '', curp: '', correo: '', telefono: '', nacimiento: '',
  password: '', passwordConfirm: '',
  estadoActual: '', municipioActual: '', direccionActual: '',
  estadoPermanente: '', municipioPermanente: '', direccionPermanente: '',
  nombreFamiliar: '', parentesco: '', telefonoFamiliar: '',
  ultimoGrado: '', institucion: '', promedio: '',
  idiomas: '', publicaciones: '', apoyos: '', experiencia: '',
  unidad: '', departamento: '', seccion: '', programa: '', modalidad: 'Presencial',
  tutorPropuesto: '', comentarios: ''
};

const requiredFields = [
  'nombre', 'usuario', 'curp', 'correo', 'telefono', 'nacimiento', 'password', 'passwordConfirm',
  'estadoActual', 'municipioActual', 'direccionActual',
  'estadoPermanente', 'municipioPermanente', 'direccionPermanente',
  'nombreFamiliar', 'parentesco', 'telefonoFamiliar',
  'ultimoGrado', 'institucion', 'promedio',
  'unidad', 'departamento', 'seccion', 'programa', 'modalidad'
];

const sectionDefs = [
  {id: 'generales',          title: '1. Datos Generales',         required: ['nombre','usuario','curp','correo','telefono','nacimiento']},
  {id: 'domicilioActual',    title: '2. Domicilio Actual',         required: ['estadoActual','municipioActual','direccionActual']},
  {id: 'domicilioPermanente',title: '3. Domicilio Permanente',     required: ['estadoPermanente','municipioPermanente','direccionPermanente']},
  {id: 'familiar',           title: '4. Datos de un Familiar',    required: ['nombreFamiliar','parentesco','telefonoFamiliar']},
  {id: 'escolaridad',        title: '5. Escolaridad',              required: ['ultimoGrado','institucion','promedio']},
  {id: 'idiomas',            title: '6. Idiomas',                  required: []},
  {id: 'publicaciones',      title: '7. Publicaciones',            required: []},
  {id: 'apoyos',             title: '8. Apoyos',                   required: []},
  {id: 'experiencia',        title: '9. Experiencia Profesional',  required: []},
  {id: 'cinvestav',          title: '10. Cinvestav',               required: ['unidad','departamento','seccion','programa','modalidad']},
  {id: 'adscripcion',        title: '11. Adscripción',             required: []},
];

function getDraft(){
  try { return JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null'); } catch { return null; }
}
function saveDraft(f){ try { localStorage.setItem(DRAFT_KEY, JSON.stringify(f)); } catch {} }
function clearDraft(){ try { localStorage.removeItem(DRAFT_KEY); } catch {} }

/* badge: checks / total required in this section */
function SectionBadge({def, form, errors}){
  const hasErr = def.required.some(f => errors[f]);
  const done   = def.required.filter(f => `${form[f]||''}`.trim()).length;
  const total  = def.required.length;
  if (total === 0) return null;
  if (hasErr) return <span className="sec-badge sec-badge--err">!</span>;
  if (done === total) return <span className="sec-badge sec-badge--ok">✓</span>;
  return <span className="sec-badge sec-badge--partial">{done}/{total}</span>;
}

function Field({label, req, error, children}){
  return (
    <label className="af-label">
      <span className="af-label-text">{label}{req && <em> *</em>}</span>
      {children}
      {error && <span className="field-error">{error}</span>}
    </label>
  );
}

export default function AspirantRegistration(){
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [form, setForm]           = useState(() => ({...initialForm, ...(getDraft()||{})}));
  const [submitted, setSubmitted]  = useState(false);
  const [submitData, setSubmitData] = useState(null);
  const [errors, setErrors]        = useState({});
  const [apiError, setApiError]    = useState('');
  const [sending, setSending]      = useState(false);
  const [activeId, setActiveId]    = useState('generales');

  const completion = useMemo(() => {
    const done = requiredFields.filter(f => `${form[f]||''}`.trim()).length;
    return Math.round((done / requiredFields.length) * 100);
  }, [form]);

  const lidaPacket = useMemo(() => ({
    processDefinitionKey: 'sinac_preregistro_v1',
    businessKey: `PREREG-${(form.curp||'SINCURP').toUpperCase()}-${(form.programa||'BASE').replace(/\s+/g,'').toUpperCase()}`,
    camundaStartEvent: 'StartPreregistro',
    payload: form,
  }), [form]);

  function selectSection(id){ setActiveId(id); }

  function handleChange(e){
    const {name, value} = e.target;
    const next = (name==='curp'||name==='usuario') ? value.toUpperCase().replace(/\s+/g,'') : value;
    setForm(prev => { const u={...prev,[name]:next}; saveDraft(u); return u; });
  }

  function validate(){
    const errs = {};
    requiredFields.forEach(f => { if(!`${form[f]||''}`.trim()) errs[f]='Obligatorio.'; });
    if(form.curp && !/^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$/.test(form.curp)) errs.curp='CURP no válida (18 caracteres, formato oficial).';
    if(form.correo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.correo)) errs.correo='Correo no válido.';
    if(form.password && form.password.length < 8) errs.password='Mínimo 8 caracteres.';
    if(form.password !== form.passwordConfirm) errs.passwordConfirm='Las contraseñas no coinciden.';
    setErrors(errs);
    const errSec = sectionDefs.find(s => s.required.some(f => errs[f]));
    if(errSec) setActiveId(errSec.id);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit(e){
    e.preventDefault();
    if(!validate()) return;
    setSending(true);
    setApiError('');
    const payload = {
      nombre: form.nombre, usuario: form.usuario, curp: form.curp,
      correo: form.correo, telefono: form.telefono, nacimiento: form.nacimiento,
      password: form.password,
      estado_actual: form.estadoActual, municipio_actual: form.municipioActual,
      direccion_actual: form.direccionActual,
      estado_permanente: form.estadoPermanente, municipio_permanente: form.municipioPermanente,
      direccion_permanente: form.direccionPermanente,
      nombre_familiar: form.nombreFamiliar, parentesco: form.parentesco,
      telefono_familiar: form.telefonoFamiliar,
      ultimo_grado: form.ultimoGrado, institucion: form.institucion, promedio: form.promedio,
      idiomas: form.idiomas, publicaciones: form.publicaciones,
      apoyos: form.apoyos, experiencia: form.experiencia,
      unidad: form.unidad, departamento: form.departamento, seccion: form.seccion,
      programa: form.programa, modalidad: form.modalidad,
      tutor_propuesto: form.tutorPropuesto, comentarios: form.comentarios,
    };
    try {
      const res = await fetch('/api/preregistro/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        const serverErrors = data && typeof data === 'object' ? data : {};
        const fieldErrors = Object.entries(serverErrors).reduce((acc, [key, value]) => {
          const messages = Array.isArray(value) ? value : [value];
          acc[key] = messages.flatMap((item) => String(item).split('.').filter(Boolean)).join(' ');
          return acc;
        }, {});
        setErrors(prev => ({...prev, ...fieldErrors}));
        const msg = Object.values(fieldErrors).join(' ') || Object.values(serverErrors).flat().join(' ');
        setApiError(msg || 'Error al enviar el pre-registro.');
        setSending(false);
        return;
      }
      setSubmitData(data);
      setSubmitted(true);
      clearDraft();
    } catch {
      setApiError('No se pudo conectar con el servidor. Verifica tu conexión.');
    }
    setSending(false);
  }

  if(submitted){
    return (
      <section id="portal-aspirantes" className="registration-section">
        <div className="success-box" style={{maxWidth:760,margin:'40px auto'}}>
          <h3>✅ Pre-registro enviado correctamente</h3>
          <p>Tu solicitud fue recibida. Guarda estos datos para acceder al sistema.</p>
          {submitData && (
            <div className="success-detail">
              <div><strong>Business Key:</strong> {submitData.business_key}</div>
              <div><strong>Estado LIDA:</strong> {submitData.proceso_estado}</div>
              {submitData.camunda_id && <div><strong>Instancia Camunda:</strong> {submitData.camunda_id}</div>}
              <div style={{marginTop:10,fontSize:'.88rem',color:'var(--muted)'}}>Guarda tu usuario y contraseña para iniciar sesión como Aspirante.</div>
            </div>
          )}
        </div>
      </section>
    );
  }

  if(!privacyAccepted){
    return (
      <section className="registration-privacy-gate" aria-labelledby="privacy-gate-title">
        <div className="registration-privacy-card">
          <div className="privacy-gate-icon" aria-hidden="true">✓</div>
          <span className="privacy-gate-kicker">PORTAL DE ASPIRANTES · SINAC NEXT</span>
          <h1 id="privacy-gate-title">Antes de comenzar</h1>
          <p>Si tienes dudas sobre la información que vas a capturar a continuación, te invitamos a consultar nuestro <strong>Aviso de Privacidad</strong>, disponible en el pie de página.</p>
          <div className="privacy-gate-note"><span aria-hidden="true">i</span><span>La información proporcionada será utilizada para gestionar tu proceso de registro y admisión.</span></div>
          <button type="button" className="privacy-gate-accept" onClick={() => setPrivacyAccepted(true)}>Aceptar y continuar</button>
        </div>
      </section>
    );
  }

  const activeDef = sectionDefs.find(s => s.id === activeId);

  function renderPanel(){
    switch(activeId){
      case 'generales': return (
        <div className="cf-grid">
          <Field label="Nombre completo" req error={errors.nombre}><input name="nombre" value={form.nombre} onChange={handleChange}/></Field>
          <Field label="Usuario" req error={errors.usuario}><input name="usuario" value={form.usuario} onChange={handleChange} maxLength="20"/></Field>
          <Field label="CURP" req error={errors.curp}><input name="curp" value={form.curp} onChange={handleChange} maxLength="18" placeholder="18 caracteres"/></Field>
          <Field label="Correo electrónico" req error={errors.correo}><input name="correo" type="email" value={form.correo} onChange={handleChange}/></Field>
          <Field label="Teléfono / celular" req error={errors.telefono}><input name="telefono" type="tel" value={form.telefono} onChange={handleChange}/></Field>
          <Field label="Fecha de nacimiento" req error={errors.nacimiento}><input name="nacimiento" type="date" value={form.nacimiento} onChange={handleChange}/></Field>
          <Field label="Contraseña" req error={errors.password}><input name="password" type="password" value={form.password} onChange={handleChange} placeholder="Mínimo 8 caracteres"/></Field>
          <Field label="Confirmar contraseña" req error={errors.passwordConfirm}><input name="passwordConfirm" type="password" value={form.passwordConfirm} onChange={handleChange}/></Field>
        </div>
      );
      case 'domicilioActual': return (
        <div className="cf-grid">
          <Field label="Estado" req error={errors.estadoActual}><input name="estadoActual" value={form.estadoActual} onChange={handleChange}/></Field>
          <Field label="Municipio" req error={errors.municipioActual}><input name="municipioActual" value={form.municipioActual} onChange={handleChange}/></Field>
          <Field label="Dirección" req error={errors.direccionActual}><input name="direccionActual" value={form.direccionActual} onChange={handleChange} className="cf-full"/></Field>
        </div>
      );
      case 'domicilioPermanente': return (
        <div className="cf-grid">
          <Field label="Estado" req error={errors.estadoPermanente}><input name="estadoPermanente" value={form.estadoPermanente} onChange={handleChange}/></Field>
          <Field label="Municipio" req error={errors.municipioPermanente}><input name="municipioPermanente" value={form.municipioPermanente} onChange={handleChange}/></Field>
          <Field label="Dirección" req error={errors.direccionPermanente}><input name="direccionPermanente" value={form.direccionPermanente} onChange={handleChange} className="cf-full"/></Field>
        </div>
      );
      case 'familiar': return (
        <div className="cf-grid">
          <Field label="Nombre" req error={errors.nombreFamiliar}><input name="nombreFamiliar" value={form.nombreFamiliar} onChange={handleChange}/></Field>
          <Field label="Parentesco" req error={errors.parentesco}><input name="parentesco" value={form.parentesco} onChange={handleChange}/></Field>
          <Field label="Teléfono" req error={errors.telefonoFamiliar}><input name="telefonoFamiliar" type="tel" value={form.telefonoFamiliar} onChange={handleChange}/></Field>
        </div>
      );
      case 'escolaridad': return (
        <div className="cf-grid">
          <Field label="Último grado" req error={errors.ultimoGrado}><input name="ultimoGrado" value={form.ultimoGrado} onChange={handleChange}/></Field>
          <Field label="Institución" req error={errors.institucion}><input name="institucion" value={form.institucion} onChange={handleChange}/></Field>
          <Field label="Promedio" req error={errors.promedio}><input name="promedio" value={form.promedio} onChange={handleChange} placeholder="ej. 9.5"/></Field>
        </div>
      );
      case 'idiomas': return (
        <label className="af-label af-label--full">
          <span className="af-label-text">Idiomas que dominas</span>
          <textarea name="idiomas" rows="4" value={form.idiomas} onChange={handleChange} placeholder="Inglés – Avanzado, Francés – Intermedio…"/>
        </label>
      );
      case 'publicaciones': return (
        <label className="af-label af-label--full">
          <span className="af-label-text">Publicaciones (artículos, libros, etc.)</span>
          <textarea name="publicaciones" rows="4" value={form.publicaciones} onChange={handleChange}/>
        </label>
      );
      case 'apoyos': return (
        <label className="af-label af-label--full">
          <span className="af-label-text">Becas o apoyos recibidos</span>
          <textarea name="apoyos" rows="4" value={form.apoyos} onChange={handleChange}/>
        </label>
      );
      case 'experiencia': return (
        <label className="af-label af-label--full">
          <span className="af-label-text">Experiencia laboral o de investigación</span>
          <textarea name="experiencia" rows="5" value={form.experiencia} onChange={handleChange}/>
        </label>
      );
      case 'cinvestav': return (
        <div className="cf-grid">
          <Field label="Unidad" req error={errors.unidad}><select name="unidad" value={form.unidad} onChange={handleChange}><option value="">Selecciona unidad</option><option value="Zacatenco">Zacatenco</option></select></Field>
          <Field label="Departamento" req error={errors.departamento}><select name="departamento" value={form.departamento} onChange={handleChange}><option value="">Selecciona departamento</option>{DEPARTAMENTOS.map(x=><option key={x}>{x}</option>)}</select></Field>
          <Field label="Sección" req error={errors.seccion}><select name="seccion" value={form.seccion} onChange={handleChange}><option value="">Selecciona sección</option>{SECCIONES.map(x=><option key={x}>{x}</option>)}</select><small>Para conocer la sección consulta el croquis de Cinvestav Zacatenco.</small></Field>
          <Field label="Programa de interés" req error={errors.programa}><select name="programa" value={form.programa} onChange={handleChange}><option value="">Selecciona programa</option>{PROGRAMAS.map(x=><option key={x}>{x}</option>)}</select></Field>
          <Field label="Modalidad" req error={errors.modalidad}>
            <select name="modalidad" value={form.modalidad} onChange={handleChange}>
              <option>Presencial</option><option>Híbrida</option><option>En línea</option>
            </select>
          </Field>
        </div>
      );
      case 'adscripcion': return (
        <div className="cf-grid">
          <Field label="Tutor propuesto"><input name="tutorPropuesto" value={form.tutorPropuesto} onChange={handleChange}/></Field>
          <label className="af-label af-label--full">
            <span className="af-label-text">Comentarios</span>
            <textarea name="comentarios" rows="4" value={form.comentarios} onChange={handleChange}/>
          </label>
        </div>
      );
      default: return null;
    }
  }

  return (
    <section id="portal-aspirantes" className="registration-section">
      <div className="registration-hero">
        <div>
          <h1>Portal de Pre-registro SINAC</h1>
          <p>Selecciona una sección del menú izquierdo para completarla.</p>
        </div>
        <div className="progress-outer" title={`${completion}% completado`}>
          <div className="progress-inner" style={{width:`${completion}%`}}/>
          <span className="progress-label">{completion}%</span>
        </div>
      </div>

      <form className="sb-form" onSubmit={handleSubmit} noValidate>
        {/* sidebar */}
        <nav className="sb-nav" aria-label="Secciones del formulario">
          {sectionDefs.map(def => (
            <button
              key={def.id}
              type="button"
              className={`sb-item${activeId===def.id?' sb-item--active':''}`}
              onClick={()=>selectSection(def.id)}
            >
              <span className="sb-item-title">{def.title}</span>
              <SectionBadge def={def} form={form} errors={errors}/>
            </button>
          ))}
        </nav>

        {/* panel */}
        <div className="sb-panel">
          <div className="sb-panel-header">
            <h2>{activeDef?.title}</h2>
            {activeDef?.required.length > 0 && (
              <span className="sb-required-note">* campos obligatorios</span>
            )}
          </div>
          <div className="sb-panel-body">
            {renderPanel()}
          </div>
          <div className="sb-panel-footer">
            <div className="lida-panel">
              <strong>LIDA</strong>
              <span style={{marginLeft:10,fontSize:'.85rem',color:'var(--muted)'}}>{lidaPacket.businessKey}</span>
            </div>
            {apiError && <div className="api-error">{apiError}</div>}
            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={sending}>
                {sending ? 'Enviando...' : 'Enviar pre-registro'}
              </button>
            </div>
          </div>
        </div>
      </form>
    </section>
  );
}
