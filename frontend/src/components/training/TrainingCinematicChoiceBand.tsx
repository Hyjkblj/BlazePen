import { useMemo, useState, type KeyboardEvent } from 'react';
import type { TrainingScenarioOption } from '@/types/training';
import './TrainingCinematicChoiceBand.css';

type ChoiceSlot = 'left' | 'top' | 'right';

interface TrainingCinematicChoiceBandProps {
  options: TrainingScenarioOption[];
  selectedOptionId: string | null;
  onSelectOption: (optionId: string) => void;
  disabled?: boolean;
  ariaLabel?: string;
  narrativeLabels?: Record<string, string>;
}

const clampIndex = (index: number, optionCount: number): number => {
  if (optionCount <= 0) {
    return 0;
  }

  return Math.max(0, Math.min(optionCount - 1, index));
};

const resolveSlotMap = (optionCount: number): ChoiceSlot[] => {
  if (optionCount <= 1) {
    return ['top'];
  }

  if (optionCount === 2) {
    return ['left', 'right'];
  }

  return ['left', 'top', 'right'];
};

const findSelectedIndex = (
  options: TrainingScenarioOption[],
  selectedOptionId: string | null
): number => {
  if (!selectedOptionId) {
    return 0;
  }

  const nextIndex = options.findIndex((option) => option.id === selectedOptionId);
  return nextIndex >= 0 ? nextIndex : 0;
};

const buildSyncKey = (optionSignature: string, selectedOptionId: string | null): string =>
  `${optionSignature}::${selectedOptionId ?? ''}`;

interface ActiveNavigationState {
  syncKey: string;
  index: number | null;
}

function TrainingCinematicChoiceBand({
  options,
  selectedOptionId,
  onSelectOption,
  disabled = false,
  ariaLabel = 'Training cinematic choices',
  narrativeLabels,
}: TrainingCinematicChoiceBandProps) {
  const cinematicOptions = useMemo(() => options.slice(0, 3), [options]);
  const optionSignature = useMemo(
    () => cinematicOptions.map((option) => `${option.id}:${option.label}`).join('|'),
    [cinematicOptions]
  );
  const syncKey = useMemo(
    () => buildSyncKey(optionSignature, selectedOptionId),
    [optionSignature, selectedOptionId]
  );
  const selectedIndex = useMemo(
    () => findSelectedIndex(cinematicOptions, selectedOptionId),
    [cinematicOptions, selectedOptionId]
  );
  const [navigationState, setNavigationState] = useState<ActiveNavigationState>(() => ({
    syncKey,
    index: null,
  }));
  const activeIndex =
    navigationState.syncKey === syncKey && navigationState.index !== null
      ? clampIndex(navigationState.index, cinematicOptions.length)
      : selectedIndex;

  if (cinematicOptions.length === 0) {
    return null;
  }

  const slotMap = resolveSlotMap(cinematicOptions.length);

  const moveActiveIndex = (nextIndex: number) => {
    setNavigationState({
      syncKey,
      index: clampIndex(nextIndex, cinematicOptions.length),
    });
  };

  const handleSelect = (index: number) => {
    const nextIndex = clampIndex(index, cinematicOptions.length);
    const nextOption = cinematicOptions[nextIndex];
    if (!nextOption || disabled) {
      return;
    }

    setNavigationState({
      syncKey,
      index: nextIndex,
    });
    onSelectOption(nextOption.id);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (disabled || cinematicOptions.length === 0) {
      return;
    }

    const key = event.key.toLowerCase();

    if (event.key === 'ArrowLeft' || key === 'a') {
      event.preventDefault();
      moveActiveIndex(activeIndex - 1);
      return;
    }

    if (event.key === 'ArrowRight' || key === 'd') {
      event.preventDefault();
      moveActiveIndex(activeIndex + 1);
      return;
    }

    if (event.key === 'Home') {
      event.preventDefault();
      moveActiveIndex(0);
      return;
    }

    if (event.key === 'End') {
      event.preventDefault();
      moveActiveIndex(cinematicOptions.length - 1);
      return;
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleSelect(activeIndex);
    }
  };

  return (
    <section
      className={`training-cinematic-choice-band${disabled ? ' training-cinematic-choice-band--disabled' : ''}`}
      role="region"
      aria-label={ariaLabel}
      tabIndex={disabled ? -1 : 0}
      onKeyDown={handleKeyDown}
    >
      <div className="training-cinematic-choice-band__beam" aria-hidden="true" />
      <div className="training-cinematic-choice-band__reticle" aria-hidden="true">
        <span className="training-cinematic-choice-band__reticle-ring training-cinematic-choice-band__reticle-ring--outer" />
        <span className="training-cinematic-choice-band__reticle-ring training-cinematic-choice-band__reticle-ring--inner" />
        <span className="training-cinematic-choice-band__reticle-core" />
        <span className="training-cinematic-choice-band__reticle-axis training-cinematic-choice-band__reticle-axis--horizontal" />
        <span className="training-cinematic-choice-band__reticle-axis training-cinematic-choice-band__reticle-axis--vertical" />
      </div>

      {cinematicOptions.map((option, index) => {
        const isActive = index === activeIndex;
        const isSelected = option.id === selectedOptionId;

        return (
          <button
            key={option.id}
            type="button"
            className={[
              'training-cinematic-choice-band__option',
              isActive ? 'is-active' : '',
              isSelected ? 'is-selected' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            data-slot={slotMap[index]}
            onClick={() => handleSelect(index)}
            onMouseEnter={() => moveActiveIndex(index)}
            onFocus={() => moveActiveIndex(index)}
            disabled={disabled}
            aria-pressed={isSelected}
          >
            <span className="training-cinematic-choice-band__option-mark">
              OPTION {String(index + 1).padStart(2, '0')}
            </span>
            <strong className="training-cinematic-choice-band__option-label">{option.label}</strong>
            {option.impactHint ? (
              <span className="training-cinematic-choice-band__option-hint">
                {option.impactHint}
              </span>
            ) : null}
            {narrativeLabels?.[option.id] ? (
              <span className="training-cinematic-choice-band__option-narrative">
                {narrativeLabels[option.id]}
              </span>
            ) : null}
          </button>
        );
      })}
    </section>
  );
}

export default TrainingCinematicChoiceBand;
