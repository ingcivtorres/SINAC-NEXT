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

  function handleNavigate(target){
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
    setSession(sess);
    const authenticatedRole = String(sess.role || 'aspirante').trim().toLowerCase();
    const target = authenticatedRole === 'admin'
      ? 'admin-panel'
      : authenticatedRole === 'coordinacion'
        ? 'coordinacion-panel'
        : authenticatedRole === 'docente'
          ? 'docente-panel'
          : authenticatedRole === 'alumno'
          ? 'alumno-panel'
            : authenticatedRole === 'director'
              ? 'director-panel'
              : authenticatedRole === 'servicios' || authenticatedRole === 'servicios_escolares'
                ? 'servicios-panel'
              : 'panel';
    handleNavigate(target);
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
          session
            ? <PanelAspirante session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'admin-panel' && (
          session
            ? <PanelAdministrador session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'coordinacion-panel' && (
          session
            ? <PanelCoordinacion session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'alumno-panel' && (
          session
            ? <PanelAlumno session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'docente-panel' && (
          session
            ? <PanelDocente session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'director-panel' && (
          session
            ? <PanelDirector session={session} onLogout={handleLogout} />
            : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
        {displayView === 'servicios-panel' && (
          session ? <PanelServiciosEscolares session={session} onLogout={handleLogout} /> : <LoginView onBackHome={()=>handleNavigate('home')} onLoginSuccess={handleLoginSuccess}/>
        )}
      </main>
      {session && <NotificationBell session={session} />}
      {!loading && <Footer onNavigate={handleNavigate} />}
    </div>
  )
}
