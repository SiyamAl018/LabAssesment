import { useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, CircleAlert, LoaderCircle, LockKeyhole, Mail, UserRound } from 'lucide-react';
import AuthLayout from '../components/auth/AuthLayout';
import AuthField from '../components/auth/AuthField';
import { authMockEnabled, authService } from '../services/auth';
import '../styles/auth.css';

export default function AuthPage({ mode }: { mode: 'login' | 'signup' }) {
  const signup = mode === 'signup';
  const navigate = useNavigate();
  const location = useLocation();
  const [values, setValues] = useState({ fullName: '', email: '', password: '', confirmPassword: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(location.state?.registrationComplete === true ? 'Registration accepted. Please log in, or complete any required account verification.' : '');
  function update(name: keyof typeof values, value: string) {
    setValues(current => ({ ...current, [name]: value }));
    setErrors(current => ({ ...current, [name]: '' })); setError(''); setNotice('');
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    const next: Record<string, string> = {};
    if (signup && !values.fullName.trim()) next.fullName = 'Enter your full name.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) next.email = 'Enter a valid email address.';
    if (!values.password) next.password = 'Enter your password.';
    else if (signup && values.password.length < 8) next.password = 'Use at least 8 characters.';
    if (signup && (!values.confirmPassword || values.password !== values.confirmPassword)) next.confirmPassword = 'Passwords must match.';
    setErrors(next); setError(''); setNotice('');
    if (Object.keys(next).length) { document.getElementById(Object.keys(next)[0])?.focus(); return; }
    submitting.current = true; setPending(true);
    try {
      const input = { email: values.email.trim(), password: values.password };
      if (signup) await authService.register({ ...input, fullName: values.fullName.trim() });
      else await authService.login(input);
      setValues(current => ({ ...current, password: '', confirmPassword: '' }));
      if (!signup) { navigate('/', { replace: true }); return; }
      // Registration is not proof of a session. Confirm it with the existing service.
      try { await authService.me(); }
      catch {
        navigate('/login', { replace: true, state: { registrationComplete: true } });
        return;
      }
      navigate('/', { replace: true });
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Something went wrong. Please try again.'); }
    finally { submitting.current = false; setPending(false); }
  }
  return <AuthLayout><div className="auth-card"><div className="auth-heading-icon"><SproutMark /></div><p className="auth-kicker">{signup ? 'START YOUR NEXT CHAPTER' : 'BACK TO THE FIELD'}</p><h1>{signup ? 'Create your account' : 'Welcome back'}</h1><p className="auth-intro">{signup ? 'A better way to keep every farm visit connected.' : 'Your notes, your farms, your next step. All here.'}</p>
    {authMockEnabled && <div className="auth-demo" role="note"><strong>Demo Mode</strong><p>Use fictional details. Demo profiles reset on refresh and passwords are not verified.</p></div>}
    <form noValidate onSubmit={submit} aria-label={signup ? 'Sign up' : 'Login'} aria-busy={pending}>
      <fieldset disabled={pending} className="auth-fieldset">
        {signup && <AuthField id="fullName" label="Full name" icon={UserRound} autoComplete="name" placeholder="Your full name" value={values.fullName} onChange={e => update('fullName', e.target.value)} error={errors.fullName} required />}
        <AuthField id="email" type="email" label="Email address" icon={Mail} autoComplete="email" inputMode="email" placeholder="you@example.com" value={values.email} onChange={e => update('email', e.target.value)} error={errors.email} required />
        <AuthField id="password" type="password" label="Password" icon={LockKeyhole} autoComplete={signup ? 'new-password' : 'current-password'} placeholder={signup ? 'Create a strong password' : 'Enter your password'} value={values.password} onChange={e => update('password', e.target.value)} error={errors.password} hint={signup ? 'Use at least 8 characters.' : undefined} required />
        {signup && <AuthField id="confirmPassword" type="password" label="Confirm password" icon={LockKeyhole} autoComplete="new-password" placeholder="Re-enter your password" value={values.confirmPassword} onChange={e => update('confirmPassword', e.target.value)} error={errors.confirmPassword} required />}
        {!signup && <><div className="auth-options flex items-center justify-between gap-3"><label className="auth-remember"><input type="checkbox" name="remember"/> Remember me</label><button className="auth-text-button" type="button" onClick={() => setNotice('Password reset is not available yet. Please contact your project administrator.')}>Forgot password?</button></div><p className="auth-hint auth-remember-hint">Remember me is a preview option; it does not change session duration.</p></>}
        {error && <div className="auth-error" role="alert"><CircleAlert size={18}/><span>{error}</span></div>}
        {notice && <div className="auth-notice" role="status">{notice}</div>}
        <button className="button auth-submit flex w-full items-center justify-center gap-3" type="submit" disabled={pending}>{pending ? <><LoaderCircle className="auth-spinner" size={18}/> {signup ? 'Creating account...' : 'Logging in...'}</> : <>{signup ? 'Create account' : 'Log in'}<ArrowRight size={18}/></>}</button>
      </fieldset>
    </form><p className="auth-switch">{signup ? 'Already have an account?' : 'New to FarmLog?'} <Link to={signup ? '/login' : '/signup'}>{signup ? 'Log in' : 'Create an account'}</Link></p>
    </div></AuthLayout>;
}
function SproutMark() { return <UserRound size={23} aria-hidden="true"/>; }

