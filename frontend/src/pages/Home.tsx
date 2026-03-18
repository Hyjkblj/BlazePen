import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Typography, Button, App as AntdApp } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import backgroundImage from '@/assets/images/home-background.jpg';
import LoadingScreen from '@/components/loading';
import { checkServerHealth } from '@/services/healthApi';
import { ROUTES } from '@/config/routes';

const { Title } = Typography;

function Home() {
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [loading, setLoading] = useState(false);

  const handleBegin = async () => {
    setLoading(true);

    try {
      const isHealthy = await checkServerHealth();
      if (isHealthy) {
        navigate(ROUTES.FIRST_STEP);
      } else {
        message.error('无法连接到服务器，请检查后端服务是否运行。');
      }
    } catch {
      message.error('连接服务器失败，请稍后重试。');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingScreen message="正在连接服务器..." />;
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
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.2)',
          zIndex: 1,
        }}
      />

      <div
        style={{
          position: 'relative',
          zIndex: 2,
          textAlign: 'center',
          width: '100%',
          maxWidth: '800px',
        }}
      >
        <div style={{ marginBottom: '60px' }}>
          <Title
            level={1}
            style={{
              fontSize: '64px',
              fontWeight: 'bold',
              color: '#ff8c00',
              textShadow: '3px 3px 6px rgba(0, 0, 0, 0.5), 0 0 10px rgba(255, 140, 0, 0.5)',
              marginBottom: '10px',
              lineHeight: '1.2',
              fontFamily: 'Arial Black, sans-serif',
              letterSpacing: '2px',
            }}
          >
            NO ENDING
          </Title>
          <Title
            level={1}
            style={{
              fontSize: '80px',
              fontWeight: 'bold',
              color: '#ffd700',
              textShadow: '3px 3px 6px rgba(0, 0, 0, 0.5), 0 0 10px rgba(255, 215, 0, 0.5)',
              marginTop: '0',
              lineHeight: '1.2',
              fontFamily: 'Arial Black, sans-serif',
              letterSpacing: '2px',
            }}
          >
            Story
          </Title>
        </div>

        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={handleBegin}
          style={{
            fontSize: '24px',
            height: '60px',
            padding: '0 40px',
            background: 'linear-gradient(135deg, #ffa500 0%, #ff8c00 100%)',
            border: '3px solid #ff6b00',
            borderRadius: '8px',
            fontWeight: 'bold',
            textTransform: 'uppercase',
            letterSpacing: '2px',
            boxShadow: '0 4px 15px rgba(255, 140, 0, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3)',
            transition: 'all 0.3s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(255, 140, 0, 0.6), inset 0 2px 5px rgba(255, 255, 255, 0.4)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = '0 4px 15px rgba(255, 140, 0, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3)';
          }}
        >
          BEGIN
        </Button>
      </div>
    </div>
  );
}

export default Home;
