import React, {useState, useEffect} from 'react';
import civMerida from '../assets/civmerida.jpg';
import civGuadalajara from '../assets/civguadalajara.jpg';
import civMont from '../assets/civmont.jpg';
import civQuere from '../assets/civquere.jpg';
import civSaltillo from '../assets/civsaltillo.jpg';
import civSur from '../assets/civsur.jpg';
import civZaca from '../assets/civzaca.jpg';

const centers = [
  {name: 'Cinvestav Unidad Mérida', descriptionKey: 'home.center.merida', image: civMerida},
  {name: 'Cinvestav Unidad Guadalajara', descriptionKey: 'home.center.guadalajara', image: civGuadalajara},
  {name: 'Cinvestav Unidad Monterrey', descriptionKey: 'home.center.monterrey', image: civMont},
  {name: 'Cinvestav Unidad Querétaro', descriptionKey: 'home.center.queretaro', image: civQuere},
  {name: 'Cinvestav Unidad Saltillo', descriptionKey: 'home.center.saltillo', image: civSaltillo},
  {name: 'Cinvestav Unidad CDMX Sur', descriptionKey: 'home.center.sur', image: civSur},
  {name: 'Cinvestav Unidad CDMX Zacatenco', descriptionKey: 'home.center.zacatenco', image: civZaca}
];

const INTERVAL_MS = 6000;

function prefersReducedMotion(){
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch (e) {
    return false;
  }
}

function animationsPausedBySite(){
  return document.documentElement.hasAttribute('data-pause-animations');
}

export default function Carousel({t}){
  const [idx, setIdx] = useState(0);
  const [stoppedByUser, setStoppedByUser] = useState(prefersReducedMotion);
  const [sitePaused, setSitePaused] = useState(animationsPausedBySite);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const stopped = stoppedByUser || sitePaused;
  const rotating = !stopped && !hovered && !focused;

  useEffect(() => {
    const observer = new MutationObserver(() => setSitePaused(animationsPausedBySite()));
    observer.observe(document.documentElement, {attributes: true, attributeFilter: ['data-pause-animations']});
    return () => observer.disconnect();
  }, []);

  useEffect(()=>{
    if (!rotating) return undefined;
    const timer = setInterval(()=> setIdx(i => (i+1)%centers.length), INTERVAL_MS);
    return ()=> clearInterval(timer);
  },[rotating]);

  function onBlur(event){
    if (!event.currentTarget.contains(event.relatedTarget)) setFocused(false);
  }

  return (
    <section
      className="carousel-root"
      aria-roledescription={t('carousel.roleDescription')}
      aria-label={t('carousel.label')}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setFocused(true)}
      onBlur={onBlur}
    >
      <div className="carousel-controls">
        <button
          type="button"
          className="carousel-toggle"
          disabled={sitePaused}
          onClick={() => setStoppedByUser(value => !value)}
        >
          <span aria-hidden="true">{stopped ? '▶' : '❚❚'}</span>
          {stopped ? t('carousel.play') : t('carousel.pause')}
        </button>
      </div>
      <div
        role="group"
        aria-roledescription={t('carousel.slide')}
        aria-label={`${idx + 1} / ${centers.length}`}
        aria-live={rotating ? 'off' : 'polite'}
      >
        <div className="carousel-image">
          <img src={centers[idx].image} alt={centers[idx].name} />
        </div>
        <div className="carousel-item">
          <h2>{centers[idx].name}</h2>
          <p>{t(centers[idx].descriptionKey)}</p>
        </div>
      </div>
      <div className="carousel-dots">
        {centers.map((c,i)=>(
          <button
            type="button"
            key={c.name}
            className={i===idx? 'dot active':'dot'}
            onClick={()=>setIdx(i)}
            aria-label={`${t('carousel.show')} ${c.name}`}
            aria-current={i===idx ? 'true' : undefined}
          />
        ))}
      </div>
    </section>
  )
}
