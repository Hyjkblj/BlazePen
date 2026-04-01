import { useMemo, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import StaticAssetImage from '@/components/StaticAssetImage';
import TrainingCinematicChoiceBand from '@/components/training/TrainingCinematicChoiceBand';
import { ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import './Training.css';

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
    retrySceneImage,
    sessionView,
    hasResumeTarget,
    sceneImageStatus,
    sceneImageUrl,
    sceneImageErrorMessage,
    selectedOptionId,
    submitOption,
  } = flow;

  const hasInsightEntry = flow.insightSessionId !== null;
  if (!sessionView && !hasInsightEntry) {
    return <Navigate to={hasResumeTarget ? ROUTES.TRAINING_LANDING : ROUTES.TRAINING_MAINHOME} replace />;
  }

  const hasSession = Boolean(sessionView);
  const currentScenario = sessionView?.currentScenario ?? null;
  const options = currentScenario?.options ?? [];
  const isSubmitting = roundStatus === 'submitting';
  const optionDisabled = !hasSession || isSubmitting || Boolean(sessionView?.isCompleted);
  const showCompletionNotice = Boolean(sessionView?.isCompleted);
  const showLoadingMask = isSubmitting || bootstrapStatus === 'restoring';
  const placeholderText = buildScenePlaceholderText({ hasSession, bootstrapStatus, sceneImageStatus });
  const hasSceneImageWarning = !sceneImageUrl && sceneImageStatus === 'failed';
  const [sceneAssetFailed, setSceneAssetFailed] = useState(false);
  const staticAssetOrigin = (import.meta.env.VITE_STATIC_ASSET_ORIGIN ?? '').trim();
  const normalizedSceneImageUrl = useMemo(() => (sceneImageUrl ? String(sceneImageUrl).trim() : ''), [sceneImageUrl]);
  const isRelativeStaticUrl = normalizedSceneImageUrl.startsWith('/static/');
  const showStaticAssetWarning = Boolean(sceneAssetFailed) && Boolean(normalizedSceneImageUrl);
  const showStaticAssetContractWarning = Boolean(isRelativeStaticUrl) && !staticAssetOrigin;
  const showChoiceBand = !showCompletionNotice && options.length > 0;

  return (
    <div className="training-page training-page--simplified">
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
                  staticAssetOrigin: staticAssetOrigin || null,
                },
              });
            }}
          />
          {showLoadingMask ? <div className="training-simplified__scene-mask">训练流程处理中...</div> : null}
          {showChoiceBand ? (
            <div className="training-simplified__choice-overlay">
              <TrainingCinematicChoiceBand
                options={options}
                selectedOptionId={selectedOptionId}
                disabled={optionDisabled}
                onSelectOption={(optionId) => {
                  void submitOption(optionId);
                }}
              />
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
          {showStaticAssetContractWarning ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>
                当前场景图返回的是 `/static/...` 路径，但未配置 `VITE_STATIC_ASSET_ORIGIN`。若当前入口没有 `/static`
                代理到训练后端，将出现“后端已生成但前端取不到”。建议配置 `VITE_STATIC_ASSET_ORIGIN`（例如
                `http://localhost:8010`）或为该入口补 `/static` 代理。
              </span>
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
          <div className="training-simplified__completion">训练已完成，评估结果将统一输出。</div>
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
