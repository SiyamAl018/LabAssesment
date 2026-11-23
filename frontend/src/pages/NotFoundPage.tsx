import { Link } from 'react-router-dom';
import EmptyState from '../components/ui/EmptyState';

export default function NotFoundPage() {
  return <section className="panel"><EmptyState title="Page not found" description="This page does not exist." action={<Link className="button" to="/">Back to overview</Link>} /></section>;
}
