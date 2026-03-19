import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  appearanceOptions,
  nameSamples,
  personalityOptions,
  styleOptions,
} from '@/config/characterOptions';
import { ROUTES } from '@/config/routes';
import { useFeedback, useGameFlow } from '@/contexts';
import { createCharacter } from '@/services/characterApi';
import { checkServerHealth } from '@/services/healthApi';
import type { CharacterData } from '@/types/game';

export interface SelectedKeywordChip {
  label: string;
  value: number;
  onRemove: () => void;
}

export interface UseCharacterCreationFlowResult {
  loading: boolean;
  loadingMessage: string;
  isModalVisible: boolean;
  name: string;
  height: number;
  weight: number;
  age: number;
  gender: 'male' | 'female';
  currentCategory: number;
  selectedAppearance: number[];
  selectedPersonality: number[];
  selectedStyle: number | null;
  setName: (value: string) => void;
  setHeight: (value: number) => void;
  setWeight: (value: number) => void;
  setAge: (value: number) => void;
  setGender: (value: 'male' | 'female') => void;
  setCurrentCategory: (value: number) => void;
  setSelectedStyle: (value: number | null) => void;
  openConfirmModal: () => void;
  closeConfirmModal: () => void;
  toggleAppearance: (index: number) => void;
  togglePersonality: (index: number) => void;
  randomizeName: () => void;
  randomizeAll: () => void;
  toggleGender: () => void;
  previousCategory: () => void;
  nextCategory: () => void;
  submit: () => Promise<void>;
  selectedAppearanceKeywords: SelectedKeywordChip[];
  selectedPersonalityKeywords: SelectedKeywordChip[];
  selectedStyleChip: SelectedKeywordChip | null;
}

const maxKeywordSelection = 5;

const isValidCharacterId = (value: unknown): value is string | number =>
  value !== undefined &&
  value !== null &&
  value !== 'undefined' &&
  value !== 'null' &&
  String(value).trim() !== '';

const delay = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

const mapKeywordsToIndexes = (options: readonly string[], keywords?: string[]) => {
  if (!Array.isArray(keywords)) return [];

  return keywords
    .map((keyword) => options.indexOf(keyword))
    .filter((index): index is number => index >= 0);
};

const pickRandomUniqueIndexes = (max: number, count: number) => {
  const pool = [...Array(max).keys()];
  const result: number[] = [];

  for (let index = 0; index < count && pool.length > 0; index += 1) {
    const randomIndex = Math.floor(Math.random() * pool.length);
    result.push(pool.splice(randomIndex, 1)[0]);
  }

  return result;
};

