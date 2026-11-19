import React, {Suspense, lazy, useState, useEffect, useRef} from 'react';
import {createPortal} from 'react-dom';
import LoadingScreen from './components/LoadingScreen';
import LogoutModal from './components/LogoutModal';
import Navbar from './components/Navbar';
import HomePage from './components/HomePage';
import AspirantRegistration from './components/AspirantRegistration';
import LoginView from './components/LoginView';
import AvisoPrivacidad from './components/AvisoPrivacidad';
import Footer from './components/Footer';
import ContactPage from './components/ContactPage';
import NotificationBell from './components/NotificationBell';
import ErrorPage from './components/ErrorPage';
import ErrorBoundary from './components/ErrorBoundary';
import AccessibilityStatement from './components/AccessibilityStatement';
import {cerrarSesionServidor} from './auth';
import {instalarGestorModales} from './a11yModales';
import {instalarMejorasTablas} from './a11yTablas';
import {homeViewForRole, isDocentePanelRole, normalizedRole, ROLE_HOME_VIEW, ROLE_VIEW_ACCESS} from './roles';
import {useLanguage} from './translations';
import './styles.css';
import './components/Navbar.css';
import './components/Footer.css';
import './components/RegistrationPrivacyGate.css';
import './components/Login.css';

const PanelAspirante = lazy(() => import('./components/PanelAspirante'));
const PanelAdministrador = lazy(() => import('./components/PanelAdministrador'));
const PanelAlumno = lazy(() => import('./components/PanelAlumno'));
const PanelCoordinacion = lazy(() => import('./components/PanelCoordinacion'));
const PanelDocente = lazy(() => import('./components/PanelDocente'));
const PanelDirector = lazy(() => import('./components/PanelDirector'));
const PanelServiciosEscolares = lazy(() => import('./components/PanelServiciosEscolares'));
const VerificarCredencial = lazy(() => import('./components/VerificarCredencial'));

const PUBLIC_VIEWS = ['home', 'contact', 'privacy', 'accessibility', 'portal', 'login', 'verify', 'error-403', 'error-404'];
const VERIFY_PATH = /^\/verificar\/([^/]+)$/;

const VIEW_TITLE_KEYS = {
  home: 'navbar.home',
  contact: 'navbar.contact',
  privacy: 'page.privacy',
  accessibility: 'page.accessibility',
  portal: 'navbar.portal',
  login: 'login.signIn',
  verify: 'page.verify',
  panel: 'navbar.panel',
  'alumno-panel': 'navbar.alumnoPanel',
  'docente-panel': 'navbar.docentePanel',
  'director-panel': 'role.director',
  'coordinacion-panel': 'navbar.coordinacionPanel',
  'servicios-panel': 'role.servicios',
  'admin-panel': 'navbar.adminPanel',
  'error-403': 'page.error403',
  'error-404': 'page.error404',
};
const KNOWN_VIEWS = new Set([...PUBLIC_VIEWS, ...Object.values(ROLE_HOME_VIEW)]);

function clearAuthStorage(){
  localStorage.removeItem('sinac_access');
  localStorage.removeItem('sinac_refresh');
  localStorage.removeItem('sinac_role');
  sessionStorage.removeItem('sinac_access');
  sessionStorage.removeItem('sinac_refresh');
  sessionStorage.removeItem('sinac_role');
}

function SessionToast({message, onClose}){
  useEffect(() => {
    const timeoutId = window.setTimeout(onClose, 3200);
    return () => window.clearTimeout(timeoutId);
  }, [onClose]);

  return (
    <div className="session-toast" role="status" aria-live="polite">
      <strong>Sesión</strong>
      <span>{message}</span>
    </div>
  );
}

function getSession(){
  const access = localStorage.getItem('sinac_access') || sessionStorage.getItem('sinac_access');
  const role   = localStorage.getItem('sinac_role')   || sessionStorage.getItem('sinac_role');
  return access ? {access, role: normalizedRole(role)} : null;
}

