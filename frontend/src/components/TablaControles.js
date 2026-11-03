import React, {useEffect, useMemo, useState} from 'react';
import {useLanguage} from '../translations';
import './TablaControles.css';

const ETIQUETAS = {
  es: {period: 'Periodo', type: 'Tipo', subject: 'Materia', status: 'Estado', program: 'Programa', modality: 'Modalidad', result: 'Resultado', student: 'Alumno', director: 'Director', line: 'Línea de investigación', role: 'Rol', grade: 'Calificación', date: 'Fecha'},
  en: {period: 'Term', type: 'Type', subject: 'Course', status: 'Status', program: 'Program', modality: 'Modality', result: 'Result', student: 'Student', director: 'Director', line: 'Research line', role: 'Role', grade: 'Grade', date: 'Date'},
  de: {period: 'Zeitraum', type: 'Typ', subject: 'Fach', status: 'Status', program: 'Studiengang', modality: 'Modalität', result: 'Ergebnis', student: 'Studierende/r', director: 'Betreuer/in', line: 'Forschungslinie', role: 'Rolle', grade: 'Note', date: 'Datum'},
  zh: {period: '学期', type: '类型', subject: '课程', status: '状态', program: '项目', modality: '方式', result: '结果', student: '学生', director: '导师', line: '研究方向', role: '角色', grade: '成绩', date: '日期'},
  pt: {period: 'Período', type: 'Tipo', subject: 'Disciplina', status: 'Status', program: 'Programa', modality: 'Modalidade', result: 'Resultado', student: 'Aluno', director: 'Orientador', line: 'Linha de pesquisa', role: 'Função', grade: 'Nota', date: 'Data'},
};

const COPY = {
  es: {search: 'Buscar...', all: 'Todos', clear: 'Limpiar filtros', perPage: 'Por página', showing: 'Mostrando {desde}–{hasta} de {total}', filtered: '(filtrado de {total})', first: 'Primera página', prev: 'Página anterior', next: 'Página siguiente', last: 'Última página', page: 'Página {pagina} de {paginas}', empty: 'No hay registros que coincidan con la búsqueda o los filtros.'},
  en: {search: 'Search...', all: 'All', clear: 'Clear filters', perPage: 'Per page', showing: 'Showing {desde}–{hasta} of {total}', filtered: '(filtered from {total})', first: 'First page', prev: 'Previous page', next: 'Next page', last: 'Last page', page: 'Page {pagina} of {paginas}', empty: 'No records match the search or filters.'},
  de: {search: 'Suchen...', all: 'Alle', clear: 'Filter zurücksetzen', perPage: 'Pro Seite', showing: '{desde}–{hasta} von {total}', filtered: '(gefiltert aus {total})', first: 'Erste Seite', prev: 'Vorherige Seite', next: 'Nächste Seite', last: 'Letzte Seite', page: 'Seite {pagina} von {paginas}', empty: 'Keine Einträge entsprechen der Suche oder den Filtern.'},
  zh: {search: '搜索...', all: '全部', clear: '清除筛选', perPage: '每页', showing: '显示第 {desde}–{hasta} 条，共 {total} 条', filtered: '（从 {total} 条中筛选）', first: '第一页', prev: '上一页', next: '下一页', last: '最后一页', page: '第 {pagina} / {paginas} 页', empty: '没有符合搜索或筛选条件的记录。'},
  pt: {search: 'Buscar...', all: 'Todos', clear: 'Limpar filtros', perPage: 'Por página', showing: 'Exibindo {desde}–{hasta} de {total}', filtered: '(filtrado de {total})', first: 'Primeira página', prev: 'Página anterior', next: 'Próxima página', last: 'Última página', page: 'Página {pagina} de {paginas}', empty: 'Nenhum registro corresponde à busca ou aos filtros.'},
};

const TAMANOS = [10, 25, 50, 100];

export function useTablaCopy() {
  const {language} = useLanguage();
  return COPY[language] || COPY.es;
}

export function useEtiquetasFiltro() {
  const {language} = useLanguage();
  return ETIQUETAS[language] || ETIQUETAS.es;
}

const formatear = (texto, valores) => Object.entries(valores).reduce((acc, [clave, valor]) => acc.replace(`{${clave}}`, valor), texto);

