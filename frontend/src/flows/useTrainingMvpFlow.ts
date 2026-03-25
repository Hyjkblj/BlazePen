import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTrainingMediaTaskFeed } from '@/hooks/useTrainingMediaTaskFeed';
import { useTrainingRoundRunner } from '@/hooks/useTrainingRoundRunner';
import { useTrainingSessionBootstrap } from '@/hooks/useTrainingSessionBootstrap';
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
  TrainingRoundSubmitMediaTaskInput,
  TrainingRoundSubmitMediaTaskSummary,
  TrainingRoundDecisionContext,
  TrainingScenario,
} from '@/types/training';

const DEFAULT_TRAINING_USER_ID = 'frontend-training-user';

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

export interface TrainingRoundMediaTaskDraft {
  enableImage: boolean;
  enableTts: boolean;
  enableText: boolean;
  prompt: string;
}

const TRAINING_MODE_LABELS: Record<TrainingMode, string> = {
  guided: '\u5f15\u5bfc\u8bad\u7ec3',
  'self-paced': '\u81ea\u4e3b\u8bad\u7ec3',
  adaptive: '\u81ea\u9002\u5e94\u8bad\u7ec3',
};

const TRAINING_PORTRAIT_PRESET_IDS = new Set([
  'correspondent-female',
  'correspondent-male',
  'frontline-photographer',
  'radio-operator',
]);

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

const buildRoundSubmitMediaTasks = ({
  draft,
  scenarioId,
  userInput,
}: {
  draft: TrainingRoundMediaTaskDraft;
  scenarioId: string;
  userInput: string;
}): TrainingRoundSubmitMediaTaskInput[] => {
  const sharedPrompt = trimToNull(draft.prompt) ?? userInput;
  const mediaTasks: TrainingRoundSubmitMediaTaskInput[] = [];

  if (draft.enableImage) {
    mediaTasks.push({
      taskType: 'image',
      payload: {
        prompt: sharedPrompt,
        scenario_id: scenarioId,
      },
      maxRetries: 1,
    });
  }

  if (draft.enableTts) {
    mediaTasks.push({
      taskType: 'tts',
      payload: {
        text: userInput,
        prompt: sharedPrompt,
        scenario_id: scenarioId,
      },
      maxRetries: 1,
    });
  }

  if (draft.enableText) {
    mediaTasks.push({
      taskType: 'text',
      payload: {
        prompt: sharedPrompt,
        scenario_id: scenarioId,
      },
      maxRetries: 1,
    });
  }

  return mediaTasks;
};

