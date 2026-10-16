"""Generate the 15 demo web forms (plain HTML + one shared CSS + one shared JS).

The pages contain no profile values and no canonical keys. Field status badges
(missing / filled / verified / review / your choice) are computed in the
browser from the live DOM, so they work the same for typing and for the
Chrome extension. Scripts are external because the production nginx CSP only
allows ``script-src 'self'``.
"""

from __future__ import annotations

import hashlib
from html import escape
from pathlib import Path

from demo.forms_spec import FORMS, FormSpec, Fld, Section

CSS = r"""
:root{--accent:#1f4e79;--bg:#f5f7fa;--card:#fff;--ink:#1b2430;--muted:#5b6776;--line:#cfd7e2;
--missing:#b3261e;--review:#b45309;--verified:#157347;--filled:#1d5fbf;--choice:#7a5200;--empty:#6b7280}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--ink);line-height:1.45}
header.site{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.75rem 1.25rem;background:var(--accent);color:#fff;flex-wrap:wrap}
header.site .brand{font-weight:700;letter-spacing:.2px}
header.site .brand span{font-weight:400;font-size:.75rem;opacity:.85;margin-left:.5rem;border:1px solid rgba(255,255,255,.6);border-radius:999px;padding:.05rem .5rem}
header.site a{color:#fff}
.ribbon{background:#fff3cd;color:#664d03;border-bottom:1px solid #ecd68a;padding:.4rem 1.25rem;font-size:.82rem;font-weight:600}
main{max-width:980px;margin:0 auto;padding:1rem 1.25rem 3rem}
h1{margin:.6rem 0 .2rem;font-size:1.55rem}
.intro{color:var(--muted);margin:.2rem 0 1rem}
#status-panel{position:sticky;top:0;z-index:5;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.55rem .8rem;margin:0 0 1rem;display:flex;flex-wrap:wrap;gap:.35rem .9rem;align-items:center;font-size:.82rem;box-shadow:0 2px 6px rgba(20,30,50,.06)}
#status-panel strong{margin-right:.2rem}
.chip{display:inline-flex;align-items:center;gap:.3rem;white-space:nowrap}
.dot{width:.7rem;height:.7rem;border-radius:50%;display:inline-block}
.dot.missing{background:var(--missing)}.dot.review{background:var(--review)}.dot.verified{background:var(--verified)}
.dot.filled{background:var(--filled)}.dot.choice{background:#e0a100}.dot.empty{background:#b6bdc8}
section.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1rem 1.1rem 1.1rem;margin:0 0 1rem;border-top:4px solid var(--accent)}
section.card[hidden]{display:none}
section.card h2{margin:.1rem 0 .7rem;font-size:1.05rem}
.note{margin:-.3rem 0 .7rem;color:var(--muted);font-size:.85rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:.85rem 1rem}
.field{position:relative;display:flex;flex-direction:column;gap:.25rem;min-width:0;border:0;padding:0;margin:0}
.field.wide{grid-column:1/-1}
.field label.lbl,.field legend{font-weight:600;font-size:.88rem;padding:0}
.field.req label.lbl::after,.field.req legend::after{content:" *";color:var(--missing)}
.field input[type=text],.field input[type=email],.field input[type=tel],.field input[type=date],.field input[type=number],
.field select,.field textarea{width:100%;padding:.5rem .6rem;border:1px solid var(--line);border-radius:7px;font:inherit;background:#fff;color:var(--ink)}
.field textarea{min-height:4.4rem;resize:vertical}
.field input:focus,.field select:focus,.field textarea:focus{outline:2px solid var(--accent);outline-offset:1px}
.field .hint{font-size:.76rem;color:var(--muted)}
.opts{display:flex;flex-wrap:wrap;gap:.35rem 1rem}
.opt{display:inline-flex;gap:.35rem;align-items:center;font-size:.9rem}
.badge{align-self:flex-start;font-size:.7rem;font-weight:700;border-radius:999px;padding:.08rem .5rem;border:1px solid currentColor;background:#fff}
.badge[data-state=missing]{color:var(--missing)}.badge[data-state=review]{color:var(--review)}
.badge[data-state=verified]{color:var(--verified)}.badge[data-state=filled]{color:var(--filled)}
.badge[data-state=choice]{color:var(--choice)}.badge[data-state=empty]{color:var(--empty);border-style:dashed}
[data-field][data-state=missing] input:not([type=radio]):not([type=checkbox]),[data-field][data-state=missing] select,[data-field][data-state=missing] textarea{border-color:var(--missing);background:#fff6f5}
[data-field][data-state=verified] input:not([type=radio]):not([type=checkbox]),[data-field][data-state=verified] select,[data-field][data-state=verified] textarea{border-color:var(--verified);background:#f2faf5}
[data-field][data-state=filled] input:not([type=radio]):not([type=checkbox]),[data-field][data-state=filled] select,[data-field][data-state=filled] textarea{border-color:var(--filled);background:#f4f8ff}
[data-field][data-state=review] input:not([type=radio]):not([type=checkbox]),[data-field][data-state=review] select,[data-field][data-state=review] textarea{border-color:var(--review);background:#fff9f0}
[data-field][data-state=choice] input:not([type=radio]):not([type=checkbox]),[data-field][data-state=choice] select{border-color:#e0a100;background:#fffbea}
.table-wrap{overflow-x:auto}
table.dyn{border-collapse:collapse;width:100%;min-width:560px}
table.dyn th,table.dyn td{border:1px solid var(--line);padding:.35rem .5rem;text-align:left;vertical-align:middle}
table.dyn th{background:#eef2f7;font-size:.8rem}
table.dyn td input{width:100%;padding:.35rem .45rem;border:1px solid var(--line);border-radius:6px;font:inherit}
table.dyn td[data-field]{position:relative}
table.dyn .badge{display:block;margin-top:.2rem}
.actions{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1rem}
button{font:inherit;padding:.55rem 1rem;border-radius:8px;border:1px solid var(--accent);cursor:pointer}
button.primary{background:var(--accent);color:#fff}
button.secondary{background:#fff;color:var(--accent)}
#submit-result{margin-top:1rem;padding:.7rem .9rem;border-radius:8px;background:#e8f1ff;border:1px solid #bcd3f5}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.index-list{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:.8rem}
.index-list a{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.8rem 1rem;text-decoration:none;color:var(--ink)}
.index-list a:hover{border-color:var(--accent)}
.index-list small{color:var(--muted);display:block}
@media (max-width:560px){main{padding:.8rem}.grid{grid-template-columns:1fr}}
"""

