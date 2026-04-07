import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTrainingCompletionReportFlow } from '@/hooks/useTrainingCompletionReportFlow';
import { useTrainingRoundRunner } from '@/hooks/useTrainingRoundRunner';
import { useTrainingSceneImageFlow } from '@/hooks/useTrainingSceneImageFlow';
import { useTrainingSessionBootstrap } from '@/hooks/useTrainingSessionBootstrap';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import {
  buildTrainingSceneImageMediaTaskCreateParams,
  createTrainingMediaTask,
  getNextTrainingScenario,
} from '@/services/trainingApi';
import { readTrainingPrewarmPlan } from '@/storage/trainingSessionCache';
import {
  buildBlockedTrainingSessionView,
  buildCompletedTrainingSessionView,
  buildTrainingSessionViewFromInit,
  buildTrainingSessionViewFromNext,
  buildTrainingSessionViewFromSummary,
  useTrainingSessionViewModel,
  type TrainingSessionViewState,
} from '@/hooks/useTrainingSessionViewModel';
import type {
  TrainingConsequenceEvent,
  TrainingEvaluation,
  TrainingMode,
  TrainingPlayerProfileInput,
  TrainingRoundSubmitMediaTaskSummary,
  TrainingRoundDecisionContext,
  TrainingScenario,
  TrainingScenarioNextResult,
} from '@/types/training';

const DEFAULT_TRAINING_USER_ID = 'frontend-training-user';
const LEGACY_TRAINING_PRESET_IDS = new Set([
  'correspondent-female',
  'correspondent-male',
  'frontline-photographer',
  'radio-operator',
]);

export interface TrainingFormDraft {
  portraitPresetId: string;
  characterId: string;
  playerName: string;
  playerGender: string;
  playerIdentity: string;
  playerAge: string;
}

export interface TrainingRoundOutcomeView {
  roundNo: number;
  evaluation: TrainingEvaluation;
  consequenceEvents: TrainingConsequenceEvent[];
  decisionContext: TrainingRoundDecisionContext | null;
  mediaTasks: TrainingRoundSubmitMediaTaskSummary[];
  ending: Record<string, unknown> | null;
  isCompleted: boolean;
}

const TRAINING_MODE_LABELS: Record<TrainingMode, string> = {
  guided: '\u5f15\u5bfc\u8bad\u7ec3',
  'self-paced': '\u81ea\u4e3b\u8bad\u7ec3',
  adaptive: '\u81ea\u9002\u5e94\u8bad\u7ec3',
};

const trimToNull = (value: string): string | null => {
  const normalized = value.trim();
  return normalized === '' ? null : normalized;
};

const normalizeCharacterIdInput = (value: string): string | null => {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }

  if (!/^\d+$/.test(normalized)) {
    return null;
  }

  const parsed = Number.parseInt(normalized, 10);
  return Number.isInteger(parsed) && parsed > 0 ? String(parsed) : null;
};

const buildPlayerProfile = (draft: TrainingFormDraft): TrainingPlayerProfileInput | null => {
  const parsedAge = trimToNull(draft.playerAge);
  const age = parsedAge ? Number.parseInt(parsedAge, 10) : null;

  const profile: TrainingPlayerProfileInput = {
    name: trimToNull(draft.playerName),
    gender: trimToNull(draft.playerGender),
    identity: trimToNull(draft.playerIdentity),
    age: Number.isInteger(age) && age && age > 0 ? age : null,
  };

  return Object.values(profile).every((value) => value === null) ? null : profile;
};

const resolveSelectedOptionLabel = (
  scenario: TrainingScenario | null,
  selectedOptionId: string | null
): string | null => {
  if (!scenario || !selectedOptionId) {
    return null;
  }

  const selectedOption = scenario.options.find((option) => option.id === selectedOptionId);
  return selectedOption?.label?.trim() || null;
};

