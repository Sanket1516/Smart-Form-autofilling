(function () {
  'use strict';
  // Local-only submission: shows a success screen once every required field has a value. Nothing is sent.
  function filled(wrapper) {
    return Array.prototype.some.call(wrapper.querySelectorAll('input,select,textarea'), function (c) {
      return c.type === 'checkbox' || c.type === 'radio' ? c.checked : c.value.trim() !== '';
    });
  }
  function init() {
    var form = document.getElementById('demo-form');
    var success = document.getElementById('success-screen');
    var result = document.getElementById('submit-result');
    form.addEventListener('submit', function () {
      var missing = Array.prototype.filter.call(form.querySelectorAll('[data-field][data-required]'), function (w) { return !filled(w); });
      if (missing.length) {
        result.hidden = false;
        result.textContent = 'Demo only — nothing was sent. ' + missing.length + ' required field(s) are still missing.';
        return;
      }
      result.hidden = true;
      form.hidden = true;
      document.getElementById('status-panel').hidden = true;
      success.hidden = false;
      window.scrollTo(0, 0);
    });
    document.getElementById('back-to-form').addEventListener('click', function () {
      success.hidden = true;
      form.hidden = false;
      document.getElementById('status-panel').hidden = false;
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
