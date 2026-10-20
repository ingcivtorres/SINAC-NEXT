import React from 'react';

const FLAGS = {
  es: (
    <>
      <rect width="24" height="16" fill="#fff"/>
      <rect width="8" height="16" fill="#006847"/>
      <rect x="16" width="8" height="16" fill="#ce1126"/>
      <circle cx="12" cy="8" r="2.2" fill="#8c6b2f"/>
      <circle cx="12" cy="8" r="1.2" fill="#5a8f3c"/>
    </>
  ),
  en: (
    <>
      <rect width="24" height="16" fill="#fff"/>
      {[0, 2, 4, 6, 8, 10, 12].map((i) => (
        <rect key={i} y={i * 16 / 13} width="24" height={16 / 13} fill="#b22234"/>
      ))}
      <rect width="10.5" height={7 * 16 / 13} fill="#3c3b6e"/>
      <g fill="#fff">
        {[0, 1, 2, 3].map((r) => [0, 1, 2].map((c) => (
          <circle key={`${r}-${c}`} cx={1.9 + c * 3.2 + (r % 2) * 1.6} cy={1.4 + r * 1.9} r=".5"/>
        )))}
      </g>
    </>
  ),
  de: (
    <>
      <rect width="24" height="5.34" fill="#000"/>
      <rect y="5.33" width="24" height="5.34" fill="#dd0000"/>
      <rect y="10.66" width="24" height="5.34" fill="#ffce00"/>
    </>
  ),
  zh: (
    <>
      <rect width="24" height="16" fill="#de2910"/>
      <polygon fill="#ffde00" points="5,2 5.68,4.07 7.85,4.07 6.09,5.36 6.76,7.43 5,6.15 3.24,7.43 3.91,5.36 2.15,4.07 4.32,4.07"/>
      <circle cx="9.5" cy="2.3" r=".6" fill="#ffde00"/>
      <circle cx="11" cy="4" r=".6" fill="#ffde00"/>
      <circle cx="11" cy="6.2" r=".6" fill="#ffde00"/>
      <circle cx="9.5" cy="8" r=".6" fill="#ffde00"/>
    </>
  ),
  pt: (
    <>
      <rect width="24" height="16" fill="#009c3b"/>
      <polygon points="12,1.8 22,8 12,14.2 2,8" fill="#ffdf00"/>
      <circle cx="12" cy="8" r="3.4" fill="#002776"/>
      <path d="M8.9 7.2Q12 6.3 15.1 8.6" stroke="#fff" strokeWidth=".5" fill="none"/>
    </>
  ),
};

export default function Flag({code, className = ''}) {
  return (
    <svg className={`flag-icon ${className}`.trim()} viewBox="0 0 24 16" width="24" height="16" aria-hidden="true" focusable="false">
      {FLAGS[code] || FLAGS.es}
    </svg>
  );
}
