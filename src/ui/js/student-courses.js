/* ==========================================================================
   Mini-LMS — student courses page controller (US2)
   Fetches GET /api/student/courses and renders the list of enrolled courses.
   Served from: src/ui/js/student-courses.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc } = window.MiniLMS;

  const listArea = document.getElementById('list-area');
  const refreshBtn = document.getElementById('refresh-btn');
  const alertArea = document.getElementById('alert-area');

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* ------------------------- list four states ----------------------- */

  function renderLoading() {
    alertArea.innerHTML = '';
    listArea.innerHTML =
      `<div class="state">` +
        `<span class="spinner" aria-hidden="true"></span>` +
        `<div class="state__title u-mt-2">Loading courses…</div>` +
      `</div>`;
  }

  function renderError(err) {
    showAlert('danger', 'Failed to load courses: ' + err.message);
    listArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not load courses</div>` +
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
        `<div class="state__title">No courses found</div>` +
        `<div>You are not enrolled in any active courses at the moment.</div>` +
      `</div>`;
  }

  function renderList(data) {
    if (!data.courses || data.courses.length === 0) return renderEmpty();

    const rows = data.courses.map((c) => `
      <tr>
        <td>
          <span class="badge badge--student">
            <span class="badge__dot"></span>${esc(c.code)}
          </span>
        </td>
        <td>${esc(c.name)}</td>
        <td>${esc(c.lecturer_name)}</td>
        <td class="num">${c.quiz_count}</td>
        <td class="u-text-right">
          <a class="btn btn--primary btn--sm"
             href="/ui/html/student-course-detail.html?course_id=${c.course_id}">
            View Quizzes
          </a>
        </td>
      </tr>`).join('');

    listArea.innerHTML =
      `<div class="table-wrap">` +
        `<table class="table">` +
          `<thead><tr>` +
            `<th>Code</th><th>Course Name</th><th>Lecturer</th>` +
            `<th class="num">Quizzes</th>` +
            `<th style="text-align:right;">Action</th>` +
          `</tr></thead>` +
          `<tbody>${rows}</tbody>` +
        `</table>` +
      `</div>` +
      `<div class="card__foot u-text-muted u-text-sm">` +
        `Showing <strong>${data.count}</strong> enrolled course(s).` +
      `</div>`;
  }

  /* ------------------------------ load ------------------------------ */

  async function load() {
    renderLoading();
    try {
      const data = await Api.get('/api/student/courses');
      renderList(data);
    } catch (err) {
      renderError(err);
    }
  }

  /* ------------------------------ boot ------------------------------ */

  refreshBtn.addEventListener('click', load);
  
  // Note: Session.init() is already called in the HTML inline script,
  // so we can just load the data here. However, if we want to be safe
  // and ensure the email is set in sessionStorage before Api.get runs,
  // we can wait for Session.init() again (it's idempotent).
  async function boot() {
    try {
      await Session.init();
      await load();
    } catch (err) {
      renderError(err);
    }
  }
  
  boot();
})();