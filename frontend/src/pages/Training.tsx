import { Alert, Button } from 'antd';
import { Navigate, useSearchParams } from 'react-router-dom';
import TrainingOutcomePanel from '@/components/training/TrainingOutcomePanel';
import TrainingRoundPanel from '@/components/training/TrainingRoundPanel';
import TrainingSessionSummaryPanel from '@/components/training/TrainingSessionSummaryPanel';
import TrainingShellHeader from '@/components/training/TrainingShellHeader';
import { ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import './Training.css';

const formatProgressPercent = (progressPercent: number): string =>
  `${Number(progressPercent.toFixed(1))}%`;

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
    clearWorkspace,
    sessionView,
    hasResumeTarget,
    insightSessionId,
    latestOutcome,
    selectedOptionId,
    selectOption,
    responseInput,
    setResponseInput,
    mediaTaskDraft,
    updateMediaTaskDraft,
    submissionPreview,
    mediaTasks,
    mediaTaskFeedStatus,
    mediaTaskFeedErrorMessage,
    isPollingMediaTasks,
    refreshMediaTasks,
    canSubmitRound,
    submitCurrentRound,
  } = flow;

  const hasInsightEntry = insightSessionId !== null;

  if (!sessionView && !hasInsightEntry) {
    return <Navigate to={hasResumeTarget ? ROUTES.TRAINING_LANDING : ROUTES.TRAINING_MAINHOME} replace />;
  }

  const loadingMessage =
    roundStatus === 'submitting'
      ? 'Submitting current round...'
      : bootstrapStatus === 'restoring'
        ? 'Restoring training session...'
        : null;

  if (!sessionView) {
    return (
      <div className="training-page">
        <section className="training-shell">
          <TrainingShellHeader
            hasInsightEntry={hasInsightEntry}
            insightSessionId={insightSessionId}
            onClearWorkspace={clearWorkspace}
          />

          {loadingMessage ? (
            <Alert className="training-shell__banner" type="info" showIcon message={loadingMessage} />
          ) : null}

          {bootstrapErrorMessage ? (
            <Alert
              className="training-shell__alert"
              type="error"
              showIcon
              message="Failed to restore training session"
              description={bootstrapErrorMessage}
              action={
                <Button size="small" onClick={() => void retryRestore()}>
                  Retry restore
                </Button>
              }
            />
          ) : null}

          {noticeMessage ? (
            <Alert
              className="training-shell__notice"
              type="success"
              showIcon
              message={noticeMessage}
              closable
              onClose={dismissNotice}
            />
          ) : null}

          <div className="training-shell__workspace">
            <div className="training-shell__panel training-shell__panel--primary">
              <p className="training-shell__empty">
                Syncing session state from backend. The round view will appear automatically after recovery.
              </p>
              <div className="training-shell__stack-actions">
                <Button
                  className="training-shell__primary-button"
                  type="primary"
                  loading={bootstrapStatus === 'restoring'}
                  onClick={() => void retryRestore()}
                >
                  Restore current session
                </Button>
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  const sessionTrainingModeLabel =
    sessionView.trainingMode === 'self-paced'
      ? 'Self-paced'
      : sessionView.trainingMode === 'adaptive'
        ? 'Adaptive'
        : 'Guided';

  const sessionProgressLabel = sessionView.progressAnchor
    ? formatProgressPercent(sessionView.progressAnchor.progressPercent)
    : null;

  return (
    <div className="training-page">
      <section className="training-shell">
        <TrainingShellHeader
          hasInsightEntry={hasInsightEntry}
          insightSessionId={insightSessionId}
          onClearWorkspace={clearWorkspace}
        />

        {loadingMessage ? (
          <Alert className="training-shell__banner" type="info" showIcon message={loadingMessage} />
        ) : null}

        {roundErrorMessage ? (
          <Alert
            className="training-shell__alert"
            type="error"
            showIcon
            message="Round submission failed"
            description={roundErrorMessage}
            action={
              <Button size="small" onClick={() => void retryRestore()}>
                Restore current session
              </Button>
            }
          />
        ) : null}

        {noticeMessage ? (
          <Alert
            className="training-shell__notice"
            type="success"
            showIcon
            message={noticeMessage}
            closable
            onClose={dismissNotice}
          />
        ) : null}

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
            mediaTaskDraft={mediaTaskDraft}
            updateMediaTaskDraft={updateMediaTaskDraft}
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
          <TrainingOutcomePanel
            latestOutcome={latestOutcome}
            mediaTasks={mediaTasks}
            mediaTaskFeedStatus={mediaTaskFeedStatus}
            mediaTaskFeedErrorMessage={mediaTaskFeedErrorMessage}
            isPollingMediaTasks={isPollingMediaTasks}
            refreshMediaTasks={refreshMediaTasks}
          />
        </div>
      </section>
    </div>
  );
}

export default Training;
