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

  function easeOut(x) { x = Math.min(1, Math.max(0, x)); return 1 - Math.pow(1 - x, 3); }

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

  window.renderAt = function (t) {
    var tl = window.TIMELINE; if (!tl) return;
    var active = tl.slides[0];
    tl.slides.forEach(function (s) { if (t >= s.start) active = s; });

    tl.slides.forEach(function (win) {
      var el = slideEls[win.id]; if (!el) return;
      if (t < win.start || t >= win.end) { el.style.opacity = 0; el.style.transform = 'translateY(40px)'; return; }
      var span = win.end - win.start;
      var p = easeOut((t - win.start) / Math.min(0.6, span));
      el.style.opacity = p;
      el.style.transform = 'translateY(' + ((1 - p) * 40) + 'px)';
      if (el.dataset.type === 'diagram') {
        var g = easeOut((t - win.start) / Math.min(1.0, span));
        Array.prototype.forEach.call(el.querySelectorAll('.bar'), function (bar) {
          bar.style.height = (g * parseFloat(bar.dataset.val) * 520) + 'px';
        });
      }
    });

    // kinetic captions for the active slide
    var words = tl.words.filter(function (w) { return w.slide === active.id; });
    var sig = active.id + ':' + words.length;
    if (captionEl.dataset.sig !== sig) {
      captionEl.dataset.sig = sig; captionEl.innerHTML = '';
      // size caption to viewport; place above the bottom safe area
      captionEl.style.bottom = Math.round(tl.height * 0.18) + 'px';
      var fs = Math.round(tl.width * 0.052);
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
