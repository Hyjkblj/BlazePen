import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTrainingRoundRunner } from '@/hooks/useTrainingRoundRunner';
import { useTrainingSessionBootstrap } from '@/hooks/useTrainingSessionBootstrap';
import type {
  TrainingConsequenceEvent,
  TrainingEvaluation,
  TrainingMode,
  TrainingPlayerProfileInput,
  TrainingProgressAnchor,
  TrainingRoundDecisionContext,
  TrainingRoundSubmitResult,
  TrainingRuntimeState,
  TrainingScenario,
  TrainingScenarioNextResult,
  TrainingSessionSummaryResult,
} from '@/types/training';

const DEFAULT_TRAINING_USER_ID = 'frontend-training-user';

export interface TrainingFormDraft {
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
  ending: Record<string, unknown> | null;
  isCompleted: boolean;
}

export interface TrainingSessionViewState {
  sessionId: string;
  trainingMode: TrainingMode;
  characterId: string | null;
  status: string;
  roundNo: number;
  totalRounds: number | null;
  runtimeState: TrainingRuntimeState;
  currentScenario: TrainingScenario | null;
  scenarioCandidates: TrainingScenario[];
  progressAnchor: TrainingProgressAnchor | null;
  canResume: boolean;
  isCompleted: boolean;
  createdAt: string | null;
  updatedAt: string | null;
  endTime: string | null;
}

interface TrainingRestoreIdentity {
  sessionId: string | null;
  trainingMode: TrainingMode | null;
  characterId: string | null;
}

const TRAINING_MODE_LABELS: Record<TrainingMode, string> = {
  guided: '引导训练',
  'self-paced': '自主训练',
  adaptive: '自适应训练',
};

const deriveProgressAnchor = (
  totalRounds: number | null,
  roundNo: number,
  isCompleted: boolean
): TrainingProgressAnchor | null => {
  if (!totalRounds || totalRounds <= 0) {
    return null;
  }

  const completedRounds = isCompleted ? totalRounds : Math.min(roundNo, totalRounds);
  const remainingRounds = Math.max(totalRounds - completedRounds, 0);

  return {
    roundNo,
    totalRounds,
    completedRounds,
    remainingRounds,
    progressPercent: (completedRounds / totalRounds) * 100,
    nextRoundNo: remainingRounds > 0 ? roundNo + 1 : null,
  };
};

const buildSessionViewFromSummary = (
  summaryResult: TrainingSessionSummaryResult,
  characterId: string | null
): TrainingSessionViewState => ({
  sessionId: summaryResult.sessionId,
  trainingMode: summaryResult.trainingMode,
  characterId,
  status: summaryResult.status,
  roundNo: summaryResult.roundNo,
  totalRounds: summaryResult.totalRounds,
  runtimeState: summaryResult.runtimeState,
  currentScenario: summaryResult.resumableScenario,
  scenarioCandidates: summaryResult.scenarioCandidates,
  progressAnchor: summaryResult.progressAnchor,
  canResume: summaryResult.canResume,
  isCompleted: summaryResult.isCompleted,
  createdAt: summaryResult.createdAt,
  updatedAt: summaryResult.updatedAt,
  endTime: summaryResult.endTime,
});

const buildSessionViewFromInit = (
  sessionResult: {
    sessionId: string;
    trainingMode: TrainingMode;
    status: string;
    roundNo: number;
    runtimeState: TrainingRuntimeState;
    nextScenario: TrainingScenario | null;
    scenarioCandidates: TrainingScenario[];
  },
  characterId: string | null
): TrainingSessionViewState => ({
  sessionId: sessionResult.sessionId,
  trainingMode: sessionResult.trainingMode,
  characterId,
  status: sessionResult.status,
  roundNo: sessionResult.roundNo,
  totalRounds: null,
  runtimeState: sessionResult.runtimeState,
  currentScenario: sessionResult.nextScenario,
  scenarioCandidates: sessionResult.scenarioCandidates,
  progressAnchor: null,
  canResume: sessionResult.nextScenario !== null,
  isCompleted: false,
  createdAt: null,
  updatedAt: null,
  endTime: null,
});

const buildSessionViewFromNext = (
  currentSession: TrainingSessionViewState,
  nextScenarioResult: TrainingScenarioNextResult
): TrainingSessionViewState => ({
  ...currentSession,
  status: nextScenarioResult.status,
  roundNo: nextScenarioResult.roundNo,
  runtimeState: nextScenarioResult.runtimeState,
  currentScenario: nextScenarioResult.scenario,
  scenarioCandidates: nextScenarioResult.scenarioCandidates,
  progressAnchor: deriveProgressAnchor(currentSession.totalRounds, nextScenarioResult.roundNo, false),
  canResume: nextScenarioResult.scenario !== null,
  isCompleted: nextScenarioResult.status === 'completed',
  updatedAt: null,
});

