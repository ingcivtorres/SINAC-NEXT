import React from 'react';
import simboloLogo from '../assets/logosimbolo-03.png';
import cinvestavLogo from '../assets/6-removebg-preview.png';
import './AvisoPrivacidad.css';

const secciones = [
  ['Compromiso', <p>El <strong>Cinvestav</strong> busca que SINAC NEXT pueda ser utilizado por todas las personas, incluidas aquellas con discapacidad visual, auditiva, motriz o cognitiva, y por quienes usan tecnologías de asistencia.</p>],
  ['Estándar de referencia', <><p>SINAC NEXT toma como referencia las <strong>Pautas de Accesibilidad para el Contenido Web (WCAG) 2.1, nivel AA</strong>, del W3C, y las <strong>Disposiciones Generales de Accesibilidad Web</strong> publicadas en el Diario Oficial de la Federación el 3 de diciembre de 2015.</p><p>Estado actual: <strong>parcialmente conforme</strong>. Algunas partes del sistema todavía no cumplen por completo con el estándar (ver «Limitaciones conocidas»).</p></>],
  ['Funciones de accesibilidad', <ul>
    <li>Enlace «Saltar al contenido principal» al inicio de cada página.</li>
    <li>Navegación completa con teclado en menús, selector de idioma, carrusel y ventanas modales (Tab, flechas, Inicio, Fin y Escape).</li>
    <li>Panel de accesibilidad en la barra superior con lectura en voz alta, ajuste del tamaño de letra (80 % a 160 %), alto contraste, espaciado de texto, fuente de lectura fácil, resaltado de enlaces y pausa de animaciones.</li>
    <li>Tema claro y oscuro, y respeto a la preferencia del sistema de reducir el movimiento.</li>
    <li>Título de página y anuncio para lectores de pantalla en cada cambio de sección.</li>
    <li>Errores de formulario asociados a su campo y anunciados por los lectores de pantalla.</li>
    <li>Interfaz disponible en español, inglés, alemán, chino y portugués.</li>
  </ul>],
  ['Limitaciones conocidas', <ul>
    <li>Los documentos PDF que suben los usuarios (actas, constancias y expedientes) no se generan en el sistema y pueden no ser accesibles.</li>
    <li>Algunas tablas extensas de los paneles se leen mejor en pantallas grandes.</li>
    <li>La lectura en voz alta del panel usa la voz del navegador; su calidad depende del sistema operativo y no sustituye a un lector de pantalla profesional.</li>
  </ul>],
  ['Compatibilidad', <p>SINAC NEXT se ha revisado con las versiones recientes de Chrome, Edge y Firefox, y está diseñado para funcionar con lectores de pantalla como NVDA, JAWS y VoiceOver.</p>],
  ['Reportar una barrera de accesibilidad', <p>Si encuentra algún contenido o función que no pueda utilizar, comuníquelo mediante los datos de la sección <strong>Contacto</strong> o al teléfono <strong>55 5747 3800</strong>. Indique la página, la acción que intentaba realizar y, si es posible, el navegador y la tecnología de asistencia que utiliza.</p>],
];

export default function AccessibilityStatement({onNavigate}) {
  return <section className="privacy-page" aria-labelledby="declaracion-accesibilidad-titulo">
    <div className="privacy-sheet">
      <header className="privacy-header">
        <img src={simboloLogo} alt="Cinvestav" className="privacy-logo privacy-logo-left" />
        <div className="privacy-institution"><span>CENTRO DE INVESTIGACIÓN Y DE ESTUDIOS AVANZADOS</span><small>Cinvestav Zacatenco</small></div>
        <img src={cinvestavLogo} alt="" className="privacy-logo privacy-logo-right" />
      </header>
      <div className="privacy-title-row"><div><span className="privacy-kicker">SINAC NEXT · DOCUMENTO DE EJEMPLO</span><h1 id="declaracion-accesibilidad-titulo">Declaración de accesibilidad</h1><p>Compromiso, nivel de cumplimiento y canales de reporte</p></div><button type="button" className="privacy-back" onClick={() => onNavigate && onNavigate('home')}>Volver al inicio</button></div>
      <div className="privacy-notice">Este contenido es una versión de ejemplo para SINAC NEXT y deberá validarse institucionalmente antes de su publicación oficial.</div>
      <div className="privacy-content">{secciones.map(([titulo, contenido], index) => <article className="privacy-section" key={titulo}><span className="privacy-number" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span><div><h2>{titulo}</h2>{contenido}</div></article>)}</div>
      <footer className="privacy-update"><span>Última revisión: noviembre de 2026</span><button type="button" onClick={() => onNavigate && onNavigate('contact')}>Contacto</button></footer>
    </div>
  </section>;
}
