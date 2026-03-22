import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ConfigEnv, UserConfig, UserConfigExport } from 'vite';
import storyConfig from './vite.story.config';
import trainingConfig from './vite.training.config';

const resolveConfig = async (configExport: UserConfigExport): Promise<UserConfig> => {
  if (typeof configExport === 'function') {
    return await configExport({
      command: 'serve',
      mode: 'test',
      isSsrBuild: false,
      isPreview: false,
    } as ConfigEnv);
  }

  return configExport;
};

describe('vite app config', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('routes the story frontend to the story backend by default', async () => {
    const config = await resolveConfig(storyConfig);
    expect(config.server?.proxy).toMatchObject({
      '/api': {
        target: 'http://localhost:8000',
      },
      '/static': {
        target: 'http://localhost:8000',
      },
      '/health': {
        target: 'http://localhost:8000',
      },
    });
  });

  it('routes the training frontend to the training backend by default', async () => {
    const config = await resolveConfig(trainingConfig);
    expect(config.server?.proxy).toMatchObject({
      '/api': {
        target: 'http://localhost:8010',
      },
      '/static': {
        target: 'http://localhost:8010',
      },
      '/health': {
        target: 'http://localhost:8010',
      },
    });
  });

  it('allows the training backend target to be overridden explicitly', async () => {
    vi.stubEnv('VITE_TRAINING_API_TARGET', 'http://localhost:9010');

    const config = await resolveConfig(trainingConfig);
    expect(config.server?.proxy).toMatchObject({
      '/api': {
        target: 'http://localhost:9010',
      },
    });
  });
});
