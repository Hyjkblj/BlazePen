import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  TrainingRoundDecisionContext,
  TrainingScenario,
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

const TRAINING_MODE_LABELS: Record<TrainingMode, string> = {
  guided: '引导训练',
  'self-paced': '自主训练',
  adaptive: '自适应训练',
};

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
  const sessionViewModel = useTrainingSessionViewModel({
    sessionView,
    activeSession: bootstrap.activeSession,
    resumeTarget: bootstrap.resumeTarget,
  });

  const restoreSessionView = useCallback(
    async (sessionId?: string | null) => {
      const restoreIdentity = sessionViewModel.resolveRestoreIdentity(sessionId);
      const summaryResult = await bootstrap.restoreSession(restoreIdentity);

      if (!summaryResult) {
        return null;
      }

      setSessionView(buildTrainingSessionViewFromSummary(summaryResult, restoreIdentity.characterId));
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
      setFormDraft((current) => ({
        ...current,
        characterId: preferredCharacterId,
      }));
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
    setSessionView(buildTrainingSessionViewFromInit(initResult, trimToNull(formDraft.characterId)));
  }, [bootstrap, formDraft, roundRunner, trainingMode]);

  const retryRestore = useCallback(async () => {
    roundRunner.dismissError();
    bootstrap.dismissError();
    setNoticeMessage(null);
    await restoreSessionView(sessionViewModel.currentSessionId);
  }, [bootstrap, restoreSessionView, roundRunner, sessionViewModel.currentSessionId]);

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
      setSessionView(
        buildTrainingSessionViewFromSummary(transition.summaryResult, sessionView.characterId)
      );

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
      setSessionView(buildTrainingSessionViewFromNext(sessionView, transition.nextScenarioResult));
      return;
    }

    if (transition.submitResult?.isCompleted) {
      setSessionView(buildCompletedTrainingSessionView(sessionView, transition.submitResult));
      setNoticeMessage('本次训练已完成。');
      return;
    }

    if (transition.submitResult) {
      setSessionView(buildBlockedTrainingSessionView(sessionView, transition.submitResult));
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
