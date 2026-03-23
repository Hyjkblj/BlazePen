import type { TrainingMode } from '@/types/training';

interface TrainingFormDraftValue {
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
}

interface TrainingBootstrapPanelsProps {
  trainingMode: TrainingMode;
  setTrainingMode: (mode: TrainingMode) => void;
  formDraft: TrainingFormDraftValue;
  updateFormDraft: (field: keyof TrainingFormDraftValue, value: string) => void;
  canStartTraining: boolean;
  startTraining: () => void;
  hasResumeTarget: boolean;
  resumeSessionId: string | null;
  resumeTrainingMode: TrainingMode | null;
  resumeStatus: string | null;
  retryRestore: () => void;
}

const TRAINING_MODE_OPTIONS = [
  ['guided', '引导训练', '适合首次进入，优先给出推荐路径。'],
  ['self-paced', '自主训练', '保留更多手动选择空间。'],
  ['adaptive', '自适应训练', '按当前状态动态调整训练分支。'],
] as const;

function TrainingBootstrapPanels({
  trainingMode,
  setTrainingMode,
  formDraft,
  updateFormDraft,
  canStartTraining,
  startTraining,
  hasResumeTarget,
  resumeSessionId,
  resumeTrainingMode,
  resumeStatus,
  retryRestore,
}: TrainingBootstrapPanelsProps) {
  return (
    <div className="training-shell__workspace">
      <article className="training-shell__panel training-shell__panel--primary">
        <h2>开始训练</h2>
        <p className="training-shell__empty">
          本地缓存只记住可恢复的 `sessionId` 入口，不保存服务端会话事实。页面刷新后统一走
          `session summary` 手动恢复。
        </p>

        <div className="training-shell__mode-list" role="radiogroup" aria-label="训练模式">
          {TRAINING_MODE_OPTIONS.map(([modeValue, title, description]) => (
            <label
              key={modeValue}
              className={`training-shell__mode-card${
                trainingMode === modeValue ? ' training-shell__mode-card--active' : ''
              }`}
            >
              <input
                type="radio"
                name="training-mode"
                value={modeValue}
                checked={trainingMode === modeValue}
                onChange={() => setTrainingMode(modeValue)}
              />
              <span>{title}</span>
              <small>{description}</small>
            </label>
          ))}
        </div>

        <div className="training-shell__form-grid">
          <label className="training-shell__field">
            <span>characterId</span>
            <input
              value={formDraft.characterId}
              onChange={(event) => updateFormDraft('characterId', event.target.value)}
              placeholder="可选，绑定训练角色"
              inputMode="numeric"
            />
          </label>
          <label className="training-shell__field">
            <span>姓名</span>
            <input
              value={formDraft.playerName}
              onChange={(event) => updateFormDraft('playerName', event.target.value)}
              placeholder="可选"
            />
          </label>
          <label className="training-shell__field">
            <span>身份</span>
            <input
              value={formDraft.playerIdentity}
              onChange={(event) => updateFormDraft('playerIdentity', event.target.value)}
              placeholder="例如：战地记者"
            />
          </label>
          <label className="training-shell__field">
            <span>性别</span>
            <input
              value={formDraft.playerGender}
              onChange={(event) => updateFormDraft('playerGender', event.target.value)}
              placeholder="可选"
            />
          </label>
          <label className="training-shell__field">
            <span>年龄</span>
            <input
              value={formDraft.playerAge}
              onChange={(event) => updateFormDraft('playerAge', event.target.value)}
              placeholder="可选"
              inputMode="numeric"
            />
          </label>
        </div>

        <button
          className="training-shell__primary-button"
          type="button"
          disabled={!canStartTraining}
          onClick={startTraining}
        >
          启动训练
        </button>
      </article>

      <article className="training-shell__panel">
        <h2>恢复入口</h2>
        {hasResumeTarget ? (
          <dl className="training-shell__summary">
            <div>
              <dt>sessionId</dt>
              <dd>{resumeSessionId ?? '当前上下文会话'}</dd>
            </div>
            <div>
              <dt>训练模式</dt>
              <dd>{resumeTrainingMode ?? '等待服务端恢复确认'}</dd>
            </div>
            <div>
              <dt>缓存状态</dt>
              <dd>{resumeStatus ?? '未知'}</dd>
            </div>
          </dl>
        ) : (
          <p className="training-shell__empty">
            当前没有可恢复的训练入口。首次进入会走初始化路径，刷新后才走服务端恢复路径。
          </p>
        )}

        <div className="training-shell__stack-actions">
          <button
            className="training-shell__secondary-button"
            type="button"
            disabled={!hasResumeTarget}
            onClick={retryRestore}
          >
            恢复上次训练
          </button>
        </div>
      </article>
    </div>
  );
}

export default TrainingBootstrapPanels;
