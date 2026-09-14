import React from 'react';
import sinacLogo from '../assets/SINAC5-removebg-preview.png';

export default function Footer({onNavigate}){
  return (
    <footer className="site-footer" aria-label="Pie de página institucional">
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="footer-mark"><img src={sinacLogo} alt="SINAC NEXT" /></span>
        </div>
        <div className="footer-meta">
          <span>&copy; {new Date().getFullYear()} SINAC NEXT - Cinvestav Unidad Zacatenco</span>
          <span className="footer-divider" aria-hidden="true">|</span>
          <button type="button" onClick={() => onNavigate && onNavigate('privacy')}>Aviso de privacidad</button>
        </div>
      </div>
    </footer>
  )
}
