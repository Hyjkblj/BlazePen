// API响应类型
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

// 用户相关类型
export interface User {
  id: string;
  username: string;
  email?: string;
  createdAt: string;
}

// 故事线程类型
export interface Thread {
  id: string;
  userId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

// 对话消息类型
export interface Message {
  id: string;
  threadId: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

// 故事状态类型
export interface StoryState {
  id: string;
  threadId: string;
  currentScene: string;
  characters: Record<string, unknown>;
  emotions: Record<string, number>;
  metadata: Record<string, unknown>;
}
