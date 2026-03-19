import type { GameMessage, InitialGameData, SelectedScene, StorySceneData } from '@/types/game';

type StoryDataLike = Pick<
  InitialGameData | StorySceneData,
  'sceneId' | 'sceneImageUrl' | 'compositeImageUrl' | 'storyBackground' | 'characterDialogue'
>;

export interface PreferredCharacterIdParams {
  currentCharacterId?: string | null;
  activeCharacterId?: string | null;
  draftCharacterId?: string | null;
}

export interface SelectedSceneTransition {
  sceneId: string;
  sceneName: string;
}

const normalizeSessionString = (value: string | null | undefined): string | null => {
  if (typeof value !== 'string') {
    return null;
  }

  const normalized = value.trim();
  if (normalized === '' || normalized === 'null' || normalized === 'undefined') {
    return null;
  }

  return normalized;
};

export const resolvePreferredCharacterId = ({
  currentCharacterId,
  activeCharacterId,
  draftCharacterId,
}: PreferredCharacterIdParams): string | null => {
  const candidates = [currentCharacterId, activeCharacterId, draftCharacterId];

  for (const candidate of candidates) {
    const normalizedCandidate = normalizeSessionString(candidate);
    if (normalizedCandidate) {
      return normalizedCandidate;
    }
  }

  return null;
};

export const hasStorySceneVisual = (storyData: StoryDataLike): boolean =>
  Boolean(
    normalizeSessionString(storyData.compositeImageUrl) ||
      normalizeSessionString(storyData.sceneImageUrl) ||
      normalizeSessionString(storyData.sceneId)
  );

export const buildInitialAssistantMessages = (storyData: StoryDataLike): GameMessage[] => {
  const messages: GameMessage[] = [];
  const storyBackground = normalizeSessionString(storyData.storyBackground);
  const characterDialogue = normalizeSessionString(storyData.characterDialogue);

  if (storyBackground) {
    messages.push({
      role: 'assistant',
      content: storyBackground,
    });
  }

  if (characterDialogue) {
    messages.push({
      role: 'assistant',
      content: characterDialogue,
    });
  }

  return messages;
};

export const resolveSelectedSceneTransition = (
  selectedScene: SelectedScene | null | undefined,
  resolveSceneName: (sceneId: string) => string | null
): SelectedSceneTransition | null => {
  const sceneId = normalizeSessionString(selectedScene?.id);
  if (!sceneId) {
    return null;
  }

  const sceneName =
    normalizeSessionString(selectedScene?.name) ??
    normalizeSessionString(resolveSceneName(sceneId)) ??
    sceneId;

  return {
    sceneId,
    sceneName,
  };
};
