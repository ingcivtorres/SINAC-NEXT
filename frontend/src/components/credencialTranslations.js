import {useLanguage} from '../translations';

const textos = {
  es: {
    locale: 'es-MX', title: 'Credencial digital', kicker: 'IDENTIFICACIÓN', front: 'Frente', back: 'Reverso',
    cardTitle: 'CREDENCIAL DE ALUMNO', studentId: 'Matrícula', program: 'Programa', degree: 'Grado', unit: 'Unidad',
    validUntil: 'Vigente hasta', period: 'Periodo', folio: 'Folio', valid: 'Vigente', notValid: 'No vigente',
    scan: 'Escanea el código para verificar la autenticidad y vigencia de esta credencial.',
    renew: s => `El código se renueva en ${s} s`, download: 'Descargar para imprimir (PDF)', openVerify: 'Abrir verificación',
    noPhoto: 'Tu credencial no tiene fotografía. Agrégala en Mi perfil para que puedan identificarte.', goProfile: 'Ir a Mi perfil',
    loading: 'Cargando tu credencial…', error: 'No se pudo cargar la credencial.', downloadError: 'No se pudo descargar la credencial.',
    expired: 'Tu sesión expiró.', photoAlt: nombre => `Fotografía de ${nombre}`, qrAlt: 'Código QR de verificación',
    verifyTitle: 'Verificación de credencial', verifyIntro: 'Resultado de la consulta en los registros de SINAC NEXT.',
    verifying: 'Verificando credencial…', resultValid: 'CREDENCIAL VIGENTE', resultNotValid: 'CREDENCIAL NO VIGENTE',
    resultInvalid: 'CREDENCIAL NO VÁLIDA', checkedAt: 'Consultado el', home: 'Ir al inicio', name: 'Nombre',
    reasons: {
      baja: 'El alumno causó baja.', egresado: 'El alumno ya egresó del programa.', sin_inscripcion: 'El alumno no tiene inscripción en un periodo escolar.',
      periodo_concluido: 'El periodo escolar ya concluyó; se renueva al reinscribirse.', firma: 'El código no fue emitido por SINAC NEXT o fue alterado.',
      qr_expirado: 'El código de pantalla caducó. Pide al alumno que muestre el código actualizado.', reemplazada: 'Esta credencial fue repuesta y ya no es válida.',
      impresa_vencida: 'La credencial impresa corresponde a un periodo anterior.',
    },
  },
  en: {
    locale: 'en-US', title: 'Digital ID card', kicker: 'IDENTIFICATION', front: 'Front', back: 'Back',
    cardTitle: 'STUDENT ID CARD', studentId: 'Student ID', program: 'Program', degree: 'Degree', unit: 'Campus',
    validUntil: 'Valid until', period: 'Term', folio: 'Serial', valid: 'Valid', notValid: 'Not valid',
    scan: 'Scan the code to verify the authenticity and validity of this card.',
    renew: s => `The code refreshes in ${s} s`, download: 'Download for printing (PDF)', openVerify: 'Open verification',
    noPhoto: 'Your card has no photo. Add one in My profile so you can be identified.', goProfile: 'Go to My profile',
    loading: 'Loading your ID card…', error: 'The ID card could not be loaded.', downloadError: 'The ID card could not be downloaded.',
    expired: 'Your session expired.', photoAlt: nombre => `Photo of ${nombre}`, qrAlt: 'Verification QR code',
    verifyTitle: 'ID card verification', verifyIntro: 'Result of the lookup in SINAC NEXT records.',
    verifying: 'Verifying ID card…', resultValid: 'VALID ID CARD', resultNotValid: 'ID CARD NOT VALID',
    resultInvalid: 'INVALID ID CARD', checkedAt: 'Checked on', home: 'Go to home', name: 'Name',
    reasons: {
      baja: 'The student has withdrawn.', egresado: 'The student has graduated.', sin_inscripcion: 'The student is not enrolled in any term.',
      periodo_concluido: 'The term has ended; it renews upon re-enrollment.', firma: 'The code was not issued by SINAC NEXT or was altered.',
      qr_expirado: 'The on-screen code expired. Ask the student to show the updated code.', reemplazada: 'This card was replaced and is no longer valid.',
      impresa_vencida: 'The printed card belongs to a previous term.',
    },
  },
  de: {
    locale: 'de-DE', title: 'Digitaler Studierendenausweis', kicker: 'IDENTIFIKATION', front: 'Vorderseite', back: 'Rückseite',
    cardTitle: 'STUDIERENDENAUSWEIS', studentId: 'Matrikelnummer', program: 'Studiengang', degree: 'Abschluss', unit: 'Standort',
    validUntil: 'Gültig bis', period: 'Semester', folio: 'Nummer', valid: 'Gültig', notValid: 'Ungültig',
    scan: 'Scannen Sie den Code, um Echtheit und Gültigkeit dieses Ausweises zu prüfen.',
    renew: s => `Der Code wird in ${s} s erneuert`, download: 'Zum Drucken herunterladen (PDF)', openVerify: 'Prüfung öffnen',
    noPhoto: 'Ihr Ausweis hat kein Foto. Fügen Sie eines unter Mein Profil hinzu.', goProfile: 'Zu Mein Profil',
    loading: 'Ausweis wird geladen…', error: 'Der Ausweis konnte nicht geladen werden.', downloadError: 'Der Ausweis konnte nicht heruntergeladen werden.',
    expired: 'Ihre Sitzung ist abgelaufen.', photoAlt: nombre => `Foto von ${nombre}`, qrAlt: 'QR-Code zur Prüfung',
    verifyTitle: 'Ausweisprüfung', verifyIntro: 'Ergebnis der Abfrage in den SINAC-NEXT-Daten.',
    verifying: 'Ausweis wird geprüft…', resultValid: 'AUSWEIS GÜLTIG', resultNotValid: 'AUSWEIS NICHT GÜLTIG',
    resultInvalid: 'AUSWEIS UNGÜLTIG', checkedAt: 'Geprüft am', home: 'Zur Startseite', name: 'Name',
    reasons: {
      baja: 'Die Person ist exmatrikuliert.', egresado: 'Die Person hat das Studium abgeschlossen.', sin_inscripcion: 'Keine Einschreibung in einem Semester.',
      periodo_concluido: 'Das Semester ist beendet; Verlängerung bei Rückmeldung.', firma: 'Der Code stammt nicht von SINAC NEXT oder wurde verändert.',
      qr_expirado: 'Der Bildschirmcode ist abgelaufen. Bitte den aktuellen Code zeigen lassen.', reemplazada: 'Dieser Ausweis wurde ersetzt und ist ungültig.',
      impresa_vencida: 'Der gedruckte Ausweis gehört zu einem früheren Semester.',
    },
  },
  zh: {
    locale: 'zh-CN', title: '电子学生证', kicker: '身份识别', front: '正面', back: '背面',
    cardTitle: '学生证', studentId: '学号', program: '专业', degree: '学位', unit: '校区',
    validUntil: '有效期至', period: '学期', folio: '编号', valid: '有效', notValid: '无效',
    scan: '扫描二维码以验证此学生证的真实性和有效性。',
    renew: s => `二维码将在 ${s} 秒后刷新`, download: '下载打印版 (PDF)', openVerify: '打开验证页面',
    noPhoto: '你的学生证没有照片。请在“我的资料”中添加。', goProfile: '前往我的资料',
    loading: '正在加载学生证…', error: '无法加载学生证。', downloadError: '无法下载学生证。',
    expired: '会话已过期。', photoAlt: nombre => `${nombre} 的照片`, qrAlt: '验证二维码',
    verifyTitle: '学生证验证', verifyIntro: 'SINAC NEXT 记录查询结果。',
    verifying: '正在验证学生证…', resultValid: '学生证有效', resultNotValid: '学生证已失效',
    resultInvalid: '学生证无效', checkedAt: '查询时间', home: '返回首页', name: '姓名',
    reasons: {
      baja: '该学生已退学。', egresado: '该学生已毕业。', sin_inscripcion: '该学生未在任何学期注册。',
      periodo_concluido: '学期已结束；重新注册后自动续期。', firma: '该代码并非由 SINAC NEXT 签发或已被篡改。',
      qr_expirado: '屏幕二维码已过期，请让学生出示最新代码。', reemplazada: '此学生证已补办，旧证无效。',
      impresa_vencida: '打印版学生证属于以前的学期。',
    },
  },
  pt: {
    locale: 'pt-BR', title: 'Carteirinha digital', kicker: 'IDENTIFICAÇÃO', front: 'Frente', back: 'Verso',
    cardTitle: 'CARTEIRA DE ESTUDANTE', studentId: 'Matrícula', program: 'Programa', degree: 'Grau', unit: 'Unidade',
    validUntil: 'Válida até', period: 'Período', folio: 'Número', valid: 'Válida', notValid: 'Não válida',
    scan: 'Escaneie o código para verificar a autenticidade e a validade desta carteirinha.',
    renew: s => `O código é renovado em ${s} s`, download: 'Baixar para imprimir (PDF)', openVerify: 'Abrir verificação',
    noPhoto: 'Sua carteirinha não tem foto. Adicione-a em Meu perfil.', goProfile: 'Ir para Meu perfil',
    loading: 'Carregando sua carteirinha…', error: 'Não foi possível carregar a carteirinha.', downloadError: 'Não foi possível baixar a carteirinha.',
    expired: 'Sua sessão expirou.', photoAlt: nombre => `Foto de ${nombre}`, qrAlt: 'Código QR de verificação',
    verifyTitle: 'Verificação de carteirinha', verifyIntro: 'Resultado da consulta nos registros do SINAC NEXT.',
    verifying: 'Verificando carteirinha…', resultValid: 'CARTEIRINHA VÁLIDA', resultNotValid: 'CARTEIRINHA NÃO VÁLIDA',
    resultInvalid: 'CARTEIRINHA INVÁLIDA', checkedAt: 'Consultado em', home: 'Ir para o início', name: 'Nome',
    reasons: {
      baja: 'O aluno foi desligado.', egresado: 'O aluno já concluiu o programa.', sin_inscripcion: 'O aluno não está inscrito em nenhum período.',
      periodo_concluido: 'O período terminou; renova-se com a rematrícula.', firma: 'O código não foi emitido pelo SINAC NEXT ou foi alterado.',
      qr_expirado: 'O código da tela expirou. Peça ao aluno o código atualizado.', reemplazada: 'Esta carteirinha foi substituída e não é mais válida.',
      impresa_vencida: 'A carteirinha impressa pertence a um período anterior.',
    },
  },
};

export function useCredencialCopy() {
  const {language} = useLanguage();
  return textos[language] || textos.es;
}

export function formatoFechaCorta(valor, locale) {
  if (!valor) return '—';
  const fecha = /^\d{4}-\d{2}-\d{2}$/.test(valor) ? new Date(`${valor}T12:00:00`) : new Date(valor);
  return Number.isNaN(fecha.getTime()) ? '—' : fecha.toLocaleDateString(locale, {day: '2-digit', month: 'short', year: 'numeric'});
}
