const fetchOriginal = window.fetch.bind(window);
let renovacionEnCurso = null;

function almacenSesion() {
  if (localStorage.getItem('sinac_refresh')) return localStorage;
  if (sessionStorage.getItem('sinac_refresh')) return sessionStorage;
  return null;
}

export function tokenAcceso() {
  return localStorage.getItem('sinac_access') || sessionStorage.getItem('sinac_access');
}

export function tokenRenovacion() {
  return almacenSesion()?.getItem('sinac_refresh') || null;
}

async function renovarToken() {
  const almacen = almacenSesion();
  if (!almacen) return null;
  try {
    const respuesta = await fetchOriginal('/api/auth/refresh/', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({refresh: almacen.getItem('sinac_refresh')}),
    });
    if (!respuesta.ok) return null;
    const datos = await respuesta.json();
    almacen.setItem('sinac_access', datos.access);
    if (datos.refresh) almacen.setItem('sinac_refresh', datos.refresh);
    window.dispatchEvent(new CustomEvent('sinac:token', {detail: datos.access}));
    return datos.access;
  } catch {
    return null;
  }
}

function esApiProtegida(url, cabeceras) {
  const ruta = url.startsWith(window.location.origin) ? url.slice(window.location.origin.length) : url;
  return ruta.startsWith('/api/') && !ruta.startsWith('/api/auth/') && (cabeceras.get('Authorization') || '').startsWith('Bearer ');
}

function conToken(init, cabeceras, token) {
  const nuevas = new Headers(cabeceras);
  nuevas.set('Authorization', `Bearer ${token}`);
  return {...init, headers: nuevas};
}

window.fetch = async (input, init = {}) => {
  const url = typeof input === 'string' ? input : input.url;
  const cabeceras = new Headers(init.headers || (typeof input === 'string' ? undefined : input.headers));
  if (!esApiProtegida(url, cabeceras)) return fetchOriginal(input, init);

  const vigente = tokenAcceso();
  const respuesta = await fetchOriginal(input, vigente ? conToken(init, cabeceras, vigente) : init);
  if (respuesta.status !== 401) return respuesta;

  renovacionEnCurso = renovacionEnCurso || renovarToken().finally(() => { renovacionEnCurso = null; });
  const nuevo = await renovacionEnCurso;
  return nuevo ? fetchOriginal(input, conToken(init, cabeceras, nuevo)) : respuesta;
};

export function cerrarSesionServidor() {
  const refresh = tokenRenovacion();
  if (!refresh) return Promise.resolve();
  return fetchOriginal('/api/auth/logout/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({refresh}),
  }).catch(() => {});
}
