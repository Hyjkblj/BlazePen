import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import backgroundImage from '@/assets/images/home-background.jpg';
import LoadingScreen from '@/components/loading';
import { checkServerHealth } from '@/services/healthApi';
import { ROUTES } from '@/config/routes';

function Home() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleBegin = async () => {
    setErrorMessage(null);
    setLoading(true);

    try {
      const isHealthy = await checkServerHealth();
      if (isHealthy) {
        navigate(ROUTES.FIRST_STEP);
      } else {
        setErrorMessage('无法连接到服务器，请检查后端服务是否运行。');
      }
    } catch {
      setErrorMessage('连接服务器失败，请稍后重试。');
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
          <h1
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
          </h1>
          <h1
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
          </h1>
        </div>

        <button
          type="button"
          onClick={handleBegin}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            fontSize: '24px',
            height: '60px',
            padding: '0 40px',
            background: 'linear-gradient(135deg, #ffa500 0%, #ff8c00 100%)',
            border: '3px solid #ff6b00',
            borderRadius: '8px',
            fontWeight: 'bold',
            color: '#fff',
            cursor: 'pointer',
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
          <span aria-hidden="true" style={{ display: 'inline-flex', width: '26px', height: '26px' }}>
            <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
              <path d="M12 2a10 10 0 1 0 10 10A10.01 10.01 0 0 0 12 2Zm-1.5 14.5v-9l7 4.5Z" />
            </svg>
          </span>
          BEGIN
        </button>

        {errorMessage && (
          <div
            role="alert"
            style={{
              marginTop: '20px',
              display: 'inline-block',
              maxWidth: '520px',
              padding: '12px 16px',
              background: 'rgba(92, 0, 17, 0.82)',
              border: '1px solid rgba(255, 163, 158, 0.75)',
              borderRadius: '10px',
              color: '#fff2f0',
              fontSize: '15px',
              lineHeight: '1.5',
              boxShadow: '0 10px 30px rgba(0, 0, 0, 0.18)',
              backdropFilter: 'blur(10px)',
            }}
          >
            {errorMessage}
          </div>
        )}
      </div>
    </div>
  );
}

export default Home;
