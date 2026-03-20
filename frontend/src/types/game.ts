/** 对话消息（游戏内） */
export interface GameMessage {
  role: 'user' | 'assistant';
  content: string;
}

/** 玩家选项 */
export interface PlayerOption {
  id: number;
  text: string;
  type: string;
  state_changes?: Record<string, number>;
}

export interface GameSessionSnapshot {
  currentDialogue: string;
  currentOptions: PlayerOption[];
  currentScene: string | null;
  sceneImageUrl: string | null;
  characterImageUrl: string | null;
  compositeImageUrl: string | null;
  shouldUseComposite: boolean;
  isGameFinished: boolean;
}

export interface StorySceneData {
  sceneId: string | null;
  sceneImageUrl: string | null;
  compositeImageUrl: string | null;
  storyBackground: string | null;
  characterDialogue: string | null;
  playerOptions: PlayerOption[];
  isGameFinished: boolean;
}

export interface StoryEndingKeyStates {
  favorability: number | null;
  trust: number | null;
  hostility: number | null;
  dependence: number | null;
}

export interface StoryEndingSummary {
  type: string;
  description: string;
  sceneId: string | null;
  eventTitle: string | null;
  keyStates: StoryEndingKeyStates;
}

export interface StoryEndingCheckItem {
  type: string;
  description: string;
  favorability: number | null;
  trust: number | null;
  hostility: number | null;
}

export interface StoryEndingCheckResult {
  hasEnding: boolean;
  ending: StoryEndingCheckItem | null;
}

export interface StoryEndingSummaryResult {
  threadId: string;
  status: string | null;
  roundNo: number;
  hasEnding: boolean;
  ending: StoryEndingSummary | null;
  updatedAt: string | null;
  expiresAt: string | null;
}

export interface StoryHistoryUserAction {
  kind: string;
  summary: string;
  rawInput: string | null;
  optionIndex: number | null;
  optionText: string | null;
  optionType: string | null;
}

export interface StoryHistoryStateSummary {
  changes: Record<string, number>;
  currentStates: Record<string, number>;
}

export interface StoryHistoryItem {
  roundNo: number;
  status: string;
  sceneId: string | null;
  eventTitle: string | null;
  characterDialogue: string | null;
  userAction: StoryHistoryUserAction;
  stateSummary: StoryHistoryStateSummary;
  isEventFinished: boolean;
  isGameFinished: boolean;
  createdAt: string | null;
}

export interface StorySessionHistoryResult {
  threadId: string;
  status: string | null;
  currentRoundNo: number;
  latestSceneId: string | null;
  updatedAt: string | null;
  expiresAt: string | null;
  history: StoryHistoryItem[];
}

export interface StorySessionInitParams {
  userId?: string;
  gameMode?: string;
  characterId: string;
}

export interface StorySessionInitResult {
  threadId: string;
  userId: string | null;
  gameMode: string | null;
}

export interface StoryTurnSubmitParams {
  threadId: string;
  userInput: string;
  userId?: string;
  characterId?: string;
}

export interface GameTurnResult extends StorySceneData {
  threadId: string | null;
  sessionRestored: boolean;
  needReselectOption: boolean;
  restoredFromThreadId: string | null;
}

export interface StorySessionSnapshotResult extends GameTurnResult {
  roundNo: number;
  status: string | null;
  updatedAt: string | null;
  expiresAt: string | null;
}

/** 存档：按 thread 保存的完整消息列表与元信息 */
export interface GameSave {
  threadId: string;
  characterId?: string;
  messages: GameMessage[];
  lastMessage?: string;
  snapshot?: GameSessionSnapshot;
  timestamp: number;
}

/** 主存档入口（继续游戏用） */
export interface MainGameSave {
  threadId: string;
  characterId?: string;
  lastMessage?: string;
  snapshot?: GameSessionSnapshot;
  timestamp: number;
}

/** 选中的场景（大场景） */
export interface SelectedScene {
  id: string;
  name?: string;
  description?: string;
  imageUrl?: string;
}

export interface CharacterVoiceConfig {
  voice_type: string;
  preset_voice_id?: string | null;
  voice_name?: string;
  voice_description?: string;
  voice_id?: string;
  voice_design_description?: string | null;
  voice_params?: Record<string, unknown>;
}

/** sessionStorage 中的角色数据（创建/选择角色后写入） */
export interface CharacterData {
  characterId: string;
  name?: string;
  height?: number;
  weight?: number;
  age?: number;
  gender?: 'male' | 'female';
  appearance?: string[];
  personality?: string[];
  style?: string | null;
  imageUrl?: string;
  image_urls?: string[];
  transparentImageUrl?: string;
  originalImageUrl?: string;
  selectedImageUrl?: string;
  selectedImageIndex?: number;
  selectedCharacterId?: string;
  selectedScene?: SelectedScene;
  voiceConfig?: CharacterVoiceConfig;
  timestamp?: number;
}

export interface CharacterCreationResult {
  characterId: string;
  name: string | null;
  imageUrl: string | null;
  imageUrls: string[];
}

/** 初遇页写入的初始游戏数据（供 Game 页消费） */
export interface InitialGameData {
  sceneId: string | null;
  storyBackground: string | null;
  characterDialogue: string | null;
  playerOptions: PlayerOption[];
  compositeImageUrl: string | null;
  sceneImageUrl: string | null;
  isGameFinished: boolean;
}
