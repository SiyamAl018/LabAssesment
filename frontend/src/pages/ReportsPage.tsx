import { useState } from 'react';
import PageHeader from '../components/ui/PageHeader';
import useApi from '../hooks/useApi';
import { localDate } from '../services/api';
import type { Report } from '../types';

export default function ReportsPage() {
  const [month, setMonth] = useState(localDate().slice(0, 7));
  const { data, loading, error } = useApi<Report>(`/reports?month=${encodeURIComponent(month)}`);
  return <><PageHeader eyebrow="SEE THE BIGGER PICTURE" title="Monthly report" description="Stored visit records only. Missing information stays missing." />
    <section className="panel form-panel"><label htmlFor="report-month">Report month</label><input id="report-month" type="month" required value={month} onChange={e => { if (e.target.value) setMonth(e.target.value); }} />
      {loading && <p role="status">Loading report…</p>}{error && <p role="alert">{error}</p>}
      {data && <><dl><dt>Total visits</dt><dd>{data.total_visits}</dd><dt>Unique matched farms</dt><dd>{data.unique_farms}</dd><dt>No-problem visits</dt><dd>{data.no_problem_count}</dd><dt>Unmatched visits</dt><dd>{data.unmatched_visits}</dd></dl>
        <h2>Problems</h2>{data.problems.length ? <ul>{data.problems.map(p => <li key={p.note_id}>{p.text}</li>)}</ul> : <p>No problems recorded.</p>}
        <h2>Advice</h2>{data.advice.length ? <ul>{data.advice.map(a => <li key={a.note_id}>{a.text}</li>)}</ul> : <p>No advice recorded.</p>}
        <h2>All visits ({data.total_visits})</h2>{data.visits.map(v => <article key={v.id}><h3>{v.visit_date} · {v.parsed.farmer || 'Farmer not recorded'}</h3><p>{v.parsed.no_problem ? 'No problem reported' : v.parsed.problem || 'Problem not recorded'}</p><p>{v.parsed.advice || 'Advice not recorded'}</p></article>)}
      </>}
    </section></>;
}
