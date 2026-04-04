import { type ReactNode, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ROUTES,
  buildTrainingDiagnosticsRoute,
  buildTrainingProgressRoute,
  buildTrainingReportRoute,
} from '@/config/routes';
import {
  getEndingTypeLabel,
  pickDisplayableEndingPayload,
  TrainingInsightEndingBadge,
} from '@/components/training/TrainingInsightEndingBadge';
import './TrainingInsightShell.css';

type TrainingInsightView = 'progress' | 'report' | 'diagnostics';

interface TrainingInsightEmptyState {
  title: string;
  description: string;
}

interface TrainingInsightShellProps {
  title: string;
  /** 当 title 为结局分类等非固定文案时，用于无障碍命名（如「学习总结」） */
  titleAriaLabel?: string | null;
  description: string;
  activeView: TrainingInsightView;
  sessionId: string | null;
  /** 已完成会话时由读模型附带，用于标题栏右侧展示结局钤印 */
  sessionEnding?: Record<string, unknown> | null;
  /** 开局填写的 playerProfile.identity（用户设定的身份，如职业/角色） */
  sessionIdentity?: string | null;
  /** 开局填写的 playerProfile.name（用户设定姓名） */
  sessionDisplayName?: string | null;
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
    label: '学习进度',
    to: buildTrainingProgressRoute(sessionId),
  },
  {
    key: 'report' as const,
    label: '学习总结',
    to: buildTrainingReportRoute(sessionId),
  },
  {
    key: 'diagnostics' as const,
    label: '学情诊断',
    to: buildTrainingDiagnosticsRoute(sessionId),
  },
];

const STORY_BY_VIEW: Record<
  TrainingInsightView,
  { chapter: string; tagline: string; flavors: string[] }
> = {
  progress: {
    chapter: '第一程 · 学习过程',
    tagline: '每一次选择都会留下痕迹，这里帮你看见自己是怎么走过来的。',
    flavors: [
      '卡住的时候，试着把问题拆成小步。',
      '信息越多，越要先分清「已知」和「待核实」。',
      '压力之下，守住底线比抢速度更重要。',
    ],
  },
  report: {
    chapter: '第二程 · 学习总结',
    tagline: '把零散表现收成一张「成绩单」，是为了下一步练得更准。',
    flavors: [
      '分数是参考，真正重要的是你弄懂了哪一条原则。',
      '进步不必一次很大，方向对就很值得肯定。',
      '短板不是标签，而是你下一周最值得投入的时间。',
    ],
  },
  diagnostics: {
    chapter: '第三程 · 学情诊断',
    tagline: '系统帮你把容易忽略的细节标出来，方便对照课堂要求自查。',
    flavors: [
      '提示与告警是在帮你预习「真实工作里会踩的坑」。',
      '看到风险别紧张，先想想如果是你会怎么改。',
      '复盘的目的不是追责，而是让下一次决策更稳。',
    ],
  },
};

const JOURNEY_STEP: Record<TrainingInsightView, number> = {
  progress: 0,
  report: 1,
  diagnostics: 2,
};

