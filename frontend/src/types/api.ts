import type { PlayerOption } from '@/types/game';

export type GenericApiRecord = Record<string, unknown>;

export interface ApiStructuredError extends GenericApiRecord {
  code?: string;
  details?: unknown;
  traceId?: string;
  trace_id?: string;
}

export interface ApiResponse<T = unknown> extends GenericApiRecord {
  code?: number;
  message?: string;
  data?: T;
  error?: unknown;
  details?: unknown;
  traceId?: string;
  trace_id?: string;
}

export interface ApiErrorData extends GenericApiRecord {
  code?: number;
  message?: string;
  detail?: unknown;
  error?: ApiStructuredError | unknown;
  details?: unknown;
  traceId?: string;
  trace_id?: string;
}

export interface CreateCharacterRequest {
  name: string;
  appearance: Record<string, unknown>;
  personality: Record<string, unknown>;
  background: Record<string, unknown>;
  gender?: string;
  age?: number;
  identity?: string;
  initial_scene?: string;
  initial_scene_prompt?: string;
}

export interface CreateCharacterResponse extends GenericApiRecord {
  character_id?: string | number;
  name?: string;
  image_url?: string;
  image_urls?: string[];
}

export interface CharacterImagesResponse {
  images?: string[];
}

export interface StoryResponsePayload extends GenericApiRecord {
  scene?: string;
  scene_image_url?: string;
  composite_image_url?: string;
  story_background?: string;
  character_dialogue?: string;
  player_options?: PlayerOption[];
  is_game_finished?: boolean;
  snapshot?: GenericApiRecord | null;
}

export interface RemoveBackgroundResponse {
  original_url: string;
  transparent_url: string;
  local_path: string;
  selected_image_url?: string;
}

export interface InitializeStoryResponse extends StoryResponsePayload {
  thread_id?: string;
}

export interface SceneApiItem extends GenericApiRecord {
  id?: string;
  name?: string;
  description?: string;
  imageUrl?: string;
}

export interface GetScenesResponse extends GenericApiRecord {
  scenes?: SceneApiItem[];
}

export interface GameInitRequest {
  user_id?: string;
  game_mode: string;
  character_id: string;
}

export interface GameInputRequest {
  thread_id: string;
  user_input: string;
  user_id?: string;
  character_id?: string;
}

export interface GameInitResponse extends GenericApiRecord {
  thread_id?: string;
  user_id?: string;
  game_mode?: string;
}

export interface ProcessGameInputResponse extends StoryResponsePayload {
  thread_id?: string;
  round_no?: number;
  status?: string;
  session_restored?: boolean;
  need_reselect_option?: boolean;
  restored_from_thread_id?: string;
}

export interface StorySessionSnapshotResponse extends ProcessGameInputResponse {
  updated_at?: string;
  expires_at?: string;
}

export interface PresetVoiceItem {
  id: string;
  name: string;
  description?: string;
  voice_id?: string | null;
  gender?: string;
  style?: string;
  preview_text?: string;
}

export interface PresetVoiceGroups {
  female?: PresetVoiceItem[];
  male?: PresetVoiceItem[];
  neutral?: PresetVoiceItem[];
  [key: string]: PresetVoiceItem[] | undefined;
}

export interface PresetVoicesResponse {
  voices?: PresetVoiceItem[] | PresetVoiceGroups;
}

export interface GenerateSpeechOptions {
  use_cache?: boolean;
  emotion_params?: Record<string, unknown>;
}

export interface GenerateSpeechResponse {
  audio_url: string;
  duration?: number;
  cached?: boolean;
}

export interface VoicePreviewResponse {
  audio_url: string;
  duration?: number;
}

export interface SetVoiceConfigRequest {
  character_id: number;
  voice_type: string;
  preset_voice_id?: string | null;
  voice_design_description?: string | null;
  voice_params?: Record<string, unknown>;
}
