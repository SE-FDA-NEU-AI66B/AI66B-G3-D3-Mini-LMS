/* ==========================================================================
   Mini-LMS — quiz result page controller
   Reads ?attempt_id=… and renders score + percentage.
   Per-question review is deferred to US10.
   Served from: src/ui/js/quiz-result.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, fmtDateTime } = window.MiniLMS;

  const params = new URLSearchParams(window.location.search);
  const ATTEMPT_ID = params.get('attempt_id')
    ? Number(params.get('attempt_id'))
    : null;

  const $ = (id) => document.getElementById(id);
  const pageTitleEl = $('page-title');
  const pageSubEl   = $('page-sub');
  const alertArea   = $('alert-area');
  const resultCard  = $('result-card');
  const resultBody  = $('result-body');
  const stateCard   = $('state-card');
  const stateArea   = $('state-area');

  function renderError(msg) {
    resultCard.hidden = true;
    stateCard.hidden  = false;
    stateArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not load result</div>` +
        `<div>${esc(msg)}</div>` +
        `<div class="state__actions">` +
          `<a class="btn btn--ghost" href="/ui/html/student-dashboard.html">` +
            `Back to dashboard` +
          `</a>` +
        `</div>` +
      `</div>`;
  }

  function fmtPct(p) { return Number(p).toFixed(2) + '%'; }

  async function boot() {
    await Session.init();

    if (!ATTEMPT_ID) return renderError('Missing attempt_id parameter.');

    let res;
    try {
      res = await Api.get(`/api/attempts/${ATTEMPT_ID}/result`);
    } catch (err) {
      return renderError(err.message || 'Could not load the result.');
    }

    pageTitleEl.textContent = res.quiz_title;
    pageSubEl.textContent   =
      `${res.course_code} · Attempt #${res.attempt_id}`;

    if (res.auto_submitted) {
      alertArea.innerHTML =
        `<div class="alert alert--warning" role="status">` +
          `<svg class="alert__icon" width="16" height="16" viewBox="0 0 24 24"` +
          `     fill="none" stroke="currentColor" stroke-width="2">` +
            `<circle cx="12" cy="12" r="9"/>` +
            `<path d="M12 8v5M12 16.5v.01"/>` +
          `</svg>` +
          `<div><strong>Time is up.</strong> Your attempt was auto-submitted.</div>` +
        `</div>`;
    }

    const pct = fmtPct(res.percentage);
    const ok  = res.percentage >= 50;

    resultBody.innerHTML =
      `<div style="text-align: center;">` +
        `<div class="u-text-muted u-text-sm">Your score</div>` +
        `<div style="font-size: 56px; font-weight: 700; margin: 8px 0;">` +
          `${res.score}` +
          `<span class="u-text-muted" style="font-size: 28px; font-weight: 500;">` +
            ` / ${res.total}` +
          `</span>` +
        `</div>` +
        `<div class="badge ${ok ? 'badge--active' : 'badge--disabled'}"` +
        `     style="font-size: 14px; padding: 6px 14px;">` +
          `${pct}` +
        `</div>` +
        `<div class="u-text-muted u-text-sm u-mt-4">` +
          `Submitted ${esc(fmtDateTime(res.submitted_at))}` +
        `</div>` +
      `</div>` +
      `<div class="card__foot u-text-muted u-text-sm u-mt-4"` +
      `     style="text-align: center;">` +
        (res.answers_released
          ? `Your lecturer has released the answers.`
          : `Your lecturer has not released the answers yet.`) +
      `</div>`;

    stateCard.hidden  = true;
    resultCard.hidden = false;
  }

  boot();
})();