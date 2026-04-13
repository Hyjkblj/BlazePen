import { useCallback } from 'react';
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
  onStartTraining: (context: { codename: string }) => void | Promise<void>;
  onPrewarmAllSceneImages: (characterId: string) => void | Promise<void>;
  updateFormDraft: (field: keyof TrainingFormDraftValue, value: string) => void;
};

const TRAINING_CODENAME_MAP: Record<string, { male: string; female: string }> = {
  'underground-reporter': { male: '墨刃', female: '笔心' },
  'frontline-war-correspondent': { male: '锋录', female: '星笔' },
  'photo-intelligence': { male: '镜影', female: '影棱' },
  'newsboy-courier': { male: '风报', female: '铃童' },
  'concession-correspondent': { male: '澜喉', female: '潮声' },
};

const resolveCodenameByIdentityText = (identityText: string): { male: string; female: string } | null => {
  const text = String(identityText || '').trim();
  if (!text) {
    return null;
  }
  if (text.includes('地下') || text.includes('敌后')) return { male: '墨刃', female: '笔心' };
  if (text.includes('火线') || text.includes('战地')) return { male: '锋录', female: '星笔' };
  if (text.includes('摄影') || text.includes('镜头')) return { male: '镜影', female: '影棱' };
  if (text.includes('报童') || text.includes('街头')) return { male: '风报', female: '铃童' };
  if (text.includes('租界') || text.includes('涉外')) return { male: '澜喉', female: '潮声' };
  return null;
};

const resolveCodename = (portraitPresetId: string, playerGender: string, playerIdentity: string): string => {
  const mapping =
    TRAINING_CODENAME_MAP[String(portraitPresetId || '').trim()] ??
    resolveCodenameByIdentityText(playerIdentity);
  if (!mapping) {
    return '黄蜂';
  }
  const normalizedGender = String(playerGender || '').trim().toLowerCase();
  const isMale = normalizedGender === '男' || normalizedGender === 'male' || normalizedGender === 'm';
  return isMale ? mapping.male : mapping.female;
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
  onPrewarmAllSceneImages,
  updateFormDraft,
}: TrainingLandingProps) {
  const handleStartTraining = useCallback(async () => {
    const codename = resolveCodename(
      formDraft.portraitPresetId,
      formDraft.playerGender,
      formDraft.playerIdentity
    );
    await onStartTraining({ codename });
  }, [
    formDraft.playerGender,
    formDraft.playerIdentity,
    formDraft.portraitPresetId,
    onStartTraining,
  ]);

  const previewFlow = useTrainingCharacterPreviewFlow({
    formDraft,
    onStartTraining: handleStartTraining,
    onPrewarmAllSceneImages,
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
