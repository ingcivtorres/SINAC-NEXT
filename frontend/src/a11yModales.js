const MODAL_SELECTOR = '[aria-modal="true"]';
const FOCUSABLE_SELECTOR = [
  'a[href]', 'area[href]', 'button:not([disabled])', 'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])', 'textarea:not([disabled])', 'iframe', '[contenteditable="true"]',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

let idSequence = 0;

/** Manejador para el fondo de un modal: solo reacciona a clics sobre el propio fondo. */
export function alPulsarFondo(cerrar){
  return event => {
    if (event.target === event.currentTarget) cerrar();
  };
}

function focusablesIn(element){
  return Array.from(element.querySelectorAll(FOCUSABLE_SELECTOR))
    .filter(node => node.getClientRects().length > 0 && !node.closest('[inert]'));
}

function ensureAccessibleName(dialog){
  if (dialog.hasAttribute('aria-labelledby') || dialog.hasAttribute('aria-label')) return;
  const heading = dialog.querySelector('h1, h2, h3, h4, h5, h6');
  if (!heading) return;
  if (!heading.id) heading.id = `sinac-modal-titulo-${++idSequence}`;
  dialog.setAttribute('aria-labelledby', heading.id);
}

function focusInitial(dialog){
  if (dialog.contains(document.activeElement)) return;
  const preferred = dialog.querySelector('[autofocus], [data-autofocus]');
  const target = preferred || focusablesIn(dialog)[0];
  if (target) {
    target.focus();
    return;
  }
  if (!dialog.hasAttribute('tabindex')) dialog.setAttribute('tabindex', '-1');
  dialog.focus();
}

/**
 * Aplica a todo elemento con aria-modal="true": nombre accesible, foco inicial,
 * retención del foco con Tab, cierre con Escape (mediante el clic del fondo,
 * que ya respeta los estados en que el modal no debe cerrarse) y devolución
 * del foco al elemento que lo abrió.
 */
export function instalarGestorModales(){
  const stack = [];
  let lastFocusedOutside = null;

  function topDialog(){
    return stack.length ? stack[stack.length - 1].dialog : null;
  }

  function sync(){
    const present = Array.from(document.querySelectorAll(MODAL_SELECTOR));
    for (let i = stack.length - 1; i >= 0; i -= 1) {
      const entry = stack[i];
      if (present.includes(entry.dialog) && entry.dialog.isConnected) continue;
      stack.splice(i, 1);
      const focusLost = !document.activeElement || document.activeElement === document.body || !document.activeElement.isConnected;
      if (focusLost && entry.returnTo?.isConnected) entry.returnTo.focus();
    }
    present.forEach(dialog => {
      if (stack.some(entry => entry.dialog === dialog)) return;
      stack.push({dialog, returnTo: lastFocusedOutside});
      ensureAccessibleName(dialog);
      focusInitial(dialog);
    });
  }

  function onFocusIn(event){
    const dialog = topDialog();
    if (!dialog) {
      if (!event.target.closest?.(MODAL_SELECTOR)) lastFocusedOutside = event.target;
      return;
    }
    if (!dialog.contains(event.target)) focusInitial(dialog);
  }

  function onKeyDown(event){
    const dialog = topDialog();
    if (!dialog) return;
    if (event.key === 'Escape') {
      const backdrop = dialog.parentElement;
      if (backdrop && backdrop !== document.body) {
        event.preventDefault();
        backdrop.click();
      }
      return;
    }
    if (event.key !== 'Tab') return;
    const items = focusablesIn(dialog);
    if (!items.length) {
      event.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  const observer = new MutationObserver(sync);
  observer.observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['aria-modal']});
  document.addEventListener('focusin', onFocusIn);
  document.addEventListener('keydown', onKeyDown);
  if (document.activeElement && document.activeElement !== document.body) lastFocusedOutside = document.activeElement;
  sync();

  return () => {
    observer.disconnect();
    document.removeEventListener('focusin', onFocusIn);
    document.removeEventListener('keydown', onKeyDown);
  };
}
