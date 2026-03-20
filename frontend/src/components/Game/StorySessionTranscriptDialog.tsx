import ModalDialog from '@/components/ModalDialog';
import type { StoryTranscriptEntry } from '@/hooks/useStorySessionTranscript';

export interface StorySessionTranscriptDialogProps {
  open: boolean;
  entries: StoryTranscriptEntry[];
  onClose: () => void;
}

export default function StorySessionTranscriptDialog({
  open,
  entries,
  onClose,
}: StorySessionTranscriptDialogProps) {
  return (
    <ModalDialog
      open={open}
      title="当前设备会话记录"
      onClose={onClose}
      className="story-session-dialog"
      footer={
        <button
          type="button"
          className="story-session-dialog-action story-session-dialog-action-primary"
          onClick={onClose}
        >
          关闭
        </button>
      }
    >
      <div className="story-session-dialog-content">
        <p className="story-session-dialog-caption">
          这里只展示当前设备已经加载过的会话内容，用于恢复和回看，不代表服务端完整历史。
        </p>

        {entries.length === 0 ? (
          <p className="story-session-dialog-empty">当前没有可展示的会话记录。</p>
        ) : (
          <ol className="story-session-transcript-list">
            {entries.map((entry) => (
              <li key={entry.id} className="story-session-transcript-item">
                <div className="story-session-transcript-meta">
                  <span className="story-session-transcript-sequence">
                    #{entry.sequenceNo}
                  </span>
                  <span className="story-session-transcript-role">{entry.roleLabel}</span>
                </div>
                <p className="story-session-transcript-content">{entry.content}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </ModalDialog>
  );
}
