/** 路由路径常量，与 router 配置一致 */
export const ROUTES = {
  HOME: '/',
  FIRST_STEP: '/firststep',
  CHARACTER_SETTING: '/charactersetting',
  CHARACTER_SELECTION: '/characterselection',
  FIRST_MEETING: '/firstmeeting',
  GAME: '/game',
  TRAINING: '/training',
  TRAINING_MAINHOME: '/training/mainhome',
  TRAINING_LANDING: '/training/landing',
  TRAINING_CINEMATIC_DEMO: '/training/cinematic-demo',
  TRAINING_PROGRESS: '/training/progress',
  TRAINING_REPORT: '/training/report',
  TRAINING_DIAGNOSTICS: '/training/diagnostics',
} as const;

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];

const normalizeSessionId = (sessionId?: string | null): string | null => {
  if (typeof sessionId !== 'string') {
    return null;
  }

  const normalized = sessionId.trim();
  return normalized === '' ? null : normalized;
};

const buildTrainingReadRoute = (basePath: string, sessionId?: string | null): string => {
  const normalizedSessionId = normalizeSessionId(sessionId);
  if (!normalizedSessionId) {
    return basePath;
  }

  const searchParams = new URLSearchParams({
    sessionId: normalizedSessionId,
  });
  return `${basePath}?${searchParams.toString()}`;
};

export const buildTrainingProgressRoute = (sessionId?: string | null): string =>
  buildTrainingReadRoute(ROUTES.TRAINING_PROGRESS, sessionId);

export const buildTrainingReportRoute = (sessionId?: string | null): string =>
  buildTrainingReadRoute(ROUTES.TRAINING_REPORT, sessionId);

export const buildTrainingDiagnosticsRoute = (sessionId?: string | null): string =>
  buildTrainingReadRoute(ROUTES.TRAINING_DIAGNOSTICS, sessionId);
