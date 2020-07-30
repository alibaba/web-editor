var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; };

(function (global, factory) {
  (typeof exports === 'undefined' ? 'undefined' : _typeof(exports)) === 'object' && typeof module !== 'undefined' ? module.exports = factory() : typeof define === 'function' && define.amd ? define(factory) : (global = global || self, global.AsyncComputed = factory());
})(this, function () {
  'use strict';

  function isComputedLazy(item) {
    return item.hasOwnProperty('lazy') && item.lazy;
  }

  function isLazyActive(vm, key) {
    return vm[lazyActivePrefix + key];
  }

  var lazyActivePrefix = 'async_computed$lazy_active$',
      lazyDataPrefix = 'async_computed$lazy_data$';

  function initLazy(data, key) {
    data[lazyActivePrefix + key] = false;
    data[lazyDataPrefix + key] = null;
  }

  function makeLazyComputed(key) {
    return {
      get: function get() {
        this[lazyActivePrefix + key] = true;
        return this[lazyDataPrefix + key];
      },
      set: function set(value) {
        this[lazyDataPrefix + key] = value;
      }
    };
  }

  function silentSetLazy(vm, key, value) {
    vm[lazyDataPrefix + key] = value;
  }
  function silentGetLazy(vm, key) {
    return vm[lazyDataPrefix + key];
  }

  var getGetterWatchedByArray = function getGetterWatchedByArray(computedAsyncProperty) {
    return function getter() {
      var _this = this;

      computedAsyncProperty.watch.forEach(function (key) {
        // Check if nested key is watched.
        var splittedByDot = key.split('.');
        if (splittedByDot.length === 1) {
          // If not, just access it.
          // eslint-disable-next-line no-unused-expressions
          _this[key];
        } else {
          // Access the nested propety.
          try {
            var start = _this;
            splittedByDot.forEach(function (part) {
              start = start[part];
            });
          } catch (error) {
            console.error('AsyncComputed: bad path: ', key);
            throw error;
          }
        }
      });
      return computedAsyncProperty.get.call(this);
    };
  };

  var getGetterWatchedByFunction = function getGetterWatchedByFunction(computedAsyncProperty) {
    return function getter() {
      computedAsyncProperty.watch.call(this);
      return computedAsyncProperty.get.call(this);
    };
  };

  function getWatchedGetter(computedAsyncProperty) {
    if (typeof computedAsyncProperty.watch === 'function') {
      return getGetterWatchedByFunction(computedAsyncProperty);
    } else if (Array.isArray(computedAsyncProperty.watch)) {
      computedAsyncProperty.watch.forEach(function (key) {
        if (typeof key !== 'string') {
          throw new Error('AsyncComputed: watch elemnts must be strings');
        }
      });
      return getGetterWatchedByArray(computedAsyncProperty);
    } else {
      throw Error('AsyncComputed: watch should be function or an array');
    }
  }

  var DidNotUpdate = typeof Symbol === 'function' ? Symbol('did-not-update') : {};

  var getGetterWithShouldUpdate = function getGetterWithShouldUpdate(asyncProprety, currentGetter) {
    return function getter() {
      return asyncProprety.shouldUpdate.call(this) ? currentGetter.call(this) : DidNotUpdate;
    };
  };

  var shouldNotUpdate = function shouldNotUpdate(value) {
    return DidNotUpdate === value;
  };

  var prefix = '_async_computed$';

  var AsyncComputed = {
    install: function install(Vue, pluginOptions) {
      pluginOptions = pluginOptions || {};

      Vue.config.optionMergeStrategies.asyncComputed = Vue.config.optionMergeStrategies.computed;

      Vue.mixin({
        data: function data() {
          return {
            _asyncComputed: {}
          };
        },

        computed: {
          $asyncComputed: function $asyncComputed() {
            return this.$data._asyncComputed;
          }
        },
        beforeCreate: function beforeCreate() {
          var asyncComputed = this.$options.asyncComputed || {};

          if (!Object.keys(asyncComputed).length) return;

          for (var key in asyncComputed) {
            var getter = getterFn(key, asyncComputed[key]);
            this.$options.computed[prefix + key] = getter;
          }

          this.$options.data = initDataWithAsyncComputed(this.$options);
        },
        created: function created() {
          for (var key in this.$options.asyncComputed || {}) {
            var item = this.$options.asyncComputed[key],
                value = generateDefault.call(this, item, pluginOptions);
            if (isComputedLazy(item)) {
              silentSetLazy(this, key, value);
            } else {
              this[key] = value;
            }
          }

          for (var _key in this.$options.asyncComputed || {}) {
            handleAsyncComputedPropetyChanges(this, _key, pluginOptions, Vue);
          }
        }
      });
    }
  };
  function handleAsyncComputedPropetyChanges(vm, key, pluginOptions, Vue) {
    var promiseId = 0;
    var watcher = function watcher(newPromise) {
      var thisPromise = ++promiseId;

      if (shouldNotUpdate(newPromise)) return;

      if (!newPromise || !newPromise.then) {
        newPromise = Promise.resolve(newPromise);
      }
      setAsyncState(vm, key, 'updating');

      newPromise.then(function (value) {
        if (thisPromise !== promiseId) return;
        setAsyncState(vm, key, 'success');
        vm[key] = value;
      }).catch(function (err) {
        if (thisPromise !== promiseId) return;

        setAsyncState(vm, key, 'error');
        Vue.set(vm.$data._asyncComputed[key], 'exception', err);
        if (pluginOptions.errorHandler === false) return;

        var handler = pluginOptions.errorHandler === undefined ? console.error.bind(console, 'Error evaluating async computed property:') : pluginOptions.errorHandler;

        if (pluginOptions.useRawError) {
          handler(err, vm, err.stack);
        } else {
          handler(err.stack);
        }
      });
    };
    Vue.set(vm.$data._asyncComputed, key, {
      exception: null,
      update: function update() {
        watcher(getterOnly(vm.$options.asyncComputed[key]).apply(vm));
      }
    });
    setAsyncState(vm, key, 'updating');
    vm.$watch(prefix + key, watcher, { immediate: true });
  }

  function initDataWithAsyncComputed(options) {
    var optionData = options.data;
    var asyncComputed = options.asyncComputed || {};

    return function vueAsyncComputedInjectedDataFn(vm) {
      var data = (typeof optionData === 'function' ? optionData.call(this, vm) : optionData) || {};
      for (var key in asyncComputed) {
        var item = this.$options.asyncComputed[key];
        if (isComputedLazy(item)) {
          initLazy(data, key);
          this.$options.computed[key] = makeLazyComputed(key);
        } else {
          data[key] = null;
        }
      }
      return data;
    };
  }

  function setAsyncState(vm, stateObject, state) {
    vm.$set(vm.$data._asyncComputed[stateObject], 'state', state);
    vm.$set(vm.$data._asyncComputed[stateObject], 'updating', state === 'updating');
    vm.$set(vm.$data._asyncComputed[stateObject], 'error', state === 'error');
    vm.$set(vm.$data._asyncComputed[stateObject], 'success', state === 'success');
  }

  function getterOnly(fn) {
    if (typeof fn === 'function') return fn;

    return fn.get;
  }

  function getterFn(key, fn) {
    if (typeof fn === 'function') return fn;

    var getter = fn.get;

    if (fn.hasOwnProperty('watch')) {
      getter = getWatchedGetter(fn);
    }

    if (fn.hasOwnProperty('shouldUpdate')) {
      getter = getGetterWithShouldUpdate(fn, getter);
    }

    if (isComputedLazy(fn)) {
      var nonLazy = getter;
      getter = function lazyGetter() {
        if (isLazyActive(this, key)) {
          return nonLazy.call(this);
        } else {
          return silentGetLazy(this, key);
        }
      };
    }
    return getter;
  }

  function generateDefault(fn, pluginOptions) {
    var defaultValue = null;

    if ('default' in fn) {
      defaultValue = fn.default;
    } else if ('default' in pluginOptions) {
      defaultValue = pluginOptions.default;
    }

    if (typeof defaultValue === 'function') {
      return defaultValue.call(this);
    } else {
      return defaultValue;
    }
  }

  /* istanbul ignore if */
  if (typeof window !== 'undefined' && window.Vue) {
    // Auto install in dist mode
    window.Vue.use(AsyncComputed);
  }

  return AsyncComputed;
});
