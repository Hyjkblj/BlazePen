import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  ROUTES,
  buildTrainingDiagnosticsRoute,
  buildTrainingProgressRoute,
  buildTrainingReportRoute,
} from '@/config/routes';
import './TrainingInsightShell.css';

type TrainingInsightView = 'progress' | 'report' | 'diagnostics';

interface TrainingInsightShellProps {
  title: string;
  description: string;
  activeView: TrainingInsightView;
  sessionId: string | null;
  navigationSessionId?: string | null;
  sessionStatus?: string | null;
  loadingMessage?: string | null;
  errorMessage?: string | null;
  onRetry?: (() => void) | null;
  children: ReactNode;
}

const buildNavItems = (sessionId: string | null) => [
  {
    key: 'progress' as const,
    label: '训练进度',
    to: buildTrainingProgressRoute(sessionId),
  },
  {
    key: 'report' as const,
    label: '训练报告',
    to: buildTrainingReportRoute(sessionId),
  },
  {
    key: 'diagnostics' as const,
    label: '训练诊断',
    to: buildTrainingDiagnosticsRoute(sessionId),
  },
];

export function TrainingInsightShell({
  title,
  description,
  activeView,
  sessionId,
  navigationSessionId = null,
  sessionStatus = null,
  loadingMessage = null,
  errorMessage = null,
  onRetry = null,
  children,
}: TrainingInsightShellProps) {
  return (
    <div className="training-insight-page">
      <section className="training-insight-shell">
        <div className="training-insight-shell__eyebrow">PR-08</div>
        <h1 className="training-insight-shell__title">{title}</h1>
        <p className="training-insight-shell__description">{description}</p>

        <div className="training-insight-shell__actions">
          <Link className="training-insight-shell__link" to={ROUTES.HOME}>
            返回首页
          </Link>
          <Link className="training-insight-shell__secondary-link" to={ROUTES.TRAINING}>
            返回训练主页
          </Link>
        </div>

        <nav className="training-insight-shell__nav" aria-label="训练结果导航">
          {buildNavItems(navigationSessionId).map((item) => (
            <Link
              key={item.key}
              className={`training-insight-shell__nav-link${
                item.key === activeView ? ' training-insight-shell__nav-link--active' : ''
              }`}
              to={item.to}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {(sessionId || sessionStatus) && (
          <dl className="training-insight-shell__meta">
            {sessionId ? (
              <div>
                <dt>sessionId</dt>
                <dd>{sessionId}</dd>
              </div>
            ) : null}
            {sessionStatus ? (
              <div>
                <dt>状态</dt>
                <dd>{sessionStatus}</dd>
              </div>
            ) : null}
          </dl>
        )}

        {loadingMessage ? (
          <div className="training-insight-shell__banner" role="status">
            {loadingMessage}
          </div>
        ) : null}

        {errorMessage ? (
          <div className="training-insight-shell__alert" role="alert">
            <span>{errorMessage}</span>
            {onRetry ? (
              <button type="button" onClick={onRetry}>
                重新加载
              </button>
            ) : null}
          </div>
        ) : null}

        <div className="training-insight-shell__content">{children}</div>
      </section>
    </div>
  );
}

export default TrainingInsightShell;
