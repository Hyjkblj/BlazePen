import './AppErrorFallback.css';

export interface AppErrorFallbackProps {
  message: string;
  onReset: () => void;
  onNavigateHome: () => void;
}

function AppErrorFallback({ message, onReset, onNavigateHome }: AppErrorFallbackProps) {
  return (
    <main className="app-error-fallback" role="alert" aria-live="assertive">
      <div className="app-error-fallback__panel">
        <div className="app-error-fallback__eyebrow">Runtime Guard</div>
        <h1 className="app-error-fallback__title">The app hit an unexpected error.</h1>
        <p className="app-error-fallback__description">
          The current page could not finish rendering. You can retry in place or return to the
          app home route.
        </p>
        <pre className="app-error-fallback__message">{message}</pre>
        <div className="app-error-fallback__actions">
          <button type="button" className="app-error-fallback__button" onClick={onReset}>
            Try again
          </button>
          <button
            type="button"
            className="app-error-fallback__button app-error-fallback__button--secondary"
            onClick={onNavigateHome}
          >
            Return home
          </button>
        </div>
      </div>
    </main>
  );
}

export default AppErrorFallback;

