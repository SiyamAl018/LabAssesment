import { useState, type InputHTMLAttributes } from 'react';
import { Eye, EyeOff, type LucideIcon } from 'lucide-react';

type Props = InputHTMLAttributes<HTMLInputElement> & { label: string; icon: LucideIcon; error?: string; hint?: string };
export default function AuthField({ label, icon: Icon, error, hint, id, type, ...props }: Props) {
  const [visible, setVisible] = useState(false);
  const password = type === 'password';
  return <div className="auth-field"><label htmlFor={id}>{label}</label><div className="auth-input-wrap"><Icon size={18} aria-hidden="true" /><input {...props} id={id} type={password && visible ? 'text' : type} aria-invalid={!!error} aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined} />{password && <button className="password-toggle" type="button" onClick={() => setVisible(!visible)} aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`} aria-pressed={visible}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button>}</div>{hint && <p id={`${id}-hint`} className="auth-hint">{hint}</p>}{error && <p className="auth-field-error" id={`${id}-error`}>{error}</p>}</div>;
}
