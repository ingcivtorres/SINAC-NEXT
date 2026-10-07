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

export default function Carousel({t}){
  const [idx, setIdx] = useState(0);
  useEffect(()=>{
    const t = setInterval(()=> setIdx(i => (i+1)%centers.length), 3500);
    return ()=> clearInterval(t);
  },[]);

  return (
    <div className="carousel-root">
      <div className="carousel-image">
        <img src={centers[idx].image} alt={centers[idx].name} />
      </div>
      <div className="carousel-item">
        <h2>{centers[idx].name}</h2>
        <p>{t(centers[idx].descriptionKey)}</p>
      </div>
      <div className="carousel-dots">
        {centers.map((c,i)=>(
          <button key={i} className={i===idx? 'dot active':'dot'} onClick={()=>setIdx(i)} aria-label={`Mostrar ${c.name}`}></button>
        ))}
      </div>
    </div>
  )
}
