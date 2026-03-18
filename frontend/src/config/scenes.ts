/**
 * 场景配置
 * 前端直接从静态文件服务获取场景图片，不依赖后端API
 */

export interface SceneConfig {
  id: string;
  name: string;
  description: string;
  imageExtensions?: string[]; // 支持的图片扩展名
}

// 场景配置列表（根据 backend/images/scenes 目录中的文件）
// 格式：{scene_id}_{场景名称}.{ext}
export const SCENE_CONFIGS: SceneConfig[] = [
  {
    id: 'cafe_nearby',
    name: '咖啡厅',
    description: '在温馨的咖啡厅里偶然邂逅',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'restaurant',
    name: '餐厅',
    description: '在优雅的餐厅中初次相遇',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'convenience_store',
    name: '便利店',
    description: '在便利店里不期而遇',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'company',
    name: '公司',
    description: '在公司里初次见面',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'zoo',
    name: '动物园',
    description: '在动物园中初次相遇',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'aquarium',
    name: '水族馆',
    description: '在水族馆里不期而遇',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'amusement_park',
    name: '游乐园',
    description: '在游乐园中初次相遇',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'badminton_court',
    name: '羽毛球场',
    description: '在羽毛球场遇见',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'study_room',
    name: '自习室',
    description: '在自习室中不期而遇',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
  {
    id: 'street',
    name: '马路',
    description: '在马路上初次相遇',
    imageExtensions: ['.jpeg', '.jpg', '.png', '.webp'],
  },
];

/**
 * 构建场景图片URL
 * 格式：/static/images/scenes/{scene_id}_{场景名称}.{ext}
 * 注意：需要对中文进行URL编码
 */
export function buildSceneImageUrl(sceneId: string, sceneName: string, extension: string = '.jpeg'): string {
  // 对场景名称进行URL编码，确保中文文件名能正确访问
  const encodedSceneName = encodeURIComponent(sceneName);
  return `/static/images/scenes/${sceneId}_${encodedSceneName}${extension}`;
}

/**
 * 尝试获取场景图片URL（按优先级尝试不同扩展名）
 */
export function getSceneImageUrl(scene: SceneConfig): string | null {
  const extensions = scene.imageExtensions || ['.jpeg', '.jpg', '.png', '.webp'];
  const url = buildSceneImageUrl(scene.id, scene.name, extensions[0]);
  return url;
}

/** 场景 ID -> 中文名（先查 SCENE_CONFIGS，再查扩展表；小场景等未在 config 中的用扩展表） */
const SCENE_NAME_MAP: Record<string, string> = {
  school: '学校',
  library: '图书馆',
  classroom: '教室',
  cafeteria: '食堂',
  playground: '操场',
  dormitory: '宿舍',
  campus_path: '校园小径',
  school_gate: '校门口',
  rooftop: '天台',
  gym: '体育馆',
  cafe_nearby: '咖啡厅',
  bookstore: '书店',
  restaurant: '餐厅',
  convenience_store: '便利店',
  company: '公司',
  zoo: '动物园',
  aquarium: '水族馆',
  amusement_park: '游乐园',
  badminton_court: '羽毛球场',
  study_room: '自习室',
  street: '马路',
};

/**
 * 根据场景 ID 返回中文名称，与 SCENE_CONFIGS 及扩展表一致
 */
export function getSceneNameById(sceneId: string): string {
  const fromConfig = SCENE_CONFIGS.find((c) => c.id === sceneId);
  if (fromConfig) return fromConfig.name;
  return SCENE_NAME_MAP[sceneId] ?? sceneId;
}
