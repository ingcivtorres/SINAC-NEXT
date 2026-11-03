import React from 'react';
import {useLanguage} from '../translations';
import './ErrorPage.css';

const COPY = {
  es: {
    label: 'Error', home: 'Ir al inicio', back: 'Regresar', retry: 'Reintentar', login: 'Iniciar sesión',
    help: 'Si el problema persiste, comunícate con el área de soporte e indica el código mostrado.', path: 'Ruta solicitada',
    codes: {
      400: {title: 'Solicitud no válida', text: 'La información enviada no tiene el formato esperado. Revisa los datos e inténtalo de nuevo.'},
      401: {title: 'Sesión requerida', text: 'Tu sesión expiró o no has iniciado sesión. Ingresa con tus credenciales para continuar.'},
      403: {title: 'Acceso restringido', text: 'No tienes permisos para consultar esta sección. Si crees que es un error, solicita acceso a tu coordinación.'},
      404: {title: 'Página no encontrada', text: 'La página que buscas no existe, cambió de dirección o ya no está disponible.'},
      500: {title: 'Error interno del sistema', text: 'Ocurrió un problema inesperado. Nuestro equipo ya puede revisarlo; intenta nuevamente en unos momentos.'},
      503: {title: 'Servicio no disponible', text: 'El sistema está en mantenimiento o recibe demasiadas solicitudes. Vuelve a intentarlo en unos minutos.'},
    },
  },
  en: {
    label: 'Error', home: 'Go to home', back: 'Go back', retry: 'Try again', login: 'Sign in',
    help: 'If the problem persists, contact support and mention the code shown.', path: 'Requested path',
    codes: {
      400: {title: 'Invalid request', text: 'The submitted information does not have the expected format. Check the data and try again.'},
      401: {title: 'Sign-in required', text: 'Your session expired or you are not signed in. Sign in with your credentials to continue.'},
      403: {title: 'Restricted access', text: 'You do not have permission to view this section. If you think this is a mistake, request access from your coordination office.'},
      404: {title: 'Page not found', text: 'The page you are looking for does not exist, has moved or is no longer available.'},
      500: {title: 'Internal system error', text: 'An unexpected problem occurred. Our team can now review it; please try again in a few moments.'},
      503: {title: 'Service unavailable', text: 'The system is under maintenance or receiving too many requests. Please try again in a few minutes.'},
    },
  },
  de: {
    label: 'Fehler', home: 'Zur Startseite', back: 'Zurück', retry: 'Erneut versuchen', login: 'Anmelden',
    help: 'Wenn das Problem weiterhin besteht, wenden Sie sich an den Support und nennen Sie den angezeigten Code.', path: 'Angeforderter Pfad',
    codes: {
      400: {title: 'Ungültige Anfrage', text: 'Die gesendeten Daten haben nicht das erwartete Format. Prüfen Sie die Angaben und versuchen Sie es erneut.'},
      401: {title: 'Anmeldung erforderlich', text: 'Ihre Sitzung ist abgelaufen oder Sie sind nicht angemeldet. Melden Sie sich an, um fortzufahren.'},
      403: {title: 'Zugriff eingeschränkt', text: 'Sie haben keine Berechtigung für diesen Bereich. Wenn Sie einen Fehler vermuten, beantragen Sie den Zugriff bei Ihrer Koordination.'},
      404: {title: 'Seite nicht gefunden', text: 'Die gesuchte Seite existiert nicht, wurde verschoben oder ist nicht mehr verfügbar.'},
      500: {title: 'Interner Systemfehler', text: 'Ein unerwartetes Problem ist aufgetreten. Bitte versuchen Sie es in einigen Augenblicken erneut.'},
      503: {title: 'Dienst nicht verfügbar', text: 'Das System wird gewartet oder ist überlastet. Bitte versuchen Sie es in einigen Minuten erneut.'},
    },
  },
  zh: {
    label: '错误', home: '返回首页', back: '返回上一页', retry: '重试', login: '登录',
    help: '如果问题仍然存在，请联系支持部门并提供显示的代码。', path: '请求路径',
    codes: {
      400: {title: '请求无效', text: '提交的信息格式不正确。请检查数据后重试。'},
      401: {title: '需要登录', text: '您的会话已过期或尚未登录。请使用您的凭据登录以继续。'},
      403: {title: '访问受限', text: '您无权查看此部分。如认为有误，请向协调部门申请访问权限。'},
      404: {title: '页面未找到', text: '您要查找的页面不存在、已移动或不再可用。'},
      500: {title: '系统内部错误', text: '发生意外问题。请稍后重试。'},
      503: {title: '服务不可用', text: '系统正在维护或请求过多。请几分钟后重试。'},
    },
  },
  pt: {
    label: 'Erro', home: 'Ir para o início', back: 'Voltar', retry: 'Tentar novamente', login: 'Entrar',
    help: 'Se o problema persistir, entre em contato com o suporte e informe o código exibido.', path: 'Caminho solicitado',
    codes: {
      400: {title: 'Solicitação inválida', text: 'As informações enviadas não têm o formato esperado. Revise os dados e tente novamente.'},
      401: {title: 'Login necessário', text: 'Sua sessão expirou ou você não está conectado. Entre com suas credenciais para continuar.'},
      403: {title: 'Acesso restrito', text: 'Você não tem permissão para consultar esta seção. Se achar que é um erro, solicite acesso à sua coordenação.'},
      404: {title: 'Página não encontrada', text: 'A página que você procura não existe, mudou de endereço ou não está mais disponível.'},
      500: {title: 'Erro interno do sistema', text: 'Ocorreu um problema inesperado. Tente novamente em alguns instantes.'},
      503: {title: 'Serviço indisponível', text: 'O sistema está em manutenção ou recebendo muitas solicitações. Tente novamente em alguns minutos.'},
    },
  },
};

