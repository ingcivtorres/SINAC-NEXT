import React, {useEffect, useState} from 'react';
import {fotoUrl} from './PerfilAspirante';
import {useLanguage} from '../translations';

const COPY = {
  es: {
    locale: 'es-MX', roles: {director: 'Director de tesis', coordinacion: 'Coordinación académica', servicios: 'Servicios Escolares'},
    loadError: 'No se pudo integrar el expediente centralizado.', openError: 'No se pudo abrir el archivo.',
    noRecord: 'El alumno aún no cuenta con un expediente digital oficial.', loading: 'Integrando expediente digital...',
    kicker: 'EXPEDIENTE CENTRALIZADO', viewPdf: 'Ver PDF', downloadPdf: 'Descargar PDF',
    documents: 'Documentos', enrollments: 'Inscripciones', signatures: 'Firmas', thesis: 'Tesis',
    eSignatures: 'Firmas electrónicas', fingerprint: 'Huella', noSignatures: 'Sin firmas todavía.',
    view: 'Ver', noDocuments: 'Sin documentos cargados.', thesisTrack: 'Trayectoria de tesis',
  },
  en: {
    locale: 'en-US', roles: {director: 'Thesis director', coordinacion: 'Academic Coordination', servicios: 'School Services'},
    loadError: 'The centralized record could not be assembled.', openError: 'The file could not be opened.',
    noRecord: 'The student does not have an official digital record yet.', loading: 'Assembling digital record...',
    kicker: 'CENTRALIZED RECORD', viewPdf: 'View PDF', downloadPdf: 'Download PDF',
    documents: 'Documents', enrollments: 'Enrollments', signatures: 'Signatures', thesis: 'Thesis',
    eSignatures: 'Electronic signatures', fingerprint: 'Fingerprint', noSignatures: 'No signatures yet.',
    view: 'View', noDocuments: 'No documents uploaded.', thesisTrack: 'Thesis trajectory',
  },
  de: {
    locale: 'de-DE', roles: {director: 'Dissertationsbetreuer/in', coordinacion: 'Akademische Koordination', servicios: 'Studierendenverwaltung'},
    loadError: 'Die zentrale Akte konnte nicht zusammengestellt werden.', openError: 'Die Datei konnte nicht geöffnet werden.',
    noRecord: 'Für die/den Studierende/n gibt es noch keine offizielle digitale Akte.', loading: 'Digitale Akte wird zusammengestellt...',
    kicker: 'ZENTRALE AKTE', viewPdf: 'PDF ansehen', downloadPdf: 'PDF herunterladen',
    documents: 'Dokumente', enrollments: 'Einschreibungen', signatures: 'Unterschriften', thesis: 'Dissertation',
    eSignatures: 'Elektronische Unterschriften', fingerprint: 'Fingerabdruck', noSignatures: 'Noch keine Unterschriften.',
    view: 'Ansehen', noDocuments: 'Keine Dokumente hochgeladen.', thesisTrack: 'Dissertationsverlauf',
  },
  zh: {
    locale: 'zh-CN', roles: {director: '论文导师', coordinacion: '教务协调处', servicios: '学生事务服务'},
    loadError: '无法整合集中档案。', openError: '无法打开文件。',
    noRecord: '该学生尚无官方电子档案。', loading: '正在整合电子档案...',
    kicker: '集中档案', viewPdf: '查看 PDF', downloadPdf: '下载 PDF',
    documents: '文件', enrollments: '注册记录', signatures: '签名', thesis: '论文',
    eSignatures: '电子签名', fingerprint: '指纹', noSignatures: '尚无签名。',
    view: '查看', noDocuments: '尚未上传文件。', thesisTrack: '论文进程',
  },
  pt: {
    locale: 'pt-BR', roles: {director: 'Orientador de tese', coordinacion: 'Coordenação Acadêmica', servicios: 'Serviços Escolares'},
    loadError: 'Não foi possível integrar o expediente centralizado.', openError: 'Não foi possível abrir o arquivo.',
    noRecord: 'O aluno ainda não possui um expediente digital oficial.', loading: 'Integrando expediente digital...',
    kicker: 'EXPEDIENTE CENTRALIZADO', viewPdf: 'Ver PDF', downloadPdf: 'Baixar PDF',
    documents: 'Documentos', enrollments: 'Inscrições', signatures: 'Assinaturas', thesis: 'Tese',
    eSignatures: 'Assinaturas eletrônicas', fingerprint: 'Impressão digital', noSignatures: 'Ainda sem assinaturas.',
    view: 'Ver', noDocuments: 'Nenhum documento enviado.', thesisTrack: 'Trajetória da tese',
  },
};