export function useTrainingMvpFlow(explicitSessionId: string | null = null) {
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
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [responseInput, setResponseInput] = useState('');
  const [mediaTaskDraft, setMediaTaskDraft] = useState<TrainingRoundMediaTaskDraft>({
    enableImage: false,
    enableTts: false,
    enableText: false,
    prompt: '',
  });
  const [latestOutcome, setLatestOutcome] = useState<TrainingRoundOutcomeView | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const autoRestoreSessionIdRef = useRef<string | null>(null);
  const sessionViewModel = useTrainingSessionViewModel({
    explicitSessionId,
    sessionView,
    activeSession: bootstrap.activeSession,
    resumeTarget: bootstrap.resumeTarget,
  });
  const mediaTaskFeed = useTrainingMediaTaskFeed({
    sessionId: sessionView?.sessionId ?? null,
    roundNo: latestOutcome?.roundNo ?? null,
    seedTasks: latestOutcome?.mediaTasks,
  });

  const restoreSessionView = useCallback(
    async (sessionId?: string | null) => {
      const restoreIdentity = sessionViewModel.resolveRestoreIdentity(sessionId);
      const summaryResult = await bootstrap.restoreSession(restoreIdentity);

      if (!summaryResult) {
        return null;
      }

      setSessionView(buildTrainingSessionViewFromSummary(summaryResult));
      return summaryResult;
    },
    [bootstrap.restoreSession, sessionViewModel]
  );

  useEffect(() => {
    if (sessionView) {
      return;
    }

    const resumableSessionId = sessionViewModel.autoRestoreSessionId;
    if (!resumableSessionId) {
      autoRestoreSessionIdRef.current = null;
      return;
    }

    if (autoRestoreSessionIdRef.current === resumableSessionId) {
      return;
    }

    autoRestoreSessionIdRef.current = resumableSessionId;
    void restoreSessionView(resumableSessionId);
  }, [restoreSessionView, sessionView, sessionViewModel.autoRestoreSessionId]);

  useEffect(() => {
    if (sessionView) {
      return;
    }

    if (sessionViewModel.preferredTrainingMode) {
      setTrainingMode(sessionViewModel.preferredTrainingMode);
    }

    const preferredCharacterId = sessionViewModel.preferredCharacterId;
    if (preferredCharacterId) {
      const normalizedPreferredCharacterId = normalizeCharacterIdInput(preferredCharacterId);
      if (normalizedPreferredCharacterId) {
        setFormDraft((current) => ({
          ...current,
          characterId: normalizedPreferredCharacterId,
        }));
      } else {
        const legacyPresetId = preferredCharacterId.trim();
        if (TRAINING_PORTRAIT_PRESET_IDS.has(legacyPresetId)) {
          setFormDraft((current) => ({
            ...current,
            portraitPresetId: legacyPresetId,
          }));
        }
      }
    }
  }, [sessionView, sessionViewModel.preferredCharacterId, sessionViewModel.preferredTrainingMode]);

  useEffect(() => {
    setSelectedOptionId(null);
    setResponseInput('');
  }, [sessionView?.currentScenario?.id, sessionView?.sessionId]);

  const updateFormDraft = useCallback((field: keyof TrainingFormDraft, value: string) => {
    setFormDraft((current) => ({
      ...current,
      [field]: value,
    }));
  }, []);

  const updateMediaTaskDraft = useCallback(
    <K extends keyof TrainingRoundMediaTaskDraft>(
      field: K,
      value: TrainingRoundMediaTaskDraft[K]
    ) => {
      setMediaTaskDraft((current) => ({
        ...current,
        [field]: value,
      }));
    },
    []
  );

  const clearWorkspace = useCallback(() => {
    bootstrap.clearTrainingSession();
    roundRunner.dismissError();
    setSessionView(null);
    setLatestOutcome(null);
    setSelectedOptionId(null);
    setResponseInput('');
    setMediaTaskDraft({
      enableImage: false,
      enableTts: false,
      enableText: false,
      prompt: '',
    });
    setNoticeMessage(null);
    autoRestoreSessionIdRef.current = null;
  }, [bootstrap, roundRunner]);

  const startTraining = useCallback(async () => {
    roundRunner.dismissError();
    bootstrap.dismissError();
    setNoticeMessage(null);

    const initResult = await bootstrap.startTrainingSession({
      userId: DEFAULT_TRAINING_USER_ID,
      characterId: normalizeCharacterIdInput(formDraft.characterId),
      trainingMode,
      playerProfile: buildPlayerProfile(formDraft),
    });

    if (!initResult) {
      return false;
    }

    setLatestOutcome(null);
    setSessionView(buildTrainingSessionViewFromInit(initResult));
    return true;
  }, [bootstrap, formDraft, roundRunner, trainingMode]);

  const retryRestore = useCallback(async () => {
    roundRunner.dismissError();
    bootstrap.dismissError();
    setNoticeMessage(null);
    return restoreSessionView(sessionViewModel.currentSessionId ?? bootstrap.resumeTarget?.sessionId);
  }, [bootstrap, restoreSessionView, roundRunner, sessionViewModel.currentSessionId]);

  const submitCurrentRound = useCallback(async () => {
    if (!sessionView?.currentScenario) {
      return;
    }

    const selectedOptionLabel = resolveSelectedOptionLabel(sessionView.currentScenario, selectedOptionId);
    const normalizedResponse = responseInput.trim();
    const userInput = normalizedResponse || selectedOptionLabel || '';

    if (!userInput) {
      setNoticeMessage('\u8bf7\u9009\u62e9\u4e00\u4e2a\u8bad\u7ec3\u9009\u9879\u6216\u586b\u5199\u672c\u8f6e\u64cd\u4f5c\u8bf4\u660e\u3002');
      return;
    }

    bootstrap.dismissError();
    roundRunner.dismissError();
    setNoticeMessage(null);

    const mediaTasks = buildRoundSubmitMediaTasks({
      draft: mediaTaskDraft,
      scenarioId: sessionView.currentScenario.id,
      userInput,
    });

    const transition = await roundRunner.submitRound({
      scenarioId: sessionView.currentScenario.id,
      userInput,
      selectedOption: selectedOptionId,
      mediaTasks,
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
      if (submitMediaTasks.length > 0) {
        setNoticeMessage(
          `本轮已创建 ${submitMediaTasks.length} 个媒体任务，正在后台处理中。`
        );
      }
    } else {
      setLatestOutcome(null);
    }

    if (transition.summaryResult) {
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
      setSessionView(buildTrainingSessionViewFromNext(sessionView, transition.nextScenarioResult));
      return;
    }

    if (transition.submitResult?.isCompleted) {
      setSessionView(buildCompletedTrainingSessionView(sessionView, transition.submitResult));
      setNoticeMessage('\u672c\u6b21\u8bad\u7ec3\u5df2\u5b8c\u6210\u3002');
      return;
    }

    if (transition.submitResult) {
      setSessionView(buildBlockedTrainingSessionView(sessionView, transition.submitResult));
      setNoticeMessage('\u56de\u5408\u5df2\u63d0\u4ea4\uff0c\u8bf7\u91cd\u8bd5\u6062\u590d\u5f53\u524d\u8bad\u7ec3\u4f1a\u8bdd\u3002');
    }
  }, [bootstrap, mediaTaskDraft, responseInput, roundRunner, selectedOptionId, sessionView]);

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
    mediaTaskDraft,
    updateMediaTaskDraft,
    startTraining,
    retryRestore,
    clearWorkspace,
    sessionView,
    insightSessionId: sessionViewModel.currentSessionId,
    latestOutcome,
    selectedOptionId,
    selectOption: setSelectedOptionId,
    responseInput,
    setResponseInput,
    submissionPreview,
    mediaTasks: mediaTaskFeed.tasks,
    mediaTaskFeedStatus: mediaTaskFeed.status,
    mediaTaskFeedErrorMessage: mediaTaskFeed.errorMessage,
    isPollingMediaTasks: mediaTaskFeed.isPolling,
    refreshMediaTasks: () => {
      void mediaTaskFeed.refresh();
    },
    canStartTraining: bootstrap.status !== 'starting',
    canSubmitRound:
      Boolean(sessionView?.currentScenario) &&
      roundRunner.status !== 'submitting' &&
      (responseInput.trim() !== '' || submissionPreview !== null),
    submitCurrentRound,
  };
}
