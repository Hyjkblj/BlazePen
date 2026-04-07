import { useEffect } from 'react';

const TRAINING_LOBBY_BGM_URL = new URL(
  '../assets/audio/Mission Part.1-韩国群星.mp3',
  import.meta.url
).href;

let trainingLobbyBgmAudio: HTMLAudioElement | null = null;
let trainingLobbyBgmConsumers = 0;
let trainingLobbyBgmStopTimer: number | null = null;

const clearTrainingLobbyBgmStopTimer = () => {
  if (typeof window === 'undefined' || trainingLobbyBgmStopTimer === null) {
    return;
  }
  window.clearTimeout(trainingLobbyBgmStopTimer);
  trainingLobbyBgmStopTimer = null;
};

const getTrainingLobbyBgmAudio = (): HTMLAudioElement | null => {
  if (typeof window === 'undefined' || typeof window.Audio === 'undefined') {
    return null;
  }

  if (!trainingLobbyBgmAudio) {
    try {
      const audio = new window.Audio(TRAINING_LOBBY_BGM_URL);
      audio.preload = 'auto';
      audio.loop = true;
      audio.volume = 0.35;
      trainingLobbyBgmAudio = audio;
    } catch {
      trainingLobbyBgmAudio = null;
    }
  }

  return trainingLobbyBgmAudio;
};

const tryPlayTrainingLobbyBgm = () => {
  const audio = getTrainingLobbyBgmAudio();
  if (!audio) {
    return;
  }

  try {
    const playback = audio.play();
    if (playback && typeof playback.catch === 'function') {
      void playback.catch(() => {
        // Ignore autoplay failures until user gesture arrives.
      });
    }
  } catch {
    // Ignore runtime playback failures.
  }
};

const stopTrainingLobbyBgm = () => {
  const audio = trainingLobbyBgmAudio;
  if (!audio) {
    return;
  }
  try {
    audio.pause();
    audio.currentTime = 0;
  } catch {
    // Ignore pause failures in non-media environments.
  }
};

export function useTrainingLobbyBgm() {
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    trainingLobbyBgmConsumers += 1;
    clearTrainingLobbyBgmStopTimer();
    tryPlayTrainingLobbyBgm();

    const resumeOnGesture = () => {
      tryPlayTrainingLobbyBgm();
    };
    window.addEventListener('pointerdown', resumeOnGesture, { passive: true });
    window.addEventListener('keydown', resumeOnGesture);

    return () => {
      window.removeEventListener('pointerdown', resumeOnGesture);
      window.removeEventListener('keydown', resumeOnGesture);

      trainingLobbyBgmConsumers = Math.max(0, trainingLobbyBgmConsumers - 1);
      if (trainingLobbyBgmConsumers > 0) {
        return;
      }

      clearTrainingLobbyBgmStopTimer();
      trainingLobbyBgmStopTimer = window.setTimeout(() => {
        trainingLobbyBgmStopTimer = null;
        if (trainingLobbyBgmConsumers > 0) {
          return;
        }
        stopTrainingLobbyBgm();
      }, 180);
    };
  }, []);
}

