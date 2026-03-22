import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import AppStory from '../../src/apps/story/AppStory';
import '../../src/index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppStory />
  </StrictMode>
);
