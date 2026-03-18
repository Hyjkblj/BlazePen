import { useCallback, useEffect, useRef } from 'react';
import { getStaticAssetUrl } from '@/services/assetUrl';
import { generateSpeech } from '@/services/ttsApi';
import { logger } from '@/utils/logger';

const extractSpokenText = (dialogue: string) =>
  dialogue.replace(/^[^:：]+[:：]/, '').trim() || dialogue;

export function useGameTts(currentDialogue: string, characterId: string | null) {
  const lastTtsKeyRef = useRef('');
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  const requestIdRef = useRef(0);

  const stopAudio = useCallback(() => {
    const activeAudio = activeAudioRef.current;
    if (!activeAudio) {
      return;
    }

    activeAudio.pause();
    activeAudio.currentTime = 0;
    activeAudio.onended = null;
    activeAudio.onerror = null;
    activeAudioRef.current = null;
  }, []);

  useEffect(() => {
    return () => {
      requestIdRef.current += 1;
      stopAudio();
    };
  }, [stopAudio]);

  useEffect(() => {
    const normalizedDialogue = currentDialogue?.trim();
    if (!normalizedDialogue || !characterId) {
      return;
    }

    const normalizedCharacterId = String(characterId).trim();
    if (!normalizedCharacterId || normalizedCharacterId === 'undefined' || normalizedCharacterId === 'null') {
      return;
    }

    const ttsKey = `${normalizedCharacterId}:${normalizedDialogue}`;
    if (ttsKey === lastTtsKeyRef.current) {
      return;
    }

    lastTtsKeyRef.current = ttsKey;
    const textForTts = extractSpokenText(normalizedDialogue);
    if (!textForTts) {
      return;
    }

    requestIdRef.current += 1;
    const requestId = requestIdRef.current;
    stopAudio();

    let cancelled = false;

    void (async () => {
      try {
        const result = await generateSpeech(textForTts, normalizedCharacterId);
        if (cancelled || requestIdRef.current !== requestId || !result?.audio_url) {
          return;
        }

        const audio = new Audio(getStaticAssetUrl(result.audio_url));
        activeAudioRef.current = audio;

        audio.onended = () => {
          if (activeAudioRef.current === audio) {
            activeAudioRef.current = null;
          }
        };

        audio.onerror = () => {
          if (activeAudioRef.current === audio) {
            activeAudioRef.current = null;
          }
          logger.warn('[game] TTS playback failed.');
        };

        try {
          await audio.play();
        } catch (error) {
          if (activeAudioRef.current === audio) {
            activeAudioRef.current = null;
          }
          logger.warn('[game] TTS playback failed:', error);
        }
      } catch (error) {
        if (!cancelled && requestIdRef.current === requestId) {
          logger.warn('[game] TTS request failed:', error);
        }
      }
    })();

    return () => {
      cancelled = true;
      if (requestIdRef.current === requestId) {
        stopAudio();
      }
    };
  }, [characterId, currentDialogue, stopAudio]);
}
