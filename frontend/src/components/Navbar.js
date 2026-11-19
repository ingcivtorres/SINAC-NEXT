import React, {useState, useEffect} from 'react';
import cinvestavLogo from '../assets/logo2civ-removebg-preview.png';
import sinacLogo from '../assets/SINAC5-removebg-preview.png';
import {supportedLanguages, useLanguage} from '../translations';
import Flag from './Flag';
import AccessibilityMenu from './AccessibilityMenu';
import useDisclosure from './useDisclosure';
import {homeViewForRole, normalizedRole, panelLabelKey} from '../roles';

const MAIN_CONTENT_ID = 'contenido-principal';
const NAV_MENU_ID = 'sinac-menu-navegacion';
const LANGUAGE_MENU_ID = 'sinac-menu-idioma';

export default function Navbar({onNavigate, activeView, session, onLogout}){
  const {t, language, setLanguage} = useLanguage();
  const languageMenu = useDisclosure();
  const navMenu = useDisclosure();
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

  function toggleTheme(){
    setTheme(t => t === 'light' ? 'dark' : 'light')
  }

  function changeLanguage(lang){
    setLanguage(lang)
    languageMenu.closeAndReturnFocus()
  }

  function navigateTo(view){
    navMenu.setOpen(false)
    if (typeof onNavigate === 'function') {
      onNavigate(view)
    }
  }

  function skipToContent(event){
    const main = document.getElementById(MAIN_CONTENT_ID);
    if (!main) return;
    event.preventDefault();
    main.focus();
    main.scrollIntoView({block: 'start'});
  }

  const role = session ? normalizedRole(session.role) : null;
  const rolePanel = role ? homeViewForRole(role) : null;
  const rolePanelActive = Boolean(role) && (
    ['panel', 'alumno-panel', 'admin-panel', 'coordinacion-panel', 'director-panel', 'servicios-panel'].includes(activeView)
    || (activeView === 'docente-panel' && role !== 'director')
  );

  function navItem(view, label, {active = activeView === view, full = false} = {}){
    return (
      <button
        type="button"
        className={`dropdown-item ${full ? 'dropdown-full' : ''} ${active ? 'active' : ''}`}
        aria-current={active ? 'page' : undefined}
        onClick={() => navigateTo(view)}
      >
        {label}
      </button>
    );
  }

  return (
    <>
      <a href={`#${MAIN_CONTENT_ID}`} className="skip-link" onClick={skipToContent}>{t('navbar.skipToContent')}</a>
      <header className="site-header">
        <div className="left">
          <img src={cinvestavLogo} alt="Cinvestav" className="logo small" />
          <img src={sinacLogo} alt="SINAC NEXT" className="logo small sinac" />
        </div>
        <div className="right">
          <AccessibilityMenu />
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-pressed={theme === 'dark'}
            aria-label={t('navbar.toggleTheme')}
            title={theme === 'dark' ? t('navbar.toggleThemeDark') : t('navbar.toggleThemeLight')}
          >
            <span aria-hidden="true">{theme === 'dark' ? '🌙' : '☀️'}</span>
          </button>
          <div className="language-picker" ref={languageMenu.wrapperRef} onBlur={languageMenu.onWrapperBlur}>
            <button
              type="button"
              ref={languageMenu.triggerRef}
              className="language-picker-trigger"
              aria-expanded={languageMenu.open}
              aria-controls={LANGUAGE_MENU_ID}
              onClick={() => languageMenu.open ? languageMenu.setOpen(false) : languageMenu.openWithFocus('selected')}
              onKeyDown={languageMenu.onTriggerKeyDown}
            >
              <span className="a11y-sr-only">{t('navbar.language')}: </span>
              <span className="language-picker-flag" aria-hidden="true"><Flag code={selectedLanguage.code}/></span>
              <span className="language-picker-label">{selectedLanguage.label}</span>
              <span className="language-picker-short">{selectedLanguage.short}</span>
              <span className="language-picker-chevron" aria-hidden="true">▾</span>
            </button>
            {languageMenu.open && (
              <div
                id={LANGUAGE_MENU_ID}
                ref={languageMenu.listRef}
                className="language-picker-menu"
                role="group"
                aria-label={t('navbar.language')}
              >
                {supportedLanguages.map(item => (
                  <button
                    type="button"
                    lang={item.code}
                    aria-pressed={language === item.code}
                    className={`language-picker-option ${language === item.code ? 'active' : ''}`}
                    key={item.code}
                    onClick={() => changeLanguage(item.code)}
                  >
                    <span className="language-picker-flag" aria-hidden="true"><Flag code={item.code}/></span>
                    <span>{item.label}</span>
                    <span className="language-picker-code" aria-hidden="true">{item.short}</span>
                    {language === item.code && <span className="language-picker-check" aria-hidden="true">✓</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div
            className={`menu-dropdown ${navMenu.open ? 'open' : ''}`}
            ref={navMenu.wrapperRef}
            onBlur={navMenu.onWrapperBlur}
          >
            <button
              type="button"
              ref={navMenu.triggerRef}
              className="menu"
              aria-label={navMenu.open ? t('navbar.closeMenu') : t('navbar.openMenu')}
              aria-expanded={navMenu.open}
              aria-controls={NAV_MENU_ID}
              onClick={() => navMenu.open ? navMenu.setOpen(false) : navMenu.openWithFocus('first')}
              onKeyDown={navMenu.onTriggerKeyDown}
            >
              <span aria-hidden="true">☰</span>
            </button>
            <nav
              id={NAV_MENU_ID}
              ref={navMenu.listRef}
              className="dropdown-menu"
              aria-label={t('navbar.mainNavigation')}
            >
              {navItem('home', t('navbar.home'))}
              {!session && navItem('portal', t('navbar.portal'))}
              {session
                ? <>
                    {role === 'director' && navItem('docente-panel', t('navbar.docentePanel'))}
                    {navItem(rolePanel, t(panelLabelKey(role)), {active: rolePanelActive})}
                    <button type="button" className="dropdown-item dropdown-full" onClick={() => { navMenu.setOpen(false); onLogout && onLogout(t('navbar.logoutMessage')); }}>{t('navbar.logout')}</button>
                  </>
                : navItem('login', t('login.signIn'))
              }
              {navItem('contact', t('navbar.contact'), {full: true})}
            </nav>
          </div>
        </div>
      </header>
    </>
  )
}
