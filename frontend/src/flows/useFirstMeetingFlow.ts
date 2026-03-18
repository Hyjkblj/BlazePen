import { useEffect, useRef, useState } from 'react';
import type { WheelEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { useFeedback, useGameFlow } from '@/contexts';
import { getScenes, initializeStory } from '@/services/characterApi';
import { initGame } from '@/services/gameApi';
import { checkServerHealth } from '@/services/healthApi';
import type { GetScenesResponse, InitializeStoryResponse, SceneApiItem } from '@/types/api';
import type { PlayerOption, SelectedScene } from '@/types/game';

export interface SceneOption extends SelectedScene {
  name: string;
  description: string;
}

export interface UseFirstMeetingFlowResult {
  loading: boolean;
  loadingMessage: string;
  sceneOptions: SceneOption[];
  currentSceneIndex: number;
  currentScene: SceneOption | null;
  goToCharacterSetup: () => void;
  previousScene: () => void;
  nextScene: () => void;
  handleWheel: (event: WheelEvent<HTMLDivElement>) => void;
  selectScene: () => Promise<void>;
}

interface InitialGameDataPayload {
  character_dialogue?: string;
  player_options?: PlayerOption[];
  composite_image_url?: string;
  scene_image_url?: string;
  scene?: string;
}

const normalizeScene = (scene: SceneApiItem | undefined, index: number): SceneOption => {
  const rawImage = scene?.imageUrl;
  const imageUrl =
    typeof rawImage === 'string' && rawImage !== '' && rawImage !== 'null'
      ? rawImage
      : undefined;

  return {
    id: scene?.id || `scene-${index}`,
    name: scene?.name || 'Unnamed Scene',
    description: scene?.description || '',
    imageUrl,
  };
};

export function useFirstMeetingFlow(): UseFirstMeetingFlowResult {
  const navigate = useNavigate();
  const feedback = useFeedback();
  const { state, setActiveSession, updateCharacterDraft } = useGameFlow();

  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Loading scenes...');
  const [currentSceneIndex, setCurrentSceneIndex] = useState(0);
  const [sceneOptions, setSceneOptions] = useState<SceneOption[]>([]);

  const wheelTimeoutRef = useRef<number | null>(null);
  const isWheelingRef = useRef(false);

  useEffect(() => {
    const loadScenes = async () => {
      setLoading(true);
      setLoadingMessage('Loading scenes...');

      try {
        const isHealthy = await checkServerHealth();
        if (!isHealthy) {
          feedback.error('Backend is unavailable.');
          setSceneOptions([]);
          return;
        }

        const response: GetScenesResponse = await getScenes();
        const scenes = Array.isArray(response.scenes) ? response.scenes : [];

        if (scenes.length === 0) {
          feedback.warning('No scenes available.');
          setSceneOptions([]);
          return;
        }

        setSceneOptions(scenes.map((scene, index) => normalizeScene(scene, index)));
      } catch (error: unknown) {
        const err = error as { response?: { data?: { message?: string } }; message?: string };
        feedback.error(err.response?.data?.message || err.message || 'Failed to load scenes.');
        setSceneOptions([
          {
            id: 'school',
            name: 'School',
            description: 'A lively campus scene.',
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    void loadScenes();
  }, [feedback]);

  useEffect(() => {
    return () => {
      if (wheelTimeoutRef.current) {
        window.clearTimeout(wheelTimeoutRef.current);
      }
    };
  }, []);

  const previousScene = () => {
    if (sceneOptions.length === 0) return;
    setCurrentSceneIndex((prev) => (prev === 0 ? sceneOptions.length - 1 : prev - 1));
  };

  const nextScene = () => {
    if (sceneOptions.length === 0) return;
    setCurrentSceneIndex((prev) => (prev === sceneOptions.length - 1 ? 0 : prev + 1));
  };

  const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault();

    if (isWheelingRef.current) return;
    isWheelingRef.current = true;

    if (event.deltaY > 50) {
      nextScene();
    } else if (event.deltaY < -50) {
      previousScene();
    }

    if (wheelTimeoutRef.current) {
      window.clearTimeout(wheelTimeoutRef.current);
    }

    wheelTimeoutRef.current = window.setTimeout(() => {
      isWheelingRef.current = false;
    }, 300);
  };

  const selectScene = async () => {
    const selectedScene = sceneOptions[currentSceneIndex];
    const characterData = state.characterDraft;

    if (!selectedScene) {
      feedback.error('No scene selected.');
      return;
    }

    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        feedback.error('Backend is unavailable.');
        return;
      }

      if (!characterData?.characterId) {
        feedback.error('Character is missing, please create one first.');
        navigate(ROUTES.CHARACTER_SETTING);
        return;
      }

      const characterId = characterData.characterId;
      updateCharacterDraft((current) => (current ? { ...current, selectedScene } : current));

      setLoading(true);
      setLoadingMessage('Initializing game...');

      const initResponse = await initGame({
        game_mode: 'solo',
        character_id: characterId,
      });

      const threadId = initResponse.thread_id;
      if (!threadId) {
        throw new Error('Missing thread_id from initGame response.');
      }

      setLoadingMessage('Preparing first scene...');

      const characterImageUrl =
        characterData.selectedImageUrl || characterData.originalImageUrl || characterData.imageUrl;

      const storyResponse: InitializeStoryResponse = await initializeStory(
        threadId,
        characterId,
        selectedScene.id,
        characterImageUrl
      );

      const initialGameData: InitialGameDataPayload = {
        character_dialogue: storyResponse.character_dialogue,
        player_options: Array.isArray(storyResponse.player_options)
          ? storyResponse.player_options
          : [],
        composite_image_url: storyResponse.composite_image_url,
        scene_image_url: storyResponse.scene_image_url,
        scene: storyResponse.scene,
      };

      setActiveSession({
        threadId,
        characterId,
        initialGameData,
      });
      navigate(ROUTES.GAME);
    } catch (error: unknown) {
      const err = error as { message?: string; response?: { data?: { message?: string } } };
      let errorMessage = 'Failed to select scene, please try again.';

      if (err.message?.includes('timeout')) {
        errorMessage = 'Initialization timed out, please try again shortly.';
      } else if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      }

      feedback.error(errorMessage);
      setLoading(false);
    }
  };

  const goToCharacterSetup = () => {
    navigate(ROUTES.CHARACTER_SETTING);
  };

  const currentScene = sceneOptions.length > 0 ? sceneOptions[currentSceneIndex] : null;

  return {
    loading,
    loadingMessage,
    sceneOptions,
    currentSceneIndex,
    currentScene,
    goToCharacterSetup,
    previousScene,
    nextScene,
    handleWheel,
    selectScene,
  };
}
