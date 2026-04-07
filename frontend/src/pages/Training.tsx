import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import SceneTransition from '@/components/SceneTransition';
import StaticAssetImage from '@/components/StaticAssetImage';
import NarrativeConsequenceView from '@/components/training/NarrativeConsequenceView';
import ProgressBadge from '@/components/training/ProgressBadge';
import TrainingCinematicChoiceBand from '@/components/training/TrainingCinematicChoiceBand';
import { buildTrainingReportRoute, ROUTES } from '@/config/routes';
import { useTrainingMvpFlow } from '@/flows/useTrainingMvpFlow';
import { useNarrativePhaseEngine } from '@/hooks/useNarrativePhaseEngine';
import { useTrainingMajorSceneTransition } from '@/hooks/useTrainingMajorSceneTransition';
import { normalizeTrainingSessionId } from '@/hooks/useTrainingSessionReadTarget';
import { useSceneFadeTransition } from '@/hooks/useSceneFadeTransition';
import { useStoryScriptPayload } from '@/hooks/useStoryScriptPayload';
import { useTypewriter } from '@/hooks/useTypewriter';
import { getStaticAssetContractWarning } from '@/services/assetUrl';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { resolveNarrativeForScenario } from '@/utils/trainingSession';
import './Training.css';

/** 场景图 URL 就绪后延迟再展示独白/选项，给大图解码与绘制留出时间 */
const POST_SCENE_IMAGE_UI_DELAY_MS = 0;
const AUTO_REVEAL_CHOICES_IDLE_MS = 20000;

const readEndingNarrativeText = (ending: Record<string, unknown> | null | undefined): string | null => {
  if (!ending || typeof ending !== 'object') return null;

  const directCandidates = ['ending_text', 'endingText', 'description', 'explanation', 'title'] as const;
  for (const key of directCandidates) {
    const value = ending[key];
    if (typeof value === 'string' && value.trim() !== '') {
      return value.trim();
    }
  }

  const nestedCandidates = ['article', 'story', 'narrative'] as const;
  for (const key of nestedCandidates) {
    const value = ending[key];
    if (!value || typeof value !== 'object') continue;
    const record = value as Record<string, unknown>;
    for (const subKey of ['text', 'content', 'summary', 'description'] as const) {
      const subValue = record[subKey];
      if (typeof subValue === 'string' && subValue.trim() !== '') {
        return subValue.trim();
      }
    }
  }

  return null;
};

const resolveEndingTypeLabel = (ending: Record<string, unknown> | null | undefined): string | null => {
  if (!ending || typeof ending !== 'object') return null;
  const raw = ending.type ?? ending.ending_type;
  if (typeof raw === 'string' && raw.trim() !== '') return raw.trim();
  if (typeof raw === 'number' && Number.isFinite(raw)) return String(raw);
  return null;
};

const sanitizeCompletionNarrativeText = (text: string): string => {
  return text
    .split('\n')
    .filter((line) => {
      const trimmed = line.trim();
      if (!trimmed) return true;
      return !/^综合能力评分/.test(trimmed) && !/^综合加权分/.test(trimmed);
    })
    .join('\n')
    .trim();
};