export function useCharacterCreationFlow(): UseCharacterCreationFlowResult {
  const navigate = useNavigate();
  const feedback = useFeedback();
  const { state, clearActiveSession, clearRestoreSession, setCharacterDraft, setCreatedCharacterId } =
    useGameFlow();

  const initialDraft = state.characterDraft;
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在连接服务器...');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [name, setName] = useState(initialDraft?.name || '');
  const [height, setHeight] = useState(initialDraft?.height || 160);
  const [weight, setWeight] = useState(initialDraft?.weight || 45);
  const [age, setAge] = useState(initialDraft?.age || 18);
  const [gender, setGender] = useState<'male' | 'female'>(initialDraft?.gender || 'male');
  const [currentCategory, setCurrentCategory] = useState(0);
  const [selectedAppearance, setSelectedAppearance] = useState<number[]>(
    mapKeywordsToIndexes(appearanceOptions, initialDraft?.appearance)
  );
  const [selectedPersonality, setSelectedPersonality] = useState<number[]>(
    mapKeywordsToIndexes(personalityOptions, initialDraft?.personality)
  );
  const [selectedStyle, setSelectedStyle] = useState<number | null>(() => {
    if (!initialDraft?.style) return null;
    const index = styleOptions.findIndex((option) => option === initialDraft.style);
    return index >= 0 ? index : null;
  });

  const toggleAppearance = (index: number) => {
    setSelectedAppearance((prev) => {
      if (prev.includes(index)) return prev.filter((value) => value !== index);
      if (prev.length >= maxKeywordSelection) {
        feedback.warning('外貌关键词最多选择 5 项');
        return prev;
      }
      return [...prev, index];
    });
  };

  const togglePersonality = (index: number) => {
    setSelectedPersonality((prev) => {
      if (prev.includes(index)) return prev.filter((value) => value !== index);
      if (prev.length >= maxKeywordSelection) {
        feedback.warning('性格关键词最多选择 5 项');
        return prev;
      }
      return [...prev, index];
    });
  };

  const randomizeName = () => {
    const randomIndex = Math.floor(Math.random() * nameSamples.length);
    setName(nameSamples[randomIndex]);
  };

  const randomizeAll = () => {
    randomizeName();
    setHeight(Math.floor(Math.random() * (200 - 140 + 1)) + 140);
    setWeight(Math.floor(Math.random() * (100 - 35 + 1)) + 35);
    setAge(Math.floor(Math.random() * (30 - 18 + 1)) + 18);
    setGender(Math.random() > 0.5 ? 'male' : 'female');
    setSelectedAppearance(pickRandomUniqueIndexes(appearanceOptions.length, maxKeywordSelection));
    setSelectedPersonality(pickRandomUniqueIndexes(personalityOptions.length, maxKeywordSelection));
    setSelectedStyle(Math.floor(Math.random() * styleOptions.length));
  };

  const toggleGender = () => {
    setGender((prev) => (prev === 'male' ? 'female' : 'male'));
  };

  const previousCategory = () => {
    setCurrentCategory((prev) => (prev > 0 ? prev - 1 : 2));
  };

  const nextCategory = () => {
    setCurrentCategory((prev) => (prev < 2 ? prev + 1 : 0));
  };

  const openConfirmModal = () => {
    setIsModalVisible(true);
  };

  const closeConfirmModal = () => {
    setIsModalVisible(false);
  };

  const submit = async () => {
    setIsModalVisible(false);
    setLoading(true);
    setLoadingMessage('正在创建角色...');

    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        feedback.error('无法连接到服务器，请检查后端服务是否运行');
        return;
      }

      const appearance = selectedAppearance.map((index) => appearanceOptions[index]);
      const personality = selectedPersonality.map((index) => personalityOptions[index]);
      const style = selectedStyle !== null ? styleOptions[selectedStyle] : null;

      setLoadingMessage('正在生成你的专属角色...');

      const response = await createCharacter({
        name: name || '未命名角色',
        appearance: {
          keywords: appearance,
          height,
          weight,
        },
        personality: {
          keywords: personality,
        },
        background: {
          style,
        },
        gender,
        age,
      });

      const characterId = response.characterId;
      if (!isValidCharacterId(characterId)) {
        feedback.error('创建角色失败：未获取到有效角色 ID');
        return;
      }

      const characterData: CharacterData = {
        characterId: String(characterId),
        name: typeof response.name === 'string' ? response.name : name || '未命名角色',
        height,
        weight,
        age,
        gender,
        appearance,
        personality,
        style,
        imageUrl: response.imageUrl ?? undefined,
        image_urls: response.imageUrls,
      };

      setCharacterDraft(characterData);
      setCreatedCharacterId(characterData.characterId);
      clearRestoreSession();
      clearActiveSession();

      setLoadingMessage('正在加载角色图片...');
      await delay(500);
      navigate(ROUTES.CHARACTER_SELECTION);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      feedback.error(err.response?.data?.detail || err.message || '创建角色失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  const selectedAppearanceKeywords = selectedAppearance.map((index) => ({
    label: appearanceOptions[index],
    value: index,
    onRemove: () =>
      setSelectedAppearance((prev) => prev.filter((currentIndex) => currentIndex !== index)),
  }));

  const selectedPersonalityKeywords = selectedPersonality.map((index) => ({
    label: personalityOptions[index],
    value: index,
    onRemove: () =>
      setSelectedPersonality((prev) => prev.filter((currentIndex) => currentIndex !== index)),
  }));

  const selectedStyleChip =
    selectedStyle === null
      ? null
      : {
          label: styleOptions[selectedStyle],
          value: selectedStyle,
          onRemove: () => setSelectedStyle(null),
        };

  return {
    loading,
    loadingMessage,
    isModalVisible,
    name,
    height,
    weight,
    age,
    gender,
    currentCategory,
    selectedAppearance,
    selectedPersonality,
    selectedStyle,
    setName,
    setHeight,
    setWeight,
    setAge,
    setGender,
    setCurrentCategory,
    setSelectedStyle,
    openConfirmModal,
    closeConfirmModal,
    toggleAppearance,
    togglePersonality,
    randomizeName,
    randomizeAll,
    toggleGender,
    previousCategory,
    nextCategory,
    submit,
    selectedAppearanceKeywords,
    selectedPersonalityKeywords,
    selectedStyleChip,
  };
}
