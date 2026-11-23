import PageHeader from '../components/ui/PageHeader';
import EmptyState from '../components/ui/EmptyState';

export default function FarmsPage() {
  return <><PageHeader eyebrow="KNOW EVERY FARM" title="Farms & history" description="A place for farm profiles and the full story of every visit." /><section className="panel"><EmptyState title="Your farm directory starts here" description="Connected farm records will link to individual profiles and visit timelines." /></section></>;
}
