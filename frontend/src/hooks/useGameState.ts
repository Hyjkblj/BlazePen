import { useState, useRef, useCallback, useMemo } from 'react';
import type { GameMessage, GameSessionSnapshot, PlayerOption } from '@/types/game';

export type SceneTransitionMode = 'silent' | 'reset' | 'advance';

export interface SceneVisualStateInput {
  sceneImageUrl: string | null;
  characterImageUrl?: string | null;
  clearCharacterImage?: boolean;
}

export interface GameSessionState {
  messages: GameMessage[];
  loading: boolean;
  threadId: string | null;
  characterId: string | null;
  currentOptions: PlayerOption[];
  currentScene: string | null;
  actNumber: number;
  showTransition: boolean;
  transitionSceneName: string;
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
  shouldUseComposite: boolean;
  currentDialogue: string;
}

export interface GameSessionActions {
  replaceMessages: (messages: GameMessage[]) => void;
  appendMessage: (message: GameMessage) => void;
  rollbackPendingUserMessage: () => void;
  startLoading: () => void;
  stopLoading: () => void;
  setThreadId: (threadId: string | null) => void;
  setCharacterId: (characterId: string | null) => void;
  setCharacterImageUrl: (url: string | null) => void;
  setDialogue: (dialogue: string | null | undefined) => void;
  setOptions: (options: PlayerOption[] | null | undefined) => void;
  enterScene: (sceneId: string, sceneName: string, mode?: SceneTransitionMode) => void;
  clearSceneTransition: () => void;
  applyCompositeScene: (imageUrl: string) => void;
  applySceneVisual: (input: SceneVisualStateInput) => void;
  markCompositeAssetFailed: () => void;
  markSceneAssetFailed: () => void;
  markCharacterAssetFailed: () => void;
  prepareOptionSelection: (optionText: string) => void;
  scrollToBottom: () => void;
}

export type GameSessionInitActions = Pick<
  GameSessionActions,
  | 'replaceMessages'
  | 'setThreadId'
  | 'setCharacterId'
  | 'setCharacterImageUrl'
  | 'setDialogue'
  | 'setOptions'
  | 'enterScene'
  | 'applyCompositeScene'
  | 'applySceneVisual'
>;

export interface GameSessionDerived {
  persistenceSnapshot: GameSessionSnapshot;
}

export interface GameStateBag {
  state: GameSessionState;
  actions: GameSessionActions;
  derived: GameSessionDerived;
}