export const normalizarTexto = (valor) => String(valor ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();

export function useTablaControl(items, {campos, filtros = {}, porPagina: porPaginaInicial = 10, sinFiltros = false} = {}) {
  const lista = useMemo(() => (Array.isArray(items) ? items : []), [items]);
  const [busqueda, setBusqueda] = useState('');
  const [valores, setValores] = useState({});
  const [pagina, setPagina] = useState(1);
  const [porPagina, setPorPagina] = useState(porPaginaInicial);

  const consulta = normalizarTexto(busqueda);
  const filtrados = sinFiltros ? lista : lista.filter(item => {
    if (consulta && campos) {
      const texto = [].concat(campos(item)).map(normalizarTexto).join(' ');
      if (!consulta.split(/\s+/).every(palabra => texto.includes(palabra))) return false;
    }
    return Object.entries(valores).every(([clave, valor]) => {
      if (valor === '' || valor == null || !filtros[clave]) return true;
      return [].concat(filtros[clave](item)).map(v => String(v ?? '')).includes(String(valor));
    });
  });

  const total = filtrados.length;
  const totalPaginas = Math.max(1, Math.ceil(total / porPagina));
  const paginaActual = Math.min(pagina, totalPaginas);
  const inicio = (paginaActual - 1) * porPagina;
  const visibles = filtrados.slice(inicio, inicio + porPagina);

  useEffect(() => { setPagina(1); }, [busqueda, valores, porPagina]);

  const opciones = (clave) => {
    if (!filtros[clave]) return [];
    const unicos = new Set();
    lista.forEach(item => [].concat(filtros[clave](item)).forEach(v => { if (v !== '' && v != null) unicos.add(String(v)); }));
    return [...unicos].sort((a, b) => a.localeCompare(b, undefined, {numeric: true}));
  };

  return {
    busqueda, setBusqueda,
    valores, setValor: (clave, valor) => setValores(prev => ({...prev, [clave]: valor})),
    limpiar: () => { setBusqueda(''); setValores({}); },
    hayFiltros: !sinFiltros && (Boolean(busqueda) || Object.values(valores).some(v => v !== '' && v != null)),
    pagina: paginaActual, setPagina, porPagina, setPorPagina,
    filtrados, visibles, total, totalOriginal: lista.length, totalPaginas,
    desde: total ? inicio + 1 : 0, hasta: Math.min(inicio + porPagina, total),
    opciones, buscable: Boolean(campos),
  };
}

export function TablaHerramientas({control, placeholder, filtros = [], children}) {
  const t = useTablaCopy();
  return <div className="tabla-herramientas">
    {control.buscable && <input type="search" className="tabla-busqueda" value={control.busqueda} onChange={event => control.setBusqueda(event.target.value)} placeholder={placeholder || t.search} aria-label={placeholder || t.search}/>}
    {filtros.map(filtro => {
      const opciones = filtro.opciones || control.opciones(filtro.clave).map(value => ({value, label: filtro.formato ? filtro.formato(value) : value}));
      return <label key={filtro.clave} className="tabla-filtro"><span>{filtro.etiqueta}</span>
        <select value={control.valores[filtro.clave] ?? ''} onChange={event => control.setValor(filtro.clave, event.target.value)}>
          <option value="">{t.all}</option>
          {opciones.map(opcion => <option key={opcion.value} value={opcion.value}>{opcion.label}</option>)}
        </select>
      </label>;
    })}
    {children}
    {control.hayFiltros && <button type="button" className="tabla-limpiar" onClick={control.limpiar}>{t.clear}</button>}
  </div>;
}

export function TablaPaginacion({control}) {
  const t = useTablaCopy();
  if (!control.totalOriginal) return null;
  const {pagina, totalPaginas, setPagina} = control;
  const paginas = [];
  for (let numero = Math.max(1, pagina - 2); numero <= Math.min(totalPaginas, pagina + 2); numero += 1) paginas.push(numero);
  return <div className="tabla-paginacion">
    <span className="tabla-resumen">
      {control.total ? formatear(t.showing, {desde: control.desde, hasta: control.hasta, total: control.total}) : t.empty}
      {control.hayFiltros && control.total !== control.totalOriginal && ` ${formatear(t.filtered, {total: control.totalOriginal})}`}
    </span>
    <label className="tabla-tamano"><span>{t.perPage}</span>
      <select value={control.porPagina} onChange={event => control.setPorPagina(Number(event.target.value))}>
        {TAMANOS.map(tamano => <option key={tamano} value={tamano}>{tamano}</option>)}
      </select>
    </label>
    {totalPaginas > 1 && <nav className="tabla-paginas" aria-label={formatear(t.page, {pagina, paginas: totalPaginas})}>
      <button type="button" onClick={() => setPagina(1)} disabled={pagina === 1} aria-label={t.first} title={t.first}>«</button>
      <button type="button" onClick={() => setPagina(pagina - 1)} disabled={pagina === 1} aria-label={t.prev} title={t.prev}>‹</button>
      {paginas.map(numero => <button type="button" key={numero} className={numero === pagina ? 'is-active' : ''} onClick={() => setPagina(numero)} aria-current={numero === pagina ? 'page' : undefined}>{numero}</button>)}
      <button type="button" onClick={() => setPagina(pagina + 1)} disabled={pagina === totalPaginas} aria-label={t.next} title={t.next}>›</button>
      <button type="button" onClick={() => setPagina(totalPaginas)} disabled={pagina === totalPaginas} aria-label={t.last} title={t.last}>»</button>
    </nav>}
  </div>;
}
