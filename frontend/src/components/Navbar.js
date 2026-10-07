import React, {useState, useEffect} from 'react';
import cinvestavLogo from '../assets/logo2civ-removebg-preview.png';
import sinacLogo from '../assets/SINAC5-removebg-preview.png';
import {supportedLanguages, useLanguage} from '../translations';

export default function Navbar({onNavigate, activeView, session, onLogout}){
  const {t, language, setLanguage} = useLanguage();
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

  function changeLanguage(lang){
    setLanguage(lang)
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
          aria-label={t('navbar.toggleTheme')}
          title={theme === 'dark' ? t('navbar.toggleThemeDark') : t('navbar.toggleThemeLight')}
        >
          <span>{theme === 'dark' ? '🌙' : '☀️'}</span>
        </button>
        <label className="language-selector" aria-label="Selector de idioma">
          <span className="language-selector-icon" aria-hidden="true">文</span>
          <select value={language} onChange={(event) => changeLanguage(event.target.value)}>
            {supportedLanguages.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
          </select>
        </label>
        <div className="menu-dropdown">
          <button className="menu" aria-expanded="false" aria-haspopup="true">☰</button>
          <div className="dropdown-menu">
            <button type="button" className={`dropdown-item ${activeView === 'home' ? 'active' : ''}`} onClick={()=>navigateTo('home')}>{t('navbar.home')}</button>
            <button type="button" className={`dropdown-item ${activeView === 'portal' ? 'active' : ''}`} onClick={()=>navigateTo('portal')}>{t('navbar.portal')}</button>
            {session
              ? <>
                  <button type="button" className={`dropdown-item ${(activeView === 'panel' || activeView === 'alumno-panel' || activeView === 'admin-panel' || activeView === 'coordinacion-panel' || activeView === 'docente-panel' || activeView === 'director-panel' || activeView === 'servicios-panel') ? 'active' : ''}`} onClick={()=>navigateTo(session.role === 'admin' ? 'admin-panel' : session.role === 'coordinacion' ? 'coordinacion-panel' : session.role === 'docente' ? 'docente-panel' : session.role === 'director' ? 'director-panel' : session.role === 'servicios' ? 'servicios-panel' : session.role === 'alumno' ? 'alumno-panel' : 'panel')}>
                    {session.role === 'admin' ? t('navbar.adminPanel') : session.role === 'coordinacion' ? t('navbar.coordinacionPanel') : session.role === 'docente' ? t('navbar.docentePanel') : session.role === 'director' ? t('role.director') : session.role === 'servicios' ? t('role.servicios') : session.role === 'alumno' ? t('navbar.alumnoPanel') : t('navbar.panel')}
                  </button>
                  <button type="button" className="dropdown-item dropdown-full" onClick={() => onLogout && onLogout(t('navbar.logoutMessage'))}>{t('navbar.logout')}</button>
                </>
              : <button type="button" className={`dropdown-item ${activeView === 'login' ? 'active' : ''}`} onClick={()=>navigateTo('login')}>{t('login.signIn')}</button>
            }
            <button type="button" className="dropdown-item dropdown-full">{t('navbar.contact')}</button>
          </div>
        </div>
      </div>
    </header>
  )
}
