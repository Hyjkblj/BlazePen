import { useRef } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import TrainingLanding from '@/components/training/TrainingLanding';
import { ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import { useTrainingLobbyBgm } from '@/hooks/useTrainingLobbyBgm';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';

function TrainingLandingPage() {
  useTrainingLobbyBgm();
  const navigate = useNavigate();
  const startTrainingFromLandingRef = useRef(false);
  const [searchParams] = useSearchParams();
  const explicitSessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const flow = useTrainingMvpFlow(explicitSessionId, { suppressAutoRestoreSessionView: true });
  const {
    bootstrapStatus,
    bootstrapErrorMessage,
    hasResumeTarget,
    resumeTarget,
    retryRestore,
    startTraining,
    sessionView,
    formDraft,
    updateFormDraft,
    canStartTraining,
  } = flow;

  if (sessionView && !startTrainingFromLandingRef.current) {
    return <Navigate to={ROUTES.TRAINING} replace />;
  }

  return (
    <TrainingLanding
      bootstrapErrorMessage={bootstrapErrorMessage}
      bootstrapStatus={bootstrapStatus}
      canStartTraining={canStartTraining}
      formDraft={formDraft}
      hasResumeTarget={hasResumeTarget}
      resumeSessionId={resumeTarget?.sessionId ?? null}
      onBackToEntryRoute={() => {
        navigate(ROUTES.TRAINING_MAINHOME);
      }}
      onManualRestore={() => {
        void retryRestore();
      }}
      onRetryRestore={() => {
        void retryRestore();
      }}
      onStartTraining={async ({ codename }) => {
        startTrainingFromLandingRef.current = true;
        try {
          const started = await startTraining();
          if (!started) {
            startTrainingFromLandingRef.current = false;
            return;
          }
        } catch (error) {
          startTrainingFromLandingRef.current = false;
          throw error;
        }
        navigate(ROUTES.TRAINING_CODENAME_REVEAL, {
          replace: true,
          state: { codename },
        });
      }}
      onPrewarmAllSceneImages={(characterId) => {
        void flow.prewarmAllSceneImages(characterId);
      }}
      updateFormDraft={updateFormDraft}
    />
  );
}

export default TrainingLandingPage;
