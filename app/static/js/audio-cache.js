/**
 * Shared Enoch Audio Cache
 *
 * Provides three caching layers:
 *   1. sessionStorage — manifest JSON survives in-session navigation
 *   2. Cache API      — audio blobs persist across sessions / page loads
 *   3. In-memory Map  — Audio objects for instant within-page replay
 *
 * Usage (from any script):
 *   const manifest = await window.EnochCache.getManifest(url);
 *   const audio    = await window.EnochCache.getAudio(url);
 *   window.EnochCache.preloadUrls([url1, url2, ...]);
 */
(function () {
    'use strict';

    var CACHE_NAME = 'enoch-audio-v1';
    var MANIFEST_KEY = 'enoch_manifest_json';
    var MANIFEST_VER_KEY = 'enoch_manifest_ver';

    var memoryPool = {};
    var blobUrlPool = {};
    var cacheSupported = 'caches' in window;
    var preloadQueue = [];
    var preloading = false;

    function getManifest(url, version) {
        var ver = version || '1';
        var cached = null;
        try {
            var storedVer = sessionStorage.getItem(MANIFEST_VER_KEY);
            if (storedVer === ver) {
                cached = sessionStorage.getItem(MANIFEST_KEY);
            }
        } catch (e) {}

        if (cached) {
            try { return Promise.resolve(JSON.parse(cached)); } catch (e) {}
        }

        return fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                try {
                    sessionStorage.setItem(MANIFEST_KEY, JSON.stringify(data));
                    sessionStorage.setItem(MANIFEST_VER_KEY, ver);
                } catch (e) {}
                return data;
            });
    }

    function _blobToAudio(blob) {
        var objUrl = URL.createObjectURL(blob);
        var a = new Audio();
        a.preload = 'auto';
        a.src = objUrl;
        return { audio: a, objUrl: objUrl };
    }

    function getAudio(url) {
        if (memoryPool[url]) {
            var a = memoryPool[url];
            a.currentTime = 0;
            return Promise.resolve(a);
        }

        if (blobUrlPool[url]) {
            var a2 = new Audio(blobUrlPool[url]);
            a2.preload = 'auto';
            memoryPool[url] = a2;
            return Promise.resolve(a2);
        }

        if (!cacheSupported) {
            var plain = new Audio(url);
            plain.preload = 'auto';
            memoryPool[url] = plain;
            return Promise.resolve(plain);
        }

        return caches.open(CACHE_NAME).then(function (cache) {
            return cache.match(url).then(function (resp) {
                if (resp) {
                    return resp.blob().then(function (blob) {
                        var result = _blobToAudio(blob);
                        blobUrlPool[url] = result.objUrl;
                        memoryPool[url] = result.audio;
                        return result.audio;
                    });
                }
                return fetch(url).then(function (netResp) {
                    var clone = netResp.clone();
                    cache.put(url, clone).catch(function () {});
                    return netResp.blob().then(function (blob) {
                        var result = _blobToAudio(blob);
                        blobUrlPool[url] = result.objUrl;
                        memoryPool[url] = result.audio;
                        return result.audio;
                    });
                });
            });
        }).catch(function () {
            var fallback = new Audio(url);
            fallback.preload = 'auto';
            memoryPool[url] = fallback;
            return fallback;
        });
    }

    function _processPreloadQueue() {
        if (preloading || preloadQueue.length === 0) return;
        preloading = true;

        var url = preloadQueue.shift();

        if (blobUrlPool[url] || memoryPool[url]) {
            preloading = false;
            setTimeout(_processPreloadQueue, 0);
            return;
        }

        if (!cacheSupported) {
            preloading = false;
            return;
        }

        caches.open(CACHE_NAME).then(function (cache) {
            return cache.match(url).then(function (existing) {
                if (existing) return;
                return fetch(url).then(function (resp) {
                    return cache.put(url, resp);
                });
            });
        }).catch(function () {}).then(function () {
            preloading = false;
            setTimeout(_processPreloadQueue, 50);
        });
    }

    function preloadUrls(urls) {
        for (var i = 0; i < urls.length; i++) {
            if (preloadQueue.indexOf(urls[i]) === -1) {
                preloadQueue.push(urls[i]);
            }
        }
        _processPreloadQueue();
    }

    function clearCache() {
        memoryPool = {};
        for (var key in blobUrlPool) {
            URL.revokeObjectURL(blobUrlPool[key]);
        }
        blobUrlPool = {};
        try { sessionStorage.removeItem(MANIFEST_KEY); } catch (e) {}
        try { sessionStorage.removeItem(MANIFEST_VER_KEY); } catch (e) {}
        if (cacheSupported) {
            caches.delete(CACHE_NAME).catch(function () {});
        }
    }

    window.EnochCache = {
        getManifest: getManifest,
        getAudio: getAudio,
        preloadUrls: preloadUrls,
        clearCache: clearCache,
    };
})();
