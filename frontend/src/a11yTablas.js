const HEADING_SELECTOR = 'h1, h2, h3, h4, h5, h6, [role="heading"]';
let idSequence = 0;

function nearestHeading(table){
  let node = table;
  while (node && node !== document.body) {
    let sibling = node.previousElementSibling;
    while (sibling) {
      if (sibling.matches(HEADING_SELECTOR)) return sibling;
      const inner = sibling.querySelectorAll(HEADING_SELECTOR);
      if (inner.length) return inner[inner.length - 1];
      sibling = sibling.previousElementSibling;
    }
    node = node.parentElement;
  }
  return null;
}

function enhanceTable(table){
  table.querySelectorAll('thead th:not([scope])').forEach(th => th.setAttribute('scope', 'col'));
  table.querySelectorAll('tbody tr > th:first-child:not([scope])').forEach(th => th.setAttribute('scope', 'row'));
  const named = table.querySelector('caption')
    || table.hasAttribute('aria-label')
    || table.hasAttribute('aria-labelledby');
  if (named) return;
  const heading = nearestHeading(table);
  if (!heading) return;
  if (!heading.id) heading.id = `sinac-tabla-titulo-${++idSequence}`;
  table.setAttribute('aria-labelledby', heading.id);
}

/**
 * Completa la semántica de todas las tablas de datos: alcance de los
 * encabezados y nombre accesible tomado del encabezado de su sección
 * cuando la tabla no declara uno propio.
 */
export function instalarMejorasTablas(){
  let scheduled = false;
  function run(){
    scheduled = false;
    document.querySelectorAll('table:not([role="presentation"])').forEach(enhanceTable);
  }
  function schedule(){
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(run);
  }
  const observer = new MutationObserver(schedule);
  observer.observe(document.body, {childList: true, subtree: true});
  run();
  return () => observer.disconnect();
}
