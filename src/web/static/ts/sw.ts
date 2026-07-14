/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Service Worker entry point, compiled to a standalone static/sw.js (see vite.config.ts).
// Caches static assets and previously-viewed prompt API responses so the app remains
// usable offline (FR-009), per specs/004-mobile-responsive-ui.
//
// Typed against a minimal ambient ServiceWorkerGlobalScope shim (see below) rather than
// pulling in the full `webworker` lib, which would conflict with the `DOM` lib the rest
// of src/web/static/ts/** relies on (both declare an incompatible global `self`).

interface MinimalCache {
  match(request: Request | string): Promise<Response | undefined>;
  put(request: Request | string, response: Response): Promise<void>;
  keys(): Promise<readonly Request[]>;
  delete(request: Request | string): Promise<boolean>;
}

interface MinimalCacheStorage {
  open(cacheName: string): Promise<MinimalCache>;
  keys(): Promise<string[]>;
  delete(cacheName: string): Promise<boolean>;
}

interface ExtendableEvent extends Event {
  waitUntil(promise: Promise<unknown>): void;
}

interface FetchEvent extends Event {
  readonly request: Request;
  respondWith(response: Promise<Response> | Response): void;
}

interface ExtendableMessageEvent extends Event {
  readonly data: unknown;
  waitUntil?(promise: Promise<unknown>): void;
}

declare const self: {
  addEventListener(type: 'install' | 'activate', listener: (event: ExtendableEvent) => void): void;
  addEventListener(type: 'fetch', listener: (event: FetchEvent) => void): void;
  addEventListener(type: 'message', listener: (event: ExtendableMessageEvent) => void): void;
  skipWaiting(): Promise<void>;
  clients: { claim(): Promise<void> };
};

declare const caches: MinimalCacheStorage;

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `promptvault-static-${CACHE_VERSION}`;
const API_CACHE = `promptvault-api-${CACHE_VERSION}`;
const CURRENT_CACHES = [STATIC_CACHE, API_CACHE];

const STATIC_ASSET_PATH_PREFIXES = ['/static/'];

function isStaticAssetRequest(url: URL): boolean {
  return STATIC_ASSET_PATH_PREFIXES.some((prefix) => url.pathname.startsWith(prefix));
}

function isCacheablePromptApiRequest(request: Request, url: URL): boolean {
  return request.method === 'GET' && /^\/api\/prompts(\/|$)/.test(url.pathname);
}

function isNavigationRequest(request: Request): boolean {
  return request.mode === 'navigate';
}

self.addEventListener('install', (event) => {
  void self.skipWaiting();
  event.waitUntil(caches.open(STATIC_CACHE).then(() => undefined));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) =>
        Promise.all(
          cacheNames
            .filter((name) => !CURRENT_CACHES.includes(name))
            .map((name) => caches.delete(name))
        )
      )
      .then(() => self.clients.claim())
  );
});

async function cacheFirst(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }
  const response = await fetch(request);
  if (response.ok) {
    await cache.put(request, response.clone());
  }
  return response;
}

async function networkFirst(request: Request, cacheName: string): Promise<Response> {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) {
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    throw error;
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Cache navigations (the HTML page itself) so a reload while offline has a
  // shell to fall back to, instead of the browser's own offline network error.
  if (isNavigationRequest(request)) {
    event.respondWith(networkFirst(request, STATIC_CACHE));
    return;
  }

  if (isStaticAssetRequest(url)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  if (isCacheablePromptApiRequest(request, url)) {
    event.respondWith(networkFirst(request, API_CACHE));
  }
});

// Clears the cached prompt API responses on logout so a subsequent user signing
// in on the same device can't be served a previous user's cached data (FR-009's
// offline cache must not leak data across sessions on shared devices).
async function clearApiCache(): Promise<void> {
  const cache = await caches.open(API_CACHE);
  const keys = await cache.keys();
  await Promise.all(keys.map((key) => cache.delete(key)));
}

self.addEventListener('message', (event) => {
  if (event.data === 'clear-api-cache') {
    void clearApiCache();
  }
});

export {};
