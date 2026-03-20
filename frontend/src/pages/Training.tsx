import { Link } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { useTrainingSessionFlow } from '@/flows/useTrainingSessionFlow';
import './Training.css';

function Training() {
  const { activeSession, hasActiveSession, trainingModeLabel, clearTrainingSession } =
    useTrainingSessionFlow();

  return (
    <div className="training-page">
      <section className="training-shell">
        <div className="training-shell__eyebrow">PR-FE-06</div>
        <h1 className="training-shell__title">Training Frontend Shell</h1>
        <p className="training-shell__description">
          训练主线已经建立独立的 `sessionId`、DTO normalizer、context 和 route shell。
          当前页面只承载训练入口边界，不在页面层直接拼装 payload、消费 storage 或兼容 story 运行态。
        </p>

        <div className="training-shell__actions">
          <Link className="training-shell__link" to={ROUTES.HOME}>
            返回首页
          </Link>
          {hasActiveSession ? (
            <button
              className="training-shell__clear-button"
              type="button"
              onClick={clearTrainingSession}
            >
              清空活动训练会话
            </button>
          ) : null}
        </div>

        <div className="training-shell__panels">
          <article className="training-shell__panel">
            <h2>当前状态</h2>
            {activeSession ? (
              <dl className="training-shell__summary">
                <div>
                  <dt>sessionId</dt>
                  <dd>{activeSession.sessionId}</dd>
                </div>
                <div>
                  <dt>训练模式</dt>
                  <dd>{trainingModeLabel}</dd>
                </div>
                <div>
                  <dt>状态</dt>
                  <dd>{activeSession.status}</dd>
                </div>
                <div>
                  <dt>回合</dt>
                  <dd>
                    {activeSession.roundNo}
                    {activeSession.totalRounds !== null ? ` / ${activeSession.totalRounds}` : ''}
                  </dd>
                </div>
                <div>
                  <dt>characterId</dt>
                  <dd>{activeSession.characterId ?? '未绑定'}</dd>
                </div>
                <div>
                  <dt>currentSceneId</dt>
                  <dd>{activeSession.runtimeState.currentSceneId ?? '暂无'}</dd>
                </div>
              </dl>
            ) : (
              <p className="training-shell__empty">
                当前没有活动训练会话。后续训练 MVP 页面可以在不污染 story 主线的前提下，直接复用这层壳结构继续开发。
              </p>
            )}
          </article>

          <article className="training-shell__panel">
            <h2>边界约束</h2>
            <ul className="training-shell__list">
              <li>训练会话只认 `sessionId`，不接受 `threadId` 混用。</li>
              <li>训练页面不直接处理后端 snake_case，也不读取本地存储作为事实源。</li>
              <li>训练 runtime 状态统一挂在 `runtimeState`，避免页面和 flow 各自持有副本。</li>
            </ul>
          </article>
        </div>
      </section>
    </div>
  );
}

export default Training;
