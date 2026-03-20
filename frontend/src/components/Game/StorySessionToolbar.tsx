import type { StoryEndingStatus } from '@/hooks/useStoryEnding';
import type { StoryHistoryStatus } from '@/hooks/useStorySessionHistory';

export interface StorySessionToolbarProps {
  hasTranscript: boolean;
  canViewHistory: boolean;
  canViewEnding: boolean;
  historyStatus: StoryHistoryStatus;
  endingStatus: StoryEndingStatus;
  onOpenTranscript: () => void;
  onOpenHistory: () => void;
  onOpenEnding: () => void;
}

const resolveHistoryButtonLabel = (historyStatus: StoryHistoryStatus): string => {
  if (historyStatus === 'loading') {
    return '服务端历史加载中';
  }

  return '服务端历史';
};

const resolveEndingButtonLabel = (endingStatus: StoryEndingStatus): string => {
  if (endingStatus === 'loading') {
    return '结局摘要加载中';
  }

  return '结局摘要';
};

export default function StorySessionToolbar({
  hasTranscript,
  canViewHistory,
  canViewEnding,
  historyStatus,
  endingStatus,
  onOpenTranscript,
  onOpenHistory,
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
        onClick={onOpenHistory}
        disabled={!canViewHistory}
      >
        {resolveHistoryButtonLabel(historyStatus)}
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
