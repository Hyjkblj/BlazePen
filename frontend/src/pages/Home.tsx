import backgroundImage from '@/assets/images/home-background.jpg';
import LoadingScreen from '@/components/loading';
import { useHomeFlow } from '@/flows/useHomeFlow';

function Home() {
  const { loading, errorMessage, beginStory, openTraining, hasTrainingResumeTarget } =
    useHomeFlow();

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
          inset: 0,
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
              marginTop: 0,
              lineHeight: '1.2',
              fontFamily: 'Arial Black, sans-serif',
              letterSpacing: '2px',
            }}
          >
            Story
          </h1>
        </div>

        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '16px',
          }}
        >
          <button
            type="button"
            onClick={() => {
              void beginStory();
            }}
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
              boxShadow:
                '0 4px 15px rgba(255, 140, 0, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3)',
              transition: 'all 0.3s ease',
            }}
            onMouseEnter={(event) => {
              event.currentTarget.style.transform = 'scale(1.05)';
              event.currentTarget.style.boxShadow =
                '0 6px 20px rgba(255, 140, 0, 0.6), inset 0 2px 5px rgba(255, 255, 255, 0.4)';
            }}
            onMouseLeave={(event) => {
              event.currentTarget.style.transform = 'scale(1)';
              event.currentTarget.style.boxShadow =
                '0 4px 15px rgba(255, 140, 0, 0.4), inset 0 2px 5px rgba(255, 255, 255, 0.3)';
            }}
          >
            <span aria-hidden="true" style={{ display: 'inline-flex', width: '26px', height: '26px' }}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="26" height="26">
                <path d="M12 2a10 10 0 1 0 10 10A10.01 10.01 0 0 0 12 2Zm-1.5 14.5v-9l7 4.5Z" />
              </svg>
            </span>
            BEGIN
          </button>

          <button
            type="button"
            onClick={openTraining}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              fontSize: '20px',
              height: '60px',
              padding: '0 32px',
              background:
                'linear-gradient(135deg, rgba(11, 57, 84, 0.96) 0%, rgba(17, 84, 120, 0.95) 100%)',
              border: '3px solid rgba(125, 210, 255, 0.78)',
              borderRadius: '8px',
              fontWeight: 'bold',
              color: '#eff9ff',
              cursor: 'pointer',
              textTransform: 'uppercase',
              letterSpacing: '1.6px',
              boxShadow:
                '0 4px 18px rgba(7, 39, 58, 0.38), inset 0 2px 5px rgba(255, 255, 255, 0.14)',
              transition: 'all 0.3s ease',
            }}
            onMouseEnter={(event) => {
              event.currentTarget.style.transform = 'scale(1.05)';
              event.currentTarget.style.boxShadow =
                '0 8px 24px rgba(7, 39, 58, 0.5), inset 0 2px 5px rgba(255, 255, 255, 0.2)';
            }}
            onMouseLeave={(event) => {
              event.currentTarget.style.transform = 'scale(1)';
              event.currentTarget.style.boxShadow =
                '0 4px 18px rgba(7, 39, 58, 0.38), inset 0 2px 5px rgba(255, 255, 255, 0.14)';
            }}
          >
            <span aria-hidden="true" style={{ display: 'inline-flex', width: '22px', height: '22px' }}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="22" height="22">
                <path d="M4 5h16v3H4zm0 5h10v3H4zm0 5h16v3H4z" />
              </svg>
            </span>
            {hasTrainingResumeTarget ? 'Resume Training' : 'Training Mode'}
          </button>
        </div>

        {errorMessage ? (
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
        ) : null}
      </div>
    </div>
  );
}

export default Home;