const buildEndingFallbackNarrative = (endingType: string | null): string => {
  const normalizedType = (endingType ?? '').toLowerCase();
  let lead = '任务暂告一段落。你在高压信息环境下完成了取舍与发布，后续影响仍在持续扩散。';

  if (normalizedType.includes('excellent') || normalizedType.includes('卓越')) {
    lead = '你在保护线索人物与公共利益之间取得了稳健平衡，报道克制且可信。';
  } else if (normalizedType.includes('recovery') || normalizedType.includes('修复')) {
    lead = '你在不利局面下及时修正策略，降低了扩散风险并守住了关键底线。';
  } else if (normalizedType.includes('steady') || normalizedType.includes('稳健')) {
    lead = '你维持了稳定推进，信息发布节奏与风险控制保持在可接受区间。';
  } else if (normalizedType.includes('costly') || normalizedType.includes('代价')) {
    lead = '你完成了核心目标，但关键节点的代价偏高，后续影响仍需持续跟进。';
  } else if (normalizedType.includes('fail') || normalizedType.includes('失败')) {
    lead = '关键节点处理出现失衡，线索保护与信息发布目标都受到明显冲击。';
  }

  return `${lead}\n\n点击下方“查看可视化评估报告”，查看完整能力雷达与回合轨迹。`;
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
    return '加载中..';
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
    completionReport,
    selectedOptionId,
    submitOption,
    pendingNextScenario,
    commitPendingNextScenario,
  } = flow;

  const hasInsightEntry = flow.insightSessionId !== null;
  const hasSession = Boolean(sessionView);
  const currentScenario = sessionView?.currentScenario ?? null;
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
  const showLoadingMask = isSubmitting || bootstrapStatus === 'restoring';
  const placeholderText = buildScenePlaceholderText({ hasSession, bootstrapStatus, sceneImageStatus });
  const isSceneImageLoading = sceneImageStatus === 'pending' || sceneImageStatus === 'running';
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
  const { payload: storyScriptPayload } = useStoryScriptPayload(sessionView?.sessionId);

  // Fallback narration text (brief + mission) used when ScriptNarrative is unavailable
  const fallbackNarrationText = useMemo(() => {
    if (!currentScenario) return '';
    const brief = String(currentScenario.brief ?? '').trim();
    const mission = String(currentScenario.mission ?? '').trim();
    if (brief && mission) return `${brief}\n\n任务：${mission}`;
    return brief || mission || '';
  }, [currentScenario]);

  const handlePhaseComplete = useCallback(() => {
    // Phase completion is handled by the engine's internal state transitions.
    // When consequence phase completes (auto-advance or click), the engine moves
    // to bridge/progress. We use the phase state to drive rendering below.
  }, []);

  const phaseEngine = useNarrativePhaseEngine({
    scenario: currentScenario,
    storyScriptPayload,
    latestOutcome: flow.latestOutcome,
    onPhaseComplete: handlePhaseComplete,
  });

  const { state: phaseState, advance: phaseAdvance } = phaseEngine;
  const currentPhase = phaseState.phase;

  useEffect(() => {
    if (!pendingNextScenario) return;
    if (currentPhase !== 'progress') return;
    commitPendingNextScenario();
  }, [commitPendingNextScenario, currentPhase, pendingNextScenario]);

  // ---------------------------------------------------------------------------
  // Task 7.2: Phase 1 (monologue) typewriter
  // ---------------------------------------------------------------------------
  const isMonologuePhase = currentPhase === 'monologue';
  const currentMonologueSegment =
    isMonologuePhase && phaseState.monologueSegments.length > 0
      ? (phaseState.monologueSegments[phaseState.currentSegmentIndex] ?? '')
      : '';

  const typewriterActive = isMonologuePhase && showChoiceOverlay && currentMonologueSegment !== '';
  const {
    displayedText: typewriterText,
    isDone: typewriterDone,
    skip: skipTypewriter,
  } = useTypewriter(typewriterActive ? currentMonologueSegment : '', {
    charIntervalMs: 32,
    autoStart: typewriterActive,
  });

  // Click on monologue: if typewriter in progress → complete segment; if done → advance to next segment/phase
  const handleMonologueClick = () => {
    if (!typewriterDone) {
      skipTypewriter();
    } else {
      phaseAdvance();
    }
  };

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

  const completionEndingPayload = useMemo<Record<string, unknown> | null>(() => {
    if (completionReport?.ending && typeof completionReport.ending === 'object') {
      return completionReport.ending;
    }
    if (flow.latestOutcome?.ending && typeof flow.latestOutcome.ending === 'object') {
      return flow.latestOutcome.ending;
    }
    return null;
  }, [completionReport?.ending, flow.latestOutcome?.ending]);

  const completionStoryText = useMemo(() => {
    if (!showCompletionNotice) return '';

    const endingText = readEndingNarrativeText(completionEndingPayload);
    const endingType = resolveEndingTypeLabel(completionEndingPayload);

    if (endingText) {
      const sanitizedEndingText = sanitizeCompletionNarrativeText(endingText);
      if (sanitizedEndingText) {
        if (endingType && !sanitizedEndingText.includes(endingType)) {
          return `[${endingType}]\n${sanitizedEndingText}`;
        }
        return sanitizedEndingText;
      }
    }

    return buildEndingFallbackNarrative(endingType);
  }, [completionEndingPayload, showCompletionNotice]);

  const {
    displayedText: completionStoryDisplayedText,
    isDone: completionStoryDone,
  } = useTypewriter(showCompletionNotice ? completionStoryText : '', {
    charIntervalMs: 28,
    autoStart: showCompletionNotice,
  });

  // Progress info for ProgressBadge (Task 7.6)
  const roundNo = sessionView?.roundNo ?? null;
  const totalRounds = sessionView?.totalRounds ?? null;

  if (!sessionView && !hasInsightEntry) {
    return <Navigate to={hasResumeTarget ? ROUTES.TRAINING_LANDING : ROUTES.TRAINING_MAINHOME} replace />;
  }

  return (
    <div className="training-page training-page--simplified">
      {showMajorTransition && !showCompletionNotice ? (
        <SceneTransition
          sceneName={majorTransitionTitle}
          actNumber={majorTransitionAct}
          tone="training"
          bridgeSummary={phaseState.bridgeSummary || null}
          onComplete={dismissMajorTransition}
        />
      ) : null}
      {/* Task 7.6: ProgressBadge */}
      {roundNo != null && !showCompletionNotice ? (
        <div className="training-simplified__progress-badge-wrapper">
          <ProgressBadge roundNo={roundNo} totalRounds={totalRounds} />
        </div>
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
            placeholderClassName={
              isSceneImageLoading
                ? 'training-simplified__scene-placeholder training-simplified__scene-placeholder--loading'
                : 'training-simplified__scene-placeholder'
            }
            placeholder={placeholderText}
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
          {showLoadingMask ? <div className="training-simplified__scene-mask">训练流程处理中...</div> : null}
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
              {currentPhase === 'dialogue' && phaseState.dialogueLines.length > 0 ? (
                <button
                  type="button"
                  className="training-simplified__narration training-narrative-phase"
                  onClick={phaseAdvance}
                  disabled={optionDisabled}
                >
                  <span className="training-simplified__narration-label training-narrative-phase__label">
                    {phaseState.dialogueLines[phaseState.currentDialogueIndex]?.speaker ?? ''}
                  </span>
                  <span className="training-simplified__narration-text training-narrative-phase__dialogue-line">
                    {phaseState.dialogueLines[phaseState.currentDialogueIndex]?.content ?? ''}
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
                    {phaseState.decisionPrompt}
                  </span>
                </button>
              ) : null}

              {/* Phase 4 — choices (with narrative labels from Task 7.3) */}
              {currentPhase === 'choice' && !engineStartedAtChoice ? (
                <TrainingCinematicChoiceBand
                  options={options}
                  selectedOptionId={selectedOptionId}
                  disabled={optionDisabled}
                  narrativeLabels={narrativeLabels}
                  onSelectOption={(optionId) => {
                    void submitOption(optionId);
                  }}
                />
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
                    <TrainingCinematicChoiceBand
                      options={options}
                      selectedOptionId={selectedOptionId}
                      disabled={optionDisabled}
                      narrativeLabels={narrativeLabels}
                      onSelectOption={(optionId) => {
                        void submitOption(optionId);
                      }}
                    />
                  ) : null}
                </>
              ) : null}
            </div>
          ) : null}
          {showCompletionNotice && completionStoryText ? (
            <div className="training-simplified__completion-story" aria-live="polite">
              <p className="training-simplified__completion-story-text">
                {completionStoryDisplayedText}
                {!completionStoryDone ? (
                  <span className="training-simplified__narration-cursor" aria-hidden="true" />
                ) : null}
              </p>
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

        {showCompletionNotice ? (
          sessionView?.sessionId ? (
            <Link
              className="training-simplified__report-link"
              to={buildTrainingReportRoute(sessionView.sessionId)}
            >
              查看可视化评估报告
            </Link>
          ) : null
        ) : (
          <div className="training-simplified__options">
            {options.length > 0 ? null : (
              <div className="training-simplified__empty-options">当前场景暂无可选项</div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

export default Training;
