import type { ReactNode } from 'react';

export default function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="empty-state"><span className="empty-icon" aria-hidden="true">↗</span><h3>{title}</h3><p>{description}</p>{action}</div>;
}
