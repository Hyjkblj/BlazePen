import path from 'path';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv, searchForWorkspaceRoot } from 'vite';

interface CreateAppViteConfigOptions {
  rootDir: string;
  port: number;
  outDir: string;
  apiTargetEnvVar: string;
  defaultApiTarget: string;
}

export const resolveApiTarget = (
  configuredApiTarget: string | undefined,
  defaultApiTarget: string
): string => {
  const normalizedApiTarget = configuredApiTarget?.trim();
  return normalizedApiTarget ? normalizedApiTarget : defaultApiTarget;
};

export const createBackendProxy = (apiTarget: string) => ({
  '/api': {
    target: apiTarget,
    changeOrigin: true,
    secure: false,
  },
  '/static': {
    target: apiTarget,
    changeOrigin: true,
    secure: false,
  },
  '/health': {
    target: apiTarget,
    changeOrigin: true,
    secure: false,
  },
});

export const createAppViteConfig = ({
  rootDir,
  port,
  outDir,
  apiTargetEnvVar,
  defaultApiTarget,
}: CreateAppViteConfigOptions) =>
  defineConfig(({ mode }) => {
    const env = loadEnv(mode, __dirname, '');
    const apiTarget = resolveApiTarget(env[apiTargetEnvVar], defaultApiTarget);

    return {
      root: path.resolve(__dirname, rootDir),
      publicDir: path.resolve(__dirname, 'public'),
      plugins: [react()],
      resolve: {
        alias: {
          '@': path.resolve(__dirname, 'src'),
        },
      },
      server: {
        port,
        proxy: createBackendProxy(apiTarget),
        fs: {
          allow: [searchForWorkspaceRoot(__dirname), path.resolve(__dirname, 'src')],
        },
      },
      preview: {
        port,
      },
      base: './',
      build: {
        outDir: path.resolve(__dirname, outDir),
        assetsDir: 'assets',
        emptyOutDir: true,
        rollupOptions: {
          output: {
            manualChunks(id) {
              if (!id.includes('node_modules')) {
                return undefined;
              }

              if (
                id.includes('/react/') ||
                id.includes('/react-dom/') ||
                id.includes('/react-router/') ||
                id.includes('/react-router-dom/')
              ) {
                return 'vendor-react';
              }

              return undefined;
            },
          },
        },
      },
    };
  });
