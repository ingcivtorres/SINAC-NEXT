import React from 'react';
import Carousel from './Carousel';
import {useLanguage} from '../translations';

export default function HomePage(){
  const {t} = useLanguage();
  return (
    <div id="inicio" className="page-root">
      <Carousel t={t} />
      <section id="servicios" className="mission-vision">
        <div className="card">
          <h3>{t('home.missionTitle')}</h3>
          <p>{t('home.missionDescription')}</p>
        </div>
        <div className="card">
          <h3>{t('home.visionTitle')}</h3>
          <p>{t('home.visionDescription')}</p>
        </div>
      </section>
    </div>
  )
}
