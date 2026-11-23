import { useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader';
import useApi from '../hooks/useApi';
import { apiRequest } from '../services/api';
import type { Farm } from '../types';

export default function FarmsPage() {
  const { data, loading, error, refresh } = useApi<Farm[]>('/farms');
  const [name, setName] = useState('');
  const [owner, setOwner] = useState('');
  const [location, setLocation] = useState('');
  const [saveError, setSaveError] = useState('');
  const [busy, setBusy] = useState(false);
  return <><PageHeader eyebrow="KNOW EVERY FARM" title="Farms & history" description="Farm profiles and the full story of every visit." />
    <section className="panel form-panel"><h2>Register a farm</h2><form onSubmit={async e => {
      e.preventDefault(); setBusy(true); setSaveError('');
      try { await apiRequest('/farms', { method: 'POST', body: JSON.stringify({ name, owner_name: owner, location: location || null }) }); setName(''); setOwner(''); setLocation(''); refresh(); }
      catch (e) { setSaveError(String(e)); } finally { setBusy(false); }
    }}><label htmlFor="farm-owner">Owner name</label><input id="farm-owner" required value={owner} onChange={e => setOwner(e.target.value)} /><label htmlFor="farm-name">Farm name</label><input id="farm-name" required value={name} onChange={e => setName(e.target.value)} /><label htmlFor="farm-location">Location (optional)</label><input id="farm-location" value={location} onChange={e => setLocation(e.target.value)} /><button className="button" disabled={busy || !name.trim() || !owner.trim()}>Add farm</button></form>{saveError && <p role="alert">{saveError}</p>}</section>
    <section className="panel"><h2>Farm directory</h2>{loading && <p role="status">Loading farms…</p>}{error && <p role="alert">{error}</p>}{data?.length === 0 && <p>No farms registered yet.</p>}<ul>{data?.map(f => <li key={f.id}><Link to={`/farms/${f.id}`}>{f.name}</Link>{f.owner_name && ` · Owner: ${f.owner_name}`}{f.location && ` · ${f.location}`}</li>)}</ul></section>
  </>;
}