export function TrainingInsightShell({
  title,
  titleAriaLabel = null,
  description,
  activeView,
  sessionId,
  sessionEnding = null,
  sessionIdentity = null,
  sessionDisplayName = null,
  navigationSessionId = null,
  sessionStatus = null,
  loadingMessage = null,
  errorMessage = null,
  hasStaleData = false,
  emptyState = null,
  onRetry = null,
  children,
}: TrainingInsightShellProps) {
  const displayNameLine =
    sessionDisplayName && sessionDisplayName.trim() ? sessionDisplayName.trim() : '未填写';
  const identityLine =
    sessionIdentity && sessionIdentity.trim() ? sessionIdentity.trim() : '未填写';

  const isCompleted = (sessionStatus ?? '').toLowerCase() === 'completed';
  const story = STORY_BY_VIEW[activeView];
  const journeyStep = JOURNEY_STEP[activeView];
  const [flavorIndex, setFlavorIndex] = useState(0);

  const flavorLine = useMemo(
    () => story.flavors[flavorIndex % story.flavors.length] ?? '',
    [flavorIndex, story.flavors]
  );

  const epilogue = useMemo(() => {
    if (!isCompleted) {
      return null;
    }
    if (activeView === 'report') {
      return '本轮实训已告一段落。建议把下面的建议抄进学习笔记，下次课前对照改进。';
    }
    if (activeView === 'diagnostics') {
      return '细项诊断已整理好。若要对照总成绩与能力曲线，可打开「学习总结」。';
    }
    return '本段学习已存档。想查看总成绩与能力变化，请打开「学习总结」。';
  }, [activeView, isCompleted]);

  const reportHref = buildTrainingReportRoute(navigationSessionId ?? sessionId);

  const endingTypeForBadge = getEndingTypeLabel(sessionEnding);
  const titleMatchesEndingType =
    activeView === 'report' &&
    Boolean(endingTypeForBadge) &&
    title.trim() === endingTypeForBadge;

  return (
    <div
      className={`training-insight-page${isCompleted ? ' training-insight-page--completed' : ''}`}
      data-active-view={activeView}
    >
      <section className="training-insight-shell">
        <div className="training-insight-shell__title-row training-insight-shell__title-row--reveal">
          <h1
            className="training-insight-shell__title"
            aria-label={titleAriaLabel && titleAriaLabel.trim() ? titleAriaLabel.trim() : undefined}
          >
            {title}
          </h1>
          {isCompleted ? (
            pickDisplayableEndingPayload(sessionEnding) ? (
              <TrainingInsightEndingBadge
                ending={sessionEnding}
                variant="header"
                hideTypeLine={titleMatchesEndingType}
              />
            ) : activeView === 'report' ? (
              <div
                className="training-ending-badge training-ending-badge--header training-ending-badge--fallback"
                role="status"
              >
                <span className="training-ending-badge__eyebrow">训练结局</span>
                <span className="training-ending-badge__type">暂未读到终局分类</span>
              </div>
            ) : (
              <div
                className="training-ending-badge training-ending-badge--header training-ending-badge--fallback"
                role="status"
              >
                <span className="training-ending-badge__eyebrow">训练结局</span>
                <Link className="training-ending-badge__link" to={reportHref}>
                  打开学习总结查看终局 →
                </Link>
              </div>
            )
          ) : null}
        </div>

        <div className="training-insight-shell__eyebrow">PR-08</div>

        <button
          type="button"
          className="training-insight-story"
          onClick={() => setFlavorIndex((i) => i + 1)}
          aria-label="换一句学习提示"
        >
          <span className="training-insight-story__chapter">{story.chapter}</span>
          <span className="training-insight-story__tagline">{story.tagline}</span>
          {flavorLine ? <span className="training-insight-story__flavor">「{flavorLine}」</span> : null}
          <span className="training-insight-story__hint">点击这里，换一句提示</span>
        </button>

        {isCompleted ? (
          <p className="training-insight-epilogue" role="status">
            {epilogue}
            {activeView !== 'report' && (navigationSessionId || sessionId) ? (
              <>
                {' '}
                <Link className="training-insight-epilogue__link" to={reportHref}>
                  查看学习总结 →
                </Link>
              </>
            ) : null}
          </p>
        ) : null}

        <details className="training-insight-shell__tech-notes">
          <summary className="training-insight-shell__tech-notes-summary">本页数据说明（可选阅读，点击展开）</summary>
          <p className="training-insight-shell__description">{description}</p>
          {sessionId ? (
            <p className="training-insight-shell__description training-insight-shell__description--mono">
              会话标识（sessionId）：{sessionId}
            </p>
          ) : null}
        </details>

        <div className="training-insight-journey" data-step={String(journeyStep)} aria-hidden="true">
          <div className="training-insight-journey__track">
            <div className="training-insight-journey__fill" />
          </div>
          <ol className="training-insight-journey__steps">
            <li data-done={journeyStep >= 0 ? 'true' : 'false'}>过程</li>
            <li data-done={journeyStep >= 1 ? 'true' : 'false'}>总结</li>
            <li data-done={journeyStep >= 2 ? 'true' : 'false'}>诊断</li>
          </ol>
        </div>

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

        <nav className="training-insight-shell__nav" aria-label="学习成果导航">
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
          <dl className="training-insight-shell__meta training-insight-shell__meta--reveal">
            <div>
              <dt>实训角色</dt>
              <dd>{identityLine}</dd>
            </div>
            <div>
              <dt>你的姓名</dt>
              <dd>{displayNameLine}</dd>
            </div>
            {sessionStatus ? (
              <div>
                <dt>学习状态</dt>
                <dd>
                  {sessionStatus}
                  {isCompleted ? (
                    <span className="training-insight-shell__seal" title="本轮实训已全部完成">
                      已完成
                    </span>
                  ) : null}
                </dd>
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

        <div className="training-insight-shell__content training-insight-shell__content--reveal">
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
