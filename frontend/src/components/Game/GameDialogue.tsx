import type { PlayerOption } from '@/types/game';

export interface GameDialogueProps {
  currentDialogue: string;
  currentOptions: PlayerOption[];
  loading: boolean;
  optionsDisabledReason: string | null;
  onOptionSelect: (index: number) => void;
}

export default function GameDialogue({
  currentDialogue,
  currentOptions,
  loading,
  optionsDisabledReason,
  onOptionSelect,
}: GameDialogueProps) {
  return (
    <div className="game-dialogue-container">
      {currentDialogue && (
        <div className="game-dialogue-box">
          <div className="dialogue-header">角色对话</div>
          <div className="dialogue-content">{currentDialogue}</div>
        </div>
      )}
      {optionsDisabledReason ? (
        <p className="game-dialogue-status">{optionsDisabledReason}</p>
      ) : null}
      {currentOptions.length > 0 && (
        <div className="game-options-container">
          {currentOptions.map((option, index) => (
            <button
              key={option.id}
              type="button"
              className="game-option-button"
              onClick={() => onOptionSelect(index)}
              disabled={loading || Boolean(optionsDisabledReason)}
            >
              {option.text}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