JS = r"""
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
"""


def _dom_name(form: FormSpec, fld: Fld) -> str:
    if fld.dynamic or not form.cryptic_names:
        return fld.key
    digest = hashlib.sha1(f"{form.number}:{fld.key}".encode()).hexdigest()[:5]
    return f"q{digest}"


def dom_map(form: FormSpec) -> dict[str, str]:
    return {f.key: _dom_name(form, f) for f in form.all_fields()}


def _wrapper_attrs(fld: Fld, extra_class: str = "") -> str:
    classes = ["field"]
    if fld.required:
        classes.append("req")
    if fld.kind in ("textarea", "radio", "checks"):
        classes.append("wide")
    if extra_class:
        classes.append(extra_class)
    attrs = f'class="{" ".join(classes)}" data-field'
    if fld.required:
        attrs += " data-required"
    if fld.user:
        attrs += " data-user"
    if fld.sensitive:
        attrs += " data-sensitive"
    return attrs


def _field_html(form: FormSpec, fld: Fld) -> str:
    name = _dom_name(form, fld)
    hint = f'<span class="hint" id="{name}-hint">{escape(fld.hint)}</span>' if fld.hint else ""
    described = f' aria-describedby="{name}-hint"' if fld.hint else ""
    req = " required" if fld.required else ""
    badge = '<span class="badge" data-badge data-state="empty"></span>'
    if fld.kind in ("radio", "checks"):
        kind = "radio" if fld.kind == "radio" else "checkbox"
        opts = "".join(
            f'<label class="opt"><input type="{kind}" name="{name}" id="{name}-{i}" value="{escape(o)}"'
            f'{req if kind == "radio" else ""}> {escape(o)}</label>'
            for i, o in enumerate(fld.options))
        return (f'<fieldset {_wrapper_attrs(fld)}><legend>{escape(fld.label)}</legend>'
                f'<div class="opts">{opts}</div>{hint}{badge}</fieldset>')
    label = f'<label class="lbl" for="{name}">{escape(fld.label)}</label>'
    if fld.kind == "checkbox":
        return (f'<div {_wrapper_attrs(fld, "wide")}><label class="opt"><input type="checkbox" name="{name}" id="{name}"'
                f'{req}> {escape(fld.label)}</label>{hint}{badge}</div>')
    if fld.kind == "textarea":
        control = f'<textarea name="{name}" id="{name}" rows="3"{req}{described}></textarea>'
    elif fld.kind == "select":
        options = '<option value="">Select…</option>' + "".join(
            f'<option value="{escape(o)}">{escape(o)}</option>' for o in fld.options)
        control = f'<select name="{name}" id="{name}"{req}{described}>{options}</select>'
    elif fld.kind == "file":
        control = f'<input type="file" name="{name}" id="{name}" accept="image/jpeg,image/png"{req}{described}>'
    else:
        extra = ""
        if fld.pattern:
            extra += f' pattern="{escape(fld.pattern)}"'
        if fld.placeholder:
            extra += f' placeholder="{escape(fld.placeholder)}"'
        if fld.kind == "number":
            extra += ' min="0" step="any"'
        control = f'<input type="{fld.kind}" name="{name}" id="{name}"{req}{extra}{described}>'
    return f'<div {_wrapper_attrs(fld)}>{label}{control}{hint}{badge}</div>'


