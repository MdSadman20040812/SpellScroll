/* ==========================================================================
   SpellScroll client runtime
   --------------------------------------------------------------------------
   Small, dependency-free helpers shared by every page: theme persistence,
   an API client, toasts, and progressive cover loading.  This replaces the
   Alpine.js + Tailwind CDN pair the previous build pulled in on every request.
   ========================================================================== */
(function () {
  "use strict";

  /* ---------------------------------------------------------------- theme */

  var THEME_KEY = "spellscroll_theme";

  function readTheme() {
    try {
      return window.localStorage.getItem(THEME_KEY) || "";
    } catch (err) {
      return "";
    }
  }

  function applyTheme(theme) {
    var root = document.documentElement;
    if (theme) {
      root.setAttribute("data-theme", theme);
    } else {
      root.removeAttribute("data-theme");
    }
    var dark =
      theme === "dark" ||
      (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.querySelectorAll("[data-theme-icon] use").forEach(function (use) {
      use.setAttribute("href", dark ? "#i-sun" : "#i-moon");
    });
  }

  function initTheme() {
    applyTheme(readTheme());
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        var current = readTheme();
        var systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        // Cycle relative to what is actually on screen, so one click always
        // visibly flips the theme regardless of the OS setting.
        var next = (current || (systemDark ? "dark" : "light")) === "dark" ? "light" : "dark";
        try {
          window.localStorage.setItem(THEME_KEY, next);
        } catch (err) {
          /* private mode: theme simply does not persist */
        }
        // Mirrored to a cookie so the server can render the right theme on the
        // first paint and avoid a flash on the next navigation.
        document.cookie =
          THEME_KEY + "=" + next + ";path=/;max-age=31536000;samesite=Lax";
        applyTheme(next);
      });
    });
  }

  /* ------------------------------------------------------------------ api */

  function getCookie(name) {
    var match = document.cookie.match(
      new RegExp("(^|;\\s*)" + name + "=([^;]*)")
    );
    return match ? decodeURIComponent(match[2]) : "";
  }

  /**
   * Call the FastAPI backend.
   *
   * Authentication rides on the httpOnly `access_token` cookie that the login
   * view sets, so no JWT is ever interpolated into a template.  The previous
   * build embedded the raw token in page HTML, which meant it leaked into
   * caches, view-source and any XSS.
   */
  async function api(path, options) {
    var opts = options || {};
    var headers = Object.assign({ Accept: "application/json" }, opts.headers || {});
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    var csrf = getCookie("csrftoken");
    if (csrf) {
      headers["X-CSRFToken"] = csrf;
    }

    var controller = new AbortController();
    var timer = window.setTimeout(function () {
      controller.abort();
    }, opts.timeout || 30000);

    try {
      var response = await fetch(path, {
        method: opts.method || "GET",
        headers: headers,
        credentials: "same-origin",
        signal: controller.signal,
        body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      });

      if (response.status === 401) {
        throw new ApiError("Your session expired. Please sign in again.", 401);
      }
      if (!response.ok) {
        var detail = "";
        try {
          detail = (await response.json()).detail || "";
        } catch (err) {
          /* body was not JSON */
        }
        throw new ApiError(detail || "Request failed (" + response.status + ")", response.status);
      }
      if (response.status === 204) {
        return null;
      }
      return await response.json();
    } catch (err) {
      if (err.name === "AbortError") {
        throw new ApiError("The request timed out. Check your connection.", 0);
      }
      if (err instanceof ApiError) {
        throw err;
      }
      throw new ApiError("Could not reach the server.", 0);
    } finally {
      window.clearTimeout(timer);
    }
  }

  function ApiError(message, status) {
    this.name = "ApiError";
    this.message = message;
    this.status = status;
  }
  ApiError.prototype = Object.create(Error.prototype);

  /* --------------------------------------------------------------- toasts */

  function toast(message, kind) {
    var stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      stack.setAttribute("role", "status");
      stack.setAttribute("aria-live", "polite");
      document.body.appendChild(stack);
    }
    var node = document.createElement("div");
    node.className = "toast";
    if (kind === "error") {
      node.style.borderLeft = "3px solid var(--ink-rose-400)";
    } else if (kind === "success") {
      node.style.borderLeft = "3px solid var(--accent-2)";
    }
    node.textContent = message;
    stack.appendChild(node);
    window.setTimeout(function () {
      node.style.opacity = "0";
      window.setTimeout(function () {
        node.remove();
      }, 200);
    }, 3600);
  }

  /* ---------------------------------------------------------------- covers */

  /**
   * Fade covers in once they decode.
   *
   * Every cover is served by our own proxy, which falls back to a generated
   * placeholder, so a hard `onerror` state should not happen - but if the
   * proxy itself is unreachable the card keeps its accent-tinted frame rather
   * than showing a broken-image glyph.
   */
  function initCovers(root) {
    (root || document).querySelectorAll("img[data-cover]").forEach(function (img) {
      if (img.dataset.bound === "1") {
        return;
      }
      img.dataset.bound = "1";
      var done = function () {
        img.dataset.loaded = "true";
      };
      if (img.complete && img.naturalWidth > 0) {
        done();
      } else {
        img.addEventListener("load", done, { once: true });
        img.addEventListener(
          "error",
          function () {
            img.style.display = "none";
          },
          { once: true }
        );
      }
    });
  }

  /* ----------------------------------------------------------------- misc */

  function escapeHtml(value) {
    return String(value === undefined || value === null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /** Trap focus inside an open dialog and restore it on close. */
  function trapFocus(container, onEscape) {
    var previous = document.activeElement;
    var selector =
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

    function onKeydown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        onEscape();
        return;
      }
      if (event.key !== "Tab") {
        return;
      }
      var nodes = Array.prototype.slice.call(container.querySelectorAll(selector));
      if (!nodes.length) {
        return;
      }
      var first = nodes[0];
      var last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeydown);
    var focusable = container.querySelector(selector);
    if (focusable) {
      focusable.focus();
    }

    return function release() {
      document.removeEventListener("keydown", onKeydown);
      if (previous && previous.focus) {
        previous.focus();
      }
    };
  }

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  window.SpellScroll = {
    api: api,
    ApiError: ApiError,
    toast: toast,
    initCovers: initCovers,
    escapeHtml: escapeHtml,
    trapFocus: trapFocus,
    getCookie: getCookie,
    ready: ready,
  };

  ready(function () {
    initTheme();
    initCovers();

    if ("serviceWorker" in navigator) {
      window.addEventListener("load", function () {
        navigator.serviceWorker.register("/static/sw.js").catch(function () {
          /* offline caching is a progressive enhancement */
        });
      });
    }
  });
})();
