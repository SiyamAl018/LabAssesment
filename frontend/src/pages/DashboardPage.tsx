import { Link } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader';
import useApi from '../hooks/useApi';
import { localDate } from '../services/api';
import type { Farm, Followups, Report } from '../types';

export default function DashboardPage() {
  const farms = useApi<Farm[]>('/farms');
  const report = useApi<Report>(`/reports?month=${localDate().slice(0, 7)}`);
  const followups = useApi<Followups>('/followups');
  const pending = followups.data ? followups.data.overdue.length + followups.data.upcoming.length + followups.data.undated.length : '—';
  return <><PageHeader eyebrow="YOUR FIELDWORK, ORGANIZED" title="A clearer day in the field." description="Capture visits, keep promises, and stay close to every farm." action={<Link className="button" to="/visits/new">+ Record a visit</Link>} />
    <section className="hero"><div><span className="hero-tag">A little less paperwork</span><h2>More time for farms.<br />Less time taking notes.</h2><p>Your visits, advice, and follow-ups come together here.</p><Link className="button light" to="/visits/new">Record a visit <span>↗</span></Link></div><div className="field-art" aria-hidden="true"><span className="sun"/><span className="hill hill-one"/><span className="hill hill-two"/><span className="hill hill-three"/><span className="field-caption">GROWING BETTER CONNECTIONS</span></div></section>
    {[farms.error, report.error, followups.error].filter(Boolean).map((error, i) => <p role="alert" key={i}>{error}</p>)}
    <section className="stats" aria-label="Visit summary">{[['Visits this month', report.data?.total_visits ?? '—'], ['Registered farms', farms.data?.length ?? '—'], ['Pending follow-ups', pending]].map(([label, value]) => <article className="stat-card" key={label}><span className="muted">{label}</span><strong>{value}</strong></article>)}</section>
    <div className="section-heading"><h2>Your follow-ups</h2><span className="muted">Every promise matters</span></div>
    {followups.loading && <p role="status">Loading follow-ups…</p>}
    <section className="two-columns">{(['overdue', 'upcoming', 'undated', 'completed'] as const).map(bucket => <article className="panel" key={bucket}><div className="panel-heading"><h3>{bucket === 'undated' ? 'Needs a due date' : bucket[0].toUpperCase() + bucket.slice(1)}</h3><span className="badge">{followups.data?.[bucket].length ?? '—'}</span></div>
      {followups.data?.[bucket].length === 0 && <p>No items.</p>}
      {followups.data?.[bucket].map(item => <div key={item.note_id}><h4>{item.farm_id ? <Link to={`/farms/${item.farm_id}`}>{item.farm_name}</Link> : 'Unmatched farm'}</h4><p>{item.follow_up}</p><p>{item.due_date || 'Date not recorded'}</p></div>)}
    </article>)}</section>
  </>;
}
