import type { FeedbackContextValue } from '@/contexts/feedbackCore';
import type { SetActiveSessionParams } from '@/contexts/gameFlowCore';
import { trackFrontendTelemetry } from '@/services/frontendTelemetry';
import { initGame, initializeStory } from '@/services/gameApi';
import { readStoryThreadSave } from '@/storage/storySessionCache';
import type { CharacterData } from '@/types/game';
import { resolveCharacterImageUrl } from '@/utils/game';
import {
  buildInitialAssistantMessages,
  type GameInitializationPlan,
} from '@/utils/gameSession';
import { logger } from '@/utils/logger';
import type { GameSessionInitActions } from './useGameState';
import type { UseStorySessionRestoreResult } from './useStorySessionRestore';

type GameInitializationFeedback = Pick<FeedbackContextValue, 'error'>;
type SetActiveSession = (params: SetActiveSessionParams) => void;

export interface GameInitializationExecutorOptions {
  plan: GameInitializationPlan;
  actions: GameSessionInitActions;
  feedback: GameInitializationFeedback;
  characterDraft: CharacterData | null;
  clearRestoreSession: () => void;
  clearInitialGameData: () => void;
  clearActiveSession: () => void;
  setActiveSession: SetActiveSession;
  setCurrentCharacterId: (characterId: string | null) => void;
  applyStoryData: UseStorySessionRestoreResult['applyStoryData'];
  applyInitialEntryData: UseStorySessionRestoreResult['applyInitialEntryData'];
  restoreFromServerSnapshot: UseStorySessionRestoreResult['restoreFromServerSnapshot'];
  notifyLocalRestoreFallback: UseStorySessionRestoreResult['notifyLocalRestoreFallback'];
  notifyRestoreFailure: UseStorySessionRestoreResult['notifyRestoreFailure'];
}

interface SessionIdentityOptions {
  actions: Pick<GameSessionInitActions, 'setThreadId' | 'setCharacterId'>;
  setCurrentCharacterId: (characterId: string | null) => void;
}

interface SessionStateOptions extends SessionIdentityOptions {
  clearActiveSession: () => void;
}

interface RestoreFailureOptions extends SessionStateOptions {
  notifyLocalRestoreFallback: UseStorySessionRestoreResult['notifyLocalRestoreFallback'];
  notifyRestoreFailure: UseStorySessionRestoreResult['notifyRestoreFailure'];
}

const hydrateSessionIdentity = (
  { actions, setCurrentCharacterId }: SessionIdentityOptions,
  threadId: string,
  characterId: string | null
) => {
  actions.setThreadId(threadId);
  actions.setCharacterId(characterId);

  if (characterId) {
    setCurrentCharacterId(characterId);
  }
};

const enterReadonlySnapshotMode = (
  { actions, clearActiveSession, setCurrentCharacterId }: SessionStateOptions,
  characterId: string | null
) => {
  clearActiveSession();
  actions.setThreadId(null);
  actions.setCharacterId(characterId);

  if (characterId) {
    setCurrentCharacterId(characterId);
  }
};

const clearInvalidSessionState = (
  { actions, clearActiveSession }: SessionStateOptions,
  characterId: string | null
) => {
  clearActiveSession();
  actions.setThreadId(null);
  actions.setCharacterId(characterId);
};

const handleRestoreFailure = (
  {
    actions,
    clearActiveSession,
    setCurrentCharacterId,
    notifyLocalRestoreFallback,
    notifyRestoreFailure,
  }: RestoreFailureOptions,
  restoreResult: Awaited<
    ReturnType<UseStorySessionRestoreResult['restoreFromServerSnapshot']>
  >,
  characterId: string | null,
  fallbackMessage: string
) => {
  if (restoreResult.source === 'local' && restoreResult.restored) {
    enterReadonlySnapshotMode(
      { actions, clearActiveSession, setCurrentCharacterId },
      characterId
    );
    notifyLocalRestoreFallback(restoreResult.error);
    return;
  }

  clearInvalidSessionState({ actions, clearActiveSession, setCurrentCharacterId }, characterId);
  notifyRestoreFailure(restoreResult.error, fallbackMessage);
};

const executeRestoreSessionPlan = async ({
  plan,
  actions,
  clearRestoreSession,
  clearActiveSession,
  setActiveSession,
  setCurrentCharacterId,
  restoreFromServerSnapshot,
  notifyLocalRestoreFallback,
  notifyRestoreFailure,
}: Pick<
  GameInitializationExecutorOptions,
  | 'plan'
  | 'actions'
  | 'clearRestoreSession'
  | 'clearActiveSession'
  | 'setActiveSession'
  | 'setCurrentCharacterId'
  | 'restoreFromServerSnapshot'
  | 'notifyLocalRestoreFallback'
  | 'notifyRestoreFailure'
>) => {
  if (plan.kind !== 'restore-session') {
    return;
  }

  const restoreResult = await restoreFromServerSnapshot(plan.threadId, plan.characterId);
  clearRestoreSession();

  if (restoreResult.source === 'server' && restoreResult.restored) {
    hydrateSessionIdentity({ actions, setCurrentCharacterId }, plan.threadId, plan.characterId);
    setActiveSession({
      threadId: plan.threadId,
      characterId: plan.characterId,
      initialGameData: null,
    });
    return;
  }

  handleRestoreFailure(
    {
      actions,
      clearActiveSession,
      setCurrentCharacterId,
      notifyLocalRestoreFallback,
      notifyRestoreFailure,
    },
    restoreResult,
    plan.characterId,
    'Failed to restore story session.'
  );
};

