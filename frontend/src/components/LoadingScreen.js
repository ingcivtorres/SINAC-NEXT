import React from 'react';
import sinacLogo from '../assets/6-removebg-preview.png';

export default function LoadingScreen(){
  return (
    <div className="loading-root">
      <div className="loading-inner">
        <div className="loading-title">Bienvenido a</div>
        <img src={sinacLogo} alt="SINAC NEXT" className="sinac-big"/>
        <div className="spinner" aria-hidden="true"></div>
      </div>
    </div>
  )
}
