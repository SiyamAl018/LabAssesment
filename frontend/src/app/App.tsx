import { Route, Routes } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import DashboardPage from '../pages/DashboardPage';
import RecordVisitPage from '../pages/RecordVisitPage';
import FarmsPage from '../pages/FarmsPage';
import FarmHistoryPage from '../pages/FarmHistoryPage';
import ReportsPage from '../pages/ReportsPage';
import NotFoundPage from '../pages/NotFoundPage';

export default function App() {
  return <Routes><Route element={<AppLayout />}>
    <Route index element={<DashboardPage />} />
    <Route path="visits/new" element={<RecordVisitPage />} />
    <Route path="farms" element={<FarmsPage />} />
    <Route path="farms/:farmId" element={<FarmHistoryPage />} />
    <Route path="reports" element={<ReportsPage />} />
    <Route path="*" element={<NotFoundPage />} />
  </Route></Routes>;
}
