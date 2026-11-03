"""Captura pantallas reales de SINAC NEXT para el manual de usuario.

Requiere el sistema en ejecución (docker compose up) y los datos de prueba cargados.
"""
import json
import os
import sys

from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, 'docs', 'assets', 'manual')
URL = os.environ.get('SINAC_URL', 'http://localhost:3000')

ROLES = [
    ('coordinacion', 'coord.demo', 'SINAC_DEMO_COORDINACION_PASSWORD'),
    ('servicios', 'serv.demo', 'SINAC_DEMO_SERVICIOS_PASSWORD'),
    ('aspirante', 'asp.demo1', 'SINAC_DEMO_ASPIRANTE_PASSWORD'),
    ('alumno', 'alu.demo1', 'SINAC_DEMO_ALUMNO_PASSWORD'),
    ('docente', 'doc.demo1', 'SINAC_DEMO_DOCENTE_PASSWORD'),
    ('director', 'dir.demo1', 'SINAC_DEMO_DIRECTOR_PASSWORD'),
    ('admin', 'admin.demo', 'SINAC_DEMO_ADMIN_PASSWORD'),
]

BOTONES_MENU = 'aside[class*="sidebar"] nav button, aside[class*="sidebar"] > button:not(.sidebar-logout)'


def esperar(page, ms=1600):
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(ms)


def captura(page, nombre):
    ruta = os.path.join(DESTINO, f'{nombre}.png')
    page.screenshot(path=ruta)
    return os.path.relpath(ruta, RAIZ).replace('\\', '/')


def abrir_menu(page, texto):
    page.hover('.menu-dropdown')
    page.locator('.dropdown-menu .dropdown-item', has_text=texto).first.click()
    page.mouse.move(20, 600)
    esperar(page, 900)
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_timeout(400)


def publicas(navegador, indice):
    page = navegador.new_page()
    page.goto(URL)
    esperar(page, 3200)
    indice['publico'] = [{'seccion': 'Inicio', 'imagen': captura(page, 'publico_01_inicio')}]
    abrir_menu(page, 'Portal')
    indice['publico'].append({'seccion': 'Portal de aspirantes', 'imagen': captura(page, 'publico_02_portal')})
    page.get_by_role('button', name='Aceptar y continuar').click()
    esperar(page, 900)
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_timeout(300)
    indice['publico'].append({'seccion': 'Formulario de preregistro', 'imagen': captura(page, 'publico_02b_preregistro')})
    abrir_menu(page, 'Iniciar sesión')
    indice['publico'].append({'seccion': 'Iniciar sesión', 'imagen': captura(page, 'publico_03_login')})
    page.fill('#login input[type="text"]', 'usuario.demo')
    page.fill('#login input[type="password"]', 'incorrecta')
    page.click('#login button[type="submit"]')
    esperar(page, 1200)
    indice['publico'].append({'seccion': 'Error de credenciales', 'imagen': captura(page, 'publico_04_login_error')})
    page.close()


def rol(navegador, clave, usuario, password, indice):
    contexto = navegador.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1.25, locale='es-MX')
    page = contexto.new_page()
    page.goto(URL)
    esperar(page, 3200)
    abrir_menu(page, 'Iniciar sesión')
    page.fill('#login input[type="text"]', usuario)
    page.fill('#login input[type="password"]', password)
    page.click('#login button[type="submit"]')
    try:
        page.wait_for_selector('aside[class*="sidebar"]', timeout=20000)
    except Exception:
        captura(page, f'error_{clave}')
        print(f'  ! {clave}: no se abrió el panel', file=sys.stderr)
        contexto.close()
        return
    esperar(page, 2500)
    secciones = []
    botones = page.locator(BOTONES_MENU)
    etiquetas = [b.inner_text().strip().replace('\n', ' ') for b in botones.all()]
    for i, etiqueta in enumerate(etiquetas):
        try:
            page.locator(BOTONES_MENU).nth(i).click()
            esperar(page)
            page.evaluate('window.scrollTo(0, 0)')
            page.wait_for_timeout(300)
            secciones.append({'seccion': etiqueta, 'imagen': captura(page, f'{clave}_{i + 1:02d}')})
        except Exception as exc:
            print(f'  ! {clave} / {etiqueta}: {exc}', file=sys.stderr)
    indice[clave] = secciones
    print(f'{clave}: {len(secciones)} secciones -> {", ".join(etiquetas)}')
    contexto.close()


def main():
    os.makedirs(DESTINO, exist_ok=True)
    ruta_indice = os.path.join(DESTINO, 'indice.json')
    indice = {}
    if os.path.exists(ruta_indice):
        with open(ruta_indice, encoding='utf-8') as f:
            indice = json.load(f)
    seleccion = set(sys.argv[1:])
    roles_seleccionados = [
        (clave, usuario, variable, os.environ.get(variable))
        for clave, usuario, variable in ROLES
        if not seleccion or clave in seleccion
    ]
    faltantes = [variable for _, _, variable, password in roles_seleccionados if not password]
    if faltantes:
        raise RuntimeError(
            f'Configura las variables de entorno requeridas: {", ".join(faltantes)}'
        )
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel='msedge', headless=True)
        if not seleccion or 'publico' in seleccion:
            publicas(navegador.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1.25, locale='es-MX'), indice)
        for clave, usuario, _, password in roles_seleccionados:
            rol(navegador, clave, usuario, password, indice)
        navegador.close()
    with open(ruta_indice, 'w', encoding='utf-8') as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