def _dynamic_html(form: FormSpec, section: Section, fld: Fld, seen: set[str]) -> str:
    prefix = fld.key.split("_")[0]
    if prefix in seen:
        return ""
    seen.add(prefix)
    if prefix.startswith("m") and prefix[1:].isdigit():
        return '<div class="field wide"><div data-dyn="members"></div></div>'
    table = next(t for t in form.subject_tables if t["prefix"] == prefix)
    names = "|".join(table["subjects"])
    title = "Class 10" if prefix == "c10" else "Class 12"
    return (f'<div class="field wide"><strong class="sr-only">{title} subject-wise marks</strong>'
            f'<div data-dyn="subjects" data-prefix="{prefix}" data-subjects="{escape(names)}"></div></div>')


def render_form(form: FormSpec) -> str:
    ids = dom_map(form)
    sections = []
    for section in form.sections:
        seen: set[str] = set()
        body = []
        for fld in section.fields:
            body.append(_dynamic_html(form, section, fld, seen) if fld.dynamic else _field_html(form, fld))
        note = f'<p class="note">{escape(section.note)}</p>' if section.note else ""
        reveal = ""
        if section.reveal:
            reveal = (f' data-reveal-when="{ids[section.reveal["when"]]}"'
                      f' data-reveal-values="{"|".join(section.reveal["values"])}" hidden')
        sections.append(f'<section class="card"{reveal}><h2>{escape(section.title)}</h2>{note}'
                        f'<div class="grid">{"".join(body)}</div></section>')
    legend = "".join(
        f'<span class="chip"><span class="dot {k}"></span>{label}: <b data-count="{k}">0</b></span>'
        for k, label in [("verified", "Verified"), ("filled", "Filled"), ("review", "Review"),
                         ("missing", "Missing"), ("choice", "Your choice"), ("empty", "Optional")])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(form.title)} — DemoGov Portal (synthetic demo form)</title>
<link rel="stylesheet" href="demo-forms.css">
</head>
<body data-demo-form="{form.number:02d}" style="--accent:{form.accent}">
<header class="site"><div class="brand">DemoGov Portal <span>fictional</span></div><nav><a href="index.html">All 15 demo forms</a></nav></header>
<div class="ribbon">SYNTHETIC DEMO FORM — fictional portal, not an official application. Nothing on this page is submitted anywhere.</div>
<main>
<h1>{escape(form.title)}</h1>
<p class="intro">{escape(form.intro)}</p>
<div id="status-panel" role="status" aria-live="polite"><strong>Field status</strong>{legend}</div>
<form id="demo-form" novalidate autocomplete="off">
{"".join(sections)}
<div class="actions"><button type="submit" class="primary">Review application (demo)</button><button type="reset" class="secondary">Clear form</button></div>
<p id="submit-result" role="status" hidden></p>
</form>
</main>
<script src="demo-forms.js" defer></script>
</body>
</html>
"""


def render_index() -> str:
    items = "".join(
        f'<li><a href="form-{f.number:02d}-{f.slug}.html"><b>Form {f.number}</b> · {escape(f.title)}'
        f'<small>{escape(f.intro[:90])}…</small></a></li>' for f in FORMS)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Demo forms — DemoGov Portal (synthetic)</title><link rel="stylesheet" href="demo-forms.css"></head>
<body><header class="site"><div class="brand">DemoGov Portal <span>fictional</span></div></header>
<div class="ribbon">SYNTHETIC DEMO FORMS — fictional portal, not official applications.</div>
<main><h1>15 demo forms</h1><p class="intro">Open a form, then use the Smart Form Chrome extension to analyse and fill it from your uploaded demo documents.</p>
<ul class="index-list">{items}</ul></main></body></html>
"""


def file_name(form: FormSpec) -> str:
    return f"form-{form.number:02d}-{form.slug}.html"


def generate(out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "demo-forms.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (out_dir / "demo-forms.js").write_text(JS.strip() + "\n", encoding="utf-8")
    (out_dir / "index.html").write_text(render_index(), encoding="utf-8")
    names = []
    for form in FORMS:
        (out_dir / file_name(form)).write_text(render_form(form), encoding="utf-8")
        names.append(file_name(form))
    return names
