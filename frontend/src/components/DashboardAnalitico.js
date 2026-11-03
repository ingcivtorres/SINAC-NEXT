import React from 'react';
import './DashboardAnalitico.css';
import {useLanguage} from '../translations';

const DEFAULTS = {
  es: {title: 'Dashboard analítico', eyebrow: 'REPORTES ESTADÍSTICOS'},
  en: {title: 'Analytics dashboard', eyebrow: 'STATISTICAL REPORTS'},
  de: {title: 'Analyse-Dashboard', eyebrow: 'STATISTISCHE BERICHTE'},
  zh: {title: '数据分析面板', eyebrow: '统计报告'},
  pt: {title: 'Painel analítico', eyebrow: 'RELATÓRIOS ESTATÍSTICOS'},
};

export default function DashboardAnalitico({title, eyebrow, description, metrics = [], distribution = []}) {
  const {language} = useLanguage();
  const defaults = DEFAULTS[language] || DEFAULTS.es;
  const maximum = Math.max(...distribution.map(item => Number(item.value) || 0), 1);
  return <section className="analytics-dashboard"><div className="analytics-dashboard-head"><div><p className="panel-kicker">{eyebrow || defaults.eyebrow}</p><h3>{title || defaults.title}</h3>{description && <p>{description}</p>}</div></div><div className="analytics-metrics">{metrics.map(metric => <article key={metric.label}><strong>{metric.value ?? 0}</strong><span>{metric.label}</span><small>{metric.detail || ''}</small></article>)}</div>{distribution.length > 0 && <div className="analytics-distribution">{distribution.map(item => { const value = Number(item.value) || 0; return <div className="analytics-distribution-row" key={item.label}><div><span>{item.label}</span><strong>{value}</strong></div><i><b style={{width: `${Math.round((value / maximum) * 100)}%`}} /></i></div>; })}</div>}</section>;
}
