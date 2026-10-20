/* ==========================================================================
   Mini-LMS — student dashboard page controller (US2)
   Fetches GET /api/quizzes and renders summary + tables with the
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

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function renderSummary(data) {
    if (!data.quizzes || data.quizzes.length === 0) {
      alertArea.innerHTML = '';
      return;
    }
    
    const availableCount = data.quizzes.filter(q => q.availability === 'available').length;
    const overdueCount = data.quizzes.filter(q => q.availability === 'overdue').length;
    const courseCodes = new Set(data.quizzes.map((q) => q.course_code));

    let summaryText = `You have <strong>${availableCount}</strong> available quiz(zes) across <strong>${courseCodes.size}</strong> course(s).`;
    
    if (overdueCount > 0) {
      summaryText += ` You also have <strong>${overdueCount}</strong> overdue quiz(zes).`;
    }

    alertArea.innerHTML =
      `<div class="alert alert--info" role="status">` +
        `<svg class="alert__icon" width="16" height="16" viewBox="0 0 24 24" ` +
             `fill="none" stroke="currentColor" stroke-width="2">` +
          `<circle cx="12" cy="12" r="9"/>` +
          `<path d="M12 8v5M12 16.5v.01"/>` +
        `</svg>` +
        `<div>${summaryText}</div>` +
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
        `<div>You have no quizzes at the moment. Check back later.</div>` +
      `</div>`;
  }

  function renderTables(data) {
    if (!data.quizzes || data.quizzes.length === 0) return renderEmpty();

    const available = data.quizzes.filter(q => q.availability === 'available');
    const overdue   = data.quizzes.filter(q => q.availability === 'overdue');

    function buildTable(quizzes, isOverdue) {
      if (quizzes.length === 0) return '';
      
      const rows = quizzes.map((q) => `
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
            ${isOverdue 
              ? `<span class="badge badge--danger">Missed</span>` 
              : `<a class="btn btn--primary btn--sm" href="/ui/html/quiz-take.html?quiz_id=${q.quiz_id}">Take</a>`}
          </td>
        </tr>`).join('');

      const heading = isOverdue ? 'Overdue Quizzes' : 'Available Quizzes';

      return `
        <section class="card">
          <div class="card__head">
            <div>
              <h2 class="card__title">${heading}</h2>
              ${!isOverdue ? `<p class="card__hint">Only quizzes with a future due date are listed.</p>` : ''}
            </div>
          </div>
          <div class="table-wrap">
            <table class="table">
              <thead><tr>
                <th>Quiz</th><th>Course</th><th>Due</th>
                <th class="num">Limit</th><th style="text-align:right;">Action</th>
              </tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </section>`;
    }

    // Render Available first, then Overdue (if any exist)
    listArea.innerHTML = buildTable(available, false) + buildTable(overdue, true);
  }

  /* ------------------------------ load ------------------------------ */

  async function load() {
    renderLoading();
    try {
      const data = await Api.get('/api/quizzes');
      renderSummary(data);
      renderTables(data);
    } catch (err) {
      showAlert('danger', 'Failed to load quizzes: ' + err.message);
      renderError(err);
    }
  }

  /* ------------------------------ boot ------------------------------ */

  async function boot() {
    try {
      const user = await Session.init();
      if (!user) return; 
      document.body.dataset.userEmail = user.email || '';
      await load();
    } catch (err) {
      showAlert('danger', 'Session error: ' + err.message);
      renderError(err);
    }
  }

  refreshBtn.addEventListener('click', load);
  boot();
})();