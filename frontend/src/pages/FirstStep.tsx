import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Modal, App as AntdApp } from 'antd';
import {
  FileTextOutlined,
  LogoutOutlined,
  PlayCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import backgroundImage from '@/assets/images/firstbackground.jpg';
import LoadingScreen from '@/components/loading';
import { ROUTES } from '@/config/routes';
import { useGameFlow } from '@/contexts';
import { checkServerHealth } from '@/services/healthApi';
import * as gameStorage from '@/storage/gameStorage';
import './FirstStep.css';

function FirstStep() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const { setRestoreSession } = useGameFlow();
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('正在连接服务器...');

  const handleContinueGame = async () => {
    const saveData = gameStorage.getMainGameSave();
    if (!saveData?.threadId) {
      message.warning('没有找到存档，请先开始新的故事。');
      return;
    }

    setLoading(true);
    setLoadingMessage('正在连接服务器...');

    try {
      const isHealthy = await checkServerHealth();
      if (!isHealthy) {
        message.error('无法连接到服务器，请检查后端服务是否运行。');
        return;
      }

      setRestoreSession(saveData.threadId, saveData.characterId ?? null);
      setLoadingMessage('正在加载存档...');
      await new Promise((resolve) => setTimeout(resolve, 500));
      navigate(ROUTES.GAME);
    } catch {
      message.error('连接服务器失败，请稍后重试。');
    } finally {
      setLoading(false);
    }
  };

  const handleNewStory = () => {
    navigate(ROUTES.CHARACTER_SETTING);
  };

  const handleSettings = () => {
    Modal.info({
      title: '游戏设置',
      content: (
        <div>
          <p>设置功能开发中...</p>
          <p>未来将包含：</p>
          <ul>
            <li>音量调节</li>
            <li>画面设置</li>
            <li>快捷键设置</li>
            <li>语言选择</li>
          </ul>
        </div>
      ),
      okText: '确定',
      width: 400,
    });
  };

  const handleExit = () => {
    Modal.confirm({
      title: '确认退出',
      content: '确定要退出游戏吗？',
      okText: '退出',
      cancelText: '取消',
      okType: 'danger',
      onOk: () => navigate(ROUTES.HOME),
    });
  };

  if (loading) {
    return <LoadingScreen message={loadingMessage} />;
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '100vh',
        backgroundImage: `url(${backgroundImage})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '40px 60px',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.1)',
          zIndex: 1,
        }}
      />

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

      <div
        style={{
          position: 'relative',
          zIndex: 2,
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
          minWidth: '280px',
        }}
      >
        <Button
          type="primary"
          size="large"
          icon={<FileTextOutlined />}
          onClick={handleContinueGame}
          className="continue-game-button"
          style={{
            fontSize: '20px',
            height: '60px',
            padding: '0 40px',
            background: 'linear-gradient(135deg, #ffd700 0%, #ffb347 100%)',
            border: '2px solid #ff8c00',
            borderRadius: '8px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            boxShadow:
              '0 4px 15px rgba(255, 215, 0, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3)',
            transition: 'all 0.3s ease',
            color: '#fff',
          }}
        >
          继续游戏
        </Button>

        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={handleNewStory}
          className="new-story-button"
          style={{
            fontSize: '20px',
            height: '60px',
            padding: '0 40px',
            background: 'linear-gradient(135deg, #ffd700 0%, #ffb347 100%)',
            border: '2px solid #ff8c00',
            borderRadius: '8px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            boxShadow:
              '0 4px 15px rgba(255, 215, 0, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3)',
            transition: 'all 0.3s ease',
            color: '#fff',
          }}
        >
          新的故事
        </Button>
      </div>

      <div
        style={{
          position: 'absolute',
          bottom: '40px',
          left: '60px',
          zIndex: 2,
          display: 'flex',
          gap: '16px',
        }}
      >
        <Button
          type="default"
          size="large"
          icon={<SettingOutlined />}
          onClick={handleSettings}
          style={{
            fontSize: '16px',
            height: '50px',
            padding: '0 24px',
            background: 'rgba(255, 255, 255, 0.9)',
            border: '2px solid rgba(255, 140, 0, 0.5)',
            borderRadius: '8px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(10px)',
          }}
          onMouseEnter={(event) => {
            event.currentTarget.style.transform = 'scale(1.05)';
            event.currentTarget.style.background = 'rgba(255, 255, 255, 1)';
            event.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
          }}
          onMouseLeave={(event) => {
            event.currentTarget.style.transform = 'scale(1)';
            event.currentTarget.style.background = 'rgba(255, 255, 255, 0.9)';
            event.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)';
          }}
        >
          设置
        </Button>

        <Button
          type="default"
          size="large"
          icon={<LogoutOutlined />}
          onClick={handleExit}
          style={{
            fontSize: '16px',
            height: '50px',
            padding: '0 24px',
            background: 'rgba(255, 255, 255, 0.9)',
            border: '2px solid rgba(255, 77, 79, 0.5)',
            borderRadius: '8px',
            fontWeight: 'bold',
            letterSpacing: '1px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(10px)',
            color: '#ff4d4f',
          }}
          onMouseEnter={(event) => {
            event.currentTarget.style.transform = 'scale(1.05)';
            event.currentTarget.style.background = 'rgba(255, 77, 79, 0.1)';
            event.currentTarget.style.borderColor = '#ff4d4f';
            event.currentTarget.style.boxShadow = '0 4px 12px rgba(255, 77, 79, 0.3)';
          }}
          onMouseLeave={(event) => {
            event.currentTarget.style.transform = 'scale(1)';
            event.currentTarget.style.background = 'rgba(255, 255, 255, 0.9)';
            event.currentTarget.style.borderColor = 'rgba(255, 77, 79, 0.5)';
            event.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)';
          }}
        >
          退出
        </Button>
      </div>
    </div>
  );
}

export default FirstStep;
