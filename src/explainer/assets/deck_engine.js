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
    if (s.type === 'diagram') {
      html += '<div class="bars">' + (s.bars || []).map(function (b) {
        return '<div class="barcol"><div class="bar ' + (b.kind === 'bad' ? 'bad' : '') +
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
    el.innerHTML = html;
    stage.appendChild(el);
  });

  var slideEls = {};
  Array.prototype.forEach.call(stage.children, function (el) { slideEls[el.dataset.id] = el; });
  var DECK_MOTION = DECK.motion || 'rise';
  var styleById = {}, typeById = {};
  DECK.slides.forEach(function (s) { styleById[s.id] = s.transition || DECK_MOTION; typeById[s.id] = s.type; });
  // reserve the bottom caption zone so centered content never collides with captions
  // (critical for short aspects like 1:1 / 16:9 which have far less vertical room than 9:16)
  var _reserve = Math.round(window.innerHeight * ((DECK.safe_bottom || 0.14) + 0.12));
  Array.prototype.forEach.call(stage.children, function (el) { el.style.paddingBottom = _reserve + 'px'; });

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
      }
    });

    // no kinetic captions on the CTA end card — the CTA text is already on screen
    if (typeById[active.id] === 'cta') {
      if (captionEl.dataset.sig !== 'cta') { captionEl.innerHTML = ''; captionEl.dataset.sig = 'cta'; }
      return;
    }
    // kinetic captions for the active slide
    var words = tl.words.filter(function (w) { return w.slide === active.id; });
    var sig = active.id + ':' + words.length;
    if (captionEl.dataset.sig !== sig) {
      captionEl.dataset.sig = sig; captionEl.innerHTML = '';
      // size caption to viewport; place above the bottom safe area
      var vw = window.innerWidth, vh = window.innerHeight;  // actual viewport (multi-aspect)
      var safeBottom = DECK.safe_bottom || 0.14;            // platform safe-zone inset
      captionEl.style.bottom = Math.round(vh * safeBottom) + 'px';
      var fs = Math.round(Math.min(vw, vh) * 0.052);        // short-side => consistent across aspects
      words.forEach(function (w) {
        var sp = document.createElement('span'); sp.className = 'w'; sp.textContent = w.word;
        sp.style.fontSize = fs + 'px'; captionEl.appendChild(sp);
      });
    }
    var spans = captionEl.children;
    for (var i = 0; i < spans.length; i++) {
      var w = words[i];
      var on = w && t >= w.start && t < w.end;
      spans[i].className = on ? 'w active' : 'w';
      spans[i].style.transform = on ? 'scale(1.12)' : 'scale(1.0)';
    }
  };

  window.__deckReady = true;
})();
