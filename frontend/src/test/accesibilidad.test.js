import React from 'react';
import {describe, it, expect, beforeEach, afterEach, vi} from 'vitest';
import {render, screen, fireEvent, act, waitFor} from '@testing-library/react';
import axe from 'axe-core';
import {translations} from '../translations';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import LoginView from '../components/LoginView';
import Carousel from '../components/Carousel';
import AccessibilityMenu from '../components/AccessibilityMenu';
import AccessibilityStatement from '../components/AccessibilityStatement';
import VerificarCredencial from '../components/VerificarCredencial';
import {instalarGestorModales, alPulsarFondo} from '../a11yModales';
import {instalarMejorasTablas} from '../a11yTablas';

const es = translations.es;
const t = key => es[key] || key;

// jsdom no calcula estilos ni geometría: el contraste se verifica en el navegador real.
const AXE_OPTIONS = {
  runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']},
  rules: {'color-contrast': {enabled: false}, region: {enabled: false}},
};

async function expectNoAxeViolations(container){
  const {violations} = await axe.run(container, AXE_OPTIONS);
  const summary = violations.map(v => `${v.id}: ${v.help}\n  ${v.nodes.map(n => n.target.join(' ')).join('\n  ')}`);
  expect(summary).toEqual([]);
}

describe('Auditoría axe por componente', () => {
  it('Navbar sin sesión', async () => {
    const {container} = render(<Navbar onNavigate={() => {}} activeView="home" session={null} onLogout={() => {}} />);
    await expectNoAxeViolations(container);
  });

  it('Footer', async () => {
    const {container} = render(<Footer onNavigate={() => {}} />);
    await expectNoAxeViolations(container);
  });

  it('LoginView', async () => {
    const {container} = render(<LoginView onBackHome={() => {}} onLoginSuccess={() => {}} />);
    await expectNoAxeViolations(container);
  });

  it('Carousel', async () => {
    const {container} = render(<Carousel t={t} />);
    await expectNoAxeViolations(container);
  });

  it('Declaración de accesibilidad', async () => {
    const {container} = render(<AccessibilityStatement onNavigate={() => {}} />);
    await expectNoAxeViolations(container);
  });

  it('El pie activa la guía de lectura y se puede quitar', async () => {
    const {container} = render(<><AccessibilityMenu /><Footer onNavigate={() => {}} /></>);
    fireEvent.click(screen.getByRole('button', {name: es['footer.readingGuide']}));
    expect(document.documentElement.hasAttribute('data-reading-guide')).toBe(true);
    const quitar = screen.getByRole('button', {name: new RegExp(es['a11y.guideOff'])});
    await expectNoAxeViolations(container);
    fireEvent.click(quitar);
    expect(document.documentElement.hasAttribute('data-reading-guide')).toBe(false);
  });

  it('Verificación pública de credencial', async () => {
    const respuesta = {resultado: 'vigente', motivo: null, nombre: 'Ana Pérez', matricula: 'A1', programa: 'Maestría', grado: 'Maestría', foto: null, periodo: '2026-B', vigencia_hasta: '2026-12-15', verificado_en: '2026-11-11T10:00:00Z'};
    const fetchOriginal = globalThis.fetch;
    globalThis.fetch = vi.fn().mockResolvedValue({ok: true, json: () => Promise.resolve(respuesta)});
    try {
      const {container} = render(<VerificarCredencial token="abc:def" onHome={() => {}} />);
      await screen.findByText('CREDENCIAL VIGENTE');
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/credencial/verificar/abc%3Adef/', expect.anything());
      expect(screen.getByText('Ana Pérez')).toBeTruthy();
      await expectNoAxeViolations(container);
    } finally {
      globalThis.fetch = fetchOriginal;
    }
  });

  it('Panel de accesibilidad abierto', async () => {
    const {container} = render(<AccessibilityMenu />);
    fireEvent.click(screen.getByRole('button', {name: es['a11y.open']}));
    await expectNoAxeViolations(container);
  });
});

describe('Barra de navegación', () => {
  it('ofrece enlace para saltar al contenido y navegación etiquetada', () => {
    render(<Navbar onNavigate={() => {}} activeView="home" session={null} onLogout={() => {}} />);
    expect(screen.getByRole('link', {name: es['navbar.skipToContent']})).toHaveProperty('hash', '#contenido-principal');
    expect(screen.getByRole('navigation', {name: es['navbar.mainNavigation']})).toBeTruthy();
  });
});

