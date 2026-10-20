import React from 'react';
import {useLanguage} from '../translations';
import './ContactPage.css';

const PRIVACY_EMAIL = 'unidaddeenlace@cinvestav.mx';
const PRIVACY_URL = 'https://www.cinvestav.mx/Datos-Personales';

export default function ContactPage({onNavigate}) {
  const {t} = useLanguage();

  return <section className="contact-page page-root" aria-labelledby="contact-title">
    <header className="contact-page-header">
      <span className="contact-page-kicker">SINAC NEXT · CINVESTAV</span>
      <h1 id="contact-title">{t('contact.title')}</h1>
      <p>{t('contact.intro')}</p>
    </header>
    <div className="contact-page-grid">
      <article className="contact-page-card">
        <span className="contact-page-icon" aria-hidden="true">⌖</span>
        <h2>{t('contact.addressLabel')}</h2>
        <address>{t('contact.address')}</address>
      </article>
      <article className="contact-page-card">
        <span className="contact-page-icon" aria-hidden="true">☎</span>
        <h2>{t('contact.phoneLabel')}</h2>
        <a href="tel:+525557473800">{t('contact.phone')}</a>
      </article>
      <article className="contact-page-card">
        <span className="contact-page-icon" aria-hidden="true">✉</span>
        <h2>{t('contact.transparencyLabel')}</h2>
        <p>{t('contact.transparencyText')}</p>
        <a href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</a>
      </article>
      <article className="contact-page-card">
        <span className="contact-page-icon" aria-hidden="true">↗</span>
        <h2>{t('contact.websiteLabel')}</h2>
        <a href={PRIVACY_URL} target="_blank" rel="noopener noreferrer">{t('contact.website')}</a>
      </article>
    </div>
    <button type="button" className="contact-page-back" onClick={() => onNavigate?.('home')}>
      {t('contact.back')}
    </button>
  </section>;
}
