import { useEffect, useRef } from 'react';
import TrainingTitleFire from '@/components/training/TrainingTitleFire';
import './TrainingMainHome.css';

const HOVER_SFX_VIDEO_URL = new URL(
  '../../assets/video/屏幕录制 2026-04-07 020459.mp4',
  import.meta.url
).href;

type TrainingMainHomeProps = {
  onEnter: () => void | Promise<void>;
  enterDisabled?: boolean;
};

function TrainingMainHome({ onEnter, enterDisabled = false }: TrainingMainHomeProps) {
  const hoverVideoAudioRef = useRef<HTMLAudioElement | null>(null);
  const hoverVideoStopTimerRef = useRef<number | null>(null);
  const hoverAudioContextRef = useRef<AudioContext | null>(null);
  const hoverSfxLastPlayedAtRef = useRef(0);

  const clearHoverVideoStopTimer = () => {
    if (hoverVideoStopTimerRef.current === null || typeof window === 'undefined') {
      return;
    }
    window.clearTimeout(hoverVideoStopTimerRef.current);
    hoverVideoStopTimerRef.current = null;
  };

  useEffect(() => {
    if (typeof window !== 'undefined' && typeof window.Audio !== 'undefined') {
      try {
        const hoverVideoAudio = new window.Audio(HOVER_SFX_VIDEO_URL);
        hoverVideoAudio.preload = 'auto';
        hoverVideoAudio.volume = 0.62;
        hoverVideoAudioRef.current = hoverVideoAudio;
      } catch {
        hoverVideoAudioRef.current = null;
      }
    }

    return () => {
      clearHoverVideoStopTimer();

      const hoverVideoAudio = hoverVideoAudioRef.current;
      hoverVideoAudioRef.current = null;
      if (hoverVideoAudio) {
        try {
          hoverVideoAudio.pause();
          hoverVideoAudio.currentTime = 0;
          hoverVideoAudio.src = '';
        } catch {
          // Ignore cleanup errors.
        }
      }

      const context = hoverAudioContextRef.current;
      hoverAudioContextRef.current = null;
      if (context) {
        void context.close();
      }
    };
  }, []);

  const playSynthHoverSfx = () => {
    try {
      const audioContextCtor =
        window.AudioContext ||
        (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!audioContextCtor) {
        return;
      }

      const audioContext = hoverAudioContextRef.current ?? new audioContextCtor();
      hoverAudioContextRef.current = audioContext;
      if (audioContext.state === 'suspended') {
        void audioContext.resume();
      }

      const startAt = audioContext.currentTime;
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = 'triangle';
      oscillator.frequency.setValueAtTime(1320, startAt);
      oscillator.frequency.exponentialRampToValueAtTime(960, startAt + 0.09);
      gain.gain.setValueAtTime(0.0001, startAt);
      gain.gain.exponentialRampToValueAtTime(0.035, startAt + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, startAt + 0.13);
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start(startAt);
      oscillator.stop(startAt + 0.13);
    } catch {
      // Ignore playback errors to avoid blocking entry behavior.
    }
  };

  const playHoverSelectionSfx = () => {
    if (enterDisabled || typeof window === 'undefined') {
      return;
    }

    const now = Date.now();
    if (now - hoverSfxLastPlayedAtRef.current < 120) {
      return;
    }
    hoverSfxLastPlayedAtRef.current = now;

    const hoverVideoAudio = hoverVideoAudioRef.current;
    if (hoverVideoAudio) {
      try {
        clearHoverVideoStopTimer();
        hoverVideoAudio.pause();
        hoverVideoAudio.currentTime = 0;

        const playback = hoverVideoAudio.play();
        hoverVideoStopTimerRef.current = window.setTimeout(() => {
          const currentAudio = hoverVideoAudioRef.current;
          if (!currentAudio) {
            return;
          }
          currentAudio.pause();
          currentAudio.currentTime = 0;
        }, 220);

        if (playback && typeof playback.catch === 'function') {
          void playback.catch(() => {
            clearHoverVideoStopTimer();
            playSynthHoverSfx();
          });
        }
        return;
      } catch {
        // Fallback to synth sfx below.
      }
    }

    playSynthHoverSfx();
  };

  return (
    <div className="training-mainhome">
      <h1 className="training-mainhome__title">
        烽火笔锋
        <TrainingTitleFire className="training-mainhome__title-fire" text="烽火笔锋" />
      </h1>

      <div className="training-mainhome__action">
        <button
          type="button"
          className="training-mainhome__entry-ribbon training-mainhome__start"
          disabled={enterDisabled}
          onMouseEnter={playHoverSelectionSfx}
          onFocus={playHoverSelectionSfx}
          onClick={() => {
            void onEnter();
          }}
        >
          <svg
            className="training-mainhome__entry-lines"
            viewBox="0 0 1200 120"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              className="training-mainhome__entry-line training-mainhome__entry-line--silver"
              d="M -120 42 C 80 92, 220 18, 430 62 C 620 92, 780 22, 960 58 C 1060 74, 1130 36, 1240 36"
            />
            <path
              className="training-mainhome__entry-line training-mainhome__entry-line--black"
              d="M -120 70 C 70 16, 220 96, 390 56 C 560 18, 760 94, 940 54 C 1040 36, 1130 46, 1240 60"
            />
            <path
              className="training-mainhome__entry-line training-mainhome__entry-line--silver"
              d="M -120 86 C 120 42, 300 90, 500 48 C 700 20, 900 82, 1080 48 C 1140 40, 1190 44, 1240 54"
            />
          </svg>
          <span className="training-mainhome__entry-label">
            点击任意处进入训练
          </span>
        </button>
      </div>
    </div>
  );
}

export default TrainingMainHome;
