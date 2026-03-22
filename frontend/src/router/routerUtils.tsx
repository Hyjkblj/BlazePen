import { Suspense, type ComponentType } from 'react';
import {
  createBrowserRouter,
  createHashRouter,
  type RouteObject,
} from 'react-router-dom';
import LoadingScreen from '@/components/loading';
import RouteErrorBoundary from '@/components/RouteErrorBoundary';

export const renderLazyPage = (PageComponent: ComponentType, boundaryId: string) => (
  <RouteErrorBoundary boundaryId={boundaryId}>
    <Suspense fallback={<LoadingScreen message="页面加载中..." />}>
      <PageComponent />
    </Suspense>
  </RouteErrorBoundary>
);

export const createRuntimeRouter = (routes: RouteObject[]) => {
  const isFileProtocol = typeof window !== 'undefined' && window.location.protocol === 'file:';
  return (isFileProtocol ? createHashRouter : createBrowserRouter)(routes);
};
