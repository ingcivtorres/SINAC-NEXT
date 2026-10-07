import React, {useMemo, useState} from 'react';
import {useLanguage} from '../translations';

const DRAFT_KEY = 'sinac_preregistro_draft_v2';
const DEPARTAMENTOS = ['Biología Celular','Biomedicina Molecular','Bioquímica','Biotecnología y Bioingeniería','Computación','Control Automático','Farmacología','Física','Fisiología, Biofísica y Neurociencias','Genética y Biología Molecular','Infectómica y Patogénesis Molecular','Ingeniería Eléctrica','Investigación y Estudios Multidisciplinarios','Matemática Educativa','Matemáticas','Química','Toxicología'];
const PROGRAMAS = ['Maestría — Teoría de la Computación (2 años)','Maestría — Inteligencia Artificial (2 años)','Maestría — Sistemas de Cómputo (2 años)','Maestría — Sistemas de Información (2 años)','Maestría — Ciencias de la Computación (2 años)','Doctorado — Teoría de la Computación (4 años)','Doctorado — Inteligencia Artificial (4 años)','Doctorado — Sistemas de Cómputo (4 años)','Doctorado — Sistemas de Información (4 años)','Doctorado — Ciencias de la Computación (4 años)'];
const SECCIONES = Array.from({length:65},(_,i)=>String(i+1));
const REGISTRATION_COPY = {
  es: {
    privacyKicker:'PORTAL DE ASPIRANTES · SINAC NEXT', privacyTitle:'Antes de comenzar', privacyIntro:'Si tienes dudas sobre la información que vas a capturar a continuación, te invitamos a consultar nuestro', privacyNotice:'Aviso de Privacidad', privacyAvailable:'disponible en el pie de página.', privacyNote:'La información proporcionada será utilizada para gestionar tu proceso de registro y admisión.', accept:'Aceptar y continuar',
    successTitle:'Pre-registro enviado correctamente', successText:'Tu solicitud fue recibida. Guarda estos datos para acceder al sistema.', businessKey:'Clave de negocio', processState:'Estado LIDA', instance:'Instancia Camunda', credentials:'Guarda tu usuario y contraseña para iniciar sesión como Aspirante.',
    portalTitle:'Portal de Pre-registro SINAC', portalIntro:'Selecciona una sección del menú izquierdo para completarla.', progress:'completado', requiredNote:'* campos obligatorios', submit:'Enviar pre-registro', sending:'Enviando...',
    required:'Obligatorio.', invalidCurp:'CURP no válida (18 caracteres, formato oficial).', invalidEmail:'Correo no válido.', minPassword:'Mínimo 8 caracteres.', passwordMismatch:'Las contraseñas no coinciden.', submitError:'Error al enviar el pre-registro.', connectionError:'No se pudo conectar con el servidor. Verifica tu conexión.',
    selectUnit:'Selecciona unidad', selectDepartment:'Selecciona departamento', selectSection:'Selecciona sección', selectProgram:'Selecciona programa',
    sections:{generales:'1. Datos Generales', domicilioActual:'2. Domicilio Actual', domicilioPermanente:'3. Domicilio Permanente', familiar:'4. Datos de un Familiar', escolaridad:'5. Escolaridad', idiomas:'6. Idiomas', publicaciones:'7. Publicaciones', apoyos:'8. Apoyos', experiencia:'9. Experiencia Profesional', cinvestav:'10. Cinvestav', adscripcion:'11. Adscripción'},
    fields:{nombre:'Nombre completo', usuario:'Usuario', curp:'CURP', correo:'Correo electrónico', telefono:'Teléfono / celular', nacimiento:'Fecha de nacimiento', password:'Contraseña', passwordConfirm:'Confirmar contraseña', estado:'Estado', municipio:'Municipio', direccion:'Dirección', familiar:'Nombre', parentesco:'Parentesco', telefonoFamiliar:'Teléfono', ultimoGrado:'Último grado', institucion:'Institución', promedio:'Promedio', idiomas:'Idiomas que dominas', publicaciones:'Publicaciones (artículos, libros, etc.)', apoyos:'Becas o apoyos recibidos', experiencia:'Experiencia laboral o de investigación', unidad:'Unidad', departamento:'Departamento', seccion:'Sección', programa:'Programa de interés', modalidad:'Modalidad', tutor:'Tutor propuesto', comentarios:'Comentarios'},
    placeholders:{curp:'18 caracteres', password:'Mínimo 8 caracteres', promedio:'ej. 9.5', idiomas:'Inglés – Avanzado, Francés – Intermedio…', selectUnit:'Selecciona unidad', selectDepartment:'Selecciona departamento', selectSection:'Selecciona sección', selectProgram:'Selecciona programa', modalidad:['Presencial','Híbrida','En línea'], degree:['Maestría','Doctorado']},
    sectionHelp:'Para conocer la sección consulta el croquis de Cinvestav Zacatenco.', lida:'LIDA',
  },
  en: {
    privacyKicker:'APPLICANT PORTAL · SINAC NEXT', privacyTitle:'Before you begin', privacyIntro:'If you have questions about the information you are about to provide, please read our', privacyNotice:'Privacy Notice', privacyAvailable:'available in the page footer.', privacyNote:'The information provided will be used to manage your registration and admission process.', accept:'Accept and continue',
    successTitle:'Pre-registration submitted successfully', successText:'Your application was received. Save these details to access the system.', businessKey:'Business key', processState:'LIDA status', instance:'Camunda instance', credentials:'Save your username and password to sign in as an Applicant.',
    portalTitle:'SINAC Pre-registration Portal', portalIntro:'Select a section from the menu on the left to complete it.', progress:'complete', requiredNote:'* required fields', submit:'Submit pre-registration', sending:'Submitting...',
    required:'Required.', invalidCurp:'Invalid CURP (18 characters, official format).', invalidEmail:'Invalid email address.', minPassword:'At least 8 characters.', passwordMismatch:'Passwords do not match.', submitError:'Could not submit the pre-registration.', connectionError:'Could not connect to the server. Check your connection.',
    selectUnit:'Select a unit', selectDepartment:'Select a department', selectSection:'Select a section', selectProgram:'Select a program',
    sections:{generales:'1. Personal Information', domicilioActual:'2. Current Address', domicilioPermanente:'3. Permanent Address', familiar:'4. Family Contact', escolaridad:'5. Education', idiomas:'6. Languages', publicaciones:'7. Publications', apoyos:'8. Financial Support', experiencia:'9. Professional Experience', cinvestav:'10. Cinvestav', adscripcion:'11. Academic Affiliation'},
    fields:{nombre:'Full name', usuario:'Username', curp:'CURP', correo:'Email address', telefono:'Phone / mobile', nacimiento:'Date of birth', password:'Password', passwordConfirm:'Confirm password', estado:'State', municipio:'City / municipality', direccion:'Address', familiar:'Name', parentesco:'Relationship', telefonoFamiliar:'Phone', ultimoGrado:'Highest degree', institucion:'Institution', promedio:'Grade average', idiomas:'Languages you speak', publicaciones:'Publications (articles, books, etc.)', apoyos:'Scholarships or support received', experiencia:'Work or research experience', unidad:'Unit', departamento:'Department', seccion:'Section', programa:'Program of interest', modalidad:'Study mode', tutor:'Proposed advisor', comentarios:'Comments'},
    placeholders:{curp:'18 characters', password:'At least 8 characters', promedio:'e.g. 9.5', idiomas:'English – Advanced, French – Intermediate…', selectUnit:'Select a unit', selectDepartment:'Select a department', selectSection:'Select a section', selectProgram:'Select a program', modalidad:['In person','Hybrid','Online'], degree:['Master’s','Doctorate']},
    sectionHelp:'Check the Cinvestav Zacatenco map to find your section.', lida:'LIDA',
  },
  de: {
    privacyKicker:'BEWERBERPORTAL · SINAC NEXT', privacyTitle:'Bevor Sie beginnen', privacyIntro:'Wenn Sie Fragen zu den folgenden Angaben haben, lesen Sie bitte unseren', privacyNotice:'Datenschutzhinweis', privacyAvailable:'im Fußbereich der Seite.', privacyNote:'Die Angaben werden zur Verwaltung Ihres Registrierungs- und Zulassungsverfahrens verwendet.', accept:'Akzeptieren und fortfahren',
    successTitle:'Vorregistrierung erfolgreich gesendet', successText:'Ihr Antrag ist eingegangen. Speichern Sie diese Daten für den Systemzugang.', businessKey:'Geschäftsschlüssel', processState:'LIDA-Status', instance:'Camunda-Instanz', credentials:'Speichern Sie Benutzername und Passwort für die Anmeldung als Bewerber.',
    portalTitle:'SINAC-Vorregistrierungsportal', portalIntro:'Wählen Sie links einen Abschnitt aus und füllen Sie ihn aus.', progress:'abgeschlossen', requiredNote:'* Pflichtfelder', submit:'Vorregistrierung senden', sending:'Wird gesendet...',
    required:'Pflichtfeld.', invalidCurp:'Ungültige CURP (18 Zeichen, offizielles Format).', invalidEmail:'Ungültige E-Mail-Adresse.', minPassword:'Mindestens 8 Zeichen.', passwordMismatch:'Die Passwörter stimmen nicht überein.', submitError:'Die Vorregistrierung konnte nicht gesendet werden.', connectionError:'Keine Verbindung zum Server. Bitte prüfen Sie Ihre Verbindung.',
    selectUnit:'Einheit auswählen', selectDepartment:'Abteilung auswählen', selectSection:'Bereich auswählen', selectProgram:'Studiengang auswählen',
    sections:{generales:'1. Persönliche Angaben', domicilioActual:'2. Aktuelle Anschrift', domicilioPermanente:'3. Dauerhafte Anschrift', familiar:'4. Familienkontakt', escolaridad:'5. Ausbildung', idiomas:'6. Sprachen', publicaciones:'7. Veröffentlichungen', apoyos:'8. Förderungen', experiencia:'9. Berufserfahrung', cinvestav:'10. Cinvestav', adscripcion:'11. Akademische Zuordnung'},
    fields:{nombre:'Vollständiger Name', usuario:'Benutzername', curp:'CURP', correo:'E-Mail-Adresse', telefono:'Telefon / Mobiltelefon', nacimiento:'Geburtsdatum', password:'Passwort', passwordConfirm:'Passwort bestätigen', estado:'Bundesstaat', municipio:'Ort / Gemeinde', direccion:'Anschrift', familiar:'Name', parentesco:'Verwandtschaftsverhältnis', telefonoFamiliar:'Telefon', ultimoGrado:'Höchster Abschluss', institucion:'Einrichtung', promedio:'Notendurchschnitt', idiomas:'Beherrschte Sprachen', publicaciones:'Veröffentlichungen (Artikel, Bücher usw.)', apoyos:'Erhaltene Stipendien oder Förderungen', experiencia:'Berufs- oder Forschungserfahrung', unidad:'Einheit', departamento:'Abteilung', seccion:'Bereich', programa:'Gewünschter Studiengang', modalidad:'Studienform', tutor:'Vorgeschlagene Betreuung', comentarios:'Kommentare'},
    placeholders:{curp:'18 Zeichen', password:'Mindestens 8 Zeichen', promedio:'z. B. 9,5', idiomas:'Englisch – Fortgeschritten, Französisch – Mittelstufe…', selectUnit:'Einheit auswählen', selectDepartment:'Abteilung auswählen', selectSection:'Bereich auswählen', selectProgram:'Studiengang auswählen', modalidad:['Präsenz','Hybrid','Online'], degree:['Master','Promotion']},
    sectionHelp:'Die Abschnittsnummer finden Sie im Lageplan von Cinvestav Zacatenco.', lida:'LIDA',
  },
  zh: {
    privacyKicker:'申请门户 · SINAC NEXT', privacyTitle:'开始之前', privacyIntro:'如果您对接下来填写的信息有疑问，请查阅我们的', privacyNotice:'隐私声明', privacyAvailable:'可在页面底部查看。', privacyNote:'所提供的信息将用于管理您的注册和录取流程。', accept:'接受并继续',
    successTitle:'预注册提交成功', successText:'已收到您的申请。请保存这些信息以访问系统。', businessKey:'业务密钥', processState:'LIDA 状态', instance:'Camunda 实例', credentials:'请保存用户名和密码，以申请人身份登录。',
    portalTitle:'SINAC 预注册门户', portalIntro:'请从左侧菜单选择一个部分并填写。', progress:'已完成', requiredNote:'* 必填项', submit:'提交预注册', sending:'正在提交...',
    required:'必填项。', invalidCurp:'CURP 无效（18 个字符，须符合官方格式）。', invalidEmail:'电子邮件地址无效。', minPassword:'至少 8 个字符。', passwordMismatch:'两次密码不一致。', submitError:'无法提交预注册。', connectionError:'无法连接服务器，请检查网络连接。',
    selectUnit:'选择单位', selectDepartment:'选择部门', selectSection:'选择组别', selectProgram:'选择项目',
    sections:{generales:'1. 个人信息', domicilioActual:'2. 当前地址', domicilioPermanente:'3. 常住地址', familiar:'4. 家庭联系人', escolaridad:'5. 教育背景', idiomas:'6. 语言', publicaciones:'7. 出版物', apoyos:'8. 资助', experiencia:'9. 工作经历', cinvestav:'10. Cinvestav', adscripcion:'11. 学术归属'},
    fields:{nombre:'姓名', usuario:'用户名', curp:'CURP', correo:'电子邮件', telefono:'电话 / 手机', nacimiento:'出生日期', password:'密码', passwordConfirm:'确认密码', estado:'州', municipio:'市 / 县', direccion:'地址', familiar:'姓名', parentesco:'关系', telefonoFamiliar:'电话', ultimoGrado:'最高学历', institucion:'院校', promedio:'平均成绩', idiomas:'掌握的语言', publicaciones:'出版物（文章、书籍等）', apoyos:'获得的奖学金或资助', experiencia:'工作或研究经历', unidad:'单位', departamento:'部门', seccion:'组别', programa:'意向项目', modalidad:'学习方式', tutor:'拟定导师', comentarios:'备注'},
    placeholders:{curp:'18 个字符', password:'至少 8 个字符', promedio:'例如 9.5', idiomas:'英语 – 高级，法语 – 中级…', selectUnit:'选择单位', selectDepartment:'选择部门', selectSection:'选择组别', selectProgram:'选择项目', modalidad:['线下','混合','线上'], degree:['硕士','博士']},
    sectionHelp:'请查看 Cinvestav Zacatenco 平面图以确认组别。', lida:'LIDA',
  },
  pt: {
    privacyKicker:'PORTAL DE CANDIDATOS · SINAC NEXT', privacyTitle:'Antes de começar', privacyIntro:'Se tiver dúvidas sobre as informações que serão preenchidas, consulte nosso', privacyNotice:'Aviso de Privacidade', privacyAvailable:'disponível no rodapé da página.', privacyNote:'As informações fornecidas serão usadas para gerenciar seu processo de cadastro e admissão.', accept:'Aceitar e continuar',
    successTitle:'Pré-cadastro enviado com sucesso', successText:'Sua solicitação foi recebida. Salve estes dados para acessar o sistema.', businessKey:'Chave de negócio', processState:'Status LIDA', instance:'Instância Camunda', credentials:'Salve seu usuário e senha para entrar como candidato.',
    portalTitle:'Portal de Pré-cadastro SINAC', portalIntro:'Selecione uma seção no menu à esquerda para preenchê-la.', progress:'concluído', requiredNote:'* campos obrigatórios', submit:'Enviar pré-cadastro', sending:'Enviando...',
    required:'Obrigatório.', invalidCurp:'CURP inválida (18 caracteres, formato oficial).', invalidEmail:'E-mail inválido.', minPassword:'Mínimo de 8 caracteres.', passwordMismatch:'As senhas não coincidem.', submitError:'Não foi possível enviar o pré-cadastro.', connectionError:'Não foi possível conectar ao servidor. Verifique sua conexão.',
    selectUnit:'Selecione uma unidade', selectDepartment:'Selecione um departamento', selectSection:'Selecione uma seção', selectProgram:'Selecione um programa',
    sections:{generales:'1. Dados pessoais', domicilioActual:'2. Endereço atual', domicilioPermanente:'3. Endereço permanente', familiar:'4. Contato familiar', escolaridad:'5. Escolaridade', idiomas:'6. Idiomas', publicaciones:'7. Publicações', apoyos:'8. Apoios financeiros', experiencia:'9. Experiência profissional', cinvestav:'10. Cinvestav', adscripcion:'11. Vínculo acadêmico'},
    fields:{nombre:'Nome completo', usuario:'Usuário', curp:'CURP', correo:'E-mail', telefono:'Telefone / celular', nacimiento:'Data de nascimento', password:'Senha', passwordConfirm:'Confirmar senha', estado:'Estado', municipio:'Município', direccion:'Endereço', familiar:'Nome', parentesco:'Parentesco', telefonoFamiliar:'Telefone', ultimoGrado:'Último grau', institucion:'Instituição', promedio:'Média', idiomas:'Idiomas que você domina', publicaciones:'Publicações (artigos, livros etc.)', apoyos:'Bolsas ou apoios recebidos', experiencia:'Experiência profissional ou de pesquisa', unidad:'Unidade', departamento:'Departamento', seccion:'Seção', programa:'Programa de interesse', modalidad:'Modalidade', tutor:'Orientador proposto', comentarios:'Comentários'},
    placeholders:{curp:'18 caracteres', password:'Mínimo de 8 caracteres', promedio:'ex.: 9,5', idiomas:'Inglês – Avançado, Francês – Intermediário…', selectUnit:'Selecione uma unidade', selectDepartment:'Selecione um departamento', selectSection:'Selecione uma seção', selectProgram:'Selecione um programa', modalidad:['Presencial','Híbrida','Online'], degree:['Mestrado','Doutorado']},
    sectionHelp:'Consulte a planta do Cinvestav Zacatenco para encontrar sua seção.', lida:'LIDA',
  },
};

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
  {id: 'generales', required: ['nombre','usuario','curp','correo','telefono','nacimiento']},
  {id: 'domicilioActual', required: ['estadoActual','municipioActual','direccionActual']},
  {id: 'domicilioPermanente', required: ['estadoPermanente','municipioPermanente','direccionPermanente']},
  {id: 'familiar', required: ['nombreFamiliar','parentesco','telefonoFamiliar']},
  {id: 'escolaridad', required: ['ultimoGrado','institucion','promedio']},
  {id: 'idiomas', required: []},
  {id: 'publicaciones', required: []},
  {id: 'apoyos', required: []},
  {id: 'experiencia', required: []},
  {id: 'cinvestav', required: ['unidad','departamento','seccion','programa','modalidad']},
  {id: 'adscripcion', required: []},
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
  const {language} = useLanguage();
  const errorText = error?.startsWith('i18n:')
    ? (REGISTRATION_COPY[language] || REGISTRATION_COPY.es)[error.slice(5)]
    : error;
  return (
    <label className="af-label">
      <span className="af-label-text">{label}{req && <em> *</em>}</span>
      {children}
      {errorText && <span className="field-error">{errorText}</span>}
    </label>
  );
}