function initialView() {
  const path = window.location.pathname.replace(/\/+$/, '');
  if (path === '/restablecer') return 'login';
  if (VERIFY_PATH.test(path)) return 'verify';
  if (path === '' || path === '/index.html') {
    const session = getSession();
    return session ? homeViewForRole(session.role) : 'home';
  }
  return 'error-404';
}

export default function App(){
  const [loading, setLoading]                 = useState(true);
  const [view, setView]                       = useState(initialView);
  const [displayView, setDisplayView]         = useState(initialView);
  const [notFoundPath]                        = useState(() => window.location.pathname);
  const [verifyToken]                         = useState(() => window.location.pathname.replace(/\/+$/, '').match(VERIFY_PATH)?.[1] || '');
  const [isViewTransitioning, setIsViewTransitioning] = useState(false);
  const [session, setSession]                 = useState(() => getSession());
  const [toastMessage, setToastMessage]       = useState('');
  const [pendingLogoutReason, setPendingLogoutReason] = useState(null);
  const switchTimerRef = useRef(null);
  const {t} = useLanguage();
  const [viewAnnouncement, setViewAnnouncement] = useState('');
  const firstViewRender = useRef(true);
  const viewTitle = t(VIEW_TITLE_KEYS[displayView] || 'navbar.home');

  useEffect(() => instalarGestorModales(), []);
  useEffect(() => instalarMejorasTablas(), []);

  useEffect(() => {
    document.title = `${viewTitle} · SINAC NEXT`;
  }, [viewTitle]);

  useEffect(() => {
    if (firstViewRender.current) {
      firstViewRender.current = false;
      return undefined;
    }
    setViewAnnouncement(`${t('page.loaded')}: ${viewTitle}`);
    const frame = window.requestAnimationFrame(() => {
      const main = document.getElementById('contenido-principal');
      if (!main || main.contains(document.activeElement)) return;
      const heading = main.querySelector('h1, h2');
      if (heading) {
        if (!heading.hasAttribute('tabindex')) heading.setAttribute('tabindex', '-1');
        heading.focus({preventScroll: true});
      } else {
        main.focus({preventScroll: true});
      }
      window.scrollTo({top: 0});
    });
    return () => window.cancelAnimationFrame(frame);
    // Solo debe reaccionar al cambio de vista, no al cambio de idioma.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayView]);

  useEffect(()=>{
    const t = setTimeout(()=> setLoading(false), 2200);
    return ()=> clearTimeout(t);
  },[]);

  useEffect(() => {
    return () => {
      if (switchTimerRef.current) clearTimeout(switchTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const actualizarToken = (event) => setSession(actual => actual ? {...actual, access: event.detail} : actual);
    window.addEventListener('sinac:token', actualizarToken);
    return () => window.removeEventListener('sinac:token', actualizarToken);
  }, []);

  function handleNavigate(target, nextSession = session){
    const role = normalizedRole(nextSession?.role);
    const allowedRoles = ROLE_VIEW_ACCESS[target];
    if (!KNOWN_VIEWS.has(target)) target = 'error-404';
    else if (allowedRoles && !nextSession) target = 'login';
    else if (allowedRoles && !allowedRoles.includes(role)) target = 'error-403';
    if (!target.startsWith('error-') && window.location.pathname !== '/') window.history.replaceState(null, '', '/');
    setView(target);
    if (target === displayView) return;
    if (switchTimerRef.current) clearTimeout(switchTimerRef.current);
    setIsViewTransitioning(true);
    switchTimerRef.current = setTimeout(() => {
      setDisplayView(target);
      setIsViewTransitioning(false);
    }, 240);
  }

  function handleLoginSuccess(sess){
    const authenticatedRole = normalizedRole(sess.role);
    const authenticatedSession = {...sess, role: authenticatedRole};
    setSession(authenticatedSession);
    handleNavigate(homeViewForRole(authenticatedRole), authenticatedSession);
  }

  const sesionActiva = Boolean(session);
  useEffect(() => {
    if (!sesionActiva) return;
    const timeoutId = window.setTimeout(() => {
      handleLogout('Tu sesión ha expirado por inactividad. Inicia sesión nuevamente.');
    }, 1000 * 60 * 60);
    return () => window.clearTimeout(timeoutId);
  }, [sesionActiva]);

  function handleLogout(reason = 'Tu sesión ha finalizado. Inicia sesión nuevamente para continuar.'){
    cerrarSesionServidor();
    clearAuthStorage();
    if (switchTimerRef.current) clearTimeout(switchTimerRef.current);
    switchTimerRef.current = null;
    setSession(null);
    setToastMessage(reason);
    setView('home');
    setDisplayView('home');
    setIsViewTransitioning(false);
  }

  function requestLogout(reason){
    setPendingLogoutReason(reason || 'Tu sesión ha finalizado. Inicia sesión nuevamente para continuar.');
  }

  function confirmLogout(){
    const reason = pendingLogoutReason;
    setPendingLogoutReason(null);
    handleLogout(reason);
  }

  return (
    <div className={`app-root ${!loading ? 'loaded' : ''}`}>
      <LoadingScreen />
      <div className="a11y-sr-only" role="status" aria-live="polite">{viewAnnouncement}</div>
      {pendingLogoutReason && createPortal(
        <LogoutModal onCancel={() => setPendingLogoutReason(null)} onConfirm={confirmLogout} />,
        document.body
      )}
      <Navbar onNavigate={handleNavigate} activeView={view} session={session} onLogout={requestLogout} />
      <main id="contenido-principal" tabIndex={-1} className={`main-content view-transition ${isViewTransitioning ? 'is-switching' : ''}`}>
        {toastMessage && createPortal(
          <SessionToast message={toastMessage} onClose={() => setToastMessage('')} />,
          document.body
        )}
        <ErrorBoundary resetKey={displayView} onHome={() => handleNavigate('home')}>
        <Suspense fallback={<div className="panel-cargando" role="status">Cargando…</div>}>
        {displayView === 'error-404' && <ErrorPage code={404} path={notFoundPath} onHome={() => handleNavigate('home')} onBack={window.history.length > 1 ? () => window.history.back() : undefined} />}
        {displayView === 'error-403' && <ErrorPage code={403} onHome={() => handleNavigate(session ? homeViewForRole(session.role) : 'home')} />}
        {displayView === 'home'   && <HomePage />}
        {displayView === 'contact' && <ContactPage onNavigate={handleNavigate} />}
        {displayView === 'privacy' && <AvisoPrivacidad onNavigate={handleNavigate} />}
        {displayView === 'accessibility' && <AccessibilityStatement onNavigate={handleNavigate} />}
        {displayView === 'portal' && <AspirantRegistration />}
        {displayView === 'verify' && <VerificarCredencial token={verifyToken} onHome={() => handleNavigate('home')} />}
        {displayView === 'login'  && (
          <LoginView
            onBackHome={()=>handleNavigate('home')}
            onLoginSuccess={handleLoginSuccess}
          />
        )}
            {displayView === 'panel'  && (
              session && normalizedRole(session.role) === 'aspirante'
            ? <PanelAspirante session={session} onLogout={requestLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'admin-panel' && (
          session && normalizedRole(session.role) === 'admin'
            ? <PanelAdministrador session={session} onLogout={requestLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'coordinacion-panel' && (
          session && normalizedRole(session.role) === 'coordinacion'
            ? <PanelCoordinacion session={session} onLogout={requestLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'alumno-panel' && (
          session && normalizedRole(session.role) === 'alumno'
            ? <PanelAlumno session={session} onLogout={requestLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'docente-panel' && (
          session && isDocentePanelRole(session.role)
            ? <PanelDocente session={session} onLogout={requestLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'director-panel' && (
          session && normalizedRole(session.role) === 'director'
            ? <PanelDirector session={session} onLogout={requestLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'servicios-panel' && (
          session && normalizedRole(session.role) === 'servicios' ? <PanelServiciosEscolares session={session} onLogout={requestLogout} /> : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        </Suspense>
        </ErrorBoundary>
      </main>
      {session && <NotificationBell session={session} />}
      {!loading && <Footer onNavigate={handleNavigate} />}
    </div>
  )
}
