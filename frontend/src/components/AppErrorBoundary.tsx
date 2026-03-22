import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ROUTES } from '@/config/routes';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import AppErrorFallback from './AppErrorFallback';

interface AppErrorBoundaryProps {
  children: ReactNode;
  onReset?: () => void;
  onNavigateHome?: () => void;
  resetKeys?: unknown[];
  telemetryMetadata?: Record<string, unknown>;
}

interface AppErrorBoundaryState {
  error: Error | null;
}

const resetKeysChanged = (previous: unknown[] = [], next: unknown[] = []) => {
  if (previous.length !== next.length) {
    return true;
  }

  return previous.some((value, index) => !Object.is(value, next[index]));
};

const resolveFallbackMessage = (error: Error | null) => {
  if (!error?.message) {
    return 'Unknown render error.';
  }

  const trimmedMessage = error.message.trim();
  return trimmedMessage === '' ? 'Unknown render error.' : trimmedMessage;
};

const navigateToHomeRoute = () => {
  if (typeof window === 'undefined') {
    return;
  }

  if (window.location.protocol === 'file:') {
    window.location.hash = '#/';
    return;
  }

  window.location.assign(ROUTES.HOME);
};

class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return {
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    trackFrontendTelemetry({
      domain: 'app',
      event: 'app.render',
      status: 'failed',
      metadata: {
        ...this.props.telemetryMetadata,
        componentStack: errorInfo.componentStack,
      },
      cause: error,
    });
  }

  componentDidUpdate(previousProps: AppErrorBoundaryProps) {
    if (
      this.state.error &&
      this.props.resetKeys &&
      resetKeysChanged(previousProps.resetKeys, this.props.resetKeys)
    ) {
      this.handleReset();
    }
  }

  handleReset = () => {
    this.props.onReset?.();
    this.setState({
      error: null,
    });
  };

  handleNavigateHome = () => {
    this.handleReset();
    if (this.props.onNavigateHome) {
      this.props.onNavigateHome();
      return;
    }

    navigateToHomeRoute();
  };

  render() {
    if (this.state.error) {
      return (
        <AppErrorFallback
          message={resolveFallbackMessage(this.state.error)}
          onReset={this.handleReset}
          onNavigateHome={this.handleNavigateHome}
        />
      );
    }

    return this.props.children;
  }
}

export default AppErrorBoundary;
