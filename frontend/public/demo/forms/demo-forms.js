(function () {
  'use strict';
  var STATE_TEXT = {missing: 'Missing', empty: 'Optional · empty', choice: 'Your choice',
    filled: 'Filled', verified: 'Filled · verified', review: 'Review'};

  function slug(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, ''); }
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') node.textContent = attrs[k]; else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }
  function badge() { return el('span', {'class': 'badge', 'data-badge': '', 'data-state': 'empty'}); }

  function numberCell(id, label) {
    var input = el('input', {type: 'number', id: id, name: id, 'aria-label': label, min: '0', max: '1000', step: 'any'});
    return el('td', {'data-field': ''}, [input, badge()]);
  }
  function textCell(id, label, type) {
    var input = el('input', {type: type || 'text', id: id, name: id, 'aria-label': label});
    return el('td', {'data-field': ''}, [input, badge()]);
  }

  // Dynamic fields: rendered here, not in the HTML, so they appear only after the page script ran.
  function renderSubjects(host) {
    var prefix = host.getAttribute('data-prefix');
    var subjects = (host.getAttribute('data-subjects') || '').split('|').filter(Boolean);
    var rows = subjects.map(function (name) {
      var key = prefix + '_' + slug(name);
      return el('tr', {}, [
        el('th', {scope: 'row', text: name}),
        numberCell(key + '_max', name + ' — maximum marks'),
        numberCell(key + '_obt', name + ' — marks obtained')]);
    });
    var table = el('table', {'class': 'dyn'}, [
      el('thead', {}, [el('tr', {}, [el('th', {text: 'Subject'}), el('th', {text: 'Maximum marks'}), el('th', {text: 'Marks obtained'})])]),
      el('tbody', {}, rows)]);
    host.appendChild(el('div', {'class': 'table-wrap'}, [table]));
  }

  function renderMembers(host) {
    var body = el('tbody');
    var count = 0;
    function addRow() {
      count += 1;
      var n = count;
      body.appendChild(el('tr', {}, [
        el('th', {scope: 'row', text: String(n)}),
        textCell('m' + n + '_name', 'Member ' + n + ' — name'),
        textCell('m' + n + '_rel', 'Member ' + n + ' — relationship to applicant'),
        numberCell('m' + n + '_age', 'Member ' + n + ' — age')]));
      refresh();
    }
    var table = el('table', {'class': 'dyn'}, [
      el('thead', {}, [el('tr', {}, [el('th', {text: '#'}), el('th', {text: 'Name'}), el('th', {text: 'Relationship'}), el('th', {text: 'Age'})])]),
      body]);
    var add = el('button', {type: 'button', 'class': 'secondary', text: '+ Add another member'});
    add.addEventListener('click', addRow);
    host.appendChild(el('div', {'class': 'table-wrap'}, [table]));
    host.appendChild(add);
    for (var i = 0; i < 3; i += 1) addRow();
  }

  // ------------------------------------------------------------------ field state
  function controls(wrapper) {
    return Array.prototype.slice.call(wrapper.querySelectorAll('input,select,textarea'));
  }
  function isFilled(wrapper) {
    var list = controls(wrapper);
    if (!list.length) return false;
    var first = list[0];
    if (first.type === 'radio' || first.type === 'checkbox') return list.some(function (c) { return c.checked; });
    if (first.type === 'file') return first.files && first.files.length > 0;
    return list.some(function (c) { return c.value.trim() !== ''; });
  }
  function hasRule(c) {
    return c.type === 'email' || c.type === 'date' || c.type === 'number' || c.tagName === 'SELECT' ||
      c.hasAttribute('pattern') || c.type === 'tel';
  }
  function stateOf(wrapper) {
    var required = wrapper.hasAttribute('data-required');
    if (!isFilled(wrapper)) {
      if (wrapper.hasAttribute('data-user')) return 'choice';
      return required ? 'missing' : 'empty';
    }
    var list = controls(wrapper);
    var invalid = list.some(function (c) { return c.value !== '' && c.type !== 'checkbox' && c.type !== 'radio' && !c.checkValidity(); });
    if (invalid) return 'review';
    if (wrapper.hasAttribute('data-sensitive')) return 'review';
    return list.some(hasRule) ? 'verified' : 'filled';
  }
  function refresh() {
    var counts = {missing: 0, review: 0, verified: 0, filled: 0, choice: 0, empty: 0};
    Array.prototype.forEach.call(document.querySelectorAll('[data-field]'), function (wrapper) {
      if (wrapper.closest('[hidden]')) return;
      var state = stateOf(wrapper);
      wrapper.setAttribute('data-state', state);
      var b = wrapper.querySelector('[data-badge]');
      if (b) {
        b.setAttribute('data-state', state);
        var text = STATE_TEXT[state];
        if (state === 'review' && wrapper.hasAttribute('data-sensitive') && isFilled(wrapper)) text = 'Review · sensitive';
        b.textContent = text;
      }
      counts[state] += 1;
    });
    var panel = document.getElementById('status-panel');
    if (panel) {
      Object.keys(counts).forEach(function (k) {
        var n = panel.querySelector('[data-count="' + k + '"]');
        if (n) n.textContent = String(counts[k]);
      });
    }
  }

  // Sections that appear after a choice (e.g. category certificate details).
  function applyReveal() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-reveal-when]'), function (section) {
      var controller = document.getElementById(section.getAttribute('data-reveal-when'));
      var values = (section.getAttribute('data-reveal-values') || '').split('|');
      var show = !!controller && values.indexOf(controller.value) !== -1;
      if (show === section.hasAttribute('hidden')) { if (show) section.removeAttribute('hidden'); else section.setAttribute('hidden', ''); }
    });
  }

  function init() {
    Array.prototype.forEach.call(document.querySelectorAll('[data-dyn="subjects"]'), renderSubjects);
    Array.prototype.forEach.call(document.querySelectorAll('[data-dyn="members"]'), renderMembers);
    applyReveal();
    refresh();
    ['input', 'change'].forEach(function (name) {
      document.addEventListener(name, function () { applyReveal(); refresh(); }, true);
    });
    window.setInterval(function () { applyReveal(); refresh(); }, 700);   // values set without events
    var form = document.getElementById('demo-form');
    window.demoSubmitAttempts = 0;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      window.demoSubmitAttempts += 1;
      var missing = document.querySelectorAll('[data-field][data-state=missing]').length;
      var out = document.getElementById('submit-result');
      out.hidden = false;
      out.textContent = 'Demo only — nothing was sent. ' + (missing ? missing + ' required field(s) are still missing.' : 'All required fields have a value.');
    });
    form.addEventListener('reset', function () { window.setTimeout(function () { applyReveal(); refresh(); }, 0); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
