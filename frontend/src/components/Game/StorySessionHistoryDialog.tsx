import ModalDialog from '@/components/ModalDialog';
import type { StoryHistoryStatus } from '@/hooks/useStorySessionHistory';
import type { StorySessionHistoryResult } from '@/types/game';
import { resolveSceneDisplayName } from '@/utils/storyScene';

const STATE_LABELS: Record<string, string> = {
  favorability: '好感',
  trust: '信任',
  hostility: '敌意',
  dependence: '依赖',
};

const USER_ACTION_LABELS: Record<string, string> = {
  option: '你的选择',
  free_text: '你的输入',
};

const formatStateDelta = (value: number): string => {
  if (value > 0) {
    return `+${value}`;
  }

  return `${value}`;
};

export interface StorySessionHistoryDialogProps {
  open: boolean;
  historyStatus: StoryHistoryStatus;
  historySession: StorySessionHistoryResult | null;
  historyError: string | null;
  onClose: () => void;
  onRetry: () => void;
}

export default function StorySessionHistoryDialog({
  open,
  historyStatus,
  historySession,
  historyError,
  onClose,
  onRetry,
}: StorySessionHistoryDialogProps) {
  const historyItems = historySession?.history ?? [];

  return (
    <ModalDialog
      open={open}
      title="服务端历史"
      onClose={onClose}
      className="story-session-dialog"
      footer={
        <div className="story-session-dialog-actions">
          {historyStatus === 'error' ? (
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
        <p className="story-session-dialog-caption">
          这里展示服务端持久化的故事回合历史，用于回看已提交内容，不包含当前设备尚未同步的临时消息。
        </p>

        {historyStatus === 'loading' ? (
          <div className="story-ending-loading">
            <div className="game-loading-spinner" aria-hidden="true" />
            <p className="story-session-dialog-caption">正在读取服务端历史...</p>
          </div>
        ) : null}

        {historyStatus === 'error' ? (
          <div className="story-ending-error">
            <p className="story-ending-heading">服务端历史加载失败</p>
            <p className="story-session-dialog-caption">
              {historyError ?? '暂时无法读取服务端历史。'}
            </p>
          </div>
        ) : null}

        {historyStatus === 'empty' ? (
          <p className="story-session-dialog-empty">当前会话还没有可展示的服务端历史。</p>
        ) : null}

        {historyStatus === 'ready' ? (
          <ol className="story-session-transcript-list">
            {historyItems.map((item) => {
              const sceneLabel = item.sceneId
                ? resolveSceneDisplayName(item.sceneId) ?? item.sceneId
                : null;
              const itemMeta = [item.eventTitle, sceneLabel].filter(
                (value): value is string => typeof value === 'string' && value.trim() !== ''
              );
              const stateChanges = Object.entries(item.stateSummary.changes);

              return (
                <li
                  key={`${item.roundNo}-${item.createdAt ?? item.eventTitle ?? item.userAction.summary}`}
                  className="story-session-transcript-item story-history-item"
                >
                  <div className="story-session-transcript-meta">
                    <span className="story-session-transcript-sequence">#{item.roundNo}</span>
                    <span className="story-session-transcript-role">
                      {USER_ACTION_LABELS[item.userAction.kind] ?? '用户操作'}
                    </span>
                    <span className="story-history-status-tag">{item.status}</span>
                  </div>

                  {itemMeta.length > 0 ? (
                    <p className="story-session-dialog-caption">{itemMeta.join(' · ')}</p>
                  ) : null}

                  <div className="story-history-block">
                    <p className="story-history-label">
                      {USER_ACTION_LABELS[item.userAction.kind] ?? '用户操作'}
                    </p>
                    <p className="story-session-transcript-content">
                      {item.userAction.summary || '本回合没有可展示的用户操作。'}
                    </p>
                  </div>

                  {item.characterDialogue ? (
                    <div className="story-history-block">
                      <p className="story-history-label">角色回应</p>
                      <p className="story-session-transcript-content">{item.characterDialogue}</p>
                    </div>
                  ) : null}

                  {stateChanges.length > 0 ? (
                    <div className="story-history-state-list">
                      {stateChanges.map(([key, delta]) => (
                        <span key={key} className="story-history-state-chip">
                          {STATE_LABELS[key] ?? key} {formatStateDelta(delta)}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ol>
        ) : null}
      </div>
    </ModalDialog>
  );
}
