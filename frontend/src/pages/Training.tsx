import TrainingBootstrapPanels from '@/components/training/TrainingBootstrapPanels';
import TrainingOutcomePanel from '@/components/training/TrainingOutcomePanel';
import TrainingRoundPanel from '@/components/training/TrainingRoundPanel';
import TrainingSessionSummaryPanel from '@/components/training/TrainingSessionSummaryPanel';
import TrainingShellHeader from '@/components/training/TrainingShellHeader';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import './Training.css';

const formatProgressPercent = (progressPercent: number): string =>
  `${Number(progressPercent.toFixed(1))}%`;

function Training() {
  const flow = useTrainingMvpFlow();
  const {
    bootstrapStatus,
    bootstrapErrorMessage,
    roundStatus,
    roundErrorMessage,
    noticeMessage,
    dismissNotice,
    hasResumeTarget,
    resumeTarget,
    trainingMode,
    setTrainingMode,
    formDraft,
    updateFormDraft,
    startTraining,
    retryRestore,
    clearWorkspace,
    sessionView,
    insightSessionId,
    latestOutcome,
    selectedOptionId,
    selectOption,
    responseInput,
    setResponseInput,
    submissionPreview,
    canStartTraining,
    canSubmitRound,
    submitCurrentRound,
  } = flow;

  const sessionTrainingModeLabel =
    sessionView?.trainingMode === 'self-paced'
      ? '自主训练'
      : sessionView?.trainingMode === 'adaptive'
        ? '自适应训练'
        : sessionView?.trainingMode === 'guided'
          ? '引导训练'
          : null;

  const loadingMessage =
    bootstrapStatus === 'starting'
      ? '正在初始化训练会话...'
      : bootstrapStatus === 'restoring'
        ? '正在恢复训练会话...'
        : roundStatus === 'submitting'
          ? '正在提交本轮训练...'
          : null;
  const sessionProgressLabel = sessionView?.progressAnchor
    ? formatProgressPercent(sessionView.progressAnchor.progressPercent)
    : null;
  const hasInsightEntry = insightSessionId !== null;

  return (
    <div className="training-page">
      <section className="training-shell">
        <TrainingShellHeader
          hasInsightEntry={hasInsightEntry}
          insightSessionId={insightSessionId}
          onClearWorkspace={clearWorkspace}
        />

        {loadingMessage ? <div className="training-shell__banner">{loadingMessage}</div> : null}
        {bootstrapErrorMessage ? (
          <div className="training-shell__alert" role="alert">
            <span>{bootstrapErrorMessage}</span>
            <button type="button" onClick={() => void retryRestore()}>
              重试恢复
            </button>
          </div>
        ) : null}
        {roundErrorMessage ? (
          <div className="training-shell__alert" role="alert">
            <span>{roundErrorMessage}</span>
            <button type="button" onClick={() => void retryRestore()}>
              恢复当前训练
            </button>
          </div>
        ) : null}
        {noticeMessage ? (
          <div className="training-shell__notice" role="status">
            <span>{noticeMessage}</span>
            <button type="button" onClick={dismissNotice}>
              关闭
            </button>
          </div>
        ) : null}

        {!sessionView ? (
          <TrainingBootstrapPanels
            trainingMode={trainingMode}
            setTrainingMode={setTrainingMode}
            formDraft={formDraft}
            updateFormDraft={updateFormDraft}
            canStartTraining={canStartTraining}
            startTraining={() => {
              void startTraining();
            }}
            hasResumeTarget={hasResumeTarget}
            resumeSessionId={resumeTarget?.sessionId ?? null}
            resumeTrainingMode={resumeTarget?.trainingMode ?? null}
            resumeStatus={resumeTarget?.status ?? null}
            retryRestore={() => {
              void retryRestore();
            }}
          />
        ) : (
          <div className="training-shell__workspace">
            <TrainingSessionSummaryPanel
              sessionId={sessionView.sessionId}
              trainingModeLabel={sessionTrainingModeLabel}
              status={sessionView.status}
              roundNo={sessionView.roundNo}
              totalRounds={sessionView.totalRounds}
              progressLabel={sessionProgressLabel}
              characterId={sessionView.characterId}
              currentSceneId={sessionView.runtimeState.currentSceneId}
              runtimeState={sessionView.runtimeState}
            />
            <TrainingRoundPanel
              isCompleted={sessionView.isCompleted}
              currentScenario={sessionView.currentScenario}
              selectedOptionId={selectedOptionId}
              selectOption={selectOption}
              responseInput={responseInput}
              setResponseInput={setResponseInput}
              submissionPreview={submissionPreview}
              canSubmitRound={canSubmitRound}
              submitCurrentRound={() => {
                void submitCurrentRound();
              }}
              retryRestore={() => {
                void retryRestore();
              }}
              clearWorkspace={clearWorkspace}
              completedEnding={latestOutcome?.ending ?? null}
            />
            <TrainingOutcomePanel latestOutcome={latestOutcome} />
          </div>
        )}
      </section>
    </div>
  );
}

export default Training;
