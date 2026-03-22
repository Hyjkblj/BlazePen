import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import AppStory from './apps/story/AppStory';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppStory />
  </StrictMode>
);
