import React from 'react';
import './DashboardAnalitico.css';

export default function DashboardAnalitico({title = 'Dashboard analítico', eyebrow = 'REPORTES ESTADÍSTICOS', description, metrics = [], distribution = []}) {
  const maximum = Math.max(...distribution.map(item => Number(item.value) || 0), 1);
  return <section className="analytics-dashboard"><div className="analytics-dashboard-head"><div><p className="panel-kicker">{eyebrow}</p><h3>{title}</h3>{description && <p>{description}</p>}</div></div><div className="analytics-metrics">{metrics.map(metric => <article key={metric.label}><strong>{metric.value ?? 0}</strong><span>{metric.label}</span><small>{metric.detail || ''}</small></article>)}</div>{distribution.length > 0 && <div className="analytics-distribution">{distribution.map(item => { const value = Number(item.value) || 0; return <div className="analytics-distribution-row" key={item.label}><div><span>{item.label}</span><strong>{value}</strong></div><i><b style={{width: `${Math.round((value / maximum) * 100)}%`}} /></i></div>; })}</div>}</section>;
}
