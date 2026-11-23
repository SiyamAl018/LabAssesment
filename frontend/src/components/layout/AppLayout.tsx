import { NavLink, Outlet } from 'react-router-dom';

const links = [['/', 'Overview'], ['/visits/new', 'Record a visit'], ['/farms', 'Farms & history'], ['/reports', 'Monthly report']];

export default function AppLayout() {
  return <div className="app-shell">
    <aside className="sidebar">
      <NavLink to="/" className="brand"><span className="brand-icon">F</span> FarmLog<span className="brand-dot">.</span></NavLink>
      <p className="eyebrow nav-label">FIELD WORKSPACE</p>
      <nav aria-label="Main navigation">{links.map(([to, label], index) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}><span className="nav-number">0{index + 1}</span>{label}</NavLink>)}</nav>
      <div className="sidebar-note"><span className="status-dot" /> Frontend preview<p>Your fieldwork, in one place.</p></div>
      <div className="profile"><span className="avatar">S</span><div><strong>Sunny</strong><small>Field officer workspace</small></div></div>
    </aside>
    <div className="workspace"><header className="topbar"><span>Workspace <span className="muted">/ Field assistant</span></span><span className="badge">Development</span></header><main id="main-content"><Outlet /></main><footer>FarmLog · Built for better follow-ups</footer></div>
  </div>;
}
