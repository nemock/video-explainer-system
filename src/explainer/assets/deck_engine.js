/* Explainer System — deterministic deck engine (Phase 1).
   Builds slide DOM from window.DECK once, then renderAt(t) sets the full visual
   state for any time t. Driven by window.TIMELINE (slide windows + word timestamps)
   injected by the renderer. No wall-clock, no CSS animation -> same input, same frames. */
(function () {
  // seeded PRNG so anything stochastic is deterministic across captures
  var _s = 42; Math.random = function () { _s = (_s * 1103515245 + 12345) & 0x7fffffff; return _s / 0x7fffffff; };

  var DECK = window.DECK || { slides: [] };
  var stage = document.getElementById('stage');
  var captionEl = document.getElementById('caption');
  var ambient = document.getElementById('ambient');
  if (ambient && DECK.ambient === false) { ambient.style.display = 'none'; ambient = null; }

  // persistent brand watermark on every slide, in a bottom corner within the safe zone
  if (DECK.watermark) {
    var wm = document.createElement('img');
    wm.id = 'watermark'; wm.src = DECK.watermark;
    var wmSize = Math.round(Math.min(window.innerWidth, window.innerHeight) * 0.085);
    wm.style.width = wm.style.height = wmSize + 'px';
    wm.style.bottom = Math.round(window.innerHeight * ((DECK.safe_bottom || 0.14) * 0.5 + 0.03)) + 'px';
    var inset = Math.round(window.innerWidth * 0.045) + 'px';
    if ((DECK.watermark_corner || 'bl') === 'br') wm.style.right = inset; else wm.style.left = inset;
    document.body.appendChild(wm);
  }

  function easeOut(x) { x = Math.min(1, Math.max(0, x)); return 1 - Math.pow(1 - x, 3); }

  // --- stat count-up: parse "$2.5M" / "90%" / "10,000" / "3x" and animate 0 -> value ---
  function splitNum(s) {
    var m = String(s).match(/^(\D*)([\d,]*\.?\d+)(.*)$/);
    if (!m) return null;
    var raw = m[2].replace(/,/g, '');
    return { pre: m[1], num: parseFloat(raw), suf: m[3],
             dec: (raw.split('.')[1] || '').length, comma: m[2].indexOf(',') >= 0 };
  }
  function fmtStat(v, info) {
    var s = info.dec > 0 ? v.toFixed(info.dec) : String(Math.round(v));
    if (info.comma) s = Number(s).toLocaleString('en-US');
    return info.pre + s + info.suf;
  }
  function countUp(eln, g) {
    if (!eln) return;
    if (eln.__info === undefined) eln.__info = splitNum(eln.dataset.val);
    var info = eln.__info; if (!info) return;  // non-numeric -> leave the literal text
    eln.textContent = fmtStat(info.num * Math.max(0, Math.min(1, g)), info);
  }

  // intro transition styles (theme motion personality + per-slide override, PRD §8.4)
  function introTransform(style, p) {
    switch (style) {
      case 'fade':  return 'translateY(0)';
      case 'pop':   return 'scale(' + (0.92 + 0.08 * p) + ')';
      case 'slide': return 'translateX(' + ((1 - p) * -70) + 'px)';
      case 'rise':
      default:      return 'translateY(' + ((1 - p) * 40) + 'px)';
    }
  }

  // wrap any word in `accent`/`accent2` lists with a highlight span
  function headlineHTML(text, accent, accent2) {
    accent = accent || []; accent2 = accent2 || [];
    var aset = {}, a2set = {};
    var key0 = function (w) { return w.toLowerCase().replace(/[^a-z0-9']/g, ''); };
    accent.forEach(function (w) { aset[key0(w)] = 1; });
    accent2.forEach(function (w) { a2set[key0(w)] = 1; });
    return text.split(/(\s+)/).map(function (tok) {
      var key = tok.toLowerCase().replace(/[^a-z0-9']/g, '');
      if (aset[key]) return '<span class="accent">' + tok + '</span>';
      if (a2set[key]) return '<span class="accent2">' + tok + '</span>';
      return tok;
    }).join('');
  }

  // build one .slide element per deck slide, structured by type
  DECK.slides.forEach(function (s) {
    var el = document.createElement('section');
    el.className = 'slide'; el.dataset.id = s.id; el.dataset.type = s.type;
    var html = '';
    if (s.kicker) html += '<div class="kicker">' + s.kicker + '</div>';
    // McKinsey action/"so-what" title pinned at top (the message; the visual below proves it).
    // Accent words use the same accent/accent2 lists, so the insight word reads in indigo.
    if (s.title) html += '<div class="slidetitle' + (s.title.length > 48 ? ' sm' : '') + '">' +
      headlineHTML(s.title, s.accent, s.accent2) + '</div>';
    if (s.type === 'diagram') {
      html += '<div class="bars">' + (s.bars || []).map(function (b) {
        var bk = b.kind === 'muted' ? 'muted' : (b.kind === 'bad' ? 'bad' : '');
        return '<div class="barcol"><div class="bar ' + bk +
          '" data-val="' + (b.value || 0) + '"></div><div class="barlabel">' + (b.label || '') + '</div></div>';
      }).join('') + '</div>';
    } else if (s.type === 'stat') {
      html += '<div class="statnum" data-val="' + (s.value || '') + '">' + (s.value || '') + '</div>';
      if (s.label) html += '<div class="statlabel">' + s.label + '</div>';
    } else if (s.type === 'statgrid') {
      html += '<div class="statgrid">' + (s.stats || []).map(function (st) {
        return '<div class="statcell"><div class="statnum" data-val="' + (st.value || '') + '">' +
          (st.value || '') + '</div><div class="statlabel">' + (st.label || '') + '</div></div>';
      }).join('') + '</div>';
    } else if (s.type === 'progress') {
      html += '<div class="progresspct">0%</div>' +
        '<div class="progresstrack"><div class="progressfill" data-val="' + (s.value || 0) + '"></div></div>';
      if (s.label) html += '<div class="statlabel">' + s.label + '</div>';
    } else if (s.type === 'compare') {
      var L = s.left || {}, R = s.right || {};
      html += '<div class="compare">' +
        '<div class="cmpcard ' + (L.kind === 'bad' ? 'bad' : 'good') + '"><div class="cmptitle">' +
          (L.title || '') + '</div><div class="cmpval">' + (L.value || '') + '</div></div>' +
        '<div class="cmpvs">vs</div>' +
        '<div class="cmpcard ' + (R.kind === 'bad' ? 'bad' : 'good') + '"><div class="cmptitle">' +
          (R.title || '') + '</div><div class="cmpval">' + (R.value || '') + '</div></div>' +
        '</div>';
    } else if (s.type === 'steps') {
      html += '<div class="steps">' + (s.steps || []).map(function (st, i) {
        var title = (typeof st === 'string') ? st : (st.title || '');
        var text = (typeof st === 'string') ? '' : (st.text || '');
        return '<div class="step"><div class="stepnum">' + (i + 1) + '</div><div class="stepbody">' +
          '<div class="steptitle">' + title + '</div>' +
          (text ? '<div class="steptext">' + text + '</div>' : '') + '</div></div>';
      }).join('') + '</div>';
    } else if (s.type === 'pictograph') {
      var pf = Math.max(0, parseInt(s.filled, 10) || 0);
      var ptot = Math.max(pf, parseInt(s.total, 10) || pf);
      var pk = s.kind === 'bad' ? 'bad' : 'good';
      var pcells = '';
      for (var pi = 0; pi < ptot; pi++) pcells += '<div class="picto-cell ' + (pi < pf ? 'on ' + pk : '') + '"></div>';
      // columns from the total so small/odd counts aren't ragged in a fixed 5-col grid
      var pcols = ptot <= 5 ? ptot : (ptot % 5 === 0 ? 5 : (ptot % 4 === 0 ? 4 : (ptot % 3 === 0 ? 3 : 5)));
      html += '<div class="pictograph" style="grid-template-columns:repeat(' + pcols + ',1fr)">' + pcells + '</div>';
      if (s.label) html += '<div class="statlabel">' + s.label + '</div>';
    } else if (s.type === 'trend') {
      var tk = s.kind === 'bad' ? 'bad' : 'good';
      el.dataset.points = JSON.stringify(s.points || []);
      html += '<div class="trendwrap"><svg class="trend ' + tk + '" viewBox="0 0 100 60" preserveAspectRatio="none">' +
        '<polyline class="trend-line" points=""></polyline></svg>' +
        '<div class="trend-dot"></div><div class="trend-end">' + (s.end_label || '') + '</div></div>';
      if (s.label) html += '<div class="statlabel">' + s.label + '</div>';
    } else if (s.type === 'ring') {
      var rk = s.kind === 'bad' ? 'bad' : 'good';
      html += '<div class="ringwrap"><svg class="ring ' + rk + '" viewBox="0 0 100 100">' +
        '<circle class="ring-track" cx="50" cy="50" r="42"></circle>' +
        '<circle class="ring-fill" cx="50" cy="50" r="42" data-val="' + (s.value || 0) + '"></circle>' +
        '</svg><div class="ring-pct">0%</div></div>';
      if (s.label) html += '<div class="statlabel">' + s.label + '</div>';
    } else if (s.type === 'ranked') {
      html += '<div class="ranked">' + (s.bars || []).map(function (b) {
        var rbk = b.kind === 'muted' ? 'muted' : (b.kind === 'bad' ? 'bad' : '');
        return '<div class="rankrow' + (b.kind === 'muted' ? ' muted' : '') + '"><div class="ranktop">' +
          '<span class="ranklabel">' + (b.label || '') + '</span>' +
          (b.display ? '<span class="rankval">' + b.display + '</span>' : '') + '</div>' +
          '<div class="ranktrack"><div class="rankbar ' + rbk +
          '" data-val="' + (b.value || 0) + '"></div></div></div>';
      }).join('') + '</div>';
    } else if (s.type === 'delta') {
      var dk = s.kind === 'bad' ? 'bad' : 'good';
      html += '<div class="delta">' +
        '<div class="delta-cell"><div class="delta-val" data-val="' + (s.from || '') + '">' + (s.from || '') + '</div>' +
        (s.from_label ? '<div class="delta-lab">' + s.from_label + '</div>' : '') + '</div>' +
        '<div class="delta-arrow">&rarr;</div>' +
        '<div class="delta-cell"><div class="delta-val ' + dk + '" data-val="' + (s.to || '') + '">' + (s.to || '') + '</div>' +
        (s.to_label ? '<div class="delta-lab">' + s.to_label + '</div>' : '') + '</div></div>';
      if (s.change) html += '<div class="delta-badge ' + dk + '">' + s.change + '</div>';
    } else if (s.type === 'timeline') {
      var evs = s.events || [];
      html += '<div class="timeline"><div class="tl-track"><div class="tl-line"></div>' + evs.map(function (e, i) {
        var left = evs.length > 1 ? (i / (evs.length - 1) * 100) : 50;
        return '<div class="tl-event" style="left:' + left.toFixed(2) + '%"><div class="tl-dot"></div>' +
          '<div class="tl-date">' + (e.date || '') + '</div><div class="tl-evlabel">' + (e.label || '') + '</div></div>';
      }).join('') + '</div></div>';
    } else if (s.type === 'waterfall') {
      var wfStart = s.start || {}, wfEnd = s.end || {}, wfSteps = s.steps || [];
      var run = Number(wfStart.value) || 0, maxTop = Math.max(0, run), wcols = [];
      wcols.push({ label: wfStart.label || '', floor: 0, val: run, cls: 'tot' });
      wfSteps.forEach(function (st) {
        var v = Number(st.value) || 0, floor = v >= 0 ? run : run + v;
        wcols.push({ label: st.label || '', floor: floor, val: Math.abs(v), cls: (st.kind === 'bad' || v < 0) ? 'bad' : 'good' });
        run += v; if (run > maxTop) maxTop = run;
      });
      var endVal = (wfEnd.value === undefined || wfEnd.value === null) ? run : Number(wfEnd.value);
      wcols.push({ label: wfEnd.label || '', floor: 0, val: endVal, cls: 'tot' });
      if (endVal > maxTop) maxTop = endVal;
      el.dataset.wfmax = String(maxTop || 1);
      html += '<div class="waterfall">' + wcols.map(function (c) {
        return '<div class="wf-col"><div class="wf-barwrap"><div class="wf-bar ' + c.cls +
          '" data-floor="' + c.floor + '" data-val="' + c.val + '"></div></div>' +
          '<div class="wf-label">' + c.label + '</div></div>';
      }).join('') + '</div>';
    } else if (s.type === 'matrix') {
      var xa = s.x_axis || ['', ''], ya = s.y_axis || ['', ''];
      html += '<div class="matrix"><div class="mx-plot"><div class="mx-axisx"></div><div class="mx-axisy"></div>' +
        (s.points || []).map(function (p) {
          return '<div class="mx-pt ' + (p.kind === 'bad' ? 'bad' : 'good') + '" style="left:' +
            (Number(p.x) * 100).toFixed(1) + '%;bottom:' + (Number(p.y) * 100).toFixed(1) + '%">' +
            '<span class="mx-ptlab">' + (p.label || '') + '</span></div>';
        }).join('') + '</div>' +
        '<div class="mx-xlo">' + (xa[0] || '') + '</div><div class="mx-xhi">' + (xa[1] || '') + '</div>' +
        '<div class="mx-ylo">' + (ya[0] || '') + '</div><div class="mx-yhi">' + (ya[1] || '') + '</div></div>';
    } else if (s.type === 'reframe') {
      var rtot = ((s.before || '') + (s.strike || '') + (s.after || '')).length;
      html += '<div class="reframe headline sm' + (rtot > 38 ? ' xs' : '') + '">' +
        '<span class="rf-before">' + (s.before || '') + ' </span>' +
        '<span class="rf-strike"><span class="rf-line"></span>' + (s.strike || '') + '</span>' +
        '<span class="rf-arrow"> &rarr; </span>' +
        '<span class="rf-after accent">' + (s.after || '') + '</span></div>';
    } else if (s.type === 'highlight') {
      var mset = {};
      (s.mark || []).forEach(function (w) { mset[w.toLowerCase().replace(/[^a-z0-9']/g, '')] = 1; });
      var hcls = (s.headline && s.headline.length > 60) ? 'headline sm' : 'headline';
      html += '<div class="' + hcls + '">' + (s.headline || '').split(/(\s+)/).map(function (tok) {
        if (mset[tok.toLowerCase().replace(/[^a-z0-9']/g, '')]) return '<span class="hl"><span class="hl-bg"></span>' + tok + '</span>';
        return tok;
      }).join('') + '</div>';
    } else if (s.type === 'build') {
      var bacc = {}, bacc2 = {};
      (s.accent || []).forEach(function (w) { bacc[w.toLowerCase().replace(/[^a-z0-9']/g, '')] = 1; });
      (s.accent2 || []).forEach(function (w) { bacc2[w.toLowerCase().replace(/[^a-z0-9']/g, '')] = 1; });
      var bcls = (s.headline && s.headline.length > 60) ? 'headline sm' : 'headline';
      html += '<div class="' + bcls + ' buildline">' + (s.headline || '').split(/\s+/).filter(Boolean).map(function (w) {
        var k = w.toLowerCase().replace(/[^a-z0-9']/g, '');
        return '<span class="bw' + (bacc[k] ? ' accent' : (bacc2[k] ? ' accent2' : '')) + '">' + w + '</span>';
      }).join(' ') + '</div>';
    } else if (s.type === 'punch') {
      var pcls = s.kind === 'bad' ? ' accent2' : (s.kind === 'good' ? ' accent' : '');
      var pword = s.word || s.headline || '';
      var psz = pword.length <= 5 ? '' : (pword.length <= 8 ? ' md' : ' sm');  // shrink so long words don't clip
      html += '<div class="punch' + psz + pcls + '">' + pword + '</div>';
    } else if (s.type === 'list') {
      html += '<div class="list">' + (s.items || []).map(function (it, i) {
        return '<div class="li-row"><span class="li-num">' + (i + 1) + '</span><span class="li-text">' + it + '</span></div>';
      }).join('') + '</div>';
    } else if (s.type === 'define') {
      var dtcls = (s.term || '').length > 16 ? ' sm' : '';  // long terms drop a size
      html += '<div class="define"><div class="def-term' + dtcls + '">' + (s.term || '') + '</div>' +
        '<div class="def-body">' + (s.definition || '') + '</div></div>';
    } else if (s.type === 'quote') {
      html += '<div class="quoteblock"><div class="quotemark">“</div><div class="quotetext">' +
        (s.quote || s.headline || '') + '</div>' +
        (s.attribution ? '<div class="quoteattr">— ' + s.attribution + '</div>' : '') + '</div>';
    } else if (s.type === 'figure') {
      html += '<div class="figframe"><img src="' + s.image + '" alt=""></div>';
      if (s.caption) html += '<div class="figcaption">' + s.caption + '</div>';
    } else if (s.type === 'cta') {
      var b = DECK.brand || {}, c = b.cta || {};
      if (b.product) html += '<div class="figframe cta-product"><img src="' + b.product + '" alt=""></div>';
      if (b.logo) html += '<img class="cta-logo" src="' + b.logo + '" alt="">';
      if (c.headline) html += '<div class="headline sm cta-head">' + c.headline + '</div>';
      if (c.subkicker) html += '<div class="subkicker">' + c.subkicker + '</div>';
      if (c.url) html += '<div class="cta-url">' + c.url + '</div>';
    } else {
      var cls = (s.headline && s.headline.length > 60) ? 'headline sm' : 'headline';
      html += '<div class="' + cls + '">' + headlineHTML(s.headline || '', s.accent, s.accent2) + '</div>';
    }
    if (s.subkicker) html += '<div class="subkicker">' + s.subkicker + '</div>';
    // sourced data-viz: a small citation pinned bottom-left (no chart-junk, just provenance).
    if (s.source) html += '<div class="srcline">Source: ' + s.source + '</div>';
    el.innerHTML = html;
    stage.appendChild(el);
  });

  var slideEls = {};
  Array.prototype.forEach.call(stage.children, function (el) { slideEls[el.dataset.id] = el; });
  var DECK_MOTION = DECK.motion || 'rise';
  var styleById = {}, typeById = {};
  DECK.slides.forEach(function (s) {
    styleById[s.id] = s.transition || (s.type === 'punch' ? 'pop' : DECK_MOTION); typeById[s.id] = s.type;
  });
  // reserve the bottom caption zone so centered content never collides with captions
  // (critical for short aspects like 1:1 / 16:9 which have far less vertical room than 9:16)
  var _reserve = Math.round(window.innerHeight * ((DECK.safe_bottom || 0.14) + 0.12));
  Array.prototype.forEach.call(stage.children, function (el) { el.style.paddingBottom = _reserve + 'px'; });

  // Aspect-aware fit for the dense devices (waterfall columns, matrix labels): scale geometry
  // to the actual viewport + element count so any count reads on any aspect. Computed once —
  // the renderer fixes the viewport before load, so window dims are final here. We scale to fit,
  // never drop data: silently truncating a waterfall would break its running total (PRD §8.6).
  (function fitDenseDevices() {
    var vw = window.innerWidth, vh = window.innerHeight, avail = Math.max(200, vw - 180);  // 90px slide pad each side
    Array.prototype.forEach.call(stage.querySelectorAll('.waterfall'), function (wf) {
      var cols = wf.querySelectorAll('.wf-col'), n = cols.length; if (!n) return;
      var gap = Math.max(12, Math.min(26, avail * 0.03));
      var colW = Math.max(40, Math.min(150, (avail - (n - 1) * gap) / n));
      // size labels to the LONGEST word (labels wrap on spaces, so a single long word is the
      // binding constraint) so dense charts don't let neighbouring labels collide.
      var lw = 1;
      Array.prototype.forEach.call(cols, function (c) {
        var lb = c.querySelector('.wf-label');
        if (lb) (lb.textContent || '').split(/\s+/).forEach(function (w) { lw = Math.max(lw, w.length); });
      });
      // bias toward larger labels for mobile legibility (a touch of overlap is fine — motion graphics)
      var labFs = Math.max(20, Math.min(38, Math.min(colW * 0.40, colW / (lw * 0.52))));
      wf.style.gap = gap.toFixed(1) + 'px';
      Array.prototype.forEach.call(cols, function (c) {
        var bw = c.querySelector('.wf-barwrap'); if (bw) bw.style.width = colW.toFixed(1) + 'px';
        var lb = c.querySelector('.wf-label');
        if (lb) { lb.style.fontSize = labFs.toFixed(1) + 'px'; lb.style.maxWidth = (colW + 14).toFixed(1) + 'px'; }
      });
    });
    Array.prototype.forEach.call(stage.querySelectorAll('.matrix'), function (mx) {
      var plotW = mx.getBoundingClientRect().width || Math.min(vh * 0.58, avail * 0.78);
      var fs = Math.max(24, Math.min(40, plotW * 0.062));  // larger for mobile legibility
      Array.prototype.forEach.call(mx.querySelectorAll('.mx-ptlab'), function (lb) {
        lb.style.fontSize = fs.toFixed(1) + 'px'; lb.style.whiteSpace = 'normal';
        lb.style.maxWidth = (plotW * 0.42).toFixed(0) + 'px'; lb.style.textAlign = 'center';
      });
      Array.prototype.forEach.call(mx.querySelectorAll('.mx-xlo, .mx-xhi, .mx-ylo, .mx-yhi'), function (lb) {
        lb.style.fontSize = fs.toFixed(1) + 'px';
      });
    });
  })();

  window.renderAt = function (t) {
    var tl = window.TIMELINE; if (!tl) return;
    if (ambient) {  // continuous breathing glow + drift — GPU-composited (cheap, no repaint).
      // Opacity breathes; position drifts on two coprime-ish frequencies so the motion never
      // stalls simultaneously on both axes (a single sine stalls at its extremes → frozen frames).
      ambient.style.opacity = (0.08 + 0.10 * (0.5 + 0.5 * Math.sin(t * 0.8))).toFixed(4);
      ambient.style.transform = 'translate(' + (3.2 * Math.sin(t * 0.37)).toFixed(2) + '%,'
        + (2.6 * Math.cos(t * 0.29)).toFixed(2) + '%)';
    }
    var active = tl.slides[0];
    tl.slides.forEach(function (s) { if (t >= s.start) active = s; });

    tl.slides.forEach(function (win) {
      var el = slideEls[win.id]; if (!el) return;
      if (t < win.start || t >= win.end) { el.style.opacity = 0; el.style.transform = 'translateY(40px)'; return; }
      var span = win.end - win.start;
      var p = easeOut((t - win.start) / Math.min(0.6, span));
      el.style.opacity = p;
      el.style.transform = introTransform(styleById[win.id] || DECK_MOTION, p);
      var rt = el.dataset.type;
      if (rt === 'diagram') {
        var g = easeOut((t - win.start) / Math.min(1.0, span));
        var barMax = window.innerHeight * 0.28;  // scale bars to viewport height
        Array.prototype.forEach.call(el.querySelectorAll('.bar'), function (bar) {
          bar.style.height = (g * parseFloat(bar.dataset.val) * barMax) + 'px';
        });
      } else if (rt === 'stat') {
        countUp(el.querySelector('.statnum'), easeOut((t - win.start) / Math.min(1.0, span)));
      } else if (rt === 'progress') {
        var pg = easeOut((t - win.start) / Math.min(1.0, span));
        var fill = el.querySelector('.progressfill'), pe = el.querySelector('.progresspct');
        var pv = parseFloat(fill.dataset.val); pv = pv > 1 ? pv / 100 : pv;  // accept 0.73 or 73 or "73%"
        fill.style.width = (pg * pv * 100).toFixed(1) + '%';
        if (pe) pe.textContent = Math.round(pg * pv * 100) + '%';
      } else if (rt === 'statgrid') {
        Array.prototype.forEach.call(el.querySelectorAll('.statcell'), function (c, idx) {
          var cg = easeOut((t - win.start - idx * 0.14) / Math.min(0.8, span));  // staggered
          c.style.opacity = Math.max(0, cg);
          countUp(c.querySelector('.statnum'), cg);
        });
      } else if (rt === 'steps') {
        Array.prototype.forEach.call(el.querySelectorAll('.step'), function (st, idx) {
          var sg = easeOut((t - win.start - idx * 0.16) / Math.min(0.7, span));  // sequential reveal
          st.style.opacity = Math.max(0, sg);
          st.style.transform = 'translateX(' + ((1 - Math.max(0, sg)) * -28).toFixed(1) + 'px)';
        });
      } else if (rt === 'pictograph') {
        var pcg = easeOut((t - win.start) / Math.min(1.0, span));
        var onCells = el.querySelectorAll('.picto-cell.on');
        var lit = Math.round(pcg * onCells.length);
        Array.prototype.forEach.call(onCells, function (c, idx) { c.style.opacity = idx < lit ? 1 : 0.16; });
      } else if (rt === 'trend') {
        var tg = easeOut((t - win.start) / Math.min(1.3, span));
        if (el.__pts === undefined) {  // parse + measure once — reading clientHeight per frame forces a reflow
          var raw = JSON.parse(el.dataset.points || '[]').map(Number);
          if (raw.length) {
            var mn = Math.min.apply(null, raw), mx = Math.max.apply(null, raw), rng = (mx - mn) || 1;
            el.__pts = raw.map(function (v, i) {
              return { x: raw.length > 1 ? i / (raw.length - 1) * 100 : 50, y: 54 - ((v - mn) / rng) * 48 };
            });
          } else { el.__pts = []; }
          el.__th = el.querySelector('.trend').clientHeight || window.innerHeight * 0.34;
        }
        var pts = el.__pts;
        if (pts.length) {
          var prog = tg * (pts.length - 1), fi = Math.floor(prog), fr = prog - fi;
          var vis = pts.slice(0, fi + 1).map(function (p) { return p.x.toFixed(2) + ',' + p.y.toFixed(2); });
          var lx = pts[Math.min(fi, pts.length - 1)].x, ly = pts[Math.min(fi, pts.length - 1)].y;
          if (fi < pts.length - 1) {
            lx = pts[fi].x + (pts[fi + 1].x - pts[fi].x) * fr; ly = pts[fi].y + (pts[fi + 1].y - pts[fi].y) * fr;
            vis.push(lx.toFixed(2) + ',' + ly.toFixed(2));
          }
          var ln = el.querySelector('.trend-line'), dot = el.querySelector('.trend-dot'), te = el.querySelector('.trend-end');
          if (ln) ln.setAttribute('points', vis.join(' '));
          if (dot) {  // HTML overlay dot (the SVG viewBox is stretched, so an SVG circle would skew)
            dot.style.left = lx.toFixed(2) + '%'; dot.style.top = (ly / 60 * el.__th).toFixed(1) + 'px';
          }
          if (te) te.style.opacity = Math.max(0, Math.min(1, (tg - 0.85) / 0.15));
        }
      } else if (rt === 'ring') {
        var rg = easeOut((t - win.start) / Math.min(1.3, span));
        var rfill = el.querySelector('.ring-fill'), rpe = el.querySelector('.ring-pct');
        var rv = parseFloat(rfill.dataset.val); rv = rv > 1 ? rv / 100 : rv;
        var RC = 2 * Math.PI * 42;
        rfill.style.strokeDasharray = RC.toFixed(2);
        rfill.style.strokeDashoffset = (RC * (1 - rg * rv)).toFixed(2);
        if (rpe) rpe.textContent = Math.round(rg * rv * 100) + '%';
      } else if (rt === 'ranked') {
        Array.prototype.forEach.call(el.querySelectorAll('.rankrow'), function (row, idx) {
          var rkg = easeOut((t - win.start - idx * 0.12) / Math.min(0.9, span));
          row.style.opacity = Math.max(0, Math.min(1, rkg * 3));
          var rb = row.querySelector('.rankbar');
          rb.style.width = (Math.max(0, rkg) * parseFloat(rb.dataset.val) * 100) + '%';
        });
      } else if (rt === 'delta') {
        var dg = easeOut((t - win.start) / Math.min(1.0, span));
        var dvals = el.querySelectorAll('.delta-val');
        if (dvals[0]) countUp(dvals[0], dg);
        if (dvals[1]) countUp(dvals[1], easeOut((t - win.start - 0.12) / Math.min(1.0, span)));
        var badge = el.querySelector('.delta-badge');
        if (badge) badge.style.opacity = Math.max(0, Math.min(1, (dg - 0.6) / 0.4));
      } else if (rt === 'timeline') {
        var tlg = easeOut((t - win.start) / Math.min(1.2, span));
        var tline = el.querySelector('.tl-line'); if (tline) tline.style.width = (tlg * 100) + '%';
        Array.prototype.forEach.call(el.querySelectorAll('.tl-event'), function (ev, idx) {
          var eg = Math.max(0, easeOut((t - win.start - 0.12 - idx * 0.18) / Math.min(0.6, span)));
          ev.style.opacity = eg;
          var d = ev.querySelector('.tl-dot'); if (d) d.style.transform = 'scale(' + (0.3 + 0.7 * eg) + ')';
        });
      } else if (rt === 'waterfall') {
        var barMaxW = window.innerHeight * 0.26, wmax = parseFloat(el.dataset.wfmax) || 1, wscale = barMaxW / wmax;
        Array.prototype.forEach.call(el.querySelectorAll('.wf-bar'), function (bar, idx) {
          var wg = Math.max(0, easeOut((t - win.start - idx * 0.13) / Math.min(0.7, span)));
          bar.style.bottom = (parseFloat(bar.dataset.floor) * wscale) + 'px';
          bar.style.height = (wg * parseFloat(bar.dataset.val) * wscale) + 'px';
        });
      } else if (rt === 'matrix') {
        Array.prototype.forEach.call(el.querySelectorAll('.mx-pt'), function (pt, idx) {
          var mg = Math.max(0, easeOut((t - win.start - 0.15 - idx * 0.14) / Math.min(0.6, span)));
          pt.style.opacity = mg;
          pt.style.transform = 'translate(-50%, 50%) scale(' + (0.2 + 0.8 * mg) + ')';
        });
      } else if (rt === 'reframe') {
        var fg = easeOut((t - win.start) / Math.min(1.4, span));
        var rl = el.querySelector('.rf-line'); if (rl) rl.style.width = (Math.min(1, fg / 0.45) * 100) + '%';
        var af = el.querySelector('.rf-after'), ra = el.querySelector('.rf-arrow');
        var ao = Math.max(0, Math.min(1, (fg - 0.45) / 0.45));
        if (af) { af.style.opacity = ao; af.style.transform = 'translateY(' + ((1 - ao) * 14).toFixed(1) + 'px)'; }
        if (ra) ra.style.opacity = ao;
      } else if (rt === 'highlight') {
        var hg = Math.max(0, easeOut((t - win.start - 0.3) / Math.min(0.8, span)));
        Array.prototype.forEach.call(el.querySelectorAll('.hl-bg'), function (bg) { bg.style.width = (hg * 100) + '%'; });
      } else if (rt === 'build') {
        // Motion serves comprehension (§8.6): when the build line's words map 1:1 to the
        // forced-alignment word timings for this slide, each word appears exactly as it's
        // spoken. Otherwise fall back to a fixed stagger from the slide start.
        var bspans = el.querySelectorAll('.bw');
        var bwords = el.__bwords;
        if (bwords === undefined) {
          var ws = tl.words.filter(function (w) { return w.slide === win.id; });
          el.__bwords = bwords = (ws.length === bspans.length) ? ws : null;
        }
        Array.prototype.forEach.call(bspans, function (w, idx) {
          var startT = bwords ? bwords[idx].start : (win.start + idx * 0.07);
          var bg = Math.max(0, easeOut((t - startT) / 0.32));
          w.style.opacity = bg;
          w.style.transform = 'translateY(' + ((1 - bg) * 18).toFixed(1) + 'px) scale(' + (0.85 + 0.15 * bg) + ')';
        });
      } else if (rt === 'list') {
        Array.prototype.forEach.call(el.querySelectorAll('.li-row'), function (row, idx) {
          var lg = Math.max(0, easeOut((t - win.start - idx * 0.14) / Math.min(0.6, span)));
          row.style.opacity = lg;
          row.style.transform = 'translateX(' + ((1 - lg) * -24).toFixed(1) + 'px)';
        });
      } else if (rt === 'define') {
        var deg = Math.max(0, easeOut((t - win.start - 0.3) / Math.min(0.6, span)));
        var body = el.querySelector('.def-body');
        if (body) { body.style.opacity = deg; body.style.transform = 'translateY(' + ((1 - deg) * 16).toFixed(1) + 'px)'; }
      }
    });

    // no kinetic captions on the CTA end card — the CTA text is already on screen
    if (typeById[active.id] === 'cta') {
      if (captionEl.dataset.sig !== 'cta') { captionEl.innerHTML = ''; captionEl.dataset.sig = 'cta'; }
      return;
    }
    // kinetic captions for the active slide.
    // caption_mode "window" (default): TikTok-style — group words into small chunks (caption_window
    //   words, breaking at sentence punctuation) and show ONLY the chunk containing the spoken word.
    // caption_mode "full": legacy — show the whole slide's narration, highlight the spoken word.
    var words = tl.words.filter(function (w) { return w.slide === active.id; });
    var capMode = DECK.caption_mode || 'window';
    var winN = DECK.caption_window || 4;
    var sig = active.id + ':' + words.length + ':' + capMode + ':' + winN;
    if (captionEl.dataset.sig !== sig) {
      captionEl.dataset.sig = sig; captionEl.innerHTML = '';
      // size caption to viewport; place above the bottom safe area
      var vw = window.innerWidth, vh = window.innerHeight;  // actual viewport (multi-aspect)
      var safeBottom = DECK.safe_bottom || 0.14;            // platform safe-zone inset
      captionEl.style.bottom = Math.round(vh * safeBottom) + 'px';
      var fs = Math.round(Math.min(vw, vh) * 0.052);        // short-side => consistent across aspects
      var chunk = 0, cnt = 0;
      words.forEach(function (w) {
        var sp = document.createElement('span'); sp.className = 'w'; sp.textContent = w.word;
        sp.style.fontSize = fs + 'px';
        sp.setAttribute('data-chunk', chunk);                // chunk membership for window mode
        captionEl.appendChild(sp);
        cnt++;
        if (cnt >= winN || /[.!?]$/.test(w.word)) { chunk++; cnt = 0; }  // break on size or sentence end
      });
    }
    var spans = captionEl.children;
    // active word index: exact time hit, else the most recent word that has started, else first.
    var act = -1;
    for (var i = 0; i < words.length; i++) { if (t >= words[i].start && t < words[i].end) { act = i; break; } }
    if (act < 0) { for (var j = 0; j < words.length; j++) { if (t >= words[j].start) act = j; } }
    if (act < 0) act = 0;
    var activeChunk = spans[act] ? +spans[act].getAttribute('data-chunk') : 0;
    for (var k = 0; k < spans.length; k++) {
      var w = words[k];
      var on = w && t >= w.start && t < w.end;
      // window mode: hide every word outside the active chunk so only ~winN words show at once.
      if (capMode === 'window') {
        spans[k].style.display = (+spans[k].getAttribute('data-chunk') === activeChunk) ? '' : 'none';
      }
      spans[k].className = on ? 'w active' : 'w';
      // gentle emphasis: color (in CSS) + a small scale. Keep the scale modest so the
      // enlarged active word doesn't visually crowd its neighbours (scale doesn't reflow).
      spans[k].style.transform = on ? 'scale(1.06)' : 'scale(1.0)';
    }
  };

  // Signal ready only once any declared @font-face glyphs are actually loaded, so the
  // first captured frame uses real fonts (not a fallback). Themes with no `fonts` field
  // declare zero faces, so this resolves immediately — no delay for them.
  function signalReady() { window.__deckReady = true; }
  if (document.fonts && document.fonts.size) {
    var loads = [];
    document.fonts.forEach(function (ff) { loads.push(ff.load().catch(function () {})); });
    Promise.all(loads).then(function () { return document.fonts.ready; }).then(signalReady, signalReady);
  } else {
    signalReady();
  }
})();
