import React, {useState, useEffect, useRef} from 'react';
import {createPortal} from 'react-dom';
import LoadingScreen from './components/LoadingScreen';
import Navbar from './components/Navbar';
import HomePage from './components/HomePage';
import AspirantRegistration from './components/AspirantRegistration';
import LoginView from './components/LoginView';
import PanelAspirante from './components/PanelAspirante';
import PanelAdministrador from './components/PanelAdministrador';
import PanelAlumno from './components/PanelAlumno';
import PanelCoordinacion from './components/PanelCoordinacion';
import PanelDocente from './components/PanelDocente';
import PanelDirector from './components/PanelDirector';
import PanelServiciosEscolares from './components/PanelServiciosEscolares';
import AvisoPrivacidad from './components/AvisoPrivacidad';
import Footer from './components/Footer';
import NotificationBell from './components/NotificationBell';
import './styles.css';
import './components/Navbar.css';
import './components/Footer.css';
import './components/RegistrationPrivacyGate.css';
import './components/Login.css';

const ROLE_HOME_VIEW = {
  aspirante: 'panel',
  alumno: 'alumno-panel',
  docente: 'docente-panel',
  director: 'director-panel',
  coordinacion: 'coordinacion-panel',
  servicios: 'servicios-panel',
  admin: 'admin-panel',
};

const ROLE_VIEW_ACCESS = Object.fromEntries(Object.entries(ROLE_HOME_VIEW).map(([role, view]) => [view, [role]]));

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
  return access ? {access, role} : null;
}

function normalizedRole(role) {
  const value = String(role || 'aspirante').trim().toLowerCase();
  if (value === 'teacher' || value === 'profesor') return 'docente';
  return ['servicios_escolares', 'servicios escolares'].includes(value) ? 'servicios' : value;
}

export default function App(){
  const [loading, setLoading]                 = useState(true);
  const [view, setView]                       = useState('home');
  const [displayView, setDisplayView]         = useState('home');
  const [isViewTransitioning, setIsViewTransitioning] = useState(false);
  const [session, setSession]                 = useState(() => getSession());
  const [toastMessage, setToastMessage]       = useState('');
  const switchTimerRef = useRef(null);

  useEffect(()=>{
    const t = setTimeout(()=> setLoading(false), 2200);
    return ()=> clearTimeout(t);
  },[]);

  useEffect(() => {
    return () => {
      if (switchTimerRef.current) clearTimeout(switchTimerRef.current);
    };
  }, []);

  function handleNavigate(target, nextSession = session){
    const role = normalizedRole(nextSession?.role);
    const allowedRoles = ROLE_VIEW_ACCESS[target];
    if (allowedRoles && (!nextSession || !allowedRoles.includes(role))) {
      setToastMessage('No tienes permisos para acceder a esa sección.');
      target = nextSession ? ROLE_HOME_VIEW[role] || 'panel' : 'login';
    }
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
    const target = ROLE_HOME_VIEW[authenticatedRole] || 'panel';
    handleNavigate(target, authenticatedSession);
  }

  useEffect(() => {
    if (!session) return;
    const timeoutId = window.setTimeout(() => {
      handleLogout('Tu sesión ha expirado por inactividad. Inicia sesión nuevamente.');
    }, 1000 * 60 * 60);
    return () => window.clearTimeout(timeoutId);
  }, [session]);

  function handleLogout(reason = 'Tu sesión ha finalizado. Inicia sesión nuevamente para continuar.'){
    clearAuthStorage();
    setSession(null);
    setToastMessage(reason);
    handleNavigate('home');
  }

  return (
    <div className={`app-root ${!loading ? 'loaded' : ''}`}>
      <LoadingScreen />
      <Navbar onNavigate={handleNavigate} activeView={view} session={session} onLogout={handleLogout} />
      <main className={`main-content view-transition ${isViewTransitioning ? 'is-switching' : ''}`}>
        {toastMessage && createPortal(
          <SessionToast message={toastMessage} onClose={() => setToastMessage('')} />,
          document.body
        )}
        {displayView === 'home'   && <HomePage />}
        {displayView === 'privacy' && <AvisoPrivacidad onNavigate={handleNavigate} />}
        {displayView === 'portal' && <AspirantRegistration />}
        {displayView === 'login'  && (
          <LoginView
            onBackHome={()=>handleNavigate('home')}
            onLoginSuccess={handleLoginSuccess}
          />
        )}
            {displayView === 'panel'  && (
              normalizedRole(session?.role) === 'aspirante'
            ? <PanelAspirante session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'admin-panel' && (
          normalizedRole(session?.role) === 'admin'
            ? <PanelAdministrador session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'coordinacion-panel' && (
          normalizedRole(session?.role) === 'coordinacion'
            ? <PanelCoordinacion session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'alumno-panel' && (
          normalizedRole(session?.role) === 'alumno'
            ? <PanelAlumno session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'docente-panel' && (
          normalizedRole(session?.role) === 'docente'
            ? <PanelDocente session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'director-panel' && (
          normalizedRole(session?.role) === 'director'
            ? <PanelDirector session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'servicios-panel' && (
          normalizedRole(session?.role) === 'servicios' ? <PanelServiciosEscolares session={session} onLogout={handleLogout} /> : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
      </main>
      {session && ['aspirante', 'alumno'].includes(normalizedRole(session.role)) && <NotificationBell session={session} />}
      {!loading && <Footer onNavigate={handleNavigate} />}
    </div>
  )
}
