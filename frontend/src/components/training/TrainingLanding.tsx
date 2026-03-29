import { Alert, Button } from 'antd';
import TrainingIdentitySetup from '@/components/training/TrainingIdentitySetup';
import TrainingPortraitPreview from '@/components/training/TrainingPortraitPreview';
import { useTrainingCharacterPreviewFlow } from '@/hooks/useTrainingCharacterPreviewFlow';
import './TrainingLanding.css';

type TrainingFormDraftValue = {
  portraitPresetId: string;
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
};

type TrainingLandingProps = {
  bootstrapErrorMessage: string | null;
  bootstrapStatus: string;
  canStartTraining: boolean;
  formDraft: TrainingFormDraftValue;
  hasResumeTarget: boolean;
  resumeSessionId: string | null;
  onBackToEntryRoute: () => void;
  onManualRestore: () => void;
  onRetryRestore: () => void;
  onStartTraining: () => void | Promise<void>;
  updateFormDraft: (field: keyof TrainingFormDraftValue, value: string) => void;
};

function TrainingLanding({
  bootstrapErrorMessage,
  bootstrapStatus,
  canStartTraining,
  formDraft,
  hasResumeTarget,
  onBackToEntryRoute,
  onManualRestore,
  onRetryRestore,
  onStartTraining,
  updateFormDraft,
}: TrainingLandingProps) {
  const previewFlow = useTrainingCharacterPreviewFlow({
    formDraft,
    onStartTraining,
    updateFormDraft,
  });

  const isStarting =
    bootstrapStatus === 'starting' ||
    bootstrapStatus === 'restoring' ||
    previewFlow.isPersistingPortraitSelection;

  return (
    <div className="training-landing">
      {hasResumeTarget ? (
        <div className="training-landing__restore-card">
          <div className="training-landing__restore-content">
            <h3>恢复上次训练</h3>
            <p>检测到本地缓存会话，可手动恢复到最近一次训练进度。</p>
          </div>
          <Button
            className="training-landing__restore"
            type="primary"
            loading={bootstrapStatus === 'restoring'}
            onClick={onManualRestore}
          >
            恢复上次训练
          </Button>
        </div>
      ) : null}

      <div className="training-landing__content">
        <div className="training-landing__setup">
          <TrainingIdentitySetup
            formDraft={formDraft}
            hasGeneratedPortrait={previewFlow.previewStatus === 'ready'}
            identityPresetError={previewFlow.identityPresetError}
            identityPresetOptions={previewFlow.identityPresetOptions}
            identityPresetStatus={previewFlow.identityPresetStatus}
            isGeneratingPortrait={previewFlow.previewStatus === 'loading'}
            onGeneratePortrait={() => {
              void previewFlow.handleGeneratePreview();
            }}
            updateFormDraft={updateFormDraft}
          />
        </div>

        <TrainingPortraitPreview
          canStartTraining={canStartTraining}
          isStartingTraining={isStarting}
          onBack={onBackToEntryRoute}
          onConfirm={previewFlow.handleConfirmTraining}
          onSelectPreview={(index) => {
            previewFlow.setSelectedPreviewIndex(index);
          }}
          previewError={previewFlow.previewError}
          previewImageUrls={previewFlow.previewImageUrls}
          previewStatus={previewFlow.previewStatus}
          selectedPreviewIndex={previewFlow.selectedPreviewIndex}
        />
      </div>

      {bootstrapErrorMessage ? (
        <Alert
          className="training-landing__alert"
          type="error"
          showIcon
          title="训练初始化失败"
          description={bootstrapErrorMessage}
          action={
            <Button size="small" onClick={onRetryRestore}>
              重试
            </Button>
          }
        />
      ) : null}
    </div>
  );
}

export default TrainingLanding;
