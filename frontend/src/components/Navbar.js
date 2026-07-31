import React, {useState, useEffect} from 'react';
import cinvestavLogo from '../assets/logo2civ-removebg-preview.png';
import sinacLogo from '../assets/6-removebg-preview.png';

export default function Navbar({onNavigate, activeView}){
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('sinac_theme') || 'light'
    } catch (e) { return 'light' }
  })

  useEffect(()=>{
    try {
      document.documentElement.setAttribute('data-theme', theme)
      localStorage.setItem('sinac_theme', theme)
    } catch (e) {}
  }, [theme])

  function toggleTheme(){
    setTheme(t => t === 'light' ? 'dark' : 'light')
  }

  function navigateTo(view){
    if (typeof onNavigate === 'function') {
      onNavigate(view)
    }
  }

  return (
    <header className="site-header">
      <div className="left">
        <img src={cinvestavLogo} alt="Cinvestav" className="logo small" />
        <img src={sinacLogo} alt="SINAC NEXT" className="logo small sinac" />
      </div>
      <div className="right">
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          aria-pressed={theme === 'dark'}
          aria-label="Alternar tema claro/oscuro"
          title={theme === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
        >
          <span>{theme === 'dark' ? '🌙' : '☀️'}</span>
        </button>
        <div className="menu-dropdown">
          <button className="menu" aria-expanded="false" aria-haspopup="true">☰</button>
          <div className="dropdown-menu">
            <button type="button" className={`dropdown-item ${activeView === 'home' ? 'active' : ''}`} onClick={()=>navigateTo('home')}>Inicio</button>
            <button type="button" className={`dropdown-item ${activeView === 'portal' ? 'active' : ''}`} onClick={()=>navigateTo('portal')}>Portal Aspirantes</button>
            <button type="button" className={`dropdown-item ${activeView === 'login' ? 'active' : ''}`} onClick={()=>navigateTo('login')}>Iniciar sesión</button>
            <button type="button" className="dropdown-item dropdown-full">Contacto</button>
          </div>
        </div>
        <button className="login" onClick={()=>navigateTo('login')}>Iniciar sesión</button>
      </div>
    </header>
  )
}
