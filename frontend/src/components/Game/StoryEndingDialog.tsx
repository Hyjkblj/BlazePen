import ModalDialog from '@/components/ModalDialog';
import type { StoryEndingStatus } from '@/hooks/useStoryEnding';
import type { StoryEndingSummary } from '@/types/game';
import { resolveSceneDisplayName } from '@/utils/storyScene';

export interface StoryEndingDialogProps {
  open: boolean;
  endingStatus: StoryEndingStatus;
  endingSummary: StoryEndingSummary | null;
  endingError: string | null;
  onClose: () => void;
  onRetry: () => void;
}

const ENDING_TITLES: Record<string, string> = {
  good_ending: '圆满结局',
  neutral_ending: '平稳结局',
  bad_ending: '遗憾结局',
  open_ending: '开放结局',
};

const resolveEndingTitle = (endingType: string | null | undefined): string => {
  if (!endingType) {
    return '结局摘要';
  }

  return ENDING_TITLES[endingType] ?? endingType;
};

export default function StoryEndingDialog({
  open,
  endingStatus,
  endingSummary,
  endingError,
  onClose,
  onRetry,
}: StoryEndingDialogProps) {
  const endingSceneLabel = endingSummary?.sceneId
    ? resolveSceneDisplayName(endingSummary.sceneId) ?? endingSummary.sceneId
    : null;
  const endingMeta = endingSummary
    ? [endingSummary.eventTitle, endingSceneLabel].filter(
        (value): value is string => typeof value === 'string' && value.trim() !== ''
      )
    : [];

  const metrics = endingSummary
    ? [
        { label: '好感', value: endingSummary.keyStates.favorability },
        { label: '信任', value: endingSummary.keyStates.trust },
        { label: '敌意', value: endingSummary.keyStates.hostility },
        { label: '依赖', value: endingSummary.keyStates.dependence },
      ].filter((metric) => metric.value !== null)
    : [];

  return (
    <ModalDialog
      open={open}
      title="故事结局"
      onClose={onClose}
      className="story-session-dialog"
      footer={
        <div className="story-session-dialog-actions">
          {endingStatus === 'error' ? (
            <button
              type="button"
              className="story-session-dialog-action"
              onClick={onRetry}
            >
              重试
            </button>
          ) : null}
          <button
            type="button"
            className="story-session-dialog-action story-session-dialog-action-primary"
            onClick={onClose}
          >
            关闭
          </button>
        </div>
      }
    >
      <div className="story-session-dialog-content">
        {endingStatus === 'loading' ? (
          <div className="story-ending-loading">
            <div className="game-loading-spinner" aria-hidden="true" />
            <p className="story-session-dialog-caption">正在读取本次故事结局摘要...</p>
          </div>
        ) : null}

        {endingStatus === 'error' ? (
          <div className="story-ending-error">
            <p className="story-ending-heading">结局摘要加载失败</p>
            <p className="story-session-dialog-caption">
              {endingError ?? '暂时无法读取当前故事的结局摘要。'}
            </p>
          </div>
        ) : null}

        {endingStatus === 'unavailable' ? (
          <div className="story-ending-error">
            <p className="story-ending-heading">结局摘要暂不可用</p>
            <p className="story-session-dialog-caption">
              当前故事已结束，但暂时没有可展示的结局摘要。
            </p>
          </div>
        ) : null}

        {endingStatus === 'ready' && endingSummary ? (
          <div className="story-ending-summary">
            <p className="story-ending-heading">
              {resolveEndingTitle(endingSummary.type)}
            </p>
            {endingMeta.length > 0 ? (
              <p className="story-session-dialog-caption">{endingMeta.join(' · ')}</p>
            ) : null}
            <p className="story-ending-description">{endingSummary.description}</p>

            {metrics.length > 0 ? (
              <div className="story-ending-metrics">
                {metrics.map((metric) => (
                  <div key={metric.label} className="story-ending-metric">
                    <span className="story-ending-metric-label">{metric.label}</span>
                    <strong className="story-ending-metric-value">{metric.value}</strong>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </ModalDialog>
  );
}
