/* Native save bridge. The browser build keeps its existing localStorage path. */
(function () {
    'use strict';
    var cap = window.Capacitor;
    var native = !!(cap && typeof cap.isNativePlatform === 'function' &&
        cap.isNativePlatform() && typeof cap.nativePromise === 'function');
    var keys = ['last_clean_land_save_v2', 'last_clean_land_save_v2_bak'];
    var bridge = window.__NATIVE_SAVE__ = {
        enabled: native, error: null, loaded: [null, null],
        ready: Promise.resolve(), save: function () {}
    };
    if (!native) { return; }
    function call(method, key, value) {
        var options = {key: key};
        if (value !== undefined) { options.value = value; }
        return cap.nativePromise('Preferences', method, options);
    }
    var timer;
    var reads = Promise.all(keys.map(function (key) {
        return call('get', key).then(function (result) {
            return result && typeof result.value === 'string' ? result.value : null;
        });
    }));
    var timeout = new Promise(function (resolve) {
        timer = setTimeout(function () { resolve(null); }, 4000);
    });
    bridge.ready = Promise.race([reads, timeout]).then(function (values) {
        clearTimeout(timer);
        if (!values) { throw new Error('原生存档读取超时'); }
        bridge.loaded = values;
        try {
            if (values[0]) { localStorage.setItem('last_clean_land_save_native', values[0]); }
            if (values[1]) { localStorage.setItem('last_clean_land_save_native_bak', values[1]); }
        } catch (e) { /* 原生存储中的副本仍可在内存中读到 */ }
    }).catch(function (error) {
        clearTimeout(timer);
        bridge.enabled = false;
        bridge.error = String(error);
    });
    var queue = Promise.resolve();
    bridge.save = function (main, backup) {
        if (!bridge.enabled || !main) { return; }
        queue = queue.catch(function () {}).then(function () {
            return call('set', keys[0], main);
        }).then(function () {
            if (backup) { return call('set', keys[1], backup); }
        }).catch(function (error) {
            bridge.error = String(error);
        });
        return queue;
    };
})();
