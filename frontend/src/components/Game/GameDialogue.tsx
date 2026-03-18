import { Button } from 'antd';
import type { PlayerOption } from '@/types/game';

export interface GameDialogueProps {
  currentDialogue: string;
  currentOptions: PlayerOption[];
  loading: boolean;
  onOptionSelect: (index: number) => void;
}

export default function GameDialogue({
  currentDialogue,
  currentOptions,
  loading,
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
      {currentOptions.length > 0 && (
        <div className="game-options-container">
          {currentOptions.map((option, index) => (
            <Button
              key={option.id}
              className="game-option-button"
              onClick={() => onOptionSelect(index)}
              disabled={loading}
            >
              {option.text}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
