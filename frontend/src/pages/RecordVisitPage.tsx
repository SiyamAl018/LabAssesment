import { useState } from 'react';
import PageHeader from '../components/ui/PageHeader';
import useSpeechToText from '../hooks/useSpeechToText';
export default function RecordVisitPage() {
  const [language, setLanguage] = useState('bn-BD');
  const [copyStatus, setCopyStatus] = useState('');
  const { transcript, setTranscript, interim, status, error, errorCode, supported, start, stop } = useSpeechToText();
  const active = status !== 'idle';
  async function copyPageLink() {
    try { await navigator.clipboard.writeText(window.location.href); setCopyStatus('Link copied. Paste it into Google Chrome.'); }
    catch { setCopyStatus(`Open Google Chrome and enter: ${window.location.href}`); }
  }
  return <><PageHeader eyebrow="CAPTURE THE CONVERSATION" title="Record a farm visit" description="Speak in Bangla, watch your words become text, then review your notes." />
    <section className="two-columns"><article className="panel form-panel"><h2>Voice visit note</h2>
      <label htmlFor="language">Spoken language</label><select id="language" value={language} disabled={active} onChange={e => setLanguage(e.target.value)}><option value="bn-BD">{'\u09ac\u09be\u0982\u09b2\u09be'} (Bangladesh)</option><option value="en-US">English (US)</option></select>
      <div className={`voice-capture ${active ? 'is-active' : ''}`}><h3>{status === 'starting' ? 'Opening microphone...' : status === 'listening' ? 'Listening to your visit note...' : status === 'stopping' ? 'Finishing transcription...' : 'Tell us about your visit'}</h3><p>Mention the farmer, problem, advice, and follow-up.</p><button type="button" className="button" disabled={!supported || status === 'stopping'} onClick={() => active ? stop() : start(language)}>{active ? 'Stop recording' : 'Start voice note'}</button><p className="helper" role="status">{active ? 'Microphone session active' : 'Ready when you are'}</p></div>
      {!supported && <p className="notice">Voice recognition is unavailable in this browser. Use a supported browser or type below.</p>}
      {error && <p className="voice-error" role="alert">{error}</p>}
      {(errorCode === 'network' || errorCode === 'service-not-allowed' || !supported) && <div className="notice"><strong>Try in Google Chrome</strong><p>The preview may expose the microphone API without a working speech service. Copy this page address and open it in a standalone browser.</p><button type="button" className="secondary-button" onClick={copyPageLink}>Copy page link</button><p role="status">{copyStatus}</p><p>After opening: allow the microphone, choose Bangla, then press Start voice note.</p></div>}
      <label htmlFor="transcript">Your transcript</label><textarea id="transcript" lang={language === 'bn-BD' ? 'bn' : 'en'} rows={8} value={transcript} readOnly={active} onChange={e => setTranscript(e.target.value)} placeholder="Your spoken words will appear here. You can also type a note." aria-describedby="transcript-help" />
      {interim && <div className="interim-transcript" role="status"><strong>Live speech</strong><p lang={language === 'bn-BD' ? 'bn' : 'en'}>{interim}</p></div>}
      <p className="helper" id="transcript-help">{active ? 'Stop recording to edit. Only finalized speech is kept.' : 'Review and correct the text. Start again to append more speech.'}</p><button type="button" className="secondary-button" disabled={active || !transcript} onClick={() => setTranscript('')}>Clear text</button>
      <p className="helper">Uses your browser's speech service, which may send audio for recognition and require internet. Transcribes live speech; no audio file is saved and notes are not submitted yet.</p>
    </article><article className="panel form-panel"><h2>Visit details</h2><p className="muted">Parsed fields will appear after backend integration.</p><div className="placeholder-list">{['Farm / farmer name', 'Problem observed', 'Advice given', 'Follow-up promise', 'Due date'].map(label => <div key={label}><span>{label}</span><strong>-</strong></div>)}</div><div className="notice">Name confirmation and previous visit advice will appear when a farm is recognized.</div></article></section></>;
}
