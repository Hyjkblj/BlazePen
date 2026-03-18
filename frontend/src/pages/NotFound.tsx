import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import './NotFound.css';

function NotFound() {
  const navigate = useNavigate();

  return (
    <main className="not-found-page">
      <div className="not-found-panel">
        <div className="not-found-code">404</div>
        <h1 className="not-found-title">页面不存在</h1>
        <p className="not-found-description">抱歉，您访问的页面不存在或已被移动。</p>
        <button
          type="button"
          className="not-found-button"
          onClick={() => navigate(ROUTES.HOME)}
        >
          <span aria-hidden="true" className="not-found-button-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M12 3.17 4 9.3V20h5v-5h6v5h5V9.3l-8-6.13Zm0-2.5 10 7.66V22h-9v-5h-2v5H2V8.33L12 .67Z" />
            </svg>
          </span>
          返回首页
        </button>
      </div>
    </main>
  );
}

export default NotFound;
