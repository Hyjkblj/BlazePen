import { Suspense, lazy, type ComponentType } from 'react';
import { createBrowserRouter, createHashRouter, RouterProvider } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import Layout from '@/components/Layout';
import LoadingScreen from '@/components/loading';

const Home = lazy(() => import('@/pages/Home'));
const FirstStep = lazy(() => import('@/pages/FirstStep'));
const CharacterSetting = lazy(() => import('@/pages/CharacterSetting'));
const CharacterSelection = lazy(() => import('@/pages/CharacterSelection'));
const FirstMeetingSelection = lazy(() => import('@/pages/FirstMeetingSelection'));
const Game = lazy(() => import('@/pages/Game'));
const Training = lazy(() => import('@/pages/Training'));
const TrainingProgress = lazy(() => import('@/pages/TrainingProgress'));
const TrainingReport = lazy(() => import('@/pages/TrainingReport'));
const TrainingDiagnostics = lazy(() => import('@/pages/TrainingDiagnostics'));
const NotFound = lazy(() => import('@/pages/NotFound'));

const renderLazyPage = (PageComponent: ComponentType) => (
  <Suspense fallback={<LoadingScreen message="页面加载中..." />}>
    <PageComponent />
  </Suspense>
);

const routes = [
  {
    path: ROUTES.HOME,
    element: <Layout />,
    children: [
      { index: true, element: renderLazyPage(Home) },
      { path: 'firststep', element: renderLazyPage(FirstStep) },
      { path: 'charactersetting', element: renderLazyPage(CharacterSetting) },
      { path: 'characterselection', element: renderLazyPage(CharacterSelection) },
      { path: 'firstmeeting', element: renderLazyPage(FirstMeetingSelection) },
      { path: 'game', element: renderLazyPage(Game) },
      { path: 'training', element: renderLazyPage(Training) },
      { path: 'training/progress', element: renderLazyPage(TrainingProgress) },
      { path: 'training/report', element: renderLazyPage(TrainingReport) },
      { path: 'training/diagnostics', element: renderLazyPage(TrainingDiagnostics) },
      { path: '*', element: renderLazyPage(NotFound) },
    ],
  },
];

const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:';
const router = (isFileProtocol ? createHashRouter : createBrowserRouter)(routes);

function AppRouter() {
  return <RouterProvider router={router} />;
}

export default AppRouter;
