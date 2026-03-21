import { Link } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import './Training.css';

const TRAINING_MODE_OPTIONS = [
  ['guided', '引导训练', '适合首次进入，优先给出推荐路径。'],
  ['self-paced', '自主训练', '保留更多手动选择空间。'],
  ['adaptive', '自适应训练', '按当前状态动态调节训练分支。'],
] as const;

const formatProgressPercent = (progressPercent: number): string =>
  `${Number(progressPercent.toFixed(1))}%`;

function Training() {
  const flow = useTrainingMvpFlow();
  const {
    bootstrapStatus,
    bootstrapErrorMessage,
    roundStatus,
    roundErrorMessage,
    noticeMessage,
    dismissNotice,
    hasResumeTarget,
    resumeTarget,
    trainingMode,
    setTrainingMode,
    formDraft,
    updateFormDraft,
    startTraining,
    retryRestore,
    clearWorkspace,
    sessionView,
    latestOutcome,
    selectedOptionId,
    selectOption,
    responseInput,
    setResponseInput,
    submissionPreview,
    canStartTraining,
    canSubmitRound,
    submitCurrentRound,
  } = flow;

  const sessionTrainingModeLabel =
    sessionView?.trainingMode === 'self-paced'
      ? '自主训练'
      : sessionView?.trainingMode === 'adaptive'
        ? '自适应训练'
        : sessionView?.trainingMode === 'guided'
          ? '引导训练'
          : null;

  const loadingMessage =
    bootstrapStatus === 'starting'
      ? '正在初始化训练会话...'
      : bootstrapStatus === 'restoring'
        ? '正在恢复训练会话...'
        : roundStatus === 'submitting'
          ? '正在提交本轮训练...'
          : null;
  const sessionProgressLabel = sessionView?.progressAnchor
    ? formatProgressPercent(sessionView.progressAnchor.progressPercent)
    : null;
  const hasInsightEntry = sessionView !== null || hasResumeTarget;

  return (
    <div className="training-page">
      <section className="training-shell">
        <div className="training-shell__eyebrow">PR-07</div>
        <h1 className="training-shell__title">Training Frontend MVP</h1>
        <p className="training-shell__description">
          训练主线通过独立 `sessionId` 驱动。初始化、回合提交、刷新恢复都收口到训练专用
          `services / hooks / flow`，页面层不直接兼容后端脏字段，也不复用 story 会话实现。
        </p>

        <div className="training-shell__actions">
          <Link className="training-shell__link" to={ROUTES.HOME}>
            返回首页
          </Link>
          {sessionView || hasResumeTarget ? (
            <button className="training-shell__clear-button" type="button" onClick={clearWorkspace}>
              清空训练入口
            </button>
          ) : null}
        </div>

        {hasInsightEntry ? (
          <div className="training-shell__subnav" aria-label="训练结果导航">
            <Link className="training-shell__subnav-link" to={ROUTES.TRAINING_PROGRESS}>
              查看训练进度
            </Link>
            <Link className="training-shell__subnav-link" to={ROUTES.TRAINING_REPORT}>
              查看训练报告
            </Link>
            <Link className="training-shell__subnav-link" to={ROUTES.TRAINING_DIAGNOSTICS}>
              查看训练诊断
            </Link>
          </div>
        ) : null}

        {loadingMessage ? <div className="training-shell__banner">{loadingMessage}</div> : null}
        {bootstrapErrorMessage ? (
          <div className="training-shell__alert" role="alert">
            <span>{bootstrapErrorMessage}</span>
            <button type="button" onClick={() => void retryRestore()}>
              重试恢复
            </button>
          </div>
        ) : null}
        {roundErrorMessage ? (
          <div className="training-shell__alert" role="alert">
            <span>{roundErrorMessage}</span>
            <button type="button" onClick={() => void retryRestore()}>
              恢复当前训练
            </button>
          </div>
        ) : null}
        {noticeMessage ? (
          <div className="training-shell__notice" role="status">
            <span>{noticeMessage}</span>
            <button type="button" onClick={dismissNotice}>
              关闭
            </button>
          </div>
        ) : null}

        {!sessionView ? (
          <div className="training-shell__workspace">
            <article className="training-shell__panel training-shell__panel--primary">
              <h2>开始训练</h2>
              <p className="training-shell__empty">
                本地缓存只记住可恢复的 `sessionId` 入口，不保存服务端会话事实。页面刷新后统一走
                `session summary` 恢复。
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
                onClick={() => {
                  void startTraining();
                }}
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
                    <dd>{resumeTarget?.sessionId ?? '当前上下文会话'}</dd>
                  </div>
                  <div>
                    <dt>训练模式</dt>
                    <dd>{resumeTarget?.trainingMode ?? '等待服务端恢复确认'}</dd>
                  </div>
                  <div>
                    <dt>缓存状态</dt>
                    <dd>{resumeTarget?.status ?? '未知'}</dd>
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
                  onClick={() => {
                    void retryRestore();
                  }}
                >
                  恢复上次训练
                </button>
              </div>
            </article>
          </div>
        ) : (
          <div className="training-shell__workspace">
            <article className="training-shell__panel">
              <h2>当前训练状态</h2>
              <dl className="training-shell__summary">
                <div>
                  <dt>sessionId</dt>
                  <dd>{sessionView.sessionId}</dd>
                </div>
                <div>
                  <dt>训练模式</dt>
                  <dd>{sessionTrainingModeLabel}</dd>
                </div>
                <div>
                  <dt>状态</dt>
                  <dd>{sessionView.status}</dd>
                </div>
                <div>
                  <dt>回合</dt>
                  <dd>
                    {sessionView.roundNo}
                    {sessionView.totalRounds !== null ? ` / ${sessionView.totalRounds}` : ''}
                  </dd>
                </div>
                {sessionProgressLabel ? (
                  <div>
                    <dt>进度</dt>
                    <dd>{sessionProgressLabel}</dd>
                  </div>
                ) : null}
                <div>
                  <dt>characterId</dt>
                  <dd>{sessionView.characterId ?? '未绑定'}</dd>
                </div>
                <div>
                  <dt>currentSceneId</dt>
                  <dd>{sessionView.runtimeState.currentSceneId ?? '暂无'}</dd>
                </div>
              </dl>

              <div className="training-shell__state-grid">
                <div>
                  <h3>State Bar</h3>
                  <ul className="training-shell__metric-list">
                    <li>editorTrust: {sessionView.runtimeState.stateBar.editorTrust}</li>
                    <li>publicStability: {sessionView.runtimeState.stateBar.publicStability}</li>
                    <li>sourceSafety: {sessionView.runtimeState.stateBar.sourceSafety}</li>
                  </ul>
                </div>
                <div>
                  <h3>Runtime Flags</h3>
                  <ul className="training-shell__metric-list">
                    <li>panicTriggered: {String(sessionView.runtimeState.runtimeFlags.panicTriggered)}</li>
                    <li>sourceExposed: {String(sessionView.runtimeState.runtimeFlags.sourceExposed)}</li>
                    <li>editorLocked: {String(sessionView.runtimeState.runtimeFlags.editorLocked)}</li>
                    <li>highRiskPath: {String(sessionView.runtimeState.runtimeFlags.highRiskPath)}</li>
                  </ul>
                </div>
              </div>
            </article>

            <article className="training-shell__panel training-shell__panel--primary">
              {sessionView.isCompleted ? (
                <>
                  <h2>训练完成</h2>
                  <p className="training-shell__empty">
                    当前训练已完成。完成态仍通过服务端 `session summary` 恢复，不回退到本地事实源。
                  </p>
                  {latestOutcome?.ending ? (
                    <pre className="training-shell__json-card">
                      {JSON.stringify(latestOutcome.ending, null, 2)}
                    </pre>
                  ) : null}
                  <div className="training-shell__stack-actions">
                    <button className="training-shell__primary-button" type="button" onClick={clearWorkspace}>
                      开始新的训练
                    </button>
                  </div>
                </>
              ) : sessionView.currentScenario ? (
                <>
                  <h2>{sessionView.currentScenario.title}</h2>
                  <p className="training-shell__scenario-meta">
                    {sessionView.currentScenario.eraDate || '未标注时间'} ·{' '}
                    {sessionView.currentScenario.location || '未标注地点'}
                  </p>
                  <p className="training-shell__scenario-brief">
                    {sessionView.currentScenario.brief ||
                      sessionView.currentScenario.briefing ||
                      '当前场景暂无额外简介。'}
                  </p>

                  <div className="training-shell__scenario-grid">
                    <div>
                      <h3>Mission</h3>
                      <p>{sessionView.currentScenario.mission || '保持训练目标可推进。'}</p>
                    </div>
                    <div>
                      <h3>Decision Focus</h3>
                      <p>{sessionView.currentScenario.decisionFocus || '根据现场状态完成判断。'}</p>
                    </div>
                  </div>

                  {sessionView.currentScenario.options.length > 0 ? (
                    <div className="training-shell__option-list">
                      {sessionView.currentScenario.options.map((option) => (
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
                      onClick={() => {
                        void submitCurrentRound();
                      }}
                    >
                      提交本轮训练
                    </button>
                    <button
                      className="training-shell__secondary-button"
                      type="button"
                      onClick={() => {
                        void retryRestore();
                      }}
                    >
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
                    <button
                      className="training-shell__primary-button"
                      type="button"
                      onClick={() => {
                        void retryRestore();
                      }}
                    >
                      恢复当前训练
                    </button>
                  </div>
                </>
              )}
            </article>

            <article className="training-shell__panel">
              <h2>本轮结果</h2>
              {latestOutcome ? (
                <>
                  <dl className="training-shell__summary">
                    <div>
                      <dt>roundNo</dt>
                      <dd>{latestOutcome.roundNo}</dd>
                    </div>
                    <div>
                      <dt>confidence</dt>
                      <dd>{latestOutcome.evaluation.confidence}</dd>
                    </div>
                    <div>
                      <dt>evalMode</dt>
                      <dd>{latestOutcome.evaluation.evalMode}</dd>
                    </div>
                    <div>
                      <dt>riskFlags</dt>
                      <dd>{latestOutcome.evaluation.riskFlags.join(', ') || '无'}</dd>
                    </div>
                  </dl>

                  <div className="training-shell__state-grid">
                    <div>
                      <h3>Evidence</h3>
                      <ul className="training-shell__metric-list">
                        {latestOutcome.evaluation.evidence.length > 0 ? (
                          latestOutcome.evaluation.evidence.map((item) => <li key={item}>{item}</li>)
                        ) : (
                          <li>无</li>
                        )}
                      </ul>
                    </div>
                    <div>
                      <h3>Consequence Events</h3>
                      <ul className="training-shell__metric-list">
                        {latestOutcome.consequenceEvents.length > 0 ? (
                          latestOutcome.consequenceEvents.map((item) => (
                            <li key={`${item.eventType}-${item.summary}`}>
                              {item.label || item.eventType}: {item.summary || '无摘要'}
                            </li>
                          ))
                        ) : (
                          <li>本轮暂无额外后果事件。</li>
                        )}
                      </ul>
                    </div>
                  </div>
                </>
              ) : (
                <p className="training-shell__empty">
                  这里展示最近一次回合提交结果。刷新后只恢复服务端当前会话状态，不回填本地临时评估结果。
                </p>
              )}
            </article>
          </div>
        )}
      </section>
    </div>
  );
}

export default Training;
