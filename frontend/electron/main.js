import { app, BrowserWindow, session, screen } from 'electron';
import path from 'path';
import { existsSync } from 'fs';
import { spawn } from 'child_process';
import { fileURLToPath, pathToFileURL } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
const DEFAULT_LOCAL_BACKEND_ORIGIN = 'http://localhost:8000';
const DEFAULT_REMOTE_BACKEND_ORIGIN = 'http://8.166.138.219';
const BACKEND_ORIGIN = (
  process.env.NO_END_STORY_BACKEND_ORIGIN ||
  (app.isPackaged ? DEFAULT_REMOTE_BACKEND_ORIGIN : DEFAULT_LOCAL_BACKEND_ORIGIN)
).replace(/\/+$/, '');
const BACKEND_HEALTH_URL = `${BACKEND_ORIGIN}/health`;
const BACKEND_BOOT_TIMEOUT_MS = 120000;
const ASPECT_RATIO = 16 / 9;
let backendBootPromise = null;
let redirectHookInstalled = false;

function normalizeFilePathname(pathname) {
  // On Windows, file:///D:/health becomes /D:/health. Strip drive letter for route matching.
  return pathname.replace(/^\/[A-Za-z]:/, '');
}

function resolveBackendProxyPath(requestUrl) {
  try {
    const url = new URL(requestUrl);
    if (url.protocol !== 'file:') return null;

    const pathname = normalizeFilePathname(url.pathname);
    const isApi = pathname === '/api' || pathname.startsWith('/api/');
    const isStatic = pathname === '/static' || pathname.startsWith('/static/');
    const isHealth = pathname === '/health';

    if (isApi || isStatic || isHealth) {
      return `${pathname}${url.search}`;
    }
  } catch {
    // Ignore malformed URL and fall through to no-redirect.
  }
  return null;
}

/** 在给定最大宽高内计算最大的 16:9 尺寸 */
function get16by9Size(maxWidth, maxHeight) {
  let width = maxWidth;
  let height = Math.round(width / ASPECT_RATIO);
  if (height > maxHeight) {
    height = maxHeight;
    width = Math.round(height * ASPECT_RATIO);
  }
  return { width, height };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function checkBackendHealth() {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3000);
    const response = await fetch(BACKEND_HEALTH_URL, { method: 'GET', signal: controller.signal });
    clearTimeout(timer);
    return response.ok;
  } catch {
    return false;
  }
}

async function waitBackendHealthy(timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await checkBackendHealth()) return true;
    await sleep(2000);
  }
  return false;
}

function shouldAutoStartBackend() {
  if (process.platform !== 'win32') return false;
  if (process.env.NO_END_STORY_DISABLE_AUTO_BACKEND === '1') return false;
  if (app.isPackaged) return process.env.NO_END_STORY_AUTO_BACKEND === '1';
  return process.env.NO_END_STORY_AUTO_BACKEND === '1';
}

function resolveStartScriptPath() {
  const scriptPath = app.isPackaged
    ? path.join(process.resourcesPath, 'scripts', 'start_stack.bat')
    : path.resolve(__dirname, '../../scripts/start_stack.bat');

  return existsSync(scriptPath) ? scriptPath : null;
}

function runStartScript(scriptPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(scriptPath, [], {
      shell: true,
      windowsHide: true,
      cwd: path.dirname(scriptPath),
    });

    let stderr = '';

    child.stdout?.on('data', (data) => {
      const text = String(data).trim();
      if (text) console.log(`[backend-stack] ${text}`);
    });

    child.stderr?.on('data', (data) => {
      const text = String(data).trim();
      if (text) {
        stderr += `${text}\n`;
        console.error(`[backend-stack] ${text}`);
      }
    });

    child.on('error', (error) => reject(error));
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`start_stack.bat exited with code ${code}. ${stderr}`.trim()));
      }
    });
  });
}

async function ensureBackendReady() {
  if (await checkBackendHealth()) return;
  if (!shouldAutoStartBackend()) return;
  if (backendBootPromise) return backendBootPromise;

  backendBootPromise = (async () => {
    const scriptPath = resolveStartScriptPath();
    if (!scriptPath) {
      throw new Error('start_stack.bat not found in resources/scripts');
    }

    await runStartScript(scriptPath);

    const healthy = await waitBackendHealthy(BACKEND_BOOT_TIMEOUT_MS);
    if (!healthy) {
      throw new Error('Backend health check timed out after start_stack.bat');
    }
  })();

  try {
    await backendBootPromise;
  } finally {
    backendBootPromise = null;
  }
}

function createWindow() {
  // 生产环境：从 file:// 加载时，将 /api、/static、/health 请求转发到本地后端
  if (!isDev && !redirectHookInstalled) {
    session.defaultSession.webRequest.onBeforeRequest({ urls: ['file://*'] }, (details, callback) => {
      const proxyPath = resolveBackendProxyPath(details.url);
      if (proxyPath) {
        callback({ redirectURL: `${BACKEND_ORIGIN}${proxyPath}` });
        return;
      }
      callback({});
    });
    redirectHookInstalled = true;
  }

  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: maxWidth, height: maxHeight } = primaryDisplay.workAreaSize;
  const { width, height } = get16by9Size(maxWidth, maxHeight);
  const { x, y } = primaryDisplay.workArea;
  const offsetX = Math.max(0, Math.floor((maxWidth - width) / 2));
  const offsetY = Math.max(0, Math.floor((maxHeight - height) / 2));

  const win = new BrowserWindow({
    width,
    height,
    minWidth: 800,
    minHeight: 450,
    x: x + offsetX,
    y: y + offsetY,
    titleBarStyle: 'default',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
    },
    icon: path.join(__dirname, '../build/icon.png'), // 如果有图标的话
  });

  // 开发环境加载本地服务器，生产环境加载打包文件
  if (isDev) {
    win.loadURL('http://localhost:3000');
  } else {
    // 生产环境加载打包后的文件
    const distIndexPath = path.join(__dirname, '../dist/index.html');
    const distIndexUrl = pathToFileURL(distIndexPath);
    distIndexUrl.hash = '/';
    win.loadURL(distIndexUrl.toString());
  }

  // 窗口关闭事件
  win.on('closed', () => {
    // 在macOS上，即使所有窗口关闭，应用通常也会继续运行
  });
}

// 当Electron完成初始化并准备创建浏览器窗口时调用
app.whenReady().then(async () => {
  try {
    await ensureBackendReady();
  } catch (error) {
    console.error('[backend-stack] failed to ensure local backend stack:', error);
  }

  createWindow();

  // macOS特定：当没有窗口打开时，点击dock图标会重新创建窗口
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 所有窗口关闭时退出应用（macOS除外）
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 安全：防止新窗口打开
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
  });
});
