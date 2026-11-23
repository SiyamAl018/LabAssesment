import { Link } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader';
import EmptyState from '../components/ui/EmptyState';

export default function DashboardPage() {
  return <><PageHeader eyebrow="YOUR FIELDWORK, ORGANIZED" title="A clearer day in the field." description="Capture visits, keep promises, and stay close to every farm." action={<Link className="button" to="/visits/new">+ Record a visit</Link>} />
    <section className="hero"><div><span className="hero-tag">A little less paperwork</span><h2>More time for farms.<br />Less time taking notes.</h2><p>Your visits, advice, and follow-ups will come together here.</p><Link className="button light" to="/visits/new">Start your first visit <span>↗</span></Link></div><div className="field-art" aria-hidden="true"><span className="sun"/><span className="hill hill-one"/><span className="hill hill-two"/><span className="hill hill-three"/><span className="field-caption">GROWING BETTER CONNECTIONS</span></div></section>
    <section className="stats" aria-label="Visit summary">{['Visits this month', 'Registered farms', 'Pending follow-ups'].map((label, index) => <article className="stat-card" key={label}><span className="muted">{label}</span><strong>—</strong><small>0{index + 1} / Awaiting data</small></article>)}</section>
    <div className="section-heading"><h2>Your follow-ups</h2><span className="muted">Every promise matters</span></div><section className="two-columns">{['Overdue', 'Due soon'].map((title, index) => <article className="panel" key={title}><div className="panel-heading"><h3><span className={`status-dot ${index === 0 ? 'amber' : ''}`} />{title}</h3><span className="badge">—</span></div><EmptyState title="Waiting for your reminders" description="Farm names, promises, and due dates will appear once the backend is connected." /></article>)}</section>
  </>;
}
