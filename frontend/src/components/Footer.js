import React from 'react';
import cinvestavLogo from '../assets/cinvestav-logo-white-horizontal.png';
import sinacLogo from '../assets/SINAC5-removebg-preview.png';
import {useLanguage} from '../translations';
import {READING_GUIDE_EVENT} from './AccessibilityMenu';

const REDES = [
  {
    nombre: 'Instagram', url: 'https://www.instagram.com/cinvestavoficial',
    icono: <><rect x="3" y="3" width="18" height="18" rx="5" /><circle cx="12" cy="12" r="4" /><circle cx="17.5" cy="6.5" r=".6" fill="currentColor" /></>,
  },
  {
    nombre: 'YouTube', url: 'https://www.youtube.com/c/CinvestavOficial',
    icono: <><path d="M2.5 17a24 24 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.6 49.6 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24 24 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.6 49.6 0 0 1-16.2 0A2 2 0 0 1 2.5 17" /><path d="m10 15 5-3-5-3z" /></>,
  },
  {
    nombre: 'LinkedIn', url: 'https://www.linkedin.com/school/cinvestavipn',
    icono: <><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z" /><rect x="2" y="9" width="4" height="12" /><circle cx="4" cy="4" r="2" /></>,
  },
];

export default function Footer({onNavigate}){
  const {t} = useLanguage();
  const ir = vista => onNavigate && onNavigate(vista);

  return (
    <footer className="site-footer" aria-label={t('footer.aria')}>
      <div className="footer-grid">
        <section className="footer-column footer-identity" aria-labelledby="footer-identidad">
          <h2 id="footer-identidad" className="a11y-sr-only">{t('footer.identity')}</h2>
          <div className="footer-logos">
            <img className="footer-logo" src={cinvestavLogo} alt="Cinvestav" />
            <span className="footer-logo-divider" aria-hidden="true" />
            <img className="footer-logo footer-logo--sinac" src={sinacLogo} alt="SINAC NEXT" />
          </div>
          <p className="footer-tagline">{t('footer.tagline')}</p>
        </section>

        <section className="footer-column" aria-labelledby="footer-informacion">
          <h2 id="footer-informacion">{t('footer.info')}</h2>
          <nav className="footer-links" aria-label={t('footer.linksAria')}>
            <button type="button" onClick={() => ir('privacy')}>{t('footer.privacy')}</button>
            <a href="https://www.cinvestav.mx/datos-personales" target="_blank" rel="noopener noreferrer">
              {t('footer.personalData')}<span className="a11y-sr-only"> {t('footer.newTab')}</span>
            </a>
            <button type="button" onClick={() => ir('accessibility')}>{t('footer.accessibility')}</button>
            <button type="button" onClick={() => window.dispatchEvent(new Event(READING_GUIDE_EVENT))}>{t('footer.readingGuide')}</button>
          </nav>
        </section>

        <section className="footer-column" aria-labelledby="footer-contacto">
          <h2 id="footer-contacto">{t('footer.contact')}</h2>
          <address>
            Av. Instituto Politécnico Nacional 2508, Col. San Pedro Zacatenco, Alcaldía Gustavo A. Madero, C.P. 07360, Ciudad de México.
          </address>
          <ul className="footer-social" aria-label={t('footer.socialAria')}>
            {REDES.map(red => (
              <li key={red.nombre}>
                <a href={red.url} target="_blank" rel="noopener noreferrer" title={red.nombre}>
                  <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{red.icono}</svg>
                  <span className="a11y-sr-only">{red.nombre} {t('footer.newTab')}</span>
                </a>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="footer-bottom">
        &copy; {new Date().getFullYear()} Cinvestav · SINAC NEXT. {t('footer.rights')}
      </div>
    </footer>
  );
}
