import type { ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import AppErrorBoundary from './AppErrorBoundary';

export interface RouteErrorBoundaryProps {
  children: ReactNode;
  boundaryId: string;
}

function RouteErrorBoundary({ children, boundaryId }: RouteErrorBoundaryProps) {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <AppErrorBoundary
      resetKeys={[location.pathname, location.search]}
      telemetryMetadata={{
        boundaryId,
        pathname: location.pathname,
        search: location.search,
      }}
      onNavigateHome={() => navigate(ROUTES.HOME)}
    >
      {children}
    </AppErrorBoundary>
  );
}

export default RouteErrorBoundary;

