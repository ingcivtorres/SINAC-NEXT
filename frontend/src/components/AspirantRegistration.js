import React, {useMemo, useState} from 'react';

const DRAFT_KEY = 'sinac_preregistro_draft_v2';

const initialForm = {
  nombre: '',
  usuario: '',
  curp: '',
  correo: '',
  telefono: '',
  nacimiento: '',
  estadoActual: '',
  municipioActual: '',
  direccionActual: '',
  estadoPermanente: '',
  municipioPermanente: '',
  direccionPermanente: '',
  nombreFamiliar: '',
  parentesco: '',
  telefonoFamiliar: '',
  ultimoGrado: '',
  institucion: '',
  promedio: '',
  idiomas: '',
  publicaciones: '',
  apoyos: '',
  experiencia: '',
  unidad: '',
  departamento: '',
  seccion: '',
  programa: '',
  modalidad: 'Presencial',
  tutorPropuesto: '',
  comentarios: ''
};

const requiredFields = [
  'nombre', 'usuario', 'curp', 'correo', 'telefono', 'nacimiento',
  'estadoActual', 'municipioActual', 'direccionActual',
  'estadoPermanente', 'municipioPermanente', 'direccionPermanente',
  'nombreFamiliar', 'parentesco', 'telefonoFamiliar',
  'ultimoGrado', 'institucion', 'promedio',
  'unidad', 'departamento', 'seccion', 'programa', 'modalidad'
];

const sections = [
  {id: 'generales', title: '1. Datos Generales', fields: ['nombre', 'usuario', 'curp', 'correo', 'telefono', 'nacimiento']},
  {id: 'domicilioActual', title: '2. Domicilio Actual', fields: ['estadoActual', 'municipioActual', 'direccionActual']},
  {id: 'domicilioPermanente', title: '3. Domicilio Permanente', fields: ['estadoPermanente', 'municipioPermanente', 'direccionPermanente']},
  {id: 'familiar', title: '4. Datos de un Familiar', fields: ['nombreFamiliar', 'parentesco', 'telefonoFamiliar']},
  {id: 'escolaridad', title: '5. Escolaridad', fields: ['ultimoGrado', 'institucion', 'promedio']},
  {id: 'idiomas', title: '6. Idiomas', fields: ['idiomas']},
  {id: 'publicaciones', title: '7. Publicaciones', fields: ['publicaciones']},
  {id: 'apoyos', title: '8. Apoyos', fields: ['apoyos']},
  {id: 'experiencia', title: '9. Experiencia Profesional', fields: ['experiencia']},
  {id: 'cinvestav', title: '10. Cinvestav', fields: ['unidad', 'departamento', 'seccion', 'programa', 'modalidad']},
  {id: 'adscripcion', title: '11. Adscripción', fields: ['tutorPropuesto', 'comentarios']}
];

function getDraft(){
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function saveDraft(form){
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(form));
  } catch (e) {}
}

function clearDraft(){
  try {
    localStorage.removeItem(DRAFT_KEY);
  } catch (e) {}
}

function formatLabel(name){
  return name
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, c => c.toUpperCase())
    .trim();
}

