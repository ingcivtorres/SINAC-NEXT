import React, {useState, useEffect, useRef} from 'react';
import LoadingScreen from './components/LoadingScreen';
import Navbar from './components/Navbar';
import HomePage from './components/HomePage';
import AspirantRegistration from './components/AspirantRegistration';
import LoginView from './components/LoginView';
import Footer from './components/Footer';
import './styles.css';

export default function App(){
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('home');
  const [displayView, setDisplayView] = useState('home');
  const [isViewTransitioning, setIsViewTransitioning] = useState(false);
  const switchTimerRef = useRef(null);

  useEffect(()=>{
    const t = setTimeout(()=> setLoading(false), 1400);
    return ()=> clearTimeout(t);
  },[]);

  useEffect(() => {
    return () => {
      if (switchTimerRef.current) {
        clearTimeout(switchTimerRef.current);
      }
    };
  }, []);

  function handleNavigate(target){
    setView(target);
    if (target === displayView) return;

    if (switchTimerRef.current) {
      clearTimeout(switchTimerRef.current);
    }

    setIsViewTransitioning(true);
    switchTimerRef.current = setTimeout(() => {
      setDisplayView(target);
      setIsViewTransitioning(false);
    }, 240);
  }

  return (
    <div className={`app-root ${!loading ? 'loaded' : ''}`}>
      <LoadingScreen />
      <Navbar onNavigate={handleNavigate} activeView={view} />
      <main className={`main-content view-transition ${isViewTransitioning ? 'is-switching' : ''}`}>
        {displayView === 'home' && <HomePage />}
        {displayView === 'portal' && <AspirantRegistration />}
        {displayView === 'login' && <LoginView onBackHome={() => handleNavigate('home')} />}
      </main>
      {!loading && <Footer />}
    </div>
  )
}