export function useGameState(): GameStateBag {
  const [messages, setMessages] = useState<GameMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [characterId, setCharacterId] = useState<string | null>(null);
  const [currentOptions, setCurrentOptions] = useState<PlayerOption[]>([]);
  const [currentScene, setCurrentScene] = useState<string | null>(null);
  const [actNumber, setActNumber] = useState(1);
  const [showTransition, setShowTransition] = useState(false);
  const [transitionSceneName, setTransitionSceneName] = useState('');
  const [compositeImageUrl, setCompositeImageUrl] = useState<string | null>(null);
  const [sceneImageUrl, setSceneImageUrl] = useState<string | null>(null);
  const [characterImageUrl, setCharacterImageUrl] = useState<string | null>(null);
  const [shouldUseComposite, setShouldUseComposite] = useState(false);
  const [currentDialogue, setCurrentDialogue] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const previousSceneRef = useRef<string | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const replaceMessages = useCallback((nextMessages: GameMessage[]) => {
    setMessages(nextMessages);
  }, []);

  const appendMessage = useCallback((message: GameMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const rollbackPendingUserMessage = useCallback(() => {
    setMessages((prev) => {
      if (prev[prev.length - 1]?.role !== 'user') {
        return prev;
      }
      return prev.slice(0, -1);
    });
  }, []);

  const startLoading = useCallback(() => {
    setLoading(true);
  }, []);

  const stopLoading = useCallback(() => {
    setLoading(false);
  }, []);

  const setDialogue = useCallback((dialogue: string | null | undefined) => {
    setCurrentDialogue(dialogue ?? '');
  }, []);

  const setOptions = useCallback((options: PlayerOption[] | null | undefined) => {
    setCurrentOptions(Array.isArray(options) ? options : []);
  }, []);

  const enterScene = useCallback((sceneId: string, sceneName: string, mode: SceneTransitionMode = 'silent') => {
    if (mode === 'reset') {
      setActNumber(1);
      setTransitionSceneName(sceneName);
      setShowTransition(true);
    } else if (mode === 'advance' && previousSceneRef.current !== sceneId && previousSceneRef.current !== null) {
      setActNumber((prev) => prev + 1);
      setTransitionSceneName(sceneName);
      setShowTransition(true);
    }

    previousSceneRef.current = sceneId;
    setCurrentScene(sceneId);
  }, []);

  const clearSceneTransition = useCallback(() => {
    setShowTransition(false);
  }, []);

  const applyCompositeScene = useCallback((imageUrl: string) => {
    setCompositeImageUrl(imageUrl);
    setShouldUseComposite(true);
    setSceneImageUrl(null);
    setCharacterImageUrl(null);
  }, []);

  const applySceneVisual = useCallback(({ sceneImageUrl, characterImageUrl, clearCharacterImage }: SceneVisualStateInput) => {
    setShouldUseComposite(false);
    setCompositeImageUrl(null);
    setSceneImageUrl(sceneImageUrl);

    if (characterImageUrl !== undefined) {
      setCharacterImageUrl(characterImageUrl);
      return;
    }

    if (clearCharacterImage) {
      setCharacterImageUrl(null);
    }
  }, []);

  const markCompositeAssetFailed = useCallback(() => {
    setShouldUseComposite(false);
    setCompositeImageUrl(null);
  }, []);

  const markSceneAssetFailed = useCallback(() => {
    setSceneImageUrl(null);
  }, []);

  const markCharacterAssetFailed = useCallback(() => {
    setCharacterImageUrl(null);
  }, []);

  const prepareOptionSelection = useCallback((optionText: string) => {
    setMessages((prev) => [...prev, { role: 'user', content: optionText }]);
    setCurrentOptions([]);
    setCurrentDialogue('');
    setLoading(true);
  }, []);

  const state = useMemo(
    () => ({
      messages,
      loading,
      threadId,
      characterId,
      currentOptions,
      currentScene,
      actNumber,
      showTransition,
      transitionSceneName,
      compositeImageUrl,
      sceneImageUrl,
      characterImageUrl,
      shouldUseComposite,
      currentDialogue,
    }),
    [
      actNumber,
      characterId,
      characterImageUrl,
      compositeImageUrl,
      currentDialogue,
      currentOptions,
      currentScene,
      loading,
      messages,
      sceneImageUrl,
      shouldUseComposite,
      showTransition,
      threadId,
      transitionSceneName,
    ]
  );

  const derived = useMemo(
    () => ({
      persistenceSnapshot: {
        currentDialogue,
        currentOptions,
        currentScene,
        sceneImageUrl,
        characterImageUrl,
        compositeImageUrl,
        shouldUseComposite,
      },
    }),
    [
      characterImageUrl,
      compositeImageUrl,
      currentDialogue,
      currentOptions,
      currentScene,
      sceneImageUrl,
      shouldUseComposite,
    ]
  );

  const actions = useMemo(
    () => ({
      replaceMessages,
      appendMessage,
      rollbackPendingUserMessage,
      startLoading,
      stopLoading,
      setThreadId,
      setCharacterId,
      setCharacterImageUrl,
      setDialogue,
      setOptions,
      enterScene,
      clearSceneTransition,
      applyCompositeScene,
      applySceneVisual,
      markCompositeAssetFailed,
      markSceneAssetFailed,
      markCharacterAssetFailed,
      prepareOptionSelection,
      scrollToBottom,
    }),
    [
      appendMessage,
      applyCompositeScene,
      applySceneVisual,
      clearSceneTransition,
      enterScene,
      markCharacterAssetFailed,
      markCompositeAssetFailed,
      markSceneAssetFailed,
      prepareOptionSelection,
      replaceMessages,
      rollbackPendingUserMessage,
      scrollToBottom,
      setDialogue,
      setOptions,
      startLoading,
      stopLoading,
    ]
  );

  return {
    state,
    actions,
    derived,
  };
}
