import React from 'react';
import Carousel from './Carousel';

export default function HomePage(){
  return (
    <div id="inicio" className="page-root">
      <Carousel />
      <section id="servicios" className="mission-vision">
        <div className="card">
          <h3>Misión</h3>
          <p>Proveer un sistema integral para la gestión académica y administrativa con enfoque en procesos eficientes y trazables.</p>
        </div>
        <div className="card">
          <h3>Visión</h3>
          <p>Ser la plataforma de referencia para la gestión educativa en los centros de investigación de México.</p>
        </div>
      </section>
    </div>
  )
}
