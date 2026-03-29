import { Navigate, useSearchParams } from 'react-router-dom';
import TrainingCinematicChoiceBand from '@/components/training/TrainingCinematicChoiceBand';
import { ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import './Training.css';

const buildScenePlaceholderText = ({
  hasSession,
  sceneImageStatus,
}: {
  hasSession: boolean;
  sceneImageStatus: string;
}): string => {
  if (!hasSession) {
    return '会话恢复中...';
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
    insightSessionId,
    sceneImageStatus,
    sceneImageUrl,
    sceneImageErrorMessage,
    selectedOptionId,
    submitOption,
  } = flow;

  const hasInsightEntry = insightSessionId !== null;
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
  const placeholderText = buildScenePlaceholderText({ hasSession, sceneImageStatus });
  const hasSceneImageWarning = !sceneImageUrl && sceneImageStatus === 'failed';

  return (
    <div className="training-page training-page--simplified">
      <section className="training-simplified" aria-live="polite">
        <div className="training-simplified__scene-frame">
          {sceneImageUrl ? (
            <img
              className="training-simplified__scene-image"
              src={sceneImageUrl}
              alt={currentScenario?.title ? `${currentScenario.title} 场景图` : '训练场景图'}
            />
          ) : (
            <div className="training-simplified__scene-placeholder">{placeholderText}</div>
          )}
          {showLoadingMask ? <div className="training-simplified__scene-mask">训练流程处理中...</div> : null}
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
            {options.length > 0 ? (
              <TrainingCinematicChoiceBand
                options={options}
                selectedOptionId={selectedOptionId}
                disabled={optionDisabled}
                onSelectOption={(optionId) => {
                  void submitOption(optionId);
                }}
              />
            ) : (
              <div className="training-simplified__empty-options">当前场景暂无可选项</div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default Training;
