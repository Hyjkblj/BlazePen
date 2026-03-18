import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildBackendRedirectUrl,
  getBackendProxyPath,
  isAllowedWindowNavigation,
  normalizeFilePathname,
} from '../../electron/navigationPolicy.js';

test('normalizeFilePathname strips Windows drive prefix but preserves route path', () => {
  assert.equal(normalizeFilePathname('/D:/api/characters'), '/api/characters');
  assert.equal(normalizeFilePathname('/static/images/demo.png'), '/static/images/demo.png');
});

test('getBackendProxyPath only proxies api, static, and health file routes', () => {
  assert.equal(
    getBackendProxyPath('file:///D:/api/characters?scene=school'),
    '/api/characters?scene=school'
  );
  assert.equal(
    getBackendProxyPath('file:///D:/static/images/demo.png'),
    '/static/images/demo.png'
  );
  assert.equal(getBackendProxyPath('file:///D:/health'), '/health');
  assert.equal(getBackendProxyPath('file:///D:/assets/index.js'), null);
  assert.equal(getBackendProxyPath('https://example.com/api/characters'), null);
  assert.equal(getBackendProxyPath('not-a-url'), null);
});

test('buildBackendRedirectUrl preserves backend origin and request query', () => {
  assert.equal(
    buildBackendRedirectUrl('file:///D:/api/characters?scene=school', 'http://localhost:8000/'),
    'http://localhost:8000/api/characters?scene=school'
  );
  assert.equal(
    buildBackendRedirectUrl('file:///D:/static/images/demo.png', 'https://server.example.com'),
    'https://server.example.com/static/images/demo.png'
  );
  assert.equal(buildBackendRedirectUrl('file:///D:/assets/index.js', 'http://localhost:8000'), null);
  assert.equal(buildBackendRedirectUrl('not-a-url', 'http://localhost:8000'), null);
});

test('isAllowedWindowNavigation allows only approved origins in dev', () => {
  assert.equal(
    isAllowedWindowNavigation('http://localhost:3000/game', {
      isDev: true,
      frontendDevOrigin: 'http://localhost:3000',
    }),
    true
  );
  assert.equal(
    isAllowedWindowNavigation('https://example.com/game', {
      isDev: true,
      frontendDevOrigin: 'http://localhost:3000',
    }),
    false
  );
});

test('isAllowedWindowNavigation allows only file protocol in packaged mode', () => {
  assert.equal(
    isAllowedWindowNavigation('file:///D:/Develop/Project/BlazePen/frontend/dist/index.html#/', {
      isDev: false,
      frontendDevOrigin: 'http://localhost:3000',
    }),
    true
  );
  assert.equal(
    isAllowedWindowNavigation('http://localhost:3000/game', {
      isDev: false,
      frontendDevOrigin: 'http://localhost:3000',
    }),
    false
  );
  assert.equal(
    isAllowedWindowNavigation('not-a-url', {
      isDev: false,
      frontendDevOrigin: 'http://localhost:3000',
    }),
    false
  );
});
