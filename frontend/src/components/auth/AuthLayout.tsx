import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Leaf, Sprout, Pause, Play } from 'lucide-react';
import FarmScene from './FarmScene';

export default function AuthLayout({ children }: { children: ReactNode }) {
  const [paused, setPaused] = useState(false);
  return <div className="auth-shell">
    <section className="auth-brand-panel living-farm-panel">
      <FarmScene paused={paused}/><div className="farm-shade" aria-hidden="true"/>
      <Link to="/" className="brand auth-brand"><span className="brand-icon"><Sprout size={26}/></span>FarmLog<span className="brand-dot">.</span></Link>
      <div className="auth-brand-copy"><p className="auth-kicker">THE FIELD OFFICER'S NOTEBOOK</p><h1>Every Farm <br/>Visit Matters.</h1><p>Capture field observations, track follow-ups, and manage farm visits in one place.</p></div>
      <div className="farm-caption"><span><span className="farm-live-dot"/> ROOTED IN THE FIELD</span><button type="button" className="farm-motion-toggle" aria-label={paused ? 'Play farm animation' : 'Pause farm animation'} aria-pressed={paused} onClick={() => setPaused(!paused)}>{paused ? <Play size={14}/> : <Pause size={14}/>}<span>{paused ? 'Play motion' : 'Pause motion'}</span></button></div>
    </section>
    <section className="auth-form-panel"><div className="auth-form-container"><Link className="auth-back" to="/">Explore the workspace <ArrowUpRight size={15}/></Link>{children}<p className="auth-footer-note"><Leaf size={14}/> A little less paperwork. More time for farms.</p></div></section>
  </div>;
}

