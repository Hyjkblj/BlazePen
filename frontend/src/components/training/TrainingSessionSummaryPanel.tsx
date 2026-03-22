import type { TrainingRuntimeState } from '@/types/training';

interface TrainingSessionSummaryPanelProps {
  sessionId: string;
  trainingModeLabel: string | null;
  status: string;
  roundNo: number;
  totalRounds: number | null;
  progressLabel: string | null;
  characterId: string | null;
  currentSceneId: string | null;
  runtimeState: TrainingRuntimeState;
}

function TrainingSessionSummaryPanel({
  sessionId,
  trainingModeLabel,
  status,
  roundNo,
  totalRounds,
  progressLabel,
  characterId,
  currentSceneId,
  runtimeState,
}: TrainingSessionSummaryPanelProps) {
  return (
    <article className="training-shell__panel">
      <h2>当前训练状态</h2>
      <dl className="training-shell__summary">
        <div>
          <dt>sessionId</dt>
          <dd>{sessionId}</dd>
        </div>
        <div>
          <dt>训练模式</dt>
          <dd>{trainingModeLabel}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>{status}</dd>
        </div>
        <div>
          <dt>回合</dt>
          <dd>
            {roundNo}
            {totalRounds !== null ? ` / ${totalRounds}` : ''}
          </dd>
        </div>
        {progressLabel ? (
          <div>
            <dt>进度</dt>
            <dd>{progressLabel}</dd>
          </div>
        ) : null}
        <div>
          <dt>characterId</dt>
          <dd>{characterId ?? '未绑定'}</dd>
        </div>
        <div>
          <dt>currentSceneId</dt>
          <dd>{currentSceneId ?? '暂无'}</dd>
        </div>
      </dl>

      <div className="training-shell__state-grid">
        <div>
          <h3>State Bar</h3>
          <ul className="training-shell__metric-list">
            <li>editorTrust: {runtimeState.stateBar.editorTrust}</li>
            <li>publicStability: {runtimeState.stateBar.publicStability}</li>
            <li>sourceSafety: {runtimeState.stateBar.sourceSafety}</li>
          </ul>
        </div>
        <div>
          <h3>Runtime Flags</h3>
          <ul className="training-shell__metric-list">
            <li>panicTriggered: {String(runtimeState.runtimeFlags.panicTriggered)}</li>
            <li>sourceExposed: {String(runtimeState.runtimeFlags.sourceExposed)}</li>
            <li>editorLocked: {String(runtimeState.runtimeFlags.editorLocked)}</li>
            <li>highRiskPath: {String(runtimeState.runtimeFlags.highRiskPath)}</li>
          </ul>
        </div>
      </div>
    </article>
  );
}

export default TrainingSessionSummaryPanel;
