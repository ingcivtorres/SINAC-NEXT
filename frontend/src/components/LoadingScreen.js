import React from 'react';
import sinacLogo from '../assets/SINAC5.jpg';

export default function LoadingScreen(){
  return (
    <div className="loading-root" role="status" aria-live="polite">
      <div className="loading-orbit loading-orbit-one" aria-hidden="true" />
      <div className="loading-orbit loading-orbit-two" aria-hidden="true" />
      <div className="loading-inner">
        <div className="loading-brand"><img src={sinacLogo} alt="SINAC NEXT" className="sinac-big"/></div>
        <div className="loading-welcome">Bienvenido a tu plataforma académica</div>
        <div className="loading-progress" aria-hidden="true"><span /></div>
        <div className="loading-status">Preparando tu espacio <span className="loading-dots">•••</span></div>
      </div>
    </div>
  )
}
