import type { StoryEndingStatus } from '@/hooks/useStoryEnding';

export interface StorySessionToolbarProps {
  hasTranscript: boolean;
  canViewEnding: boolean;
  endingStatus: StoryEndingStatus;
  onOpenTranscript: () => void;
  onOpenEnding: () => void;
}

const resolveEndingButtonLabel = (endingStatus: StoryEndingStatus): string => {
  if (endingStatus === 'loading') {
    return '结局摘要加载中';
  }

  return '结局摘要';
};

export default function StorySessionToolbar({
  hasTranscript,
  canViewEnding,
  endingStatus,
  onOpenTranscript,
  onOpenEnding,
}: StorySessionToolbarProps) {
  return (
    <div className="story-session-toolbar">
      <button
        type="button"
        className="story-session-toolbar-button"
        onClick={onOpenTranscript}
        disabled={!hasTranscript}
      >
        当前记录
      </button>

      <button
        type="button"
        className="story-session-toolbar-button"
        onClick={onOpenEnding}
        disabled={!canViewEnding}
      >
        {resolveEndingButtonLabel(endingStatus)}
      </button>
    </div>
  );
}
