import {describe, expect, it} from 'vitest';
import {
  homeViewForRole,
  isDocentePanelRole,
  normalizedRole,
  ROLE_HOME_VIEW,
  ROLE_VIEW_ACCESS,
} from '../roles';

describe('redirección por rol', () => {
  it.each([
    ['aspirante', 'panel'],
    ['alumno', 'alumno-panel'],
    ['docente', 'docente-panel'],
    ['investigador', 'docente-panel'],
    ['director', 'director-panel'],
    ['coordinacion', 'coordinacion-panel'],
    ['servicios', 'servicios-panel'],
    ['admin', 'admin-panel'],
  ])('rol canónico %s abre %s', (role, view) => {
    expect(homeViewForRole(role)).toBe(view);
    expect(ROLE_HOME_VIEW[role]).toBe(view);
  });

  it.each([
    ['Administrador', 'admin', 'admin-panel'],
    ['profesor', 'docente', 'docente-panel'],
    ['teacher', 'docente', 'docente-panel'],
    ['servicios escolares', 'servicios', 'servicios-panel'],
    ['servicios_escolares', 'servicios', 'servicios-panel'],
    ['coordinador', 'coordinacion', 'coordinacion-panel'],
    ['Coordinación Académica', 'coordinacion', 'coordinacion-panel'],
    ['coordinacion academica', 'coordinacion', 'coordinacion-panel'],
    ['director de tesis', 'director', 'director-panel'],
    ['student', 'alumno', 'alumno-panel'],
  ])('alias "%s" se normaliza a %s y abre %s', (alias, canonical, view) => {
    expect(normalizedRole(alias)).toBe(canonical);
    expect(homeViewForRole(alias)).toBe(view);
  });

  it('solo los roles autorizados entran a cada panel', () => {
    expect(ROLE_VIEW_ACCESS['admin-panel']).toEqual(['admin']);
    expect(ROLE_VIEW_ACCESS['alumno-panel']).toEqual(['alumno']);
    expect(ROLE_VIEW_ACCESS['servicios-panel']).toEqual(['servicios']);
    expect(ROLE_VIEW_ACCESS['docente-panel']).toEqual(['docente', 'investigador', 'director']);
    expect(isDocentePanelRole('director')).toBe(true);
    expect(isDocentePanelRole('alumno')).toBe(false);
  });

  it('rol desconocido cae a aspirante / panel', () => {
    expect(normalizedRole('')).toBe('aspirante');
    expect(homeViewForRole('desconocido')).toBe('panel');
  });
});