const ICONOS = {
  400: 'M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z',
  401: 'M7 11V7a5 5 0 0 1 10 0v4M5 11h14v10H5zM12 15v2',
  403: 'M12 3 4 6v6c0 5 3.4 8.4 8 9 4.6-.6 8-4 8-9V6l-8-3Zm-3 9h6',
  404: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14Zm10 17-4.4-4.4M9 9l4 4m0-4-4 4',
  500: 'M12 2v4m0 12v4M4.9 4.9l2.8 2.8m8.6 8.6 2.8 2.8M2 12h4m12 0h4M4.9 19.1l2.8-2.8m8.6-8.6 2.8-2.8',
  503: 'M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4 2.5-2.5Z',
};

export default function ErrorPage({code = 404, onHome, onBack, onRetry, onLogin, path}) {
  const {language} = useLanguage();
  const copy = COPY[language] || COPY.es;
  const clave = copy.codes[code] ? code : 500;
  const {title, text} = copy.codes[clave];
  return (
    <section className={`error-page error-page--${clave}`} role="alert" aria-labelledby="error-page-title">
      <div className="error-page-glow" aria-hidden="true" />
      <div className="error-page-card">
        <div className="error-page-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={ICONOS[clave]} /></svg>
        </div>
        <p className="error-page-kicker">{copy.label} {clave}</p>
        <div className="error-page-code" aria-hidden="true">{clave}</div>
        <h1 id="error-page-title">{title}</h1>
        <p className="error-page-text">{text}</p>
        {path && <p className="error-page-path"><span>{copy.path}</span><code>{path}</code></p>}
        <div className="error-page-actions">
          {onRetry && <button type="button" className="btn-primary" onClick={onRetry}>{copy.retry}</button>}
          {onLogin && <button type="button" className={onRetry ? 'btn-secondary' : 'btn-primary'} onClick={onLogin}>{copy.login}</button>}
          {onHome && <button type="button" className={onRetry || onLogin ? 'btn-secondary' : 'btn-primary'} onClick={onHome}>{copy.home}</button>}
          {onBack && <button type="button" className="btn-secondary" onClick={onBack}>{copy.back}</button>}
        </div>
        <p className="error-page-help">{copy.help}</p>
      </div>
    </section>
  );
}