export default function ExpedienteCentralizadoCard({expedienteId, session}) {
  const {language} = useLanguage();
  const t = COPY[language] || COPY.es;
  const [expediente, setExpediente] = useState(null);
  const [error, setError] = useState('');
  const [aviso, setAviso] = useState('');
  const fechaHora = (value) => value ? new Intl.DateTimeFormat(t.locale, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value)) : '—';

  useEffect(() => {
    if (!expedienteId) return undefined;
    const controller = new AbortController();
    setError('');
    fetch(`/api/expedientes/${expedienteId}/centralizado/`, {headers: {Authorization: `Bearer ${session.access}`}, signal: controller.signal})
      .then(response => response.ok ? response.json() : Promise.reject(new Error('load')))
      .then(setExpediente)
      .catch(err => { if (err.name !== 'AbortError') setError('load'); });
    return () => controller.abort();
  }, [expedienteId, session.access]);

  async function abrir(ruta, {descargar = false, nombre = 'expediente.pdf'} = {}) {
    setAviso('');
    try {
      const response = await fetch(ruta, {headers: {Authorization: `Bearer ${session.access}`}});
      if (!response.ok) throw new Error(t.openError);
      const url = URL.createObjectURL(new Blob([await response.blob()], {type: 'application/pdf'}));
      if (descargar) {
        const a = document.createElement('a');
        a.href = url; a.download = nombre; a.click();
      } else {
        window.open(url, '_blank', 'noopener');
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) { setAviso(t.openError); }
  }

  if (!expedienteId) return <p className="form-hint">{t.noRecord}</p>;
  if (error) return <p className="api-error">{t.loadError}</p>;
  if (!expediente) return <p className="form-hint">{t.loading}</p>;

  const {alumno, firmas, documentos} = expediente;
  const foto = fotoUrl(alumno.profile_photo);
  return <section className="expediente-centralizado-card">
    <div className="expediente-centralizado-head">
      <div><p className="panel-kicker">{t.kicker}</p><h4>{expediente.expediente.folio}</h4></div>
      <span>{expediente.expediente.estado}</span>
    </div>
    <div className="exp-alumno">
      {foto ? <img src={foto} alt={alumno.nombre} className="exp-foto"/> : <div className="exp-foto exp-foto-vacia">{(alumno.nombre || '?').charAt(0)}</div>}
      <div className="exp-alumno-datos"><strong>{alumno.nombre}</strong><small>{alumno.matricula || '—'} · {alumno.correo}</small><small>{alumno.programa || '—'}{alumno.unidad ? ` · ${alumno.unidad}` : ''}</small></div>
      <div className="exp-acciones">
        <button type="button" className="btn-primary" onClick={() => abrir(`/api/expedientes/${expedienteId}/pdf/?inline=1`)}>{t.viewPdf}</button>
        <button type="button" className="btn-secondary" onClick={() => abrir(`/api/expedientes/${expedienteId}/pdf/`, {descargar: true, nombre: `${expediente.expediente.folio}.pdf`})}>{t.downloadPdf}</button>
      </div>
    </div>
    {aviso && <p className="api-error">{aviso}</p>}
    <div className="expediente-centralizado-metrics"><div><strong>{documentos.length}</strong><span>{t.documents}</span></div><div><strong>{expediente.inscripciones.length}</strong><span>{t.enrollments}</span></div><div><strong>{firmas.length}</strong><span>{t.signatures}</span></div><div><strong>{expediente.tesis.length}</strong><span>{t.thesis}</span></div></div>

    <div className="expediente-centralizado-list"><strong>{t.eSignatures}</strong>
      {firmas.length ? firmas.map(firma => <div key={firma.id} className="exp-sello"><span className="exp-sello-check">✔</span><div><b>{firma.firmante_nombre}</b><small>{t.roles[firma.rol_firmante] || firma.rol_firmante} · {fechaHora(firma.firmado_at)}</small><code>{t.fingerprint}: {firma.huella}</code></div></div>) : <span>{t.noSignatures}</span>}
    </div>

    <div className="expediente-centralizado-list"><strong>{t.documents}</strong>
      {documentos.length ? documentos.map(d => <div key={d.id} className="exp-doc"><span>{d.tipo_label}<small>{d.nombre_original}</small></span><button type="button" className="btn-secondary" onClick={() => abrir(`${d.archivo}?inline=1`)}>{t.view}</button></div>) : <span>{t.noDocuments}</span>}
    </div>

    {expediente.tesis.length > 0 && <div className="expediente-centralizado-list"><strong>{t.thesisTrack}</strong>{expediente.tesis.map(proyecto => <span key={proyecto.id}>{proyecto.titulo} · {proyecto.estado_label}{proyecto.defensa ? ` · ${proyecto.defensa.estado_label}` : ''}</span>)}</div>}
  </section>;
}