export default function AspirantRegistration(){
  const {language} = useLanguage();
  const copy = REGISTRATION_COPY[language] || REGISTRATION_COPY.es;
  const t = (key) => copy[key] || REGISTRATION_COPY.es[key] || key;
  const sectionTitle = (id) => copy.sections[id] || REGISTRATION_COPY.es.sections[id];
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
    requiredFields.forEach(f => { if(!`${form[f]||''}`.trim()) errs[f]='i18n:required'; });
    if(form.curp && !/^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[A-Z0-9][0-9]$/.test(form.curp)) errs.curp='i18n:invalidCurp';
    if(form.correo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.correo)) errs.correo='i18n:invalidEmail';
    if(form.password && form.password.length < 8) errs.password='i18n:minPassword';
    if(form.password !== form.passwordConfirm) errs.passwordConfirm='i18n:passwordMismatch';
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
        setApiError(msg || t('submitError'));
        setSending(false);
        return;
      }
      setSubmitData(data);
      setSubmitted(true);
      clearDraft();
    } catch {
      setApiError(t('connectionError'));
    }
    setSending(false);
  }

  if(submitted){
    return (
      <section id="portal-aspirantes" className="registration-section">
        <div className="success-box" style={{maxWidth:760,margin:'40px auto'}}>
          <h3>✓ {t('successTitle')}</h3>
          <p>{t('successText')}</p>
          {submitData && (
            <div className="success-detail">
              <div><strong>{t('businessKey')}:</strong> {submitData.business_key}</div>
              <div><strong>{t('processState')}:</strong> {submitData.proceso_estado}</div>
              {submitData.camunda_id && <div><strong>{t('instance')}:</strong> {submitData.camunda_id}</div>}
              <div style={{marginTop:10,fontSize:'.88rem',color:'var(--muted)'}}>{t('credentials')}</div>
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
          <span className="privacy-gate-kicker">{t('privacyKicker')}</span>
          <h1 id="privacy-gate-title">{t('privacyTitle')}</h1>
          <p>{t('privacyIntro')} <strong>{t('privacyNotice')}</strong>, {t('privacyAvailable')}</p>
          <div className="privacy-gate-note"><span aria-hidden="true">i</span><span>{t('privacyNote')}</span></div>
          <button type="button" className="privacy-gate-accept" onClick={() => setPrivacyAccepted(true)}>{t('accept')}</button>
        </div>
      </section>
    );
  }

  const activeDef = sectionDefs.find(s => s.id === activeId);

  function renderPanel(){
    switch(activeId){
      case 'generales': return (
        <div className="cf-grid">
          <Field label={copy.fields.nombre} req error={errors.nombre}><input name="nombre" value={form.nombre} onChange={handleChange}/></Field>
          <Field label={copy.fields.usuario} req error={errors.usuario}><input name="usuario" value={form.usuario} onChange={handleChange} maxLength="20"/></Field>
          <Field label={copy.fields.curp} req error={errors.curp}><input name="curp" value={form.curp} onChange={handleChange} maxLength="18" placeholder={copy.placeholders.curp}/></Field>
          <Field label={copy.fields.correo} req error={errors.correo}><input name="correo" type="email" value={form.correo} onChange={handleChange}/></Field>
          <Field label={copy.fields.telefono} req error={errors.telefono}><input name="telefono" type="tel" value={form.telefono} onChange={handleChange}/></Field>
          <Field label={copy.fields.nacimiento} req error={errors.nacimiento}><input name="nacimiento" type="date" value={form.nacimiento} onChange={handleChange}/></Field>
          <Field label={copy.fields.password} req error={errors.password}><input name="password" type="password" value={form.password} onChange={handleChange} placeholder={copy.placeholders.password}/></Field>
          <Field label={copy.fields.passwordConfirm} req error={errors.passwordConfirm}><input name="passwordConfirm" type="password" value={form.passwordConfirm} onChange={handleChange}/></Field>
        </div>
      );
      case 'domicilioActual': return (
        <div className="cf-grid">
          <Field label={copy.fields.estado} req error={errors.estadoActual}><input name="estadoActual" value={form.estadoActual} onChange={handleChange}/></Field>
          <Field label={copy.fields.municipio} req error={errors.municipioActual}><input name="municipioActual" value={form.municipioActual} onChange={handleChange}/></Field>
          <Field label={copy.fields.direccion} req error={errors.direccionActual}><input name="direccionActual" value={form.direccionActual} onChange={handleChange} className="cf-full"/></Field>
        </div>
      );
      case 'domicilioPermanente': return (
        <div className="cf-grid">
          <Field label={copy.fields.estado} req error={errors.estadoPermanente}><input name="estadoPermanente" value={form.estadoPermanente} onChange={handleChange}/></Field>
          <Field label={copy.fields.municipio} req error={errors.municipioPermanente}><input name="municipioPermanente" value={form.municipioPermanente} onChange={handleChange}/></Field>
          <Field label={copy.fields.direccion} req error={errors.direccionPermanente}><input name="direccionPermanente" value={form.direccionPermanente} onChange={handleChange} className="cf-full"/></Field>
        </div>
      );
      case 'familiar': return (
        <div className="cf-grid">
          <Field label={copy.fields.familiar} req error={errors.nombreFamiliar}><input name="nombreFamiliar" value={form.nombreFamiliar} onChange={handleChange}/></Field>
          <Field label={copy.fields.parentesco} req error={errors.parentesco}><input name="parentesco" value={form.parentesco} onChange={handleChange}/></Field>
          <Field label={copy.fields.telefonoFamiliar} req error={errors.telefonoFamiliar}><input name="telefonoFamiliar" type="tel" value={form.telefonoFamiliar} onChange={handleChange}/></Field>
        </div>
      );
      case 'escolaridad': return (
        <div className="cf-grid">
          <Field label={copy.fields.ultimoGrado} req error={errors.ultimoGrado}><input name="ultimoGrado" value={form.ultimoGrado} onChange={handleChange}/></Field>
          <Field label={copy.fields.institucion} req error={errors.institucion}><input name="institucion" value={form.institucion} onChange={handleChange}/></Field>
          <Field label={copy.fields.promedio} req error={errors.promedio}><input name="promedio" value={form.promedio} onChange={handleChange} placeholder={copy.placeholders.promedio}/></Field>
        </div>
      );
      case 'idiomas': return (
        <label className="af-label af-label--full">
          <span className="af-label-text">{copy.fields.idiomas}</span>
          <textarea name="idiomas" rows="4" value={form.idiomas} onChange={handleChange} placeholder={copy.placeholders.idiomas}/>
        </label>
      );
      case 'publicaciones': return (
        <label className="af-label af-label--full">
          <span className="af-label-text">{copy.fields.publicaciones}</span>
          <textarea name="publicaciones" rows="4" value={form.publicaciones} onChange={handleChange}/>
        </label>
      );
      case 'apoyos': return (
        <label className="af-label af-label--full">
          <span className="af-label-text">{copy.fields.apoyos}</span>
          <textarea name="apoyos" rows="4" value={form.apoyos} onChange={handleChange}/>
        </label>
      );
      case 'experiencia': return (
        <label className="af-label af-label--full">
          <span className="af-label-text">{copy.fields.experiencia}</span>
          <textarea name="experiencia" rows="5" value={form.experiencia} onChange={handleChange}/>
        </label>
      );
      case 'cinvestav': return (
        <div className="cf-grid">
          <Field label={copy.fields.unidad} req error={errors.unidad}><select name="unidad" value={form.unidad} onChange={handleChange}><option value="">{copy.placeholders.selectUnit}</option><option value="Zacatenco">Zacatenco</option></select></Field>
          <Field label={copy.fields.departamento} req error={errors.departamento}><select name="departamento" value={form.departamento} onChange={handleChange}><option value="">{copy.placeholders.selectDepartment}</option>{DEPARTAMENTOS.map(x=><option key={x}>{x}</option>)}</select></Field>
          <Field label={copy.fields.seccion} req error={errors.seccion}><select name="seccion" value={form.seccion} onChange={handleChange}><option value="">{copy.placeholders.selectSection}</option>{SECCIONES.map(x=><option key={x}>{x}</option>)}</select><small>{copy.sectionHelp}</small></Field>
          <Field label={copy.fields.programa} req error={errors.programa}><select name="programa" value={form.programa} onChange={handleChange}><option value="">{copy.placeholders.selectProgram}</option>{PROGRAMAS.map((programa, index) => <option key={programa} value={programa}>{copy.placeholders.degree[index < 5 ? 0 : 1]}{programa.slice(programa.indexOf(' —'))}</option>)}</select></Field>
          <Field label={copy.fields.modalidad} req error={errors.modalidad}>
            <select name="modalidad" value={form.modalidad} onChange={handleChange}>
              {['Presencial','Híbrida','En línea'].map((value, index) => <option key={value} value={value}>{copy.placeholders.modalidad[index]}</option>)}
            </select>
          </Field>
        </div>
      );
      case 'adscripcion': return (
        <div className="cf-grid">
          <Field label={copy.fields.tutor}><input name="tutorPropuesto" value={form.tutorPropuesto} onChange={handleChange}/></Field>
          <label className="af-label af-label--full">
            <span className="af-label-text">{copy.fields.comentarios}</span>
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
          <h1>{t('portalTitle')}</h1>
          <p>{t('portalIntro')}</p>
        </div>
        <div className="progress-outer" title={`${completion}% ${t('progress')}`}>
          <div className="progress-inner" style={{width:`${completion}%`}}/>
          <span className="progress-label">{completion}%</span>
        </div>
      </div>

      <form className="sb-form" onSubmit={handleSubmit} noValidate>
        {/* sidebar */}
        <nav className="sb-nav" aria-label={t('portalTitle')}>
          {sectionDefs.map(def => (
            <button
              key={def.id}
              type="button"
              className={`sb-item${activeId===def.id?' sb-item--active':''}`}
              onClick={()=>selectSection(def.id)}
            >
              <span className="sb-item-title">{sectionTitle(def.id)}</span>
              <SectionBadge def={def} form={form} errors={errors}/>
            </button>
          ))}
        </nav>

        {/* panel */}
        <div className="sb-panel">
          <div className="sb-panel-header">
            <h2>{activeDef && sectionTitle(activeDef.id)}</h2>
            {activeDef?.required.length > 0 && (
              <span className="sb-required-note">{t('requiredNote')}</span>
            )}
          </div>
          <div className="sb-panel-body">
            {renderPanel()}
          </div>
          <div className="sb-panel-footer">
            <div className="lida-panel">
              <strong>{t('lida')}</strong>
              <span style={{marginLeft:10,fontSize:'.85rem',color:'var(--muted)'}}>{lidaPacket.businessKey}</span>
            </div>
            {apiError && <div className="api-error">{apiError}</div>}
            <div className="form-actions">
              <button type="submit" className="btn-primary" disabled={sending}>
                {sending ? t('sending') : t('submit')}
              </button>
            </div>
          </div>
        </div>
      </form>
    </section>
  );
}