const buildCompletedSessionView = (
  currentSession: TrainingSessionViewState,
  submitResult: TrainingRoundSubmitResult
): TrainingSessionViewState => ({
  ...currentSession,
  status: 'completed',
  roundNo: submitResult.roundNo,
  runtimeState: submitResult.runtimeState,
  currentScenario: null,
  scenarioCandidates: [],
  progressAnchor: deriveProgressAnchor(currentSession.totalRounds, submitResult.roundNo, true),
  canResume: false,
  isCompleted: true,
});

const buildBlockedSessionView = (
  currentSession: TrainingSessionViewState,
  submitResult: TrainingRoundSubmitResult
): TrainingSessionViewState => ({
  ...currentSession,
  status: 'in_progress',
  roundNo: submitResult.roundNo,
  runtimeState: submitResult.runtimeState,
  currentScenario: null,
  scenarioCandidates: [],
  progressAnchor: deriveProgressAnchor(currentSession.totalRounds, submitResult.roundNo, false),
  canResume: true,
  isCompleted: false,
});

const trimToNull = (value: string): string | null => {
  const normalized = value.trim();
  return normalized === '' ? null : normalized;
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

const resolveRestoreIdentity = ({
  sessionId,
  sessionView,
  activeSession,
  resumeTarget,
}: {
  sessionId?: string | null;
  sessionView: TrainingSessionViewState | null;
  activeSession: {
    sessionId: string;
    trainingMode: TrainingMode;
    characterId: string | null;
  } | null;
  resumeTarget: {
    sessionId: string;
    trainingMode: TrainingMode | null;
    characterId: string | null;
  } | null;
}): TrainingRestoreIdentity => {
  if (sessionId) {
    if (sessionView?.sessionId === sessionId) {
      return {
        sessionId,
        trainingMode: sessionView.trainingMode,
        characterId: sessionView.characterId,
      };
    }

    if (activeSession?.sessionId === sessionId) {
      return {
        sessionId,
        trainingMode: activeSession.trainingMode,
        characterId: activeSession.characterId,
      };
    }

    if (resumeTarget?.sessionId === sessionId) {
      return {
        sessionId,
        trainingMode: resumeTarget.trainingMode,
        characterId: resumeTarget.characterId,
      };
    }

    return {
      sessionId,
      trainingMode: null,
      characterId: null,
    };
  }

  if (activeSession?.sessionId) {
    return {
      sessionId: activeSession.sessionId,
      trainingMode: activeSession.trainingMode,
      characterId: activeSession.characterId,
    };
  }

  if (resumeTarget?.sessionId) {
    return {
      sessionId: resumeTarget.sessionId,
      trainingMode: resumeTarget.trainingMode,
      characterId: resumeTarget.characterId,
    };
  }

  return {
    sessionId: null,
    trainingMode: null,
    characterId: null,
  };
};

export function useTrainingMvpFlow() {
  const bootstrap = useTrainingSessionBootstrap();
  const roundRunner = useTrainingRoundRunner({
    restoreSession: bootstrap.restoreSession,
  });

  const [trainingMode, setTrainingMode] = useState<TrainingMode>('guided');
  const [formDraft, setFormDraft] = useState<TrainingFormDraft>({
    characterId: '',
    playerName: '',
    playerGender: '',
    playerIdentity: '',
    playerAge: '',
  });
  const [sessionView, setSessionView] = useState<TrainingSessionViewState | null>(null);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [responseInput, setResponseInput] = useState('');
  const [latestOutcome, setLatestOutcome] = useState<TrainingRoundOutcomeView | null>(null);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const autoRestoreSessionIdRef = useRef<string | null>(null);

  const restoreSessionView = useCallback(
    async (sessionId?: string | null) => {
      const restoreIdentity = resolveRestoreIdentity({
        sessionId,
        sessionView,
        activeSession: bootstrap.activeSession,
        resumeTarget: bootstrap.resumeTarget,
      });
      const summaryResult = await bootstrap.restoreSession(restoreIdentity);

      if (!summaryResult) {
        return null;
      }

      setSessionView(
        buildSessionViewFromSummary(summaryResult, restoreIdentity.characterId)
      );
      return summaryResult;
    },
    [bootstrap.activeSession, bootstrap.resumeTarget, bootstrap.restoreSession, sessionView]
  );

  useEffect(() => {
    if (sessionView) {
      return;
    }

    const resumableSessionId =
      bootstrap.activeSession?.sessionId ?? bootstrap.resumeTarget?.sessionId ?? null;
    if (!resumableSessionId) {
      autoRestoreSessionIdRef.current = null;
      return;
    }

    if (autoRestoreSessionIdRef.current === resumableSessionId) {
      return;
    }

    autoRestoreSessionIdRef.current = resumableSessionId;
    void restoreSessionView(resumableSessionId);
  }, [bootstrap.activeSession?.sessionId, bootstrap.resumeTarget?.sessionId, restoreSessionView, sessionView]);

  useEffect(() => {
    if (sessionView) {
      return;
    }

    if (bootstrap.activeSession?.trainingMode) {
      setTrainingMode(bootstrap.activeSession.trainingMode);
    } else if (bootstrap.resumeTarget?.trainingMode) {
      setTrainingMode(bootstrap.resumeTarget.trainingMode);
    }

    const preferredCharacterId =
      bootstrap.activeSession?.characterId ?? bootstrap.resumeTarget?.characterId ?? null;
    if (preferredCharacterId) {
      setFormDraft((current) => ({
        ...current,
        characterId: preferredCharacterId,
      }));
    }
  }, [
    bootstrap.activeSession?.characterId,
    bootstrap.activeSession?.trainingMode,
    bootstrap.resumeTarget?.characterId,
    bootstrap.resumeTarget?.trainingMode,
    sessionView,
  ]);

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

  const clearWorkspace = useCallback(() => {
    bootstrap.clearTrainingSession();
    roundRunner.dismissError();
    setSessionView(null);
    setLatestOutcome(null);
    setSelectedOptionId(null);
    setResponseInput('');
    setNoticeMessage(null);
    autoRestoreSessionIdRef.current = null;
  }, [bootstrap, roundRunner]);

  const startTraining = useCallback(async () => {
    roundRunner.dismissError();
    bootstrap.dismissError();
    setNoticeMessage(null);

    const initResult = await bootstrap.startTrainingSession({
      userId: DEFAULT_TRAINING_USER_ID,
      characterId: trimToNull(formDraft.characterId),
      trainingMode,
      playerProfile: buildPlayerProfile(formDraft),
    });

    if (!initResult) {
      return;
    }

    setLatestOutcome(null);
    setSessionView(buildSessionViewFromInit(initResult, trimToNull(formDraft.characterId)));
  }, [bootstrap, formDraft, roundRunner, trainingMode]);

  const retryRestore = useCallback(async () => {
    roundRunner.dismissError();
    bootstrap.dismissError();
    setNoticeMessage(null);

    const currentSessionId =
      sessionView?.sessionId ??
      bootstrap.activeSession?.sessionId ??
      bootstrap.resumeTarget?.sessionId ??
      null;

    await restoreSessionView(currentSessionId);
  }, [bootstrap, restoreSessionView, roundRunner, sessionView?.sessionId]);

  const submitCurrentRound = useCallback(async () => {
    if (!sessionView?.currentScenario) {
      return;
    }

    const selectedOptionLabel = resolveSelectedOptionLabel(sessionView.currentScenario, selectedOptionId);
    const normalizedResponse = responseInput.trim();
    const userInput = normalizedResponse || selectedOptionLabel || '';

    if (!userInput) {
      setNoticeMessage('请选择一个训练选项或填写本轮操作说明。');
      return;
    }

    bootstrap.dismissError();
    roundRunner.dismissError();
    setNoticeMessage(null);

    const transition = await roundRunner.submitRound({
      scenarioId: sessionView.currentScenario.id,
      userInput,
      selectedOption: selectedOptionId,
    });

    if (!transition) {
      return;
    }

    if (transition.submitResult) {
      setLatestOutcome({
        roundNo: transition.submitResult.roundNo,
        evaluation: transition.submitResult.evaluation,
        consequenceEvents: transition.submitResult.consequenceEvents,
        decisionContext: transition.submitResult.decisionContext,
        ending: transition.submitResult.ending,
        isCompleted: transition.submitResult.isCompleted,
      });
    } else {
      setLatestOutcome(null);
    }

    if (transition.summaryResult) {
      setSessionView(buildSessionViewFromSummary(transition.summaryResult, sessionView.characterId));

      if (transition.recoveryReason === 'duplicate') {
        setNoticeMessage('检测到重复提交，页面已按服务端训练进度恢复。');
      } else if (transition.recoveryReason === 'completed') {
        setNoticeMessage('训练已完成，页面已按服务端完成态恢复。');
      } else if (transition.recoveryReason === 'next-fetch-failed') {
        setNoticeMessage('下一训练场景加载失败，已按服务端状态恢复当前会话。');
      }

      return;
    }

    if (transition.nextScenarioResult) {
      setSessionView(buildSessionViewFromNext(sessionView, transition.nextScenarioResult));
      return;
    }

    if (transition.submitResult?.isCompleted) {
      setSessionView(buildCompletedSessionView(sessionView, transition.submitResult));
      setNoticeMessage('本次训练已完成。');
      return;
    }

    if (transition.submitResult) {
      setSessionView(buildBlockedSessionView(sessionView, transition.submitResult));
      setNoticeMessage('回合已提交，请重试恢复当前训练会话。');
    }
  }, [bootstrap, responseInput, roundRunner, selectedOptionId, sessionView]);

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
    retryRestore,
    clearWorkspace,
    sessionView,
    latestOutcome,
    selectedOptionId,
    selectOption: setSelectedOptionId,
    responseInput,
    setResponseInput,
    submissionPreview,
    canStartTraining: bootstrap.status !== 'starting',
    canSubmitRound:
      Boolean(sessionView?.currentScenario) &&
      roundRunner.status !== 'submitting' &&
      (responseInput.trim() !== '' || submissionPreview !== null),
    submitCurrentRound,
  };
}
