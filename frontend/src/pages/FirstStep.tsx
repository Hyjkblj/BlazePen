import { useState } from 'react';
import backgroundImage from '@/assets/images/firstbackground.jpg';
import ModalDialog from '@/components/ModalDialog';
import { DocumentIcon, LogoutIcon, PlayIcon, SettingsIcon } from '@/components/icons';
import LoadingScreen from '@/components/loading';
import { useFirstStepFlow } from '@/flows/useFirstStepFlow';
import './FirstStep.css';

function FirstStep() {
  const { loading, loadingMessage, continueGame, startNewStory, exitToHome } = useFirstStepFlow();
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [showExitDialog, setShowExitDialog] = useState(false);

  if (loading) {
    return <LoadingScreen message={loadingMessage} />;
  }

  return (
    <div
      className="first-step-page"
      style={{
        backgroundImage: `url(${backgroundImage})`,
      }}
    >
      <div className="first-step-overlay" />

      <div className="sakura-container">
        {Array.from({ length: 20 }).map((_, index) => (
          <div
            key={index}
            className="sakura-petal"
            style={{
              left: `${(index * 5) % 100}%`,
              animationDelay: `${index * 0.5}s`,
              animationDuration: `${8 + (index % 5)}s`,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 20 20">
              <path
                d="M10 2C10 2 12 6 16 6C12 6 10 10 10 10C10 10 8 6 4 6C8 6 10 2 10 2Z"
                fill="#ffb3d9"
                opacity="0.8"
              />
            </svg>
          </div>
        ))}
      </div>

      <div className="first-step-actions">
        <button
          type="button"
          className="first-step-button first-step-button-primary"
          onClick={() => {
            void continueGame();
          }}
        >
          <span className="first-step-button-icon" aria-hidden="true">
            <DocumentIcon />
          </span>
          <span>继续游戏</span>
        </button>

        <button
          type="button"
          className="first-step-button first-step-button-primary"
          onClick={startNewStory}
        >
          <span className="first-step-button-icon" aria-hidden="true">
            <PlayIcon />
          </span>
          <span>新的故事</span>
        </button>
      </div>

      <div className="first-step-footer-actions">
        <button
          type="button"
          className="first-step-button first-step-button-secondary"
          onClick={() => setShowSettingsDialog(true)}
        >
          <span className="first-step-button-icon" aria-hidden="true">
            <SettingsIcon />
          </span>
          <span>设置</span>
        </button>

        <button
          type="button"
          className="first-step-button first-step-button-danger"
          onClick={() => setShowExitDialog(true)}
        >
          <span className="first-step-button-icon" aria-hidden="true">
            <LogoutIcon />
          </span>
          <span>退出</span>
        </button>
      </div>

      <ModalDialog
        open={showSettingsDialog}
        title="游戏设置"
        onClose={() => setShowSettingsDialog(false)}
        width={420}
        className="first-step-dialog"
        footer={
          <div className="first-step-dialog-actions">
            <button
              type="button"
              className="first-step-dialog-button first-step-dialog-button-primary"
              onClick={() => setShowSettingsDialog(false)}
            >
              确定
            </button>
          </div>
        }
      >
        <div className="first-step-dialog-content">
          <p>设置功能开发中...</p>
          <p>未来将包含：</p>
          <ul>
            <li>音量调节</li>
            <li>画面设置</li>
            <li>快捷键设置</li>
            <li>语言选择</li>
          </ul>
        </div>
      </ModalDialog>

      <ModalDialog
        open={showExitDialog}
        title="确认退出"
        onClose={() => setShowExitDialog(false)}
        width={420}
        className="first-step-dialog"
        footer={
          <div className="first-step-dialog-actions">
            <button
              type="button"
              className="first-step-dialog-button"
              onClick={() => setShowExitDialog(false)}
            >
              取消
            </button>
            <button
              type="button"
              className="first-step-dialog-button first-step-dialog-button-danger"
              onClick={() => {
                setShowExitDialog(false);
                exitToHome();
              }}
            >
              退出
            </button>
          </div>
        }
      >
        <div className="first-step-dialog-content">
          <p>确定要退出游戏吗？</p>
        </div>
      </ModalDialog>
    </div>
  );
}

export default FirstStep;
