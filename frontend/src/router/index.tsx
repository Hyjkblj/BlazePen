import { Suspense, lazy, type ComponentType } from 'react';
import { createBrowserRouter, createHashRouter, RouterProvider } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import Layout from '@/components/Layout';
import LoadingScreen from '@/components/loading';
import RouteErrorBoundary from '@/components/RouteErrorBoundary';

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

const renderLazyPage = (PageComponent: ComponentType, boundaryId: string) => (
  <RouteErrorBoundary boundaryId={boundaryId}>
    <Suspense fallback={<LoadingScreen message="页面加载中..." />}>
      <PageComponent />
    </Suspense>
  </RouteErrorBoundary>
);

const routes = [
  {
    path: ROUTES.HOME,
    element: <Layout />,
    children: [
      { index: true, element: renderLazyPage(Home, 'home') },
      { path: 'firststep', element: renderLazyPage(FirstStep, 'first-step') },
      {
        path: 'charactersetting',
        element: renderLazyPage(CharacterSetting, 'character-setting'),
      },
      {
        path: 'characterselection',
        element: renderLazyPage(CharacterSelection, 'character-selection'),
      },
      { path: 'firstmeeting', element: renderLazyPage(FirstMeetingSelection, 'first-meeting') },
      { path: 'game', element: renderLazyPage(Game, 'story-game') },
      { path: 'training', element: renderLazyPage(Training, 'training-main') },
      {
        path: 'training/progress',
        element: renderLazyPage(TrainingProgress, 'training-progress'),
      },
      {
        path: 'training/report',
        element: renderLazyPage(TrainingReport, 'training-report'),
      },
      {
        path: 'training/diagnostics',
        element: renderLazyPage(TrainingDiagnostics, 'training-diagnostics'),
      },
      { path: '*', element: renderLazyPage(NotFound, 'not-found') },
    ],
  },
];

const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:';
const router = (isFileProtocol ? createHashRouter : createBrowserRouter)(routes);

function AppRouter() {
  return <RouterProvider router={router} />;
}

export default AppRouter;

