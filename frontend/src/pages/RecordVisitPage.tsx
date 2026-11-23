import { useState } from 'react';
import PageHeader from '../components/ui/PageHeader';
import useSpeechToText from '../hooks/useSpeechToText';
import NoteDetails from '../components/NoteDetails';
import { apiRequest, localDate } from '../services/api';
import type { Farm, FarmInfo, Visit } from '../types';
import useApi from '../hooks/useApi';
export default function RecordVisitPage() {
  const [language, setLanguage] = useState('bn-BD');
  const [copyStatus, setCopyStatus] = useState('');
  const [visitDate, setVisitDate] = useState(localDate());
  const [note, setNote] = useState<Visit | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const farms = useApi<Farm[]>('/farms');
  const [farmId, setFarmId] = useState('');
  const [farmInfo, setFarmInfo] = useState<FarmInfo>({ owner_name: '', farm_name: '', location: '', plot: '', crop: '' });
  const { transcript, setTranscript, interim, status, error, errorCode, supported, start, stop } = useSpeechToText();
  const active = status !== 'idle';
  async function saveNote() {
    setSaving(true); setSaveError('');
    try { setNote(await apiRequest<Visit>('/notes', { method: 'POST', body: JSON.stringify({ raw_text: transcript, visit_date: visitDate, farm_id: farmId || null, farm_info: farmInfo }) })); }
    catch (e) { setSaveError(String(e)); } finally { setSaving(false); }
  }
  async function copyPageLink() {
    try { await navigator.clipboard.writeText(window.location.href); setCopyStatus('Link copied. Paste it into Google Chrome.'); }
    catch { setCopyStatus(`Open Google Chrome and enter: ${window.location.href}`); }
  }
  return <><PageHeader eyebrow="CAPTURE THE CONVERSATION" title="Record a farm visit" description="Speak in Bangla, watch your words become text, then review your notes." />
    <section className="two-columns"><article className="panel form-panel"><h2>Owner and farm details</h2>
      <label htmlFor="visit-farm">Existing farm</label><select id="visit-farm" disabled={saving || !!note} value={farmId} onChange={e => {
        setFarmId(e.target.value);
        const farm = farms.data?.find(f => f.id === e.target.value);
        setFarmInfo(previous => ({ ...previous, owner_name: farm?.owner_name || '', farm_name: farm?.name || '', location: farm?.location || '' }));
      }}><option value="">Enter farm details</option>{farms.data?.map(f => <option key={f.id} value={f.id}>{f.name}{f.owner_name ? ` · ${f.owner_name}` : ''}{f.location ? ` · ${f.location}` : ''}</option>)}</select>
      {farms.error && <p role="alert">Could not load farms. You can still enter details manually.</p>}
      {(['owner_name', 'farm_name', 'location', 'plot', 'crop'] as const).map(key => <div key={key}><label htmlFor={`visit-${key}`}>{key.replace('_', ' ')}{key === 'owner_name' || key === 'farm_name' ? ' (required)' : ' (optional)'}</label><input id={`visit-${key}`} value={farmInfo[key]} disabled={saving || !!note} required={key === 'owner_name' || key === 'farm_name'} onChange={e => setFarmInfo({ ...farmInfo, [key]: e.target.value })} /></div>)}
      <p className="helper">Owner and farm details are stored with this visit so its history can be tracked.</p><h2>Voice visit note</h2>
      <label htmlFor="language">Spoken language</label><select id="language" value={language} disabled={active} onChange={e => setLanguage(e.target.value)}><option value="bn-BD">{'\u09ac\u09be\u0982\u09b2\u09be'} (Bangladesh)</option><option value="en-US">English (US)</option></select>
      <div className={`voice-capture ${active ? 'is-active' : ''}`}><h3>{status === 'starting' ? 'Opening microphone...' : status === 'listening' ? 'Listening to your visit note...' : status === 'stopping' ? 'Finishing transcription...' : 'Tell us about your visit'}</h3><p>Mention the farmer, problem, advice, and follow-up.</p><button type="button" className="button" disabled={!supported || status === 'stopping'} onClick={() => active ? stop() : start(language)}>{active ? 'Stop recording' : 'Start voice note'}</button><p className="helper" role="status">{active ? 'Microphone session active' : 'Ready when you are'}</p></div>
      {!supported && <p className="notice">Voice recognition is unavailable in this browser. Use a supported browser or type below.</p>}
      {error && <p className="voice-error" role="alert">{error}</p>}
      {(errorCode === 'network' || errorCode === 'service-not-allowed' || !supported) && <div className="notice"><strong>Try in Google Chrome</strong><p>The preview may expose the microphone API without a working speech service. Copy this page address and open it in a standalone browser.</p><button type="button" className="secondary-button" onClick={copyPageLink}>Copy page link</button><p role="status">{copyStatus}</p><p>After opening: allow the microphone, choose Bangla, then press Start voice note.</p></div>}
      <label htmlFor="transcript">Your transcript</label><textarea id="transcript" lang={language === 'bn-BD' ? 'bn' : 'en'} rows={8} value={transcript} readOnly={active} onChange={e => setTranscript(e.target.value)} placeholder="Your spoken words will appear here. You can also type a note." aria-describedby="transcript-help" />
      {interim && <div className="interim-transcript" role="status"><strong>Live speech</strong><p lang={language === 'bn-BD' ? 'bn' : 'en'}>{interim}</p></div>}
      <p className="helper" id="transcript-help">{active ? 'Stop recording to edit. Only finalized speech is kept.' : 'Review and correct the text. Start again to append more speech.'}</p><button type="button" className="secondary-button" disabled={active || !transcript} onClick={() => setTranscript('')}>Clear text</button>
      <p className="helper">Uses your browser's speech service, which may send audio for recognition and require internet. No audio file is saved.</p>
      <label htmlFor="visit-date">Visit date</label><input id="visit-date" type="date" value={visitDate} disabled={saving || !!note} onChange={e => setVisitDate(e.target.value)} />
      <button className="button" disabled={active || saving || !!note || !visitDate || !farmInfo.owner_name.trim() || !farmInfo.farm_name.trim()} onClick={() => void saveNote()}>{saving ? 'Saving…' : note ? 'Visit saved' : 'Save visit'}</button>
      {note && <button className="secondary-button" disabled={active} onClick={() => { setNote(null); setTranscript(''); setVisitDate(localDate()); }}>Start another visit</button>}
      {note && <p className="notice">The saved transcript is permanent. Use the parsed fields to make corrections.</p>}
      {saveError && <p role="alert">{saveError}</p>}
    </article><article className="panel form-panel">{note ? <NoteDetails note={note} onChange={setNote} /> : <><h2>Visit details</h2><p>Save the visit to review extracted fields and confirm its farm. Missing details are allowed.</p></>}</article></section></>;
}
