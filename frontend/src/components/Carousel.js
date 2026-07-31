import React, {useState, useEffect} from 'react';
import civMerida from '../assets/civmerida.jpg';
import civGuadalajara from '../assets/civguadalajara.jpg';
import civMont from '../assets/civmont.jpg';
import civQuere from '../assets/civquere.jpg';
import civSaltillo from '../assets/civsaltillo.jpg';
import civSur from '../assets/civsur.jpg';
import civZaca from '../assets/civzaca.jpg';

const centers = [
  {name: 'Cinvestav Unidad Mérida', desc: 'Centro especializado en biotecnología.', image: civMerida},
  {name: 'Cinvestav Unidad Guadalajara', desc: 'Investigación en electrónica y robótica.', image: civGuadalajara},
  {name: 'Cinvestav Unidad Monterrey', desc: 'Innovación en tecnología industrial.', image: civMont},
  {name: 'Cinvestav Unidad Querétaro', desc: 'Desarrollo de soluciones de ingeniería avanzada.', image: civQuere},
  {name: 'Cinvestav Unidad Saltillo', desc: 'Investigación aplicada a procesos productivos.', image: civSaltillo},
  {name: 'Cinvestav Unidad CDMX Sur', desc: 'Educación e investigación en ciencias sociales.', image: civSur},
  {name: 'Cinvestav Unidad CDMX Zacatenco', desc: 'Centro de desarrollo tecnológico e ingeniería.', image: civZaca}
];

export default function Carousel(){
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
        <p>{centers[idx].desc}</p>
      </div>
      <div className="carousel-dots">
        {centers.map((c,i)=>(
          <button key={i} className={i===idx? 'dot active':'dot'} onClick={()=>setIdx(i)} aria-label={`Mostrar ${c.name}`}></button>
        ))}
      </div>
    </div>
  )
}
