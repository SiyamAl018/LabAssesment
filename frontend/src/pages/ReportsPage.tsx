import PageHeader from '../components/ui/PageHeader';
import EmptyState from '../components/ui/EmptyState';

export default function ReportsPage() {
  return <><PageHeader eyebrow="SEE THE BIGGER PICTURE" title="Monthly report" description="Review your fieldwork, one month at a time." /><section className="panel form-panel"><label htmlFor="report-month">Report month</label><input id="report-month" type="month" /><EmptyState title="Your monthly overview" description="Monthly summaries and visit records will appear after report integration." /></section></>;
}