export function useTrainingMvpFlow(
  explicitSessionId: string | null = null,
  options: { suppressAutoRestoreSessionView?: boolean } = {}
) {
  const suppressAutoRestoreSessionView = Boolean(options.suppressAutoRestoreSessionView);
  const bootstrap = useTrainingSessionBootstrap();
  const roundRunner = useTrainingRoundRunner({
    restoreSession: bootstrap.restoreSession,
  });

  const [trainingMode, setTrainingMode] = useState<TrainingMode>('guided');
  const [formDraft, setFormDraft] = useState<TrainingFormDraft>({
    portraitPresetId: '',
    characterId: '',
    playerName: '',
    playerGender: '',
    playerIdentity: '',
    playerAge: '',
  });
  const [sessionView, setSessionView] = useState<TrainingSessionViewState | null>(null);
  const [restoreNextScenarioFailed, setRestoreNextScenarioFailed] = useState(false);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [latestOutcome, setLatestOutcome] = useState<TrainingRoundOutcomeView | null>(null);
  const [pendingNextScenario, setPendingNextScenario] = useState<TrainingScenarioNextResult | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const autoRestoreSessionIdRef = useRef<string | null>(null);
  const rejectedPreferredCharacterIdRef = useRef<string | null>(null);
  const startTrainingInFlightRef = useRef<Promise<boolean> | null>(null);
  const sessionViewModel = useTrainingSessionViewModel({
    explicitSessionId,
    sessionView,
    activeSession: bootstrap.activeSession,
    resumeTarget: bootstrap.resumeTarget,
  });
  const {
    sceneImageStatus,
    sceneImageUrl,
    sceneImageErrorMessage,
    retrySceneImage,
    resetSceneImageFlow,
  } = useTrainingSceneImageFlow(sessionView);
  const {
    completionReportStatus,
    completionReport,
    completionReportErrorMessage,
    resetCompletionReportFlow,
  } = useTrainingCompletionReportFlow(sessionView);

  const restoreSessionView = useCallback(
    async (sessionId?: string | null) => {
      const restoreIdentity = sessionViewModel.resolveRestoreIdentity(sessionId);
      const summaryResult = await bootstrap.restoreSession(restoreIdentity);

      if (!summaryResult) {
        return null;
      }
      setPendingNextScenario(null);

      const summaryView = buildTrainingSessionViewFromSummary(summaryResult);

      // Some summaries may not include a resumable scenario even though the session can continue.
      // In that case, proactively fetch the next scenario so the training page can render and
      // the scene-image flow has inputs to start.
      if (!summaryView.currentScenario && summaryResult.canResume && !summaryResult.isCompleted) {
        try {
          const nextScenarioResult = await getNextTrainingScenario({ sessionId: summaryResult.sessionId });
          const nextView = buildTrainingSessionViewFromNext(summaryView, nextScenarioResult);
          setRestoreNextScenarioFailed(false);
          setSessionView(nextView);
        } catch {
          setRestoreNextScenarioFailed(true);
          setSessionView(summaryView);
        }
        return summaryResult;
      }

      setRestoreNextScenarioFailed(false);
      setSessionView(summaryView);
      return summaryResult;
    },
    [bootstrap, sessionViewModel]
  );

  const retryRestoreNextScenario = useCallback(async () => {
    const sessionId = sessionView?.sessionId ?? bootstrap.activeSession?.sessionId ?? null;
    if (!sessionId) return;
    if (sessionView?.currentScenario) {
      setRestoreNextScenarioFailed(false);
      return;
    }
    try {
      const nextScenarioResult = await getNextTrainingScenario({ sessionId });
      setSessionView((current) =>
        current ? buildTrainingSessionViewFromNext(current, nextScenarioResult) : current
      );
      setRestoreNextScenarioFailed(false);
    } catch {
      setRestoreNextScenarioFailed(true);
    }
  }, [bootstrap.activeSession?.sessionId, sessionView, setSessionView]);

  const restoreCandidate = useMemo(() => {
    if (suppressAutoRestoreSessionView) {
      return null;
    }
    if (sessionView) {
      return null;
    }

    // Priority: explicit(autoRestore) > activeSession > resumeTarget (only when explicitly provided by bootstrap).
    const explicitSessionId = sessionViewModel.autoRestoreSessionId ?? null;
    if (explicitSessionId) {
      return { source: 'explicit', sessionId: explicitSessionId };
    }

    if (bootstrap.status !== 'ready') {
      return null;
    }

    const activeSessionId = bootstrap.activeSession?.sessionId ?? null;
    if (activeSessionId) {
      return { source: 'active', sessionId: activeSessionId };
    }

    const resumeTargetSessionId = bootstrap.resumeTarget?.sessionId ?? null;
    if (resumeTargetSessionId) {
      return { source: 'resumeTarget', sessionId: resumeTargetSessionId };
    }

    const sessionIdHint = sessionViewModel.currentSessionId ?? null;
    if (sessionIdHint) {
      return { source: 'hint', sessionId: sessionIdHint };
    }

    return null;
  }, [
    bootstrap.activeSession?.sessionId,
    bootstrap.resumeTarget?.sessionId,
    bootstrap.status,
    sessionView,
    sessionViewModel.autoRestoreSessionId,
    sessionViewModel.currentSessionId,
    suppressAutoRestoreSessionView,
  ]);

  const restoreInFlightRef = useRef<string | null>(null);

  useEffect(() => {
    if (!restoreCandidate) {
      autoRestoreSessionIdRef.current = null;
      restoreInFlightRef.current = null;
      return;
    }

    const restoreKey = `${restoreCandidate.source}:${restoreCandidate.sessionId}`;
    if (autoRestoreSessionIdRef.current === restoreKey) {
      return;
    }
    if (restoreInFlightRef.current === restoreKey) {
      return;
    }

    autoRestoreSessionIdRef.current = restoreKey;
    restoreInFlightRef.current = restoreKey;
    void restoreSessionView(restoreCandidate.sessionId).finally(() => {
      if (restoreInFlightRef.current === restoreKey) {
        restoreInFlightRef.current = null;
      }
    });
  }, [restoreCandidate, restoreSessionView]);

  useEffect(() => {
    if (sessionView) {
      return;
    }

    const timerId = window.setTimeout(() => {
      if (sessionViewModel.preferredTrainingMode) {
        setTrainingMode(sessionViewModel.preferredTrainingMode);
      }

      const preferredCharacterId = sessionViewModel.preferredCharacterId;
      if (!preferredCharacterId) {
        return;
      }

      const normalizedPreferredCharacterId = normalizeCharacterIdInput(preferredCharacterId);
      if (normalizedPreferredCharacterId) {
        setFormDraft((current) => ({
          ...current,
          characterId: normalizedPreferredCharacterId,
        }));
        return;
      }

      const normalizedLegacyPresetId = preferredCharacterId.trim();
      if (LEGACY_TRAINING_PRESET_IDS.has(normalizedLegacyPresetId)) {
        setFormDraft((current) => ({
          ...current,
          portraitPresetId: normalizedLegacyPresetId,
        }));
        return;
      }

      if (
        normalizedLegacyPresetId !== '' &&
        rejectedPreferredCharacterIdRef.current !== normalizedLegacyPresetId
      ) {
        rejectedPreferredCharacterIdRef.current = normalizedLegacyPresetId;
        trackFrontendTelemetry({
          domain: 'training',
          event: 'training.form.hydration',
          status: 'failed',
          metadata: {
            reason: 'invalid_preferred_character_id',
            preferredCharacterId: normalizedLegacyPresetId,
          },
        });
      }
    }, 0);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [sessionView, sessionViewModel.preferredCharacterId, sessionViewModel.preferredTrainingMode]);

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      setSelectedOptionId(null);
    }, 0);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [sessionView?.currentScenario?.id, sessionView?.sessionId]);

  const updateFormDraft = useCallback((field: keyof TrainingFormDraft, value: string) => {
    setFormDraft((current) => {
      const next: TrainingFormDraft = {
        ...current,
        [field]: value,
      };

      const shouldInvalidateCharacterId =
        field !== 'characterId' &&
        ['portraitPresetId', 'playerName', 'playerGender', 'playerIdentity', 'playerAge'].includes(
          field
        ) &&
        current[field] !== value;

      if (shouldInvalidateCharacterId && current.characterId.trim() !== '') {
        next.characterId = '';
      }

      return next;
    });
  }, []);

  const clearWorkspace = useCallback(() => {
    bootstrap.clearTrainingSession();
    roundRunner.dismissError();
    setSessionView(null);
    setLatestOutcome(null);
    setPendingNextScenario(null);
    setSelectedOptionId(null);
    resetSceneImageFlow();
    resetCompletionReportFlow();
    setNoticeMessage(null);
    autoRestoreSessionIdRef.current = null;
  }, [bootstrap, resetCompletionReportFlow, resetSceneImageFlow, roundRunner]);

  const prewarmAllSceneImages = useCallback(
    async (characterId: string) => {
      const plan = readTrainingPrewarmPlan();
      const sessionId = bootstrap.activeSession?.sessionId ?? null;
      if (!plan || !sessionId || plan.sessionId !== sessionId) {
        return;
      }
      const normalizedCharacterId = normalizeCharacterIdInput(characterId);
      if (!normalizedCharacterId) {
        return;
      }
      const cid = Number.parseInt(normalizedCharacterId, 10);
      if (!Number.isInteger(cid) || cid < 1) {
        return;
      }
      const roundNo = Math.max((bootstrap.activeSession?.roundNo ?? 0) + 1, 1);
      const stubScenario = (outline: { id: string; title: string }): TrainingScenario => ({
        id: outline.id,
        title: outline.title,
        eraDate: '',
        location: '',
        brief: '',
        mission: '',
        decisionFocus: '',
        targetSkills: [],
        riskTags: [],
        options: [],
        completionHint: '',
        recommendation: null,
      });
      const staggerMs = 120;
      for (const outline of plan.scenarios) {
        try {
          await createTrainingMediaTask(
            buildTrainingSceneImageMediaTaskCreateParams({
              sessionId,
              roundNo,
              scenario: stubScenario(outline),
              attemptNo: 0,
              generateStorylineSeries: false,
              characterId: cid,
            })
          );
        } catch (error: unknown) {
          trackFrontendTelemetry({
            domain: 'training',
            event: 'training.scene_image.prewarm',
            status: 'failed',
            metadata: { sessionId, scenarioId: outline.id },
            cause: error,
          });
        }
        await new Promise((r) => {
          window.setTimeout(r, staggerMs);
        });
      }
    },
    [
      bootstrap.activeSession?.roundNo,
      bootstrap.activeSession?.sessionId,
    ]
  );

  const startTraining = useCallback(async () => {
    if (startTrainingInFlightRef.current) {
      return startTrainingInFlightRef.current;
    }

    const runStartTraining = async (): Promise<boolean> => {
    roundRunner.dismissError();
    bootstrap.dismissError();
    setNoticeMessage(null);

    if (sessionView && bootstrap.activeSession?.sessionId === sessionView.sessionId) {
      return true;
    }

    const normalizedCharacterId = normalizeCharacterIdInput(formDraft.characterId);
    if (!normalizedCharacterId) {
      setNoticeMessage('\u8bf7\u5148\u751f\u6210\u5e76\u786e\u8ba4\u5f62\u8c61\u56fe\uff0c\u518d\u542f\u52a8\u8bad\u7ec3\u3002');
      return false;
    }

    const existingSessionId = bootstrap.activeSession?.sessionId ?? null;
    if (existingSessionId) {
      const summaryResult = await bootstrap.finalizePendingTrainingSession(normalizedCharacterId);
      if (!summaryResult) {
        return false;
      }
      let nextView = buildTrainingSessionViewFromSummary(summaryResult);
      if (!nextView.currentScenario && summaryResult.canResume && !summaryResult.isCompleted) {
        try {
          const nextScenarioResult = await getNextTrainingScenario({
            sessionId: summaryResult.sessionId,
          });
          nextView = buildTrainingSessionViewFromNext(nextView, nextScenarioResult);
          setRestoreNextScenarioFailed(false);
        } catch {
          setRestoreNextScenarioFailed(true);
        }
      } else {
        setRestoreNextScenarioFailed(false);
      }
      setLatestOutcome(null);
      setPendingNextScenario(null);
      resetSceneImageFlow();
      resetCompletionReportFlow();
      setSessionView(nextView);
      return true;
    }

    const initResult = await bootstrap.startTrainingSession({
      userId: DEFAULT_TRAINING_USER_ID,
      characterId: normalizedCharacterId,
      trainingMode,
      playerProfile: buildPlayerProfile(formDraft),
    });

    if (!initResult) {
      return false;
    }

    setLatestOutcome(null);
    setPendingNextScenario(null);
    resetSceneImageFlow();
    resetCompletionReportFlow();
    setSessionView(buildTrainingSessionViewFromInit(initResult));
    return true;
    };

    const inFlightPromise = runStartTraining();
    startTrainingInFlightRef.current = inFlightPromise;
    try {
      return await inFlightPromise;
    } finally {
      if (startTrainingInFlightRef.current === inFlightPromise) {
        startTrainingInFlightRef.current = null;
      }
    }
  }, [
    bootstrap,
    formDraft,
    resetCompletionReportFlow,
    resetSceneImageFlow,
    roundRunner,
    sessionView,
    trainingMode,
  ]);

  const retryRestore = useCallback(async () => {
    roundRunner.dismissError();
    bootstrap.dismissError();
    setNoticeMessage(null);
    return restoreSessionView(sessionViewModel.currentSessionId ?? bootstrap.resumeTarget?.sessionId);
  }, [bootstrap, restoreSessionView, roundRunner, sessionViewModel.currentSessionId]);

  const submitRoundWithOption = useCallback(async (overrideOptionId?: string | null) => {
    if (!sessionView?.currentScenario) {
      return;
    }

    const selectedOptionForSubmit =
      typeof overrideOptionId === 'string' && overrideOptionId.trim() !== ''
        ? overrideOptionId.trim()
        : selectedOptionId;
    const selectedOptionLabel = resolveSelectedOptionLabel(
      sessionView.currentScenario,
      selectedOptionForSubmit
    );
    const userInput = selectedOptionLabel || '';

    if (!userInput) {
      setNoticeMessage('\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a\u5267\u60c5\u9009\u9879\uff0c\u518d\u63d0\u4ea4\u672c\u8f6e\u8bad\u7ec3\u3002');
      return;
    }

    bootstrap.dismissError();
    roundRunner.dismissError();
    setNoticeMessage(null);
    setPendingNextScenario(null);

    const transition = await roundRunner.submitRound({
      scenarioId: sessionView.currentScenario.id,
      userInput,
      selectedOption: selectedOptionForSubmit,
    });

    if (!transition) {
      return;
    }

    if (transition.submitResult) {
      const submitMediaTasks = transition.submitResult.mediaTasks ?? [];
      setLatestOutcome({
        roundNo: transition.submitResult.roundNo,
        evaluation: transition.submitResult.evaluation,
        consequenceEvents: transition.submitResult.consequenceEvents,
        decisionContext: transition.submitResult.decisionContext,
        mediaTasks: submitMediaTasks,
        ending: transition.submitResult.ending,
        isCompleted: transition.submitResult.isCompleted,
      });
    } else {
      setLatestOutcome(null);
    }

    if (transition.summaryResult) {
      setPendingNextScenario(null);
      setSessionView(buildTrainingSessionViewFromSummary(transition.summaryResult));

      if (transition.recoveryReason === 'duplicate') {
        setNoticeMessage('\u68c0\u6d4b\u5230\u91cd\u590d\u63d0\u4ea4\uff0c\u9875\u9762\u5df2\u6309\u670d\u52a1\u7aef\u8bad\u7ec3\u8fdb\u5ea6\u6062\u590d\u3002');
      } else if (transition.recoveryReason === 'completed') {
        setNoticeMessage('\u8bad\u7ec3\u5df2\u5b8c\u6210\uff0c\u9875\u9762\u5df2\u6309\u670d\u52a1\u7aef\u5b8c\u6210\u6001\u6062\u590d\u3002');
      } else if (transition.recoveryReason === 'scenario-mismatch') {
        setNoticeMessage('\u63d0\u4ea4\u573a\u666f\u5df2\u53d8\u66f4\uff0c\u5df2\u6309\u670d\u52a1\u7aef\u6700\u65b0\u4f1a\u8bdd\u72b6\u6001\u6062\u590d\u3002');
      } else if (transition.recoveryReason === 'next-fetch-failed') {
        setNoticeMessage('\u4e0b\u4e00\u8bad\u7ec3\u573a\u666f\u52a0\u8f7d\u5931\u8d25\uff0c\u5df2\u6309\u670d\u52a1\u7aef\u72b6\u6001\u6062\u590d\u5f53\u524d\u4f1a\u8bdd\u3002');
      }

      return;
    }

    if (transition.nextScenarioResult) {
      setPendingNextScenario(transition.nextScenarioResult);
      return;
    }

    if (transition.submitResult?.isCompleted) {
      setPendingNextScenario(null);
      setSessionView(buildCompletedTrainingSessionView(sessionView, transition.submitResult));
      setNoticeMessage('\u672c\u6b21\u8bad\u7ec3\u5df2\u5b8c\u6210\u3002');
      return;
    }

    if (transition.submitResult) {
      setPendingNextScenario(null);
      setSessionView(buildBlockedTrainingSessionView(sessionView, transition.submitResult));
      setNoticeMessage('\u56de\u5408\u5df2\u63d0\u4ea4\uff0c\u8bf7\u91cd\u8bd5\u6062\u590d\u5f53\u524d\u8bad\u7ec3\u4f1a\u8bdd\u3002');
    }
  }, [bootstrap, roundRunner, selectedOptionId, sessionView]);

  const commitPendingNextScenario = useCallback(() => {
    if (!pendingNextScenario) {
      return false;
    }
    setSessionView((current) =>
      current ? buildTrainingSessionViewFromNext(current, pendingNextScenario) : current
    );
    setPendingNextScenario(null);
    return true;
  }, [pendingNextScenario]);

  const submitCurrentRound = useCallback(async () => {
    await submitRoundWithOption();
  }, [submitRoundWithOption]);

  const submitOption = useCallback(
    async (optionId: string) => {
      const normalizedOptionId = optionId.trim();
      if (!normalizedOptionId) {
        return;
      }
      setSelectedOptionId(normalizedOptionId);
      await submitRoundWithOption(normalizedOptionId);
    },
    [submitRoundWithOption]
  );

  const submissionPreview = useMemo(
    () => resolveSelectedOptionLabel(sessionView?.currentScenario ?? null, selectedOptionId),
    [selectedOptionId, sessionView?.currentScenario]
  );

  return {
    bootstrapStatus: bootstrap.status,
    bootstrapErrorMessage: bootstrap.errorMessage,
    roundStatus: roundRunner.status,
    roundErrorMessage: roundRunner.errorMessage,
    noticeMessage,
    dismissNotice: () => setNoticeMessage(null),
    hasResumeTarget: bootstrap.hasResumeTarget,
    resumeTarget: bootstrap.resumeTarget,
    trainingMode,
    trainingModeLabel: TRAINING_MODE_LABELS[trainingMode],
    setTrainingMode,
    formDraft,
    updateFormDraft,
    startTraining,
    prewarmAllSceneImages,
    retryRestore,
    restoreNextScenarioFailed,
    retryRestoreNextScenario,
    retrySceneImage,
    clearWorkspace,
    sessionView,
    insightSessionId: sessionViewModel.currentSessionId,
    latestOutcome,
    pendingNextScenario,
    sceneImageStatus,
    sceneImageUrl,
    sceneImageErrorMessage,
    completionReportStatus,
    completionReport,
    completionReportErrorMessage,
    selectedOptionId,
    selectOption: setSelectedOptionId,
    submissionPreview,
    canStartTraining: bootstrap.status !== 'starting',
    canSubmitRound:
      Boolean(sessionView?.currentScenario) &&
      roundRunner.status !== 'submitting' &&
      selectedOptionId !== null,
    submitCurrentRound,
    submitOption,
    commitPendingNextScenario,
  };
}
