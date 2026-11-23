import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest } from '../services/api';
import type { Farm, ParsedFields, Visit } from '../types';

export default function NoteDetails({ note, onChange }: { note: Visit; onChange: (note: Visit) => void }) {
  const [fields, setFields] = useState(note.parsed);
  const [farms, setFarms] = useState<Farm[]>([]);
  const [farmId, setFarmId] = useState(note.farm_id || '');
  const [newFarm, setNewFarm] = useState(note.farm_info?.farm_name || '');
  const [lastVisit, setLastVisit] = useState<Visit | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { setFields(note.parsed); setFarmId(note.farm_id || ''); }, [note]);
  useEffect(() => {
    let cancelled = false;
    apiRequest<Farm[]>('/farms').then(data => { if (!cancelled) setFarms(data); }).catch(e => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    let cancelled = false;
    setLastVisit(null);
    if (note.farm_id) apiRequest<Visit[]>(`/farms/${note.farm_id}/history`).then(visits => {
      const index = visits.findIndex(v => v.id === note.id);
      if (!cancelled) setLastVisit(visits[index + 1] || null);
    }).catch(e => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [note]);
  async function run(action: () => Promise<void>) {
    setBusy(true); setError(''); setMessage('');
    try { await action(); setMessage('Saved.'); } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <><h2>Saved visit details</h2><p role="status">Note saved · Parsing: {note.parse_status}</p>
    <dl>{Object.entries(note.farm_info || {}).filter(([, value]) => value).map(([key, value]) => <div key={key}><dt>{key.replace('_', ' ')}</dt><dd>{value}</dd></div>)}</dl>
    {note.parse_status === 'failed' && <p className="notice">Your original text is safe. Fill in any known fields below.</p>}
    <details><summary>Original transcript (read only)</summary><p style={{ whiteSpace: 'pre-wrap' }}>{note.raw_text || '(Empty transcript)'}</p></details>
    <form onSubmit={e => { e.preventDefault(); void run(async () => {
      const changes: Partial<ParsedFields> = {};
      for (const key of Object.keys(fields) as (keyof ParsedFields)[]) {
        if (fields[key] !== note.parsed[key]) Object.assign(changes, { [key]: fields[key] });
      }
      onChange(await apiRequest<Visit>(`/notes/${note.id}`, { method: 'PATCH', body: JSON.stringify(changes) }));
    }); }}>
      {(['farmer', 'plot', 'crop', 'problem', 'advice', 'follow_up', 'due_date'] as const).map(key => <div key={key}><label htmlFor={`parsed-${key}`}>{key.replace('_', ' ')}</label><input id={`parsed-${key}`} type={key === 'due_date' ? 'date' : 'text'} value={fields[key] || ''} onChange={e => setFields({ ...fields, [key]: e.target.value || null })} /></div>)}
      <label htmlFor="no-problem">Problem status</label><select id="no-problem" value={fields.no_problem === null ? '' : String(fields.no_problem)} onChange={e => setFields({ ...fields, no_problem: e.target.value === '' ? null : e.target.value === 'true' })}><option value="">Unknown / not recorded</option><option value="true">Explicitly no problem</option><option value="false">Problem reported / not marked clear</option></select>
      <button className="button" disabled={busy}>Save field corrections</button>
    </form>
    <h3>Farm matching</h3><p>{note.match.status.replaceAll('_', ' ')}{note.farm_confirmed ? ' · Confirmed by you' : ''}</p>
    {note.match.candidates.length > 0 && <ul>{note.match.candidates.map(c => <li key={c.id}>{c.name} ({c.score}% similarity)</li>)}</ul>}
    <label htmlFor="confirm-farm">Assign this visit</label><select id="confirm-farm" value={farmId} onChange={e => setFarmId(e.target.value)}><option value="">No farm match</option>{farms.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}</select>
    <button className="button" disabled={busy} onClick={() => void run(async () => { onChange(await apiRequest<Visit>(`/notes/${note.id}/confirm-farm`, { method: 'POST', body: JSON.stringify({ farm_id: farmId || null }) })); })}>Confirm farm decision</button>
    <label htmlFor="new-farm">Register a new farm</label><input id="new-farm" value={newFarm} onChange={e => setNewFarm(e.target.value)} />
    <button className="secondary-button" disabled={busy || !newFarm.trim()} onClick={() => void run(async () => {
      const farm = await apiRequest<Farm>('/farms', { method: 'POST', body: JSON.stringify({ name: newFarm, owner_name: note.farm_info?.owner_name || note.parsed.farmer, location: note.farm_info?.location }) });
      setFarms(previous => [...previous, farm]); setFarmId(farm.id); setNewFarm('');
      onChange(await apiRequest<Visit>(`/notes/${note.id}/confirm-farm`, { method: 'POST', body: JSON.stringify({ farm_id: farm.id }) }));
    })}>Create farm and assign</button>
    {note.farm_id && <p><Link to={`/farms/${note.farm_id}`}>View farm history</Link></p>}
    {lastVisit && <div className="notice"><strong>Previous visit · {lastVisit.visit_date}</strong><p>{lastVisit.parsed.advice || 'No advice recorded.'}</p></div>}
    {error && <p role="alert">{error}</p>}<p role="status">{message}</p>
  </>;
}
