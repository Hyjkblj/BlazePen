import { Alert, Button, Card, Skeleton } from 'antd';

export type TrainingPortraitPreviewStatus = 'idle' | 'loading' | 'ready' | 'error';

type TrainingPortraitPreviewProps = {
  canStartTraining: boolean;
  isStartingTraining: boolean;
  onBack: () => void;
  onConfirm: () => void | Promise<void>;
  onSelectPreview: (index: number) => void;
  previewError: string | null;
  previewImageUrls: string[];
  selectedPreviewIndex: number | null;
  previewStatus: TrainingPortraitPreviewStatus;
};

function TrainingPortraitPreview({
  canStartTraining,
  isStartingTraining,
  onBack,
  onConfirm,
  onSelectPreview,
  previewError,
  previewImageUrls,
  selectedPreviewIndex,
  previewStatus,
}: TrainingPortraitPreviewProps) {
  return (
    <div className="training-landing__preview">
      <Card className="training-landing__preview-card">
        <div className="training-landing__preview-grid">
          {[0, 1].map((slotIndex) => {
            const imageUrl = previewImageUrls[slotIndex] ?? null;
            const slotLabel = `渲染位 ${slotIndex + 1}`;
            const isSelected = selectedPreviewIndex === slotIndex && Boolean(imageUrl);

            return (
              <button
                aria-label={imageUrl ? `选择渲染图 ${slotIndex + 1}` : slotLabel}
                aria-pressed={isSelected}
                className={`training-landing__preview-slot${
                  isSelected ? ' training-landing__preview-slot--selected' : ''
                }`}
                data-slot-index={slotLabel}
                disabled={!imageUrl || previewStatus !== 'ready'}
                key={slotLabel}
                onClick={() => {
                  if (!imageUrl) {
                    return;
                  }
                  onSelectPreview(slotIndex);
                }}
                type="button"
              >
                {previewStatus === 'loading' ? (
                  <Skeleton.Image className="training-landing__preview-skeleton" active />
                ) : imageUrl ? (
                  <>
                    <img
                      alt={`训练身份形象渲染图 ${slotIndex + 1}`}
                      className="training-landing__preview-image"
                      src={imageUrl}
                    />
                    {isSelected ? (
                      <span className="training-landing__preview-selected-badge">已选择</span>
                    ) : null}
                  </>
                ) : (
                  <div className="training-landing__preview-placeholder">
                    <p>{slotLabel}</p>
                    <p>等待生成</p>
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {previewError ? (
          <Alert
            className="training-landing__preview-alert"
            description={previewError}
            showIcon
            title="渲染失败"
            type="error"
          />
        ) : null}

        <div className="training-landing__preview-actions">
          <Button className="training-landing__back" onClick={onBack}>
            返回
          </Button>
          <Button
            className="training-landing__confirm"
            disabled={!canStartTraining || isStartingTraining}
            loading={isStartingTraining}
            onClick={() => {
              void onConfirm();
            }}
            type="primary"
          >
            进入训练
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default TrainingPortraitPreview;
