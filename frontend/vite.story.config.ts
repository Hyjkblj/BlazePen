import { createAppViteConfig } from './vite.app.config';

export default createAppViteConfig({
  rootDir: 'apps/story',
  port: 3000,
  outDir: 'dist',
  apiTargetEnvVar: 'VITE_STORY_API_TARGET',
  defaultApiTarget: 'http://localhost:8000',
});
