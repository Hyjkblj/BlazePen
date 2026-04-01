import { lazy, useState } from 'react';
import { Navigate, RouterProvider } from 'react-router-dom';
import Layout from '@/components/Layout';
import { ROUTES } from '@/config/routes';
import { createRuntimeRouter, renderLazyPage } from './routerUtils';

const Training = lazy(() => import('@/pages/Training'));
const TrainingMainHomePage = lazy(() => import('@/pages/TrainingMainHomePage'));
const TrainingLandingPage = lazy(() => import('@/pages/TrainingLandingPage'));
const TrainingCinematicDemoPage = lazy(() => import('@/pages/TrainingCinematicDemoPage'));
const TrainingProgress = lazy(() => import('@/pages/TrainingProgress'));
const TrainingReport = lazy(() => import('@/pages/TrainingReport'));
const TrainingDiagnostics = lazy(() => import('@/pages/TrainingDiagnostics'));
const NotFound = lazy(() => import('@/pages/NotFound'));

const routes = [
  {
    path: ROUTES.HOME,
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to={ROUTES.TRAINING_MAINHOME} replace /> },
      { path: 'training', element: renderLazyPage(Training, 'training-main') },
      {
        path: 'training/mainhome',
        element: renderLazyPage(TrainingMainHomePage, 'training-mainhome'),
      },
      {
        path: 'training/landing',
        element: renderLazyPage(TrainingLandingPage, 'training-landing'),
      },
      {
        path: 'training/cinematic-demo',
        element: renderLazyPage(TrainingCinematicDemoPage, 'training-cinematic-demo'),
      },
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
      { path: '*', element: renderLazyPage(NotFound, 'training-not-found') },
    ],
  },
];

function TrainingRouter() {
  const [router] = useState(() => createRuntimeRouter(routes));
  return <RouterProvider router={router} />;
}

export default TrainingRouter;
