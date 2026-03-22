import { lazy, useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import Layout from '@/components/Layout';
import { ROUTES } from '@/config/routes';
import { createRuntimeRouter, renderLazyPage } from './routerUtils';

const Home = lazy(() => import('@/pages/Home'));
const FirstStep = lazy(() => import('@/pages/FirstStep'));
const CharacterSetting = lazy(() => import('@/pages/CharacterSetting'));
const CharacterSelection = lazy(() => import('@/pages/CharacterSelection'));
const FirstMeetingSelection = lazy(() => import('@/pages/FirstMeetingSelection'));
const Game = lazy(() => import('@/pages/Game'));
const NotFound = lazy(() => import('@/pages/NotFound'));

const routes = [
  {
    path: ROUTES.HOME,
    element: <Layout />,
    children: [
      { index: true, element: renderLazyPage(Home, 'story-home') },
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
      { path: '*', element: renderLazyPage(NotFound, 'story-not-found') },
    ],
  },
];

function StoryRouter() {
  const [router] = useState(() => createRuntimeRouter(routes));
  return <RouterProvider router={router} />;
}

export default StoryRouter;
