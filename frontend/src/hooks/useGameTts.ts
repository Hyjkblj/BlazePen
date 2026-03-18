import { useEffect, useRef } from 'react';
import { generateSpeech } from '@/services/ttsApi';
import { logger } from '@/utils/logger';

/**
 * 当 currentDialogue / characterId 变化时，使用角色音色播放 TTS
 */
export function useGameTts(currentDialogue: string, characterId: string | null) {
  const lastTtsDialogueRef = useRef('');

  useEffect(() => {
    if (!currentDialogue?.trim() || !characterId) return;
    if (currentDialogue === lastTtsDialogueRef.current) return;
    lastTtsDialogueRef.current = currentDialogue;

    const textForTts = currentDialogue.replace(/^[^:：]+[：:]/, '').trim() || currentDialogue;
    if (!textForTts) return;

    const charId = typeof characterId === 'string' ? characterId : String(characterId);
    if (charId === 'undefined' || charId === 'null' || charId === '') return;

    let cancelled = false;
    const audioRef = { current: null as HTMLAudioElement | null };
    (async () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      const result = await generateSpeech(textForTts, characterId);
      if (cancelled || !result?.audio_url) return;
      const url = result.audio_url.startsWith('http')
        ? result.audio_url
        : `${window.location.origin}${result.audio_url}`;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.play().catch((e) => logger.warn('[游戏] TTS 播放失败:', e));
      audio.onended = () => {
        audioRef.current = null;
      };
    })();
    return () => {
      cancelled = true;
    };
  }, [currentDialogue, characterId]);
}
