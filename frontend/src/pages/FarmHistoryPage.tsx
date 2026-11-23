import { useParams } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader';
import NoteDetails from '../components/NoteDetails';
import useApi from '../hooks/useApi';
import type { Visit } from '../types';

export default function FarmHistoryPage() {
  const { farmId } = useParams();
  const { data, loading, error, refresh } = useApi<Visit[]>(`/farms/${farmId}/history`);
  return <><PageHeader eyebrow="FARM TIMELINE" title="Farm visit history" description="Visits are ordered by visit date, newest first." />
    {loading && <p role="status">Loading history…</p>}{error && <p role="alert">{error}</p>}{data?.length === 0 && <section className="panel"><p>No visits recorded for this farm.</p></section>}
    {data?.map((visit, index) => <article className="panel form-panel" key={visit.id}><h2>{visit.visit_date}{index === 0 ? ' · Last visit' : ''}</h2><p>Problem: {visit.parsed.no_problem ? 'No problem reported' : visit.parsed.problem || 'Not recorded'}</p><p>Advice: {visit.parsed.advice || 'Not recorded'}</p><p>Follow-up: {visit.parsed.follow_up || 'Not recorded'} {visit.parsed.due_date && `· Due ${visit.parsed.due_date}`} {visit.completed_by && '· Completed by a later visit'}</p><details><summary>View transcript and edit parsed fields</summary><NoteDetails note={visit} onChange={refresh} /></details></article>)}
  </>;
}
