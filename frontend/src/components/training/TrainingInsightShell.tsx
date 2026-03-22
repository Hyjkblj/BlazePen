import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  ROUTES,
  buildTrainingDiagnosticsRoute,
  buildTrainingProgressRoute,
  buildTrainingReportRoute,
} from '@/config/routes';
import type { TrainingSessionReadTargetSource } from '@/hooks/useTrainingSessionReadTarget';
import './TrainingInsightShell.css';

type TrainingInsightView = 'progress' | 'report' | 'diagnostics';

interface TrainingInsightEmptyState {
  title: string;
  description: string;
}

interface TrainingInsightShellProps {
  title: string;
  description: string;
  activeView: TrainingInsightView;
  sessionId: string | null;
  sessionSource?: TrainingSessionReadTargetSource | null;
  navigationSessionId?: string | null;
  sessionStatus?: string | null;
  loadingMessage?: string | null;
  errorMessage?: string | null;
  hasStaleData?: boolean;
  emptyState?: TrainingInsightEmptyState | null;
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

const TRAINING_SESSION_SOURCE_LABELS: Record<
  Exclude<TrainingSessionReadTargetSource, 'none'>,
  string
> = {
  explicit: '显式 sessionId',
  'active-session': '当前活动会话',
  'resume-target': '本地恢复入口',
};

export function TrainingInsightShell({
  title,
  description,
  activeView,
  sessionId,
  sessionSource = null,
  navigationSessionId = null,
  sessionStatus = null,
  loadingMessage = null,
  errorMessage = null,
  hasStaleData = false,
  emptyState = null,
  onRetry = null,
  children,
}: TrainingInsightShellProps) {
  const sessionSourceLabel =
    sessionSource && sessionSource !== 'none'
      ? TRAINING_SESSION_SOURCE_LABELS[sessionSource]
      : null;

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
          {sessionId && onRetry ? (
            <button
              className="training-insight-shell__ghost-button"
              type="button"
              onClick={onRetry}
            >
              刷新读取
            </button>
          ) : null}
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
            {sessionSourceLabel ? (
              <div>
                <dt>读取来源</dt>
                <dd>{sessionSourceLabel}</dd>
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

        {hasStaleData ? (
          <div className="training-insight-shell__stale-banner" role="status">
            当前显示的是最近一次成功读取的训练结果。可以稍后重新加载以获取最新状态。
          </div>
        ) : null}

        <div className="training-insight-shell__content">
          {emptyState ? (
            <section className="training-insight-section training-insight-section--state">
              <h2>{emptyState.title}</h2>
              <p className="training-insight-empty">{emptyState.description}</p>
            </section>
          ) : null}
          {children}
        </div>
      </section>
    </div>
  );
}

export default TrainingInsightShell;
