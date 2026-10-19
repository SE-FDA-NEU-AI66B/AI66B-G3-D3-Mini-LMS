/* ==========================================================================
   Mini-LMS — quiz result page controller

   Renders the teammate's card:
     - score-display   → score in scale 10, e.g. "5.00 / 10"
                         (teammate's formula: (score/total*10).toFixed(2))
                         turns red when score/total < 0.5
     - percent-display → "X / Y câu đúng"
     - auto-msg        → "Time was up…" if auto-submitted

   Data source: GET /api/attempts/{attempt_id}/result
   (Replaces the old sessionStorage.last_result read — the backend is
   now authoritative, so F5 / new tab / cross-device works.)
   Served from: src/ui/js/quiz-result.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc } = window.MiniLMS;

  const params = new URLSearchParams(window.location.search);
  const ATTEMPT_ID = params.get('attempt_id')
    ? Number(params.get('attempt_id'))
    : null;

  const $ = (id) => document.getElementById(id);
  const scoreDisplay   = $('score-display');
  const percentDisplay = $('percent-display');
  const autoMsg        = $('auto-msg');

  /* ------------------------ fallback (teammate's) ---------------- */

  function renderFallback(message) {
    scoreDisplay.textContent = 'No Result Found';
    scoreDisplay.style.color = 'var(--color-text-muted)';
    percentDisplay.style.display = 'none';
    autoMsg.textContent = message
      || 'Please take a quiz to see your score.';
  }

  /* ------------------------------ render ------------------------ */

  function renderResult(res) {
    // Big display: score in scale 10 (teammate's formula, unchanged)
    const score10 = ((res.score / res.total) * 10).toFixed(2);
    scoreDisplay.textContent = `${score10} / 10`;

    // Teammate's colour rule: red below 50%, primary otherwise
    if (res.total > 0 && (res.score / res.total) < 0.5) {
      scoreDisplay.style.color = '#b91c1c';   // --color-danger-fg
    } else {
      scoreDisplay.style.color = 'var(--color-primary)';
    }

    // Badge: correct / total
    percentDisplay.style.display = '';
    percentDisplay.textContent = `${res.score} / ${res.total} câu đúng`;

    // Auto-submit notice (BR3)
    if (res.auto_submitted) {
      autoMsg.textContent =
        'Time was up. The quiz was auto-submitted (BR3).';
    } else {
      autoMsg.textContent = '';
    }
  }

  /* ------------------------------ boot --------------------------- */

  async function boot() {
    // Student role gate is handled by session.js before this runs.
    await Session.init();

    if (!ATTEMPT_ID) {
      return renderFallback('Please take a quiz to see your score.');
    }

    let res;
    try {
      res = await Api.get(`/api/attempts/${ATTEMPT_ID}/result`);
    } catch (err) {
      // 401 / 403 / 404 / 409 / network — surface the backend message
      return renderFallback(err.message || 'Could not load result.');
    }

    renderResult(res);
  }

  boot();
})();