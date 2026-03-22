import type { TrainingScenario } from '@/types/training';

interface TrainingRoundPanelProps {
  isCompleted: boolean;
  currentScenario: TrainingScenario | null;
  selectedOptionId: string | null;
  selectOption: (optionId: string) => void;
  responseInput: string;
  setResponseInput: (value: string) => void;
  submissionPreview: string | null;
  canSubmitRound: boolean;
  submitCurrentRound: () => void;
  retryRestore: () => void;
  clearWorkspace: () => void;
  completedEnding: Record<string, unknown> | null;
}

function TrainingRoundPanel({
  isCompleted,
  currentScenario,
  selectedOptionId,
  selectOption,
  responseInput,
  setResponseInput,
  submissionPreview,
  canSubmitRound,
  submitCurrentRound,
  retryRestore,
  clearWorkspace,
  completedEnding,
}: TrainingRoundPanelProps) {
  return (
    <article className="training-shell__panel training-shell__panel--primary">
      {isCompleted ? (
        <>
          <h2>训练完成</h2>
          <p className="training-shell__empty">
            当前训练已完成。完成态仍通过服务端 `session summary` 恢复，不回退到本地事实源。
          </p>
          {completedEnding ? (
            <pre className="training-shell__json-card">
              {JSON.stringify(completedEnding, null, 2)}
            </pre>
          ) : null}
          <div className="training-shell__stack-actions">
            <button className="training-shell__primary-button" type="button" onClick={clearWorkspace}>
              开始新的训练
            </button>
          </div>
        </>
      ) : currentScenario ? (
        <>
          <h2>{currentScenario.title}</h2>
          <p className="training-shell__scenario-meta">
            {currentScenario.eraDate || '未标注时间'} 路{' '}
            {currentScenario.location || '未标注地点'}
          </p>
          <p className="training-shell__scenario-brief">
            {currentScenario.brief || '当前场景暂无额外简介。'}
          </p>

          <div className="training-shell__scenario-grid">
            <div>
              <h3>Mission</h3>
              <p>{currentScenario.mission || '保持训练目标可推进。'}</p>
            </div>
            <div>
              <h3>Decision Focus</h3>
              <p>{currentScenario.decisionFocus || '根据现场状态完成判断。'}</p>
            </div>
          </div>

          {currentScenario.options.length > 0 ? (
            <div className="training-shell__option-list">
              {currentScenario.options.map((option) => (
                <button
                  key={option.id}
                  type="button"
                  className={`training-shell__option${
                    selectedOptionId === option.id ? ' training-shell__option--active' : ''
                  }`}
                  onClick={() => selectOption(option.id)}
                >
                  <strong>{option.label}</strong>
                  <span>{option.impactHint || '无额外提示'}</span>
                </button>
              ))}
            </div>
          ) : null}

          <label className="training-shell__field training-shell__field--textarea">
            <span>本轮操作说明</span>
            <textarea
              value={responseInput}
              onChange={(event) => setResponseInput(event.target.value)}
              placeholder="填写训练操作、采访策略或补充说明。若只选择选项，也会提交选项标签。"
              rows={6}
            />
          </label>

          {submissionPreview ? (
            <p className="training-shell__submission-preview">当前已选选项：{submissionPreview}</p>
          ) : null}

          <div className="training-shell__stack-actions">
            <button
              className="training-shell__primary-button"
              type="button"
              disabled={!canSubmitRound}
              onClick={submitCurrentRound}
            >
              提交本轮训练
            </button>
            <button className="training-shell__secondary-button" type="button" onClick={retryRestore}>
              按服务端会话恢复
            </button>
          </div>
        </>
      ) : (
        <>
          <h2>训练恢复待确认</h2>
          <p className="training-shell__empty">
            当前训练会话没有可直接提交的场景。请按服务端 `session summary` 重建当前可继续状态。
          </p>
          <div className="training-shell__stack-actions">
            <button className="training-shell__primary-button" type="button" onClick={retryRestore}>
              恢复当前训练
            </button>
          </div>
        </>
      )}
    </article>
  );
}

export default TrainingRoundPanel;
