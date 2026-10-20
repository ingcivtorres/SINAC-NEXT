import React, {useState, useEffect, useRef} from 'react';
import cinvestavLogo from '../assets/logo2civ-removebg-preview.png';
import sinacLogo from '../assets/SINAC5-removebg-preview.png';
import {supportedLanguages, useLanguage} from '../translations';
import Flag from './Flag';

export default function Navbar({onNavigate, activeView, session, onLogout}){
  const {t, language, setLanguage} = useLanguage();
  const [languageMenuOpen, setLanguageMenuOpen] = useState(false);
  const languageMenuRef = useRef(null);
  const selectedLanguage = supportedLanguages.find(item => item.code === language) || supportedLanguages[0];
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

  useEffect(() => {
    if (!languageMenuOpen) return undefined;
    function closeOnOutsideClick(event) {
      if (!languageMenuRef.current?.contains(event.target)) setLanguageMenuOpen(false);
    }
    function closeOnEscape(event) {
      if (event.key === 'Escape') setLanguageMenuOpen(false);
    }
    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [languageMenuOpen]);

  function toggleTheme(){
    setTheme(t => t === 'light' ? 'dark' : 'light')
  }

  function changeLanguage(lang){
    setLanguage(lang)
    setLanguageMenuOpen(false)
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
        <div className="language-picker" ref={languageMenuRef}>
          <button
            type="button"
            className="language-picker-trigger"
            aria-label={`${t('navbar.language')}: ${selectedLanguage.label}`}
            aria-expanded={languageMenuOpen}
            aria-haspopup="menu"
            onClick={() => setLanguageMenuOpen(open => !open)}
          >
            <span className="language-picker-flag"><Flag code={selectedLanguage.code}/></span>
            <span className="language-picker-label">{selectedLanguage.label}</span>
            <span className="language-picker-short">{selectedLanguage.short}</span>
            <span className="language-picker-chevron" aria-hidden="true">▾</span>
          </button>
          {languageMenuOpen && (
            <div className="language-picker-menu" role="group" aria-label={t('navbar.language')}>
              {supportedLanguages.map(item => (
                <button
                  type="button"
                  aria-pressed={language === item.code}
                  className={`language-picker-option ${language === item.code ? 'active' : ''}`}
                  key={item.code}
                  onClick={() => changeLanguage(item.code)}
                >
                  <span className="language-picker-flag"><Flag code={item.code}/></span>
                  <span>{item.label}</span>
                  <span className="language-picker-code">{item.short}</span>
                  {language === item.code && <span className="language-picker-check" aria-hidden="true">✓</span>}
                </button>
              ))}
            </div>
          )}
        </div>
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
            <button type="button" className={`dropdown-item dropdown-full ${activeView === 'contact' ? 'active' : ''}`} onClick={() => navigateTo('contact')}>{t('navbar.contact')}</button>
          </div>
        </div>
      </div>
    </header>
  )
}
