import { useParams } from 'react-router-dom';
import PageHeader from '../components/ui/PageHeader';
import EmptyState from '../components/ui/EmptyState';

export default function FarmHistoryPage() {
  const { farmId } = useParams();
  return <><PageHeader eyebrow="FARM TIMELINE" title="Farm visit history" description={`Farm reference: ${farmId}`} /><section className="panel"><EmptyState title="Visit timeline" description="Each visit will show its date, problem, advice, and follow-up." /></section></>;
}