const executeResumeSessionPlan = async ({
  plan,
  actions,
  clearInitialGameData,
  clearActiveSession,
  setCurrentCharacterId,
  applyInitialEntryData,
  restoreFromServerSnapshot,
  notifyLocalRestoreFallback,
  notifyRestoreFailure,
}: Pick<
  GameInitializationExecutorOptions,
  | 'plan'
  | 'actions'
  | 'clearInitialGameData'
  | 'clearActiveSession'
  | 'setCurrentCharacterId'
  | 'applyInitialEntryData'
  | 'restoreFromServerSnapshot'
  | 'notifyLocalRestoreFallback'
  | 'notifyRestoreFailure'
>) => {
  if (plan.kind !== 'resume-session') {
    return;
  }

  const hasLocalSave = Boolean(readStoryThreadSave(plan.threadId));
  if (plan.initialGameData && !hasLocalSave) {
    hydrateSessionIdentity({ actions, setCurrentCharacterId }, plan.threadId, plan.characterId);
    applyInitialEntryData(plan.initialGameData, {
      characterId: plan.characterId,
      selectedSceneTransition: plan.selectedSceneTransition,
    });
    clearInitialGameData();
    return;
  }

  const restoreResult = await restoreFromServerSnapshot(plan.threadId, plan.characterId);
  clearInitialGameData();

  if (restoreResult.source === 'server' && restoreResult.restored) {
    hydrateSessionIdentity({ actions, setCurrentCharacterId }, plan.threadId, plan.characterId);
    return;
  }

  handleRestoreFailure(
    {
      actions,
      clearActiveSession,
      setCurrentCharacterId,
      notifyLocalRestoreFallback,
      notifyRestoreFailure,
    },
    restoreResult,
    plan.characterId,
    'Failed to resume the story session.'
  );
};

const executeFreshSessionPlan = async ({
  plan,
  actions,
  feedback,
  characterDraft,
  setActiveSession,
  setCurrentCharacterId,
  applyStoryData,
}: Pick<
  GameInitializationExecutorOptions,
  | 'plan'
  | 'actions'
  | 'feedback'
  | 'characterDraft'
  | 'setActiveSession'
  | 'setCurrentCharacterId'
  | 'applyStoryData'
>) => {
  if (plan.kind !== 'fresh-session') {
    return;
  }

  actions.setCharacterId(plan.characterId);
  setCurrentCharacterId(plan.characterId);

  const initTelemetryMetadata = {
    initializationKind: plan.kind,
    characterId: plan.characterId,
    sceneId: plan.selectedSceneTransition?.sceneId ?? null,
  };

  try {
    trackFrontendTelemetry({
      domain: 'story',
      event: 'story.init',
      status: 'requested',
      metadata: initTelemetryMetadata,
    });

    const initRes = await initGame({
      gameMode: 'solo',
      characterId: plan.characterId,
    });
    const newThreadId = initRes.threadId;

    hydrateSessionIdentity({ actions, setCurrentCharacterId }, newThreadId, plan.characterId);
    setActiveSession({
      threadId: newThreadId,
      characterId: plan.characterId,
      initialGameData: null,
    });

    const imageUrl = resolveCharacterImageUrl(characterDraft);
    const storyData = await initializeStory(
      newThreadId,
      plan.characterId,
      plan.selectedSceneTransition?.sceneId,
      imageUrl
    );

    applyStoryData(storyData, {
      characterId: plan.characterId,
      sceneMode: plan.selectedSceneTransition ? 'reset' : 'silent',
    });
    actions.replaceMessages(buildInitialAssistantMessages(storyData));
    trackFrontendTelemetry({
      domain: 'story',
      event: 'story.init',
      status: 'succeeded',
      metadata: {
        ...initTelemetryMetadata,
        threadId: newThreadId,
        initialSceneId: storyData.sceneId ?? null,
      },
    });
  } catch (error: unknown) {
    trackFrontendTelemetry({
      domain: 'story',
      event: 'story.init',
      status: 'failed',
      metadata: initTelemetryMetadata,
      cause: error,
    });
    logger.error('failed to initialize game', error);
    feedback.error('Failed to initialize game.');
  }
};

export const executeGameInitializationPlan = async (
  options: GameInitializationExecutorOptions
) => {
  switch (options.plan.kind) {
    case 'restore-session':
      await executeRestoreSessionPlan(options);
      return;
    case 'resume-session':
      await executeResumeSessionPlan(options);
      return;
    case 'fresh-session':
      await executeFreshSessionPlan(options);
      return;
    case 'idle':
    default:
      return;
  }
};
