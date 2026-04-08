/**
 * Scriba TeX copy-button controller.
 *
 * Auto-initializes on DOMContentLoaded. Scans for `.scriba-tex-copy-btn`
 * inside `.scriba-tex-code-block` wrappers, reads `data-code` (HTML-entity
 * encoded) from the wrapping block, and copies to clipboard on click.
 * Shows "Copied" feedback for 2000 ms. Uses a single document-level
 * event-delegated click handler.
 *
 * Contract: the containing `.scriba-tex-code-block` element must carry a
 * `data-code` attribute whose value is the original source with standard
 * HTML entities escaped (&amp; &lt; &gt; &quot; &#39;). The controller
 * decodes these before passing to the clipboard API.
 *
 * Safe to load multiple times — guards via `window.ScribaTexCopy._initialized`.
 * No dependencies, no global namespace pollution beyond `window.ScribaTexCopy`.
 */
(function () {
  "use strict";

  if (window.ScribaTexCopy && window.ScribaTexCopy._initialized) {
    return;
  }

  var FEEDBACK_MS = 2000;
  var ORIGINAL_TEXT = "Copy";
  var COPIED_TEXT = "Copied";
  var _listenerAttached = false;

  function decodeHtmlEntities(raw) {
    if (raw == null) return "";
    var ta = document.createElement("textarea");
    ta.innerHTML = String(raw);
    return ta.value;
  }

  function fallbackCopy(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "absolute";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (err) {
      return false;
    }
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).then(
        function () {
          return true;
        },
        function () {
          return fallbackCopy(text);
        },
      );
    }
    return Promise.resolve(fallbackCopy(text));
  }

  function flashCopied(button) {
    button.classList.add("copied");
    button.textContent = COPIED_TEXT;
    window.setTimeout(function () {
      button.classList.remove("copied");
      button.textContent = ORIGINAL_TEXT;
    }, FEEDBACK_MS);
  }

  function handleClick(event) {
    var target = event.target;
    if (!target || typeof target.closest !== "function") return;
    var button = target.closest(".scriba-tex-copy-btn");
    if (!button) return;
    var block = button.closest(".scriba-tex-code-block");
    if (!block) return;
    var raw = block.getAttribute("data-code") || "";
    var decoded = decodeHtmlEntities(raw);
    event.preventDefault();
    Promise.resolve(copyToClipboard(decoded)).then(function (ok) {
      if (ok) {
        flashCopied(button);
      } else {
        console.warn("[scriba-tex-copy] clipboard copy failed");
      }
    });
  }

  function init() {
    if (_listenerAttached) return;
    document.addEventListener("click", handleClick, false);
    _listenerAttached = true;
  }

  window.ScribaTexCopy = { init: init, _initialized: true };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
