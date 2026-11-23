import { useEffect, useRef, useState } from 'react';
interface Recognition {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: { results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
  start(): void; stop(): void; abort(): void;
}
type SpeechWindow = Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
const errors: Record<string, string> = {
  'not-allowed': 'Allow microphone permission in your browser and try again.',
  'service-not-allowed': 'Your browser has blocked speech recognition.',
  'audio-capture': 'No microphone is available. Connect a microphone and retry.',
  'no-speech': 'No speech detected. Please try again.',
  network: 'The browser could not reach its speech recognition service. If you are using the VS Code preview, open this page in Google Chrome and allow microphone access. If it also fails in Chrome, check your connection, VPN, or firewall and retry.',
  'language-not-supported': 'The selected language is not supported by this speech service.',
};
export default function useSpeechToText() {
  const [transcript, setTranscript] = useState('');
  const [interim, setInterim] = useState('');
  const [status, setStatus] = useState<'idle' | 'starting' | 'listening' | 'stopping'>('idle');
  const [error, setError] = useState('');
  const [errorCode, setErrorCode] = useState('');
  const recognition = useRef<Recognition | null>(null);
  const speechWindow = window as SpeechWindow;
  const Constructor = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
  useEffect(() => () => {
    const current = recognition.current;
    if (current) { current.onresult = null; current.onerror = null; current.onend = null; current.onstart = null; current.abort(); }
  }, []);
  function start(language: string) {
    if (recognition.current) return;
    setError('');
    setErrorCode('');
    if (!Constructor) { setError('Speech recognition is unavailable. You can type below.'); return; }
    if (!window.isSecureContext) { setError('Microphone access requires HTTPS or localhost.'); return; }
    const current = new Constructor();
    const prefix = transcript.trim();
    recognition.current = current;
    current.lang = language;
    current.continuous = true;
    current.interimResults = true;
    setStatus('starting'); setInterim('');
    current.onstart = () => setStatus('listening');
    current.onresult = ({ results }) => {
      const final: string[] = []; const pending: string[] = [];
      // Rebuild session results so revised interim words are not duplicated.
      for (let i = 0; i < results.length; i++) (results[i].isFinal ? final : pending).push(results[i][0].transcript);
      setTranscript([prefix, ...final].filter(Boolean).join(' '));
      setInterim(pending.join(' '));
    };
    current.onerror = ({ error: code }) => {
      if (recognition.current !== current) return;
      if (code !== 'aborted') {
        setErrorCode(code);
        setError(errors[code] ?? `Recognition failed (${code}). Please retry.`);
      }
      // Release failed sessions immediately, even if the browser omits onend.
      current.onresult = null; current.onerror = null; current.onend = null; current.onstart = null;
      recognition.current = null;
      setStatus('idle'); setInterim('');
      current.abort();
    };
    current.onend = () => { recognition.current = null; setStatus('idle'); setInterim(''); };
    try { current.start(); } catch { recognition.current = null; setStatus('idle'); setError('Could not start the microphone. Please retry.'); }
  }
  function stop() { if (recognition.current) { setStatus('stopping'); recognition.current.stop(); } }
  return { transcript, setTranscript, interim, status, error, errorCode, supported: !!Constructor, start, stop };
}
