/* ==========================================================================
   Mini-LMS — student dashboard controller
   Fetches GET /api/quizzes and renders summary + table with the
   usual four states (loading / error / empty / data).
   Served from: src/ui/js/student-dashboard.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, fmtDateTime } = window.MiniLMS;

  const alertArea = document.getElementById('alert-area');
  const listArea  = document.getElementById('list-area');
  const refreshBtn = document.getElementById('refresh-btn');

  /* ------------------------------ alerts ---------------------------- */

  function renderSummary(data) {
    if (!data.quizzes || data.quizzes.length === 0) {
      alertArea.innerHTML = '';
      return;
    }
    const courseCodes = new Set(data.quizzes.map((q) => q.course_code));
    alertArea.innerHTML =
      `<div class="alert alert--info" role="status">` +
        `<svg class="alert__icon" width="16" height="16" viewBox="0 0 24 24" ` +
             `fill="none" stroke="currentColor" stroke-width="2">` +
          `<circle cx="12" cy="12" r="9"/>` +
          `<path d="M12 8v5M12 16.5v.01"/>` +
        `</svg>` +
        `<div>You have <strong>${data.count}</strong> upcoming quiz(zes) ` +
        `across <strong>${courseCodes.size}</strong> course(s).</div>` +
      `</div>`;
  }

  /* ------------------------- list four states ----------------------- */

  function renderLoading() {
    alertArea.innerHTML = '';
    listArea.innerHTML =
      `<div class="state">` +
        `<span class="spinner" aria-hidden="true"></span>` +
        `<div class="state__title u-mt-2">Loading quizzes…</div>` +
      `</div>`;
  }

  function renderError(err) {
    listArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not load quizzes</div>` +
        `<div>${esc(err.message)}</div>` +
        `<div class="state__actions">` +
          `<button class="btn btn--ghost" type="button" id="retry-btn">Try again</button>` +
        `</div>` +
      `</div>`;
    const retry = document.getElementById('retry-btn');
    if (retry) retry.addEventListener('click', load);
  }

  function renderEmpty() {
    listArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">No quizzes available</div>` +
        `<div>You have no upcoming quizzes at the moment. Check back later.</div>` +
      `</div>`;
  }

  function renderList(data) {
    if (!data.quizzes || data.quizzes.length === 0) return renderEmpty();

    const rows = data.quizzes.map((q) => `
      <tr>
        <td>${esc(q.title)}</td>
        <td>
          <span class="badge badge--student">
            <span class="badge__dot"></span>${esc(q.course_code)}
          </span>
        </td>
        <td class="num">${esc(fmtDateTime(q.due_at))}</td>
        <td class="num">${q.time_limit_min} min</td>
        <td class="u-text-right">
          <a class="btn btn--primary btn--sm"
             href="/ui/html/quiz-take.html?quiz_id=${q.quiz_id}">Take</a>
        </td>
      </tr>`).join('');

    listArea.innerHTML =
      `<div class="table-wrap">` +
        `<table class="table">` +
          `<thead><tr>` +
            `<th>Quiz</th><th>Course</th><th>Due</th>` +
            `<th class="num">Limit</th>` +
            `<th style="text-align:right;">Action</th>` +
          `</tr></thead>` +
          `<tbody>${rows}</tbody>` +
        `</table>` +
      `</div>` +
      `<div class="card__foot u-text-muted u-text-sm">` +
        `Showing <strong>${data.count}</strong> quiz(zes).` +
      `</div>`;
  }

  /* ------------------------------ load ------------------------------ */

  async function load() {
    renderLoading();
    try {
      const data = await Api.get('/api/quizzes');
      renderSummary(data);
      renderList(data);
    } catch (err) {
      renderError(err);
    }
  }

  /* ------------------------------ boot ------------------------------ */

  async function boot() {
    try {
      const user = await Session.init();   // ensures sessionStorage email is set
      if (!user) return;                   // session.js already redirected
      document.body.dataset.userEmail = user.email || '';
      await load();
    } catch (err) {
      renderError(err);
    }
  }

  refreshBtn.addEventListener('click', load);
  boot();
})();