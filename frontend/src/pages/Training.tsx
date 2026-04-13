import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import SceneTransition from '@/components/SceneTransition';
import StaticAssetImage from '@/components/StaticAssetImage';
import NarrativeConsequenceView from '@/components/training/NarrativeConsequenceView';
import TrainingCinematicChoiceBand from '@/components/training/TrainingCinematicChoiceBand';
import { buildTrainingCompletionRoute, ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import { useNarrativePhaseEngine } from '@/hooks/useNarrativePhaseEngine';
import { useTrainingMajorSceneTransition } from '@/hooks/useTrainingMajorSceneTransition';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import { useSceneFadeTransition } from '@/hooks/useSceneFadeTransition';
import { useTypewriter } from '@/hooks/useTypewriter';
import { getStaticAssetContractWarning } from '@/services/assetUrl';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { filterTrainingNarrationText } from '@/utils/trainingNarrationFilter';
import { resolveNarrativeForScenario } from '@/utils/trainingSession';
import './Training.css';

/** 场景图 URL 就绪后延迟再展示独白/选项，给大图解码与绘制留出时间 */
const POST_SCENE_IMAGE_UI_DELAY_MS = 0;
const AUTO_REVEAL_CHOICES_IDLE_MS = 20000;
const IMPACT_POPUP_DURATION_MS = 5000;
const IMPACT_DELTA_EPSILON = 0.0001;

const TRAINING_K_SKILL_LABELS: Record<string, string> = {
  K1: '事实核验',
  K2: '来源可信评估',
  K3: '时效-准确平衡',
  K4: '风险沟通表达',
  K5: '伦理与安全边界',
  K6: '反谣与纠偏',
  K7: '公共行动指引',
  K8: '沟通闭环管理',
};

const TRAINING_S_STATE_LABELS: Record<string, string> = {
  credibility: '公信力',
  accuracy: '报道准确性',
  public_panic: '公众恐慌度',
  source_safety: '线人与来源安全',
  editor_trust: '编辑部信任',
  actionability: '行动指引有效性',
};

const resolveTrainingMetricLabel = (code: string): string => {
  const normalizedCode = String(code ?? '').trim();
  if (!normalizedCode) return '指标';
  return TRAINING_K_SKILL_LABELS[normalizedCode] ?? TRAINING_S_STATE_LABELS[normalizedCode] ?? normalizedCode;
};

const formatSignedDelta = (value: number): string => {
  const normalized = Number.isFinite(value) ? value : 0;
  const fixed = Math.abs(normalized).toFixed(2);
  return `${normalized >= 0 ? '+' : '-'}${fixed}`;
};

const buildRoundImpactText = (
  evaluation: { skillDelta: Record<string, number>; stateDelta: Record<string, number> } | null | undefined
): string | null => {
  if (!evaluation) return null;

  const metricChanges = [
    ...Object.entries(evaluation.skillDelta ?? {}).map(([code, delta]) => ({ code, delta: Number(delta) })),
    ...Object.entries(evaluation.stateDelta ?? {}).map(([code, delta]) => ({ code, delta: Number(delta) })),
  ]
    .filter((item) => Number.isFinite(item.delta))
    .filter((item) => Math.abs(item.delta) > IMPACT_DELTA_EPSILON)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
    .slice(0, 3);

  if (metricChanges.length === 0) {
    return '本轮评估：暂无显著 K/S 波动，总部正在持续监测态势。';
  }

  return `本轮评估：${metricChanges
    .map((item) => `${resolveTrainingMetricLabel(item.code)}${item.delta > 0 ? '增加' : '减少'}（${formatSignedDelta(item.delta)}）`)
    .join('，')}`;
};

const buildScenePlaceholderText = ({
  hasSession,
  bootstrapStatus,
  sceneImageStatus,
}: {
  hasSession: boolean;
  bootstrapStatus: string;
  sceneImageStatus: string;
}): string => {
  if (!hasSession) {
    if (bootstrapStatus === 'restoring') {
      return '会话恢复中...';
    }
    return '会话未就绪...';
  }
  if (sceneImageStatus === 'pending' || sceneImageStatus === 'running') {
    return '';
  }
  return '';
};

function Training() {
  const [searchParams] = useSearchParams();
  const explicitSessionId = normalizeTrainingSessionId(searchParams.get('sessionId'));
  const flow = useTrainingMvpFlow(explicitSessionId);
  const {
    bootstrapStatus,
    bootstrapErrorMessage,
    roundStatus,
    roundErrorMessage,
    noticeMessage,
    dismissNotice,
    retryRestore,
    restoreNextScenarioFailed,
    retryRestoreNextScenario,
    retrySceneImage,
    sessionView,
    hasResumeTarget,
    sceneImageStatus,
    sceneImageUrl,
    sceneImageErrorMessage,
    selectedOptionId,
    submitOption,
    pendingNextScenario,
    commitPendingNextScenario,
  } = flow;

  const hasInsightEntry = flow.insightSessionId !== null;
  const hasSession = Boolean(sessionView);
  const currentScenario = sessionView?.currentScenario ?? null;
  const latestOutcome = flow.latestOutcome;
  const { isFadingOut, isFadingIn } = useSceneFadeTransition(currentScenario?.id ?? null);
  const {
    showMajorTransition,
    majorTransitionTitle,
    majorTransitionAct,
    dismissMajorTransition,
  } = useTrainingMajorSceneTransition(
    sessionView?.sessionId ?? null,
    currentScenario,
    Boolean(sessionView?.isCompleted)
  );
  const options = currentScenario?.options ?? [];
  const isSubmitting = roundStatus === 'submitting';
  const optionDisabled = !hasSession || isSubmitting || Boolean(sessionView?.isCompleted);
  const showCompletionNotice = Boolean(sessionView?.isCompleted);
  const waitingInProgress =
    isSubmitting ||
    bootstrapStatus === 'restoring' ||
    pendingNextScenario !== null ||
    sceneImageStatus === 'pending' ||
    sceneImageStatus === 'running';
  const placeholderText = buildScenePlaceholderText({ hasSession, bootstrapStatus, sceneImageStatus });
  const hasSceneImageWarning = !sceneImageUrl && sceneImageStatus === 'failed';
  const [sceneAssetFailed, setSceneAssetFailed] = useState(false);
  const [sceneAssetLoaded, setSceneAssetLoaded] = useState(false);
  const normalizedSceneImageUrl = useMemo(() => (sceneImageUrl ? String(sceneImageUrl).trim() : ''), [sceneImageUrl]);
  const isRelativeStaticUrl = normalizedSceneImageUrl.startsWith('/static/');
  const showStaticAssetWarning = Boolean(sceneAssetFailed) && Boolean(normalizedSceneImageUrl);
  const staticAssetContractWarning = useMemo(
    () => getStaticAssetContractWarning(normalizedSceneImageUrl),
    [normalizedSceneImageUrl]
  );
  const showChoiceBand = !showCompletionNotice && options.length > 0;
  const [topImpactMessage, setTopImpactMessage] = useState<string | null>(null);
  const lastImpactRoundKeyRef = useRef<string | null>(null);
  const showTopStatusPopup = hasSession && !showCompletionNotice && (Boolean(topImpactMessage) || waitingInProgress);
  const topStatusLabel = topImpactMessage ? '本轮影响' : '报社信息栏';
  const topStatusMainText = topImpactMessage ?? '正在将情报送回总部，等待总部发布新任务';
  // 独白/选项只在场景图真正渲染完成后出现，避免文字先于画面闪出。
  const canRevealNarrationAndChoices = showChoiceBand && sceneAssetLoaded;
  const [postImageUiReady, setPostImageUiReady] = useState(false);

  useEffect(() => {
    if (!canRevealNarrationAndChoices) {
      setPostImageUiReady(false);
      return;
    }
    setPostImageUiReady(false);
    const timer = window.setTimeout(() => {
      setPostImageUiReady(true);
    }, POST_SCENE_IMAGE_UI_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [canRevealNarrationAndChoices, currentScenario?.id, normalizedSceneImageUrl]);

  useEffect(() => {
    setSceneAssetLoaded(false);
    setSceneAssetFailed(false);
  }, [currentScenario?.id, normalizedSceneImageUrl]);

  const showChoiceOverlay = canRevealNarrationAndChoices && postImageUiReady;

  // ---------------------------------------------------------------------------
  // Task 7.1: Story script payload + narrative phase engine
  // ---------------------------------------------------------------------------
  const storyScriptPayload = flow.storyScriptPayload;

  // Fallback narration text (brief + mission) used when ScriptNarrative is unavailable
  const fallbackNarrationText = useMemo(() => {
    if (!currentScenario) return '';
    const brief = String(currentScenario.brief ?? '').trim();
    const mission = String(currentScenario.mission ?? '').trim();
    const rawNarrationText = brief && mission ? `${brief}\n\n任务：${mission}` : brief || mission || '';
    return filterTrainingNarrationText(rawNarrationText);
  }, [currentScenario]);

  const choiceTaskPreviewText = useMemo(() => {
    if (!currentScenario) return '';
    const brief = filterTrainingNarrationText(String(currentScenario.brief ?? '').trim());
    const missionRaw = String(currentScenario.mission ?? '')
      .trim()
      .replace(/^任务[:：]\s*/, '');
    const mission = filterTrainingNarrationText(missionRaw);
    const segments: string[] = [];
    if (brief) {
      segments.push(brief);
    }
    if (mission) {
      segments.push(`任务：${mission}`);
    }
    return segments.join('\n\n').trim();
  }, [currentScenario]);

  const handlePhaseComplete = useCallback(() => {
    // Phase completion is handled by the engine's internal state transitions.
    // When consequence phase completes (auto-advance or click), the engine moves
    // to bridge/progress. We use the phase state to drive rendering below.
  }, []);

  const phaseEngine = useNarrativePhaseEngine({
    scenario: currentScenario,
    storyScriptPayload,
    latestOutcome,
    onPhaseComplete: handlePhaseComplete,
  });

  const { state: phaseState, advance: phaseAdvance } = phaseEngine;
  const currentPhase = phaseState.phase;

  useEffect(() => {
    if (!pendingNextScenario) return;
    if (currentPhase !== 'progress') return;
    commitPendingNextScenario();
  }, [commitPendingNextScenario, currentPhase, pendingNextScenario]);

  useEffect(() => {
    if (!latestOutcome || !sessionView?.sessionId || showCompletionNotice) return;
    const roundNo = Number(latestOutcome.roundNo);
    if (!Number.isFinite(roundNo)) return;

    const roundKey = `${sessionView.sessionId}:${roundNo}`;
    if (lastImpactRoundKeyRef.current === roundKey) return;
    lastImpactRoundKeyRef.current = roundKey;

    const impactMessage = buildRoundImpactText(latestOutcome.evaluation);
    if (!impactMessage) return;

    setTopImpactMessage(impactMessage);
    const timer = window.setTimeout(() => {
      setTopImpactMessage((current) => (current === impactMessage ? null : current));
    }, IMPACT_POPUP_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, [latestOutcome, sessionView?.sessionId, showCompletionNotice]);

  // ---------------------------------------------------------------------------
  // Task 7.2: Phase 1 (monologue) typewriter
  // ---------------------------------------------------------------------------
  const isMonologuePhase = currentPhase === 'monologue';
  const currentMonologueRawSegment =
    isMonologuePhase && phaseState.monologueSegments.length > 0
      ? (phaseState.monologueSegments[phaseState.currentSegmentIndex] ?? '')
      : '';
  const currentMonologueSegment = useMemo(
    () => filterTrainingNarrationText(currentMonologueRawSegment),
    [currentMonologueRawSegment]
  );

  const typewriterActive = isMonologuePhase && showChoiceOverlay && currentMonologueSegment !== '';
  const {
    displayedText: typewriterText,
    isDone: typewriterDone,
    skip: skipTypewriter,
  } = useTypewriter(typewriterActive ? currentMonologueSegment : '', {
    charIntervalMs: 32,
    autoStart: typewriterActive,
  });

  // Click on monologue: if typewriter in progress 鈫?complete segment; if done 鈫?advance to next segment/phase
  const handleMonologueClick = () => {
    if (!typewriterDone) {
      skipTypewriter();
    } else {
      phaseAdvance();
    }
  };

  useEffect(() => {
    if (!showChoiceOverlay || currentPhase !== 'monologue') return;
    if (!currentMonologueRawSegment) return;
    if (currentMonologueSegment !== '') return;
    phaseAdvance();
  }, [showChoiceOverlay, currentPhase, currentMonologueRawSegment, currentMonologueSegment, phaseAdvance]);

  const currentDialogueLine =
    currentPhase === 'dialogue' ? (phaseState.dialogueLines[phaseState.currentDialogueIndex] ?? null) : null;
  const currentDialogueSpeaker = currentDialogueLine?.speaker ?? '';
  const currentDialogueContent = useMemo(
    () => filterTrainingNarrationText(currentDialogueLine?.content ?? ''),
    [currentDialogueLine?.content]
  );

  useEffect(() => {
    if (!showChoiceOverlay || currentPhase !== 'dialogue') return;
    if (!currentDialogueLine) return;
    if (currentDialogueContent !== '') return;
    phaseAdvance();
  }, [showChoiceOverlay, currentPhase, currentDialogueLine, currentDialogueContent, phaseAdvance]);

  const filteredDecisionPrompt = useMemo(
    () => filterTrainingNarrationText(phaseState.decisionPrompt),
    [phaseState.decisionPrompt]
  );

  // ---------------------------------------------------------------------------
  // Task 7.3: Phase 4 narrative labels from options_narrative
  // ---------------------------------------------------------------------------
  const narrativeLabels = useMemo<Record<string, string>>(() => {
    if (!currentScenario || !storyScriptPayload) return {};
    try {
      const narrative = resolveNarrativeForScenario(storyScriptPayload, currentScenario.id);
      if (!narrative?.options_narrative) return {};
      const labels: Record<string, string> = {};
      for (const [optionId, item] of Object.entries(narrative.options_narrative)) {
        if (item?.narrative_label) {
          labels[optionId] = item.narrative_label;
        }
      }
      return labels;
    } catch {
      return {};
    }
  }, [currentScenario, storyScriptPayload]);

  // ---------------------------------------------------------------------------
  // Task 7.4: Phase 5 consequence — handle click to advance
  // ---------------------------------------------------------------------------
  const handleConsequenceClick = useCallback(() => {
    phaseAdvance();
  }, [phaseAdvance]);

  // ---------------------------------------------------------------------------
  // Determine what to render in the overlay based on phase
  // ---------------------------------------------------------------------------
  // When phase engine starts at 'choice' (no narrative available), fall back to
  // the legacy choiceStage state machine for the narration text.
  const engineStartedAtChoice = currentPhase === 'choice' && phaseState.monologueSegments.length === 0;

  // Legacy choiceStage for fallback narration (when no ScriptNarrative)
  const narrationText = fallbackNarrationText;
  const [choiceStage, setChoiceStage] = useState<'narration' | 'choices'>(() =>
    narrationText ? 'narration' : 'choices'
  );
  const [showChoiceTaskPreview, setShowChoiceTaskPreview] = useState(false);

  // Legacy typewriter for fallback narration path
  const legacyTypewriterActive = engineStartedAtChoice && choiceStage === 'narration' && showChoiceOverlay;
  const {
    displayedText: legacyTypewriterText,
    isDone: legacyTypewriterDone,
    skip: skipLegacyTypewriter,
  } = useTypewriter(legacyTypewriterActive ? narrationText : '', {
    charIntervalMs: 32,
    autoStart: legacyTypewriterActive,
  });

  const handleLegacyNarrationClick = () => {
    if (!legacyTypewriterDone) {
      skipLegacyTypewriter();
    } else {
      setChoiceStage('choices');
    }
  };

  useEffect(() => {
    if (!engineStartedAtChoice || !showChoiceOverlay) return;
    if (!narrationText) {
      setChoiceStage('choices');
      return;
    }
    setChoiceStage('narration');
    const timer = window.setTimeout(() => setChoiceStage('choices'), AUTO_REVEAL_CHOICES_IDLE_MS);
    return () => window.clearTimeout(timer);
  }, [currentScenario?.id, narrationText, showChoiceOverlay, engineStartedAtChoice]);

  useEffect(() => {
    if (!legacyTypewriterDone || choiceStage !== 'narration') return;
    const timer = window.setTimeout(() => setChoiceStage('choices'), AUTO_REVEAL_CHOICES_IDLE_MS);
    return () => window.clearTimeout(timer);
  }, [legacyTypewriterDone, choiceStage]);

  useEffect(() => {
    setShowChoiceTaskPreview(false);
  }, [currentScenario?.id, currentPhase]);

  const handleSelectOption = useCallback(
    (optionId: string) => {
      void submitOption(optionId);
    },
    [submitOption]
  );

  if (!sessionView && !hasInsightEntry) {
    return <Navigate to={hasResumeTarget ? ROUTES.TRAINING_LANDING : ROUTES.TRAINING_MAINHOME} replace />;
  }

  if (showCompletionNotice) {
    if (sessionView?.sessionId) {
      return <Navigate to={buildTrainingCompletionRoute(sessionView.sessionId)} replace />;
    }
    return <Navigate to={ROUTES.TRAINING_MAINHOME} replace />;
  }

  return (
    <div className="training-page training-page--simplified">
      {showTopStatusPopup ? (
        <div className="training-simplified__top-status" role="status" aria-live="polite">
          <span className="training-simplified__top-status-label">{topStatusLabel}</span>
          <span className="training-simplified__top-status-body">
            <span className="training-simplified__top-status-dot" aria-hidden="true" />
            <span className="training-simplified__top-status-texts">
              <span className="training-simplified__top-status-main">{topStatusMainText}</span>
            </span>
          </span>
        </div>
      ) : null}
      {showMajorTransition && !showCompletionNotice ? (
        <SceneTransition
          sceneName={majorTransitionTitle}
          actNumber={majorTransitionAct}
          tone="training"
          bridgeSummary={phaseState.bridgeSummary || null}
          onComplete={dismissMajorTransition}
        />
      ) : null}
      <section className="training-simplified" aria-live="polite">
        <div className={[
          'training-simplified__scene-frame',
          isFadingOut ? 'training-simplified__scene-frame--fade-out' : '',
          isFadingIn ? 'training-simplified__scene-frame--fade-in' : '',
        ].filter(Boolean).join(' ')}>
          <StaticAssetImage
            imageUrl={sceneImageUrl}
            alt={currentScenario?.title ? `${currentScenario.title} 场景图` : '训练场景图'}
            imageClassName="training-simplified__scene-image"
            placeholderClassName="training-simplified__scene-placeholder"
            placeholder={placeholderText}
            preservePreviousImageWhileLoading
            onLoad={() => {
              setSceneAssetLoaded(true);
            }}
            onError={() => {
              setSceneAssetLoaded(false);
              setSceneAssetFailed(true);
              trackFrontendTelemetry({
                domain: 'training',
                event: 'training.scene_image.asset_error' as any,
                status: 'failed',
                metadata: {
                  url: sceneImageUrl,
                  isRelativeStaticUrl,
                  staticAssetOrigin: (import.meta.env.VITE_STATIC_ASSET_ORIGIN ?? '').trim() || null,
                },
              });
            }}
          />
          {showChoiceOverlay ? (
            <div className="training-simplified__choice-overlay">
              {/* Task 7.2: Phase 1 — monologue typewriter */}
              {currentPhase === 'monologue' && currentMonologueSegment ? (
                <button
                  type="button"
                  className="training-simplified__narration training-narrative-phase"
                  onClick={handleMonologueClick}
                  disabled={optionDisabled}
                >
                  <span className="training-simplified__narration-label training-narrative-phase__label">独白</span>
                  <span className="training-simplified__narration-text training-narrative-phase__segment">
                    {typewriterText}
                    {!typewriterDone ? (
                      <span className="training-simplified__narration-cursor" aria-hidden="true" />
                    ) : null}
                  </span>
                  <span className="training-simplified__narration-hint">
                    {typewriterDone ? '点击继续' : '点击跳过'}
                  </span>
                </button>
              ) : null}

              {/* Task 7.2: Phase 2 — dialogue line-by-line */}
              {currentPhase === 'dialogue' && currentDialogueLine && currentDialogueContent ? (
                <button
                  type="button"
                  className="training-simplified__narration training-narrative-phase"
                  onClick={phaseAdvance}
                  disabled={optionDisabled}
                >
                  <span className="training-simplified__narration-label training-narrative-phase__label">
                    {currentDialogueSpeaker}
                  </span>
                  <span className="training-simplified__narration-text training-narrative-phase__dialogue-line">
                    {currentDialogueContent}
                  </span>
                  <span className="training-simplified__narration-hint">点击继续</span>
                </button>
              ) : null}

              {/* Task 7.2: Phase 3 — decision pause */}
              {currentPhase === 'decision_pause' ? (
                <button
                  type="button"
                  className="training-simplified__narration training-narrative-phase"
                  onClick={phaseAdvance}
                  disabled={optionDisabled}
                >
                  <span className="training-simplified__narration-text training-narrative-phase__decision-prompt">
                    {filteredDecisionPrompt || '点击继续'}
                  </span>
                </button>
              ) : null}

              {/* Phase 4 — choices (with narrative labels from Task 7.3) */}
              {currentPhase === 'choice' && !engineStartedAtChoice ? (
                showChoiceTaskPreview && choiceTaskPreviewText ? (
                  <button
                    type="button"
                    className="training-simplified__narration training-narrative-phase"
                    onClick={() => setShowChoiceTaskPreview(false)}
                    disabled={optionDisabled}
                  >
                    <span className="training-simplified__narration-label training-narrative-phase__label">
                      任务说明
                    </span>
                    <span className="training-simplified__narration-text training-narrative-phase__segment">
                      {choiceTaskPreviewText}
                    </span>
                    <span className="training-simplified__narration-hint">点击返回选项</span>
                  </button>
                ) : (
                  <TrainingCinematicChoiceBand
                    options={options}
                    selectedOptionId={selectedOptionId}
                    disabled={optionDisabled}
                    narrativeLabels={narrativeLabels}
                    onViewTask={
                      choiceTaskPreviewText ? () => setShowChoiceTaskPreview(true) : undefined
                    }
                    viewTaskLabel="查看任务"
                    onSelectOption={handleSelectOption}
                  />
                )
              ) : null}

              {/* Task 7.4: Phase 5 — consequence narrative */}
              {currentPhase === 'consequence' && phaseState.consequenceLines.length > 0 ? (
                <NarrativeConsequenceView
                  lines={phaseState.consequenceLines}
                  onClick={handleConsequenceClick}
                />
              ) : null}

              {/* Fallback: legacy narration + choice band when no ScriptNarrative */}
              {engineStartedAtChoice ? (
                <>
                  {choiceStage === 'narration' && narrationText ? (
                    <button
                      type="button"
                      className="training-simplified__narration"
                      onClick={handleLegacyNarrationClick}
                      disabled={optionDisabled}
                    >
                      <span className="training-simplified__narration-label">当前节点</span>
                      <span className="training-simplified__narration-text">
                        {legacyTypewriterText}
                        {!legacyTypewriterDone ? (
                          <span className="training-simplified__narration-cursor" aria-hidden="true" />
                        ) : null}
                      </span>
                      <span className="training-simplified__narration-hint">
                        {legacyTypewriterDone ? '点击任意位置继续' : '点击跳过'}
                      </span>
                    </button>
                  ) : null}
                  {choiceStage === 'choices' ? (
                    showChoiceTaskPreview && choiceTaskPreviewText ? (
                      <button
                        type="button"
                        className="training-simplified__narration training-narrative-phase"
                        onClick={() => setShowChoiceTaskPreview(false)}
                        disabled={optionDisabled}
                      >
                        <span className="training-simplified__narration-label training-narrative-phase__label">
                          任务说明
                        </span>
                        <span className="training-simplified__narration-text training-narrative-phase__segment">
                          {choiceTaskPreviewText}
                        </span>
                        <span className="training-simplified__narration-hint">点击返回选项</span>
                      </button>
                    ) : (
                      <TrainingCinematicChoiceBand
                        options={options}
                        selectedOptionId={selectedOptionId}
                        disabled={optionDisabled}
                        narrativeLabels={narrativeLabels}
                        onViewTask={
                          choiceTaskPreviewText ? () => setShowChoiceTaskPreview(true) : undefined
                        }
                        viewTaskLabel="查看任务"
                        onSelectOption={handleSelectOption}
                      />
                    )
                  ) : null}
                </>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="training-simplified__feedback-stack">
          {bootstrapErrorMessage ? (
            <div className="training-simplified__feedback training-simplified__feedback--error">
              <span>{bootstrapErrorMessage}</span>
              <button type="button" onClick={() => void retryRestore()}>
                重试恢复
              </button>
            </div>
          ) : null}
          {restoreNextScenarioFailed && !currentScenario ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>会话已恢复，但加载下一场景失败。你可以重试加载场景。</span>
              <button type="button" onClick={() => void retryRestoreNextScenario()}>
                重试加载场景
              </button>
            </div>
          ) : null}
          {roundErrorMessage ? (
            <div className="training-simplified__feedback training-simplified__feedback--error">
              <span>{roundErrorMessage}</span>
            </div>
          ) : null}
          {hasSceneImageWarning ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>{sceneImageErrorMessage ?? '场景图生成失败，不影响当前回合选择。'}</span>
              <button type="button" onClick={() => void retrySceneImage()}>
                {'\u91cd\u65b0\u751f\u6210\u573a\u666f\u56fe'}
              </button>
            </div>
          ) : null}
          {showStaticAssetWarning ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>
                场景图已生成，但静态资源不可达。请确认当前前端入口具备 `/static` 代理，或配置
                `VITE_STATIC_ASSET_ORIGIN` 指向训练后端。
              </span>
            </div>
          ) : null}
          {staticAssetContractWarning ? (
            <div className="training-simplified__feedback training-simplified__feedback--warning">
              <span>{staticAssetContractWarning}</span>
            </div>
          ) : null}
          {noticeMessage ? (
            <div className="training-simplified__feedback training-simplified__feedback--notice">
              <span>{noticeMessage}</span>
              <button type="button" onClick={() => dismissNotice()}>
                关闭
              </button>
            </div>
          ) : null}
        </div>

        <div className="training-simplified__options">
          {options.length > 0 ? null : (
            <div className="training-simplified__empty-options">当前场景暂无可选项</div>
          )}
        </div>
      </section>
    </div>
  );
}

export default Training;