describe('Panel de accesibilidad', () => {
  function abrirPanel(){
    render(<AccessibilityMenu />);
    const trigger = screen.getByRole('button', {name: es['a11y.open']});
    fireEvent.click(trigger);
    return trigger;
  }

  it('abre con foco dentro y cierra con Escape devolviendo el foco', () => {
    const trigger = abrirPanel();
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByRole('group', {name: es['a11y.title']}).contains(document.activeElement)).toBe(true);
    fireEvent.keyDown(document.activeElement, {key: 'Escape'});
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    expect(document.activeElement).toBe(trigger);
  });

  it('aumenta y restablece el tamaño de letra', () => {
    abrirPanel();
    fireEvent.click(screen.getByRole('button', {name: es['a11y.fontIncrease']}));
    expect(document.documentElement.style.fontSize).toBe('110%');
    fireEvent.click(screen.getByRole('button', {name: es['a11y.fontReset']}));
    expect(document.documentElement.style.fontSize).toBe('');
  });

  it('activa alto contraste y lo anuncia', () => {
    abrirPanel();
    const toggle = screen.getByRole('button', {name: es['a11y.contrast']});
    fireEvent.click(toggle);
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
    expect(document.documentElement.getAttribute('data-contrast')).toBe('high');
    expect(screen.getByRole('status').textContent).toBe(es['a11y.contrastOn']);
  });

  it.each([
    ['a11y.textSpacing', 'data-text-spacing'],
    ['a11y.readableFont', 'data-readable-font'],
    ['a11y.highlightLinks', 'data-highlight-links'],
    ['a11y.pauseAnimations', 'data-pause-animations'],
  ])('%s alterna el atributo %s', (labelKey, attribute) => {
    abrirPanel();
    const toggle = screen.getByRole('button', {name: es[labelKey]});
    fireEvent.click(toggle);
    expect(document.documentElement.hasAttribute(attribute)).toBe(true);
    fireEvent.click(toggle);
    expect(document.documentElement.hasAttribute(attribute)).toBe(false);
  });

  it('guarda las preferencias y "Restablecer todo" las limpia', () => {
    abrirPanel();
    fireEvent.click(screen.getByRole('button', {name: es['a11y.contrast']}));
    expect(JSON.parse(localStorage.getItem('sinac_accesibilidad')).highContrast).toBe(true);
    fireEvent.click(screen.getByRole('button', {name: es['a11y.resetAll']}));
    expect(document.documentElement.hasAttribute('data-contrast')).toBe(false);
    expect(JSON.parse(localStorage.getItem('sinac_accesibilidad')).highContrast).toBe(false);
  });
});

describe('Carrusel', () => {
  it('se puede pausar y reanudar', () => {
    render(<Carousel t={t} />);
    fireEvent.click(screen.getByRole('button', {name: es['carousel.pause']}));
    expect(screen.getByRole('button', {name: es['carousel.play']})).toBeTruthy();
  });

  it('marca la diapositiva actual en los indicadores', () => {
    render(<Carousel t={t} />);
    const dots = screen.getAllByRole('button', {name: new RegExp(`^${es['carousel.show']} `)});
    fireEvent.click(dots[2]);
    expect(dots[2].getAttribute('aria-current')).toBe('true');
    expect(dots.filter(dot => dot.hasAttribute('aria-current'))).toHaveLength(1);
  });

  it('respeta la pausa global de animaciones', async () => {
    render(<Carousel t={t} />);
    act(() => document.documentElement.setAttribute('data-pause-animations', ''));
    await waitFor(() => expect(screen.getByRole('button', {name: es['carousel.play']}).disabled).toBe(true));
  });
});

describe('Inicio de sesión', () => {
  it('anuncia el error y marca los campos inválidos', () => {
    const {container} = render(<LoginView onBackHome={() => {}} onLoginSuccess={() => {}} />);
    fireEvent.submit(container.querySelector('form'));
    expect(screen.getByRole('alert').textContent).toBe(es['login.errorValidation']);
    const invalid = container.querySelectorAll('[aria-invalid="true"]');
    expect(invalid.length).toBe(2);
    invalid.forEach(input => expect(input.getAttribute('aria-describedby')).toContain('login-error'));
  });
});

describe('Gestor de modales', () => {
  let desinstalar;
  let rectsOriginal;

  beforeEach(() => {
    rectsOriginal = Element.prototype.getClientRects;
    Element.prototype.getClientRects = function(){ return [{width: 1, height: 1}]; };
    desinstalar = instalarGestorModales();
  });

  afterEach(() => {
    desinstalar();
    Element.prototype.getClientRects = rectsOriginal;
  });

  function Escenario(){
    const [abierto, setAbierto] = React.useState(false);
    return (
      <>
        <button type="button" onClick={() => setAbierto(true)}>Abrir</button>
        {abierto && (
          <div role="presentation" onClick={alPulsarFondo(() => setAbierto(false))}>
            <div role="dialog" aria-modal="true">
              <h2>Confirmar</h2>
              <button type="button">Primero</button>
              <button type="button" onClick={() => setAbierto(false)}>Último</button>
            </div>
          </div>
        )}
      </>
    );
  }

  it('nombra el diálogo, retiene el foco, cierra con Escape y devuelve el foco', async () => {
    render(<Escenario />);
    const abrir = screen.getByRole('button', {name: 'Abrir'});
    abrir.focus();
    fireEvent.click(abrir);

    const dialogo = await screen.findByRole('dialog', {name: 'Confirmar'});
    await waitFor(() => expect(document.activeElement.textContent).toBe('Primero'));

    screen.getByRole('button', {name: 'Último'}).focus();
    fireEvent.keyDown(document.activeElement, {key: 'Tab'});
    expect(document.activeElement.textContent).toBe('Primero');

    fireEvent.keyDown(document.activeElement, {key: 'Tab', shiftKey: true});
    expect(document.activeElement.textContent).toBe('Último');

    fireEvent.keyDown(document.activeElement, {key: 'Escape'});
    await waitFor(() => expect(dialogo.isConnected).toBe(false));
    await waitFor(() => expect(document.activeElement).toBe(abrir));
  });
});

describe('Mejoras de tablas', () => {
  it('agrega scope a encabezados y nombra la tabla con el título previo', async () => {
    const desinstalar = instalarMejorasTablas();
    const {container} = render(
      <section>
        <h3>Alumnos inscritos</h3>
        <table>
          <thead><tr><th>Nombre</th><th>Programa</th></tr></thead>
          <tbody><tr><th>Ana</th><td>Física</td></tr></tbody>
        </table>
      </section>
    );
    await waitFor(() => expect(container.querySelector('thead th').getAttribute('scope')).toBe('col'));
    expect(container.querySelector('tbody th').getAttribute('scope')).toBe('row');
    expect(screen.getByRole('table', {name: 'Alumnos inscritos'})).toBeTruthy();
    desinstalar();
  });
});

vi.setConfig({testTimeout: 20000});
