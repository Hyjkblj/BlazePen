/** 路由路径常量，与 router 配置一致 */
export const ROUTES = {
  HOME: '/',
  FIRST_STEP: '/firststep',
  CHARACTER_SETTING: '/charactersetting',
  CHARACTER_SELECTION: '/characterselection',
  FIRST_MEETING: '/firstmeeting',
  GAME: '/game',
} as const;

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES];