export default function AspirantRegistration(){
  const [form, setForm] = useState(() => ({...initialForm, ...(getDraft() || {})}));
  const [submitted, setSubmitted] = useState(false);
  const [errors, setErrors] = useState({});

  const completion = useMemo(() => {
    const requiredDone = requiredFields.filter(field => `${form[field] || ''}`.trim() !== '').length;
    return Math.round((requiredDone / requiredFields.length) * 100);
  }, [form]);

  const lidaPacket = useMemo(() => {
    const businessKey = `PREREG-${(form.curp || 'SINCURP').toUpperCase()}-${(form.programa || 'BASE').replace(/\s+/g, '').toUpperCase()}`;
    return {
      processDefinitionKey: 'sinac_preregistro_v1',
      processVersion: '1.0.0',
      businessKey,
      lidaStage: 'modelado-listo',
      lidaSource: 'PortalAspirantes',
      camundaStartEvent: 'StartPreregistro',
      payload: form
    };
  }, [form]);

  function handleChange(e){
    const {name, value} = e.target;
    let next = value;

    if (name === 'curp' || name === 'usuario') {
      next = value.toUpperCase().replace(/\s+/g, '');
    }

    setForm(prev => {
      const updated = {...prev, [name]: next};
      saveDraft(updated);
      return updated;
    });
  }

  function validate(){
    const nextErrors = {};

    requiredFields.forEach(field => {
      if (!`${form[field] || ''}`.trim()) {
        nextErrors[field] = 'Este campo es obligatorio.';
      }
    });

    if (form.curp && !/^[A-Z0-9]{18}$/.test(form.curp)) {
      nextErrors.curp = 'La CURP debe tener 18 caracteres alfanuméricos.';
    }

    if (form.correo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.correo)) {
      nextErrors.correo = 'Ingresa un correo válido.';
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  function handleSubmit(e){
    e.preventDefault();
    if (!validate()) return;
    setSubmitted(true);
    clearDraft();
  }

  return (
    <section id="portal-aspirantes" className="registration-section">
      <div className="registration-hero">
        <div>
          <h1>Portal de Pre-registro SINAC</h1>
          <p>Completa las 11 secciones oficiales del pre-registro. El sistema genera un paquete LIDA compatible con ejecución BPMN en Camunda.</p>
        </div>
        <div className="progress-badge" aria-label="avance del registro">{completion}% completado</div>
      </div>

      <section className="registration-overview">
        <div className="card">
          <h2>Validaciones y flujo LIDA</h2>
          <ul>
            <li>Campos obligatorios como en el manual oficial de Pre-registro.</li>
            <li>Validación de formato de CURP y correo institucional.</li>
            <li>Selección explícita de Unidad, Departamento y Sección.</li>
            <li>Generación de <strong>businessKey</strong> para instanciar workflow en Camunda.</li>
          </ul>
        </div>
      </section>

      <section className="registration-form-section">
        <div className="card form-card">
          <h2>Formulario de pre-registro</h2>

          <div className="section-grid" aria-label="secciones del formulario">
            {sections.map(section => (
              <div key={section.id} className="section-chip">
                {section.title}
              </div>
            ))}
          </div>

          {submitted ? (
            <div className="success-box">
              <h3>Pre-registro enviado correctamente</h3>
              <p>Tu solicitud quedó registrada y está lista para iniciar el proceso en Camunda con la metadata de LIDA.</p>
              <pre className="lida-preview">{JSON.stringify(lidaPacket, null, 2)}</pre>
            </div>
          ) : (
            <form className="aspirant-form" onSubmit={handleSubmit} noValidate>
              <label>
                Nombre completo *
                <input name="nombre" value={form.nombre} onChange={handleChange} />
                {errors.nombre && <span className="field-error">{errors.nombre}</span>}
              </label>

              <label>
                Usuario *
                <input name="usuario" value={form.usuario} onChange={handleChange} maxLength="20" />
                {errors.usuario && <span className="field-error">{errors.usuario}</span>}
              </label>

              <label>
                CURP *
                <input name="curp" value={form.curp} onChange={handleChange} maxLength="18" />
                {errors.curp && <span className="field-error">{errors.curp}</span>}
              </label>

              <label>
                Correo electrónico *
                <input name="correo" type="email" value={form.correo} onChange={handleChange} />
                {errors.correo && <span className="field-error">{errors.correo}</span>}
              </label>

              <label>
                Teléfono / celular *
                <input name="telefono" type="tel" value={form.telefono} onChange={handleChange} />
                {errors.telefono && <span className="field-error">{errors.telefono}</span>}
              </label>

              <label>
                Fecha de nacimiento *
                <input name="nacimiento" type="date" value={form.nacimiento} onChange={handleChange} />
                {errors.nacimiento && <span className="field-error">{errors.nacimiento}</span>}
              </label>

              <label>
                Estado actual *
                <input name="estadoActual" value={form.estadoActual} onChange={handleChange} />
                {errors.estadoActual && <span className="field-error">{errors.estadoActual}</span>}
              </label>

              <label>
                Municipio actual *
                <input name="municipioActual" value={form.municipioActual} onChange={handleChange} />
                {errors.municipioActual && <span className="field-error">{errors.municipioActual}</span>}
              </label>

              <label>
                Dirección actual *
                <input name="direccionActual" value={form.direccionActual} onChange={handleChange} />
                {errors.direccionActual && <span className="field-error">{errors.direccionActual}</span>}
              </label>

              <label>
                Estado permanente *
                <input name="estadoPermanente" value={form.estadoPermanente} onChange={handleChange} />
                {errors.estadoPermanente && <span className="field-error">{errors.estadoPermanente}</span>}
              </label>

              <label>
                Municipio permanente *
                <input name="municipioPermanente" value={form.municipioPermanente} onChange={handleChange} />
                {errors.municipioPermanente && <span className="field-error">{errors.municipioPermanente}</span>}
              </label>

              <label>
                Dirección permanente *
                <input name="direccionPermanente" value={form.direccionPermanente} onChange={handleChange} />
                {errors.direccionPermanente && <span className="field-error">{errors.direccionPermanente}</span>}
              </label>

              <label>
                Nombre de familiar *
                <input name="nombreFamiliar" value={form.nombreFamiliar} onChange={handleChange} />
                {errors.nombreFamiliar && <span className="field-error">{errors.nombreFamiliar}</span>}
              </label>

              <label>
                Parentesco *
                <input name="parentesco" value={form.parentesco} onChange={handleChange} />
                {errors.parentesco && <span className="field-error">{errors.parentesco}</span>}
              </label>

              <label>
                Teléfono de familiar *
                <input name="telefonoFamiliar" value={form.telefonoFamiliar} onChange={handleChange} />
                {errors.telefonoFamiliar && <span className="field-error">{errors.telefonoFamiliar}</span>}
              </label>

              <label>
                Último grado de estudios *
                <input name="ultimoGrado" value={form.ultimoGrado} onChange={handleChange} />
                {errors.ultimoGrado && <span className="field-error">{errors.ultimoGrado}</span>}
              </label>

              <label>
                Institución *
                <input name="institucion" value={form.institucion} onChange={handleChange} />
                {errors.institucion && <span className="field-error">{errors.institucion}</span>}
              </label>

              <label>
                Promedio *
                <input name="promedio" value={form.promedio} onChange={handleChange} />
                {errors.promedio && <span className="field-error">{errors.promedio}</span>}
              </label>

              <label className="full-width">
                Idiomas
                <textarea name="idiomas" rows="3" value={form.idiomas} onChange={handleChange} />
              </label>

              <label className="full-width">
                Publicaciones
                <textarea name="publicaciones" rows="3" value={form.publicaciones} onChange={handleChange} />
              </label>

              <label className="full-width">
                Apoyos
                <textarea name="apoyos" rows="3" value={form.apoyos} onChange={handleChange} />
              </label>

              <label className="full-width">
                Experiencia profesional
                <textarea name="experiencia" rows="3" value={form.experiencia} onChange={handleChange} />
              </label>

              <label>
                Unidad Cinvestav *
                <input name="unidad" value={form.unidad} onChange={handleChange} />
                {errors.unidad && <span className="field-error">{errors.unidad}</span>}
              </label>

              <label>
                Departamento *
                <input name="departamento" value={form.departamento} onChange={handleChange} />
                {errors.departamento && <span className="field-error">{errors.departamento}</span>}
              </label>

              <label>
                Sección *
                <input name="seccion" value={form.seccion} onChange={handleChange} />
                {errors.seccion && <span className="field-error">{errors.seccion}</span>}
              </label>

              <label>
                Programa de interés *
                <input name="programa" value={form.programa} onChange={handleChange} />
                {errors.programa && <span className="field-error">{errors.programa}</span>}
              </label>

              <label>
                Modalidad *
                <select name="modalidad" value={form.modalidad} onChange={handleChange}>
                  <option>Presencial</option>
                  <option>Híbrida</option>
                  <option>En línea</option>
                </select>
                {errors.modalidad && <span className="field-error">{errors.modalidad}</span>}
              </label>

              <label>
                Tutor propuesto
                <input name="tutorPropuesto" value={form.tutorPropuesto} onChange={handleChange} />
              </label>

              <label className="full-width">
                Comentarios de adscripción
                <textarea name="comentarios" rows="4" value={form.comentarios} onChange={handleChange} />
              </label>

              <div className="lida-panel full-width">
                <h3>Vista previa técnica LIDA / Camunda</h3>
                <p>Este pre-registro ya está estructurado para iniciar una instancia BPMN usando una business key trazable.</p>
                <ul>
                  <li><strong>Process Key:</strong> {lidaPacket.processDefinitionKey}</li>
                  <li><strong>Business Key:</strong> {lidaPacket.businessKey}</li>
                  <li><strong>Evento de inicio:</strong> {lidaPacket.camundaStartEvent}</li>
                </ul>
              </div>

              <div className="form-actions full-width">
                <button type="submit" className="btn-primary">Enviar pre-registro</button>
              </div>
            </form>
          )}
        </div>
      </section>
    </section>
  )
}
