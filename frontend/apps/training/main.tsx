import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import AppTraining from '../../src/apps/training/AppTraining';
import '../../src/index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppTraining />
  </StrictMode>
);
