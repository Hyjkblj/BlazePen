import { useEffect, useMemo, useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import SceneTransition from '@/components/SceneTransition';
import StaticAssetImage from '@/components/StaticAssetImage';
import TrainingCinematicChoiceBand from '@/components/training/TrainingCinematicChoiceBand';
import { buildTrainingReportRoute, ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import { useTrainingMajorSceneTransition } from '@/hooks/useTrainingMajorSceneTransition';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import { getStaticAssetContractWarning } from '@/services/assetUrl';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import './Training.css';

/** 场景图 URL 就绪后延迟再展示独白/选项，给大图解码与绘制留出时间 */
const POST_SCENE_IMAGE_UI_DELAY_MS = 2000;
const AUTO_REVEAL_CHOICES_IDLE_MS = 20000;

const buildScenePlaceholderText = ({
  hasSession,
  bootstrapStatus,
  sceneImageStatus,
}: {
  hasSession: boolean;
  bootstrapStatus: string;
  sceneImageStatus: string;
}): string => {
  if (!hasSession) {
    if (bootstrapStatus === 'restoring') {
      return '会话恢复中...';
    }
    return '会话未就绪...';
  }
  if (sceneImageStatus === 'pending' || sceneImageStatus === 'running') {
    return '后端正在生成场景图...';
  }
  return '';
};

function Training() {
  const [searchParams] = useSearchParams();
  const explicitSessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const flow = useTrainingMvpFlow(explicitSessionId);
  const {
    bootstrapStatus,
    bootstrapErrorMessage,
    roundStatus,
    roundErrorMessage,
    noticeMessage,
    dismissNotice,
    retryRestore,
    restoreNextScenarioFailed,
    retryRestoreNextScenario,
    retrySceneImage,
    sessionView,
    hasResumeTarget,
    sceneImageStatus,
    sceneImageUrl,
    sceneImageErrorMessage,
    completionReportStatus,
    completionReport,
    completionReportErrorMessage,
    selectedOptionId,
    submitOption,
  } = flow;

  const hasInsightEntry = flow.insightSessionId !== null;
  const hasSession = Boolean(sessionView);
  const currentScenario = sessionView?.currentScenario ?? null;
  const {
    showMajorTransition,
    majorTransitionTitle,
    majorTransitionAct,
    dismissMajorTransition,
  } = useTrainingMajorSceneTransition(
    sessionView?.sessionId ?? null,
    currentScenario,
    Boolean(sessionView?.isCompleted)
  );
  const options = currentScenario?.options ?? [];
  const isSubmitting = roundStatus === 'submitting';
  const optionDisabled = !hasSession || isSubmitting || Boolean(sessionView?.isCompleted);
  const showCompletionNotice = Boolean(sessionView?.isCompleted);
  const showLoadingMask = isSubmitting || bootstrapStatus === 'restoring';
  const placeholderText = buildScenePlaceholderText({ hasSession, bootstrapStatus, sceneImageStatus });
  const hasSceneImageWarning = !sceneImageUrl && sceneImageStatus === 'failed';
  const [sceneAssetFailed, setSceneAssetFailed] = useState(false);
  const normalizedSceneImageUrl = useMemo(() => (sceneImageUrl ? String(sceneImageUrl).trim() : ''), [sceneImageUrl]);
  const isRelativeStaticUrl = normalizedSceneImageUrl.startsWith('/static/');
  const showStaticAssetWarning = Boolean(sceneAssetFailed) && Boolean(normalizedSceneImageUrl);
  const staticAssetContractWarning = useMemo(
    () => getStaticAssetContractWarning(normalizedSceneImageUrl),
    [normalizedSceneImageUrl]
  );
  const showChoiceBand = !showCompletionNotice && options.length > 0;
  const canRevealNarrationAndChoices =
    showChoiceBand && (sceneImageStatus === 'succeeded' || sceneImageStatus === 'failed');
  const [postImageUiReady, setPostImageUiReady] = useState(false);

  useEffect(() => {
    if (!canRevealNarrationAndChoices) {
      setPostImageUiReady(false);
      return;
    }
    setPostImageUiReady(false);
    const timer = window.setTimeout(() => {
      setPostImageUiReady(true);
    }, POST_SCENE_IMAGE_UI_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [canRevealNarrationAndChoices, currentScenario?.id, normalizedSceneImageUrl]);

  const showChoiceOverlay = canRevealNarrationAndChoices && postImageUiReady;
  const narrationText = useMemo(() => {
    if (!currentScenario) {
      return '';
    }
    const brief = String(currentScenario.brief ?? '').trim();
    const mission = String(currentScenario.mission ?? '').trim();
    if (brief && mission) {
      return `${brief}\n\n任务：${mission}`;
    }
    return brief || mission || '';
  }, [currentScenario]);

  const completionReportTeaser = useMemo(() => {
    if (!sessionView?.isCompleted || !completionReport?.summary) {
      return null;
    }
    const s = completionReport.summary;
    const initial = s.weightedScoreInitial;
    const final = s.weightedScoreFinal;
    const delta = s.weightedScoreDelta;
    if (![initial, final, delta].every((x) => typeof x === 'number' && Number.isFinite(x))) {
      return null;
    }
    const deltaLabel = `${delta >= 0 ? '+' : ''}${delta.toFixed(2)}`;
    return `综合加权分 ${initial.toFixed(2)} → ${final.toFixed(2)}（${deltaLabel}）`;
  }, [completionReport, sessionView?.isCompleted]);

  const [choiceStage, setChoiceStage] = useState<'narration' | 'choices'>(() =>
    narrationText ? 'narration' : 'choices'
  );

  useEffect(() => {
    if (!showChoiceOverlay) {
      return;
    }
    if (!narrationText) {
      setChoiceStage('choices');
      return;
    }

    setChoiceStage('narration');
    const timer = window.setTimeout(() => {
      setChoiceStage('choices');
    }, AUTO_REVEAL_CHOICES_IDLE_MS);
    return () => window.clearTimeout(timer);
  }, [currentScenario?.id, narrationText, showChoiceOverlay]);

  if (!sessionView && !hasInsightEntry) {
    return <Navigate to={hasResumeTarget ? ROUTES.TRAINING_LANDING : ROUTES.TRAINING_MAINHOME} replace />;
  }

  return (
    <div className="training-page training-page--simplified">
      {showMajorTransition && !showCompletionNotice ? (
        <SceneTransition
          sceneName={majorTransitionTitle}
          actNumber={majorTransitionAct}
          tone="training"
          onComplete={dismissMajorTransition}
        />
      ) : null}
      <section className="training-simplified" aria-live="polite">
        <div className="training-simplified__scene-frame">
          <StaticAssetImage
            imageUrl={sceneImageUrl}
            alt={currentScenario?.title ? `${currentScenario.title} 场景图` : '训练场景图'}
            imageClassName="training-simplified__scene-image"
            placeholderClassName="training-simplified__scene-placeholder"
            placeholder={placeholderText}
            onError={() => {
              setSceneAssetFailed(true);
              trackFrontendTelemetry({
                domain: 'training',
                event: 'training.scene_image.asset_error' as any,
                status: 'failed',
                metadata: {
                  url: sceneImageUrl,
                  isRelativeStaticUrl,
                  staticAssetOrigin: (import.meta.env.VITE_STATIC_ASSET_ORIGIN ?? '').trim() || null,
                },
              });
            }}
          />
          {showLoadingMask ? <div className="training-simplified__scene-mask">训练流程处理中...</div> : null}
          {showChoiceOverlay ? (
            <div className="training-simplified__choice-overlay">
              {choiceStage === 'narration' && narrationText ? (
                <button
                  type="button"
                  className="training-simplified__narration"
                  onClick={() => setChoiceStage('choices')}
                  disabled={optionDisabled}
                >
                  <span className="training-simplified__narration-label">当前节点</span>
                  <span className="training-simplified__narration-text">{narrationText}</span>
                  <span className="training-simplified__narration-hint">
                    <span>点击可立即进入选项</span>
                    <span className="training-simplified__narration-hint-corner">
                      20 秒无操作将自动展开选项
                    </span>
                  </span>
                </button>
              ) : null}
              {choiceStage === 'choices' ? (
                <TrainingCinematicChoiceBand
                  options={options}
                  selectedOptionId={selectedOptionId}
                  disabled={optionDisabled}
                  onSelectOption={(optionId) => {
                    void submitOption(optionId);
                  }}
                />
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="training-simplified__feedback-stack">
          {bootstrapErrorMessage ? (
            <div className="training-simplified__feedback training-simplified__feedback--error">
              <span>{bootstrapErrorMessage}</span>
              <button type="button" onClick={() => void retryRestore()}>
                重试恢复
              </button>
            </div>
          ) : null}
          {restoreNextScenarioFailed && !currentScenario ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>会话已恢复，但加载下一场景失败。你可以重试加载场景。</span>
              <button type="button" onClick={() => void retryRestoreNextScenario()}>
                重试加载场景
              </button>
            </div>
          ) : null}
          {roundErrorMessage ? (
            <div className="training-simplified__feedback training-simplified__feedback--error">
              <span>{roundErrorMessage}</span>
            </div>
          ) : null}
          {hasSceneImageWarning ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>{sceneImageErrorMessage ?? '场景图生成失败，不影响当前回合选择。'}</span>
              <button type="button" onClick={() => void retrySceneImage()}>
                {'\u91cd\u65b0\u751f\u6210\u573a\u666f\u56fe'}
              </button>
            </div>
          ) : null}
          {showStaticAssetWarning ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>
                场景图已生成，但静态资源不可达。请确认当前前端入口具备 `/static` 代理，或配置
                `VITE_STATIC_ASSET_ORIGIN` 指向训练后端。
              </span>
            </div>
          ) : null}
          {staticAssetContractWarning ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>{staticAssetContractWarning}</span>
            </div>
          ) : null}
          {noticeMessage ? (
            <div className="training-simplified__feedback training-simplified__feedback--notice">
              <span>{noticeMessage}</span>
              <button type="button" onClick={() => dismissNotice()}>
                关闭
              </button>
            </div>
          ) : null}
        </div>

        {showCompletionNotice ? (
          <div className="training-simplified__completion-panel">
            <p className="training-simplified__completion-title">训练已完成</p>
            <p className="training-simplified__completion-lede">
              能力雷达、状态曲线与回合履历已整理为报告，请点击下方进入可视化评估页。
            </p>
            {completionReportStatus === 'loading' ? (
              <p className="training-simplified__completion-muted">正在加载评估摘要…</p>
            ) : null}
            {completionReportErrorMessage ? (
              <p className="training-simplified__completion-muted">{completionReportErrorMessage}</p>
            ) : null}
            {completionReportTeaser ? (
              <p className="training-simplified__completion-teaser">{completionReportTeaser}</p>
            ) : null}
            <div className="training-simplified__completion-actions">
              {sessionView?.sessionId ? (
                <Link
                  className="training-simplified__report-link"
                  to={buildTrainingReportRoute(sessionView.sessionId)}
                >
                  查看可视化评估报告
                </Link>
              ) : null}
              <Link className="training-simplified__completion-sub-link" to={ROUTES.TRAINING_MAINHOME}>
                返回训练首页
              </Link>
            </div>
          </div>
        ) : (
          <div className="training-simplified__options">
            {options.length > 0 ? null : (
              <div className="training-simplified__empty-options">当前场景暂无可选项</div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default Training;
