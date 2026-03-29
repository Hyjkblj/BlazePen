import { createAppViteConfig } from './vite.app.config';

export default createAppViteConfig({
  rootDir: 'apps/training',
  port: 3001,
  outDir: 'dist-training',
  base: '/',
  apiTargetEnvVar: 'VITE_TRAINING_API_TARGET',
  defaultApiTarget: 'http://localhost:8010',
});
