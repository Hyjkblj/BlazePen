import { Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import TrainingLanding from '@/components/training/TrainingLanding';
import { ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';

function TrainingLandingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const explicitSessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const flow = useTrainingMvpFlow(explicitSessionId);
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

  if (sessionView) {
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
      onStartTraining={async () => {
        const started = await startTraining();
        if (started) {
          navigate(ROUTES.TRAINING);
        }
      }}
      updateFormDraft={updateFormDraft}
    />
  );
}

export default TrainingLandingPage;
