/** Mapa canónico rol → vista de panel (login y “Mi panel”). */
export const ROLE_HOME_VIEW = {
  aspirante: 'panel',
  alumno: 'alumno-panel',
  docente: 'docente-panel',
  investigador: 'docente-panel',
  director: 'director-panel',
  coordinacion: 'coordinacion-panel',
  servicios: 'servicios-panel',
  admin: 'admin-panel',
};

const ROLE_ALIASES = {
  admin: 'admin',
  administrador: 'admin',
  coordinacion: 'coordinacion',
  coordinación: 'coordinacion',
  coordinador: 'coordinacion',
  'coordinacion academica': 'coordinacion',
  'coordinación académica': 'coordinacion',
  'coordinacion académica': 'coordinacion',
  'coordinación academica': 'coordinacion',
  docente: 'docente',
  profesor: 'docente',
  teacher: 'docente',
  director: 'director',
  'director de tesis': 'director',
  servicios: 'servicios',
  'servicios escolares': 'servicios',
  servicios_escolares: 'servicios',
  investigador: 'investigador',
  alumno: 'alumno',
  student: 'alumno',
  aspirante: 'aspirante',
};

function stripAccents(value) {
  return value.normalize('NFD').replace(/\p{M}/gu, '');
}

export function normalizedRole(role) {
  const value = String(role || '').trim().toLowerCase();
  if (ROLE_ALIASES[value]) return ROLE_ALIASES[value];
  const plain = stripAccents(value);
  if (ROLE_ALIASES[plain]) return ROLE_ALIASES[plain];
  if (plain.includes('coordin')) return 'coordinacion';
  if (plain.includes('servicio')) return 'servicios';
  if (plain.includes('director')) return 'director';
  if (plain.includes('admin')) return 'admin';
  if (plain.includes('investig')) return 'investigador';
  if (plain.includes('docente') || plain.includes('profesor') || plain === 'teacher') return 'docente';
  if (plain.includes('alumno') || plain.includes('student')) return 'alumno';
  return 'aspirante';
}

export function homeViewForRole(role) {
  return ROLE_HOME_VIEW[normalizedRole(role)] || 'panel';
}

export function panelLabelKey(role) {
  const canonical = normalizedRole(role);
  if (canonical === 'admin') return 'navbar.adminPanel';
  if (canonical === 'coordinacion') return 'navbar.coordinacionPanel';
  if (canonical === 'docente' || canonical === 'investigador') return 'navbar.docentePanel';
  if (canonical === 'director') return 'role.director';
  if (canonical === 'servicios') return 'role.servicios';
  if (canonical === 'alumno') return 'navbar.alumnoPanel';
  return 'navbar.panel';
}

export const ROLE_VIEW_ACCESS = Object.fromEntries(
  Object.entries(ROLE_HOME_VIEW).map(([role, view]) => [view, [role]]),
);
ROLE_VIEW_ACCESS['docente-panel'] = ['docente', 'investigador', 'director'];

export function isDocentePanelRole(role) {
  return ROLE_VIEW_ACCESS['docente-panel'].includes(normalizedRole(role));
}
