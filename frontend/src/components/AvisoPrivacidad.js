import React from 'react';
import simboloLogo from '../assets/logosimbolo-03.png';
import cinvestavLogo from '../assets/6-removebg-preview.png';
import './AvisoPrivacidad.css';

const secciones = [
  ['Responsable del tratamiento', <p>El <strong>Centro de Investigación y de Estudios Avanzados del Instituto Politécnico Nacional (Cinvestav)</strong>, con domicilio en Av. Instituto Politécnico Nacional No. 2508, Col. San Pedro Zacatenco, Ciudad de México, C.P. 07360 y teléfono 55 57 47 38 00, es responsable del tratamiento de los datos personales que se recaban a través de SINAC NEXT.</p>],
  ['Uso de tecnologías de rastreo', <p>Al navegar en nuestra página pueden utilizarse tecnologías de rastreo. Los datos obtenidos pueden incluir matrícula, nombre completo y programa de posgrado. Esta información se utiliza para permitir el acceso y la visualización de los datos académicos a través de la web.</p>],
  ['Negativa para finalidades adicionales', <p>Si no desea que sus datos sean tratados para finalidades adicionales, puede comunicarlo a <a href="mailto:unidaddeenlace@cinvestav.mx">unidaddeenlace@cinvestav.mx</a>. La negativa no podrá ser motivo para negar la atención que corresponda.</p>],
  ['Datos personales utilizados', <><p>Para las finalidades descritas podrán utilizarse:</p><ul><li>Datos personales de identidad.</li><li>Datos personales de contacto.</li><li>Datos personales académicos.</li><li>Datos personales laborales.</li></ul></>],
  ['¿Cómo puede ejercer los derechos ARCO?', <><p>Usted tiene derecho de <strong>Acceso</strong>, <strong>Rectificación</strong>, <strong>Cancelación</strong> y <strong>Oposición</strong> respecto al tratamiento de sus datos personales.</p><p>Para ejercer cualquiera de estos derechos, presente la solicitud a <a href="mailto:unidaddeenlace@cinvestav.mx">unidaddeenlace@cinvestav.mx</a>.</p></>],
  ['Unidad de Transparencia', <><p>Para conocer el procedimiento y requisitos puede llamar al <strong>55 5747 3800, extensión 4017</strong>, consultar <a href="https://www.cinvestav.mx/Datos-Personales" target="_blank" rel="noopener noreferrer">www.cinvestav.mx/Datos-Personales</a> o contactar a la Unidad de Transparencia.</p><address>Av. Instituto Politécnico Nacional No. 2508, Col. San Pedro Zacatenco, Ciudad de México, C.P. 07360, Alcaldía Gustavo A. Madero, ingreso por caseta 1.<br/>Tel. 55 5747-3800, ext. 4017.<br/>Correo: <a href="mailto:unidaddeenlace@cinvestav.mx">unidaddeenlace@cinvestav.mx</a></address></>],
  ['Revocación del consentimiento', <><p>Puede revocar el consentimiento otorgado para el tratamiento de sus datos personales. La revocación no siempre podrá atenderse de forma inmediata cuando exista una obligación legal de continuar con el tratamiento o sea necesaria para prestar el servicio solicitado.</p><p>La solicitud puede presentarse a <a href="mailto:unidaddeenlace@cinvestav.mx">unidaddeenlace@cinvestav.mx</a> o mediante la <a href="https://www.plataformadetransparencia.org.mx" target="_blank" rel="noopener noreferrer">Plataforma Nacional de Transparencia</a>.</p></>],
  ['Cambios al aviso de privacidad', <p>Este aviso puede sufrir modificaciones por nuevos requerimientos legales, necesidades institucionales o cambios en las prácticas de privacidad. Las actualizaciones se publicarán en <a href="https://www.cinvestav.mx/Datos-Personales" target="_blank" rel="noopener noreferrer">www.cinvestav.mx/Datos-Personales</a>.</p>],
];

export default function AvisoPrivacidad({onNavigate}) {
  return <section className="privacy-page" aria-label="Aviso de privacidad">
    <div className="privacy-sheet">
      <header className="privacy-header">
        <img src={simboloLogo} alt="Cinvestav" className="privacy-logo privacy-logo-left" />
        <div className="privacy-institution"><span>CENTRO DE INVESTIGACIÓN Y DE ESTUDIOS AVANZADOS</span><small>Cinvestav Zacatenco</small></div>
        <img src={cinvestavLogo} alt="Cinvestav" className="privacy-logo privacy-logo-right" />
      </header>
      <div className="privacy-title-row"><div><span className="privacy-kicker">SINAC NEXT · DOCUMENTO DE EJEMPLO</span><h1>Aviso de privacidad</h1><p>Tratamiento y protección de datos personales</p></div><button type="button" className="privacy-back" onClick={() => onNavigate && onNavigate('home')}>Volver al inicio</button></div>
      <div className="privacy-notice">Este contenido es una versión de ejemplo para SINAC NEXT y deberá actualizarse y validarse institucionalmente antes de su publicación oficial.</div>
      <div className="privacy-content">{secciones.map(([titulo, contenido], index) => <article className="privacy-section" key={titulo}><span className="privacy-number">{String(index + 1).padStart(2, '0')}</span><div><h2>{titulo}</h2>{contenido}</div></article>)}</div>
      <footer className="privacy-update"><span>Última actualización de referencia: 01/06/2022</span><button type="button" onClick={() => onNavigate && onNavigate('home')}>SINAC NEXT</button></footer>
    </div>
  </section>;
}
