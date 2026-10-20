/* ==========================================================================
   Mini-LMS — instructor courses page controller
   Fetches GET /api/instructor/courses and renders the list of courses
   assigned to the logged-in lecturer.
   Served from: src/ui/js/instructor-courses.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc } = window.MiniLMS;

  const alertArea = document.getElementById('alert-area');
  const listArea = document.getElementById('list-area');
  const summaryEl = document.getElementById('courses-summary');
  const refreshBtn = document.getElementById('refresh-btn');

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function clearAlert() {
    alertArea.innerHTML = '';
  }

  /* ------------------------- list four states ----------------------- */

  function renderLoading() {
    clearAlert();
    summaryEl.textContent = 'Loading…';
    listArea.innerHTML =
      `<div class="state">` +
        `<span class="spinner" aria-hidden="true"></span>` +
        `<div class="state__title u-mt-2">Loading courses…</div>` +
      `</div>`;
  }

  function renderError(err) {
    showAlert('danger', 'Failed to load courses: ' + err.message);
    summaryEl.textContent = 'Could not load courses.';
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
    summaryEl.textContent = 'No courses assigned.';
    listArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">No courses</div>` +
        `<div>You are not currently assigned to any courses. Contact the administrator.</div>` +
      `</div>`;
  }

  function renderList(data) {
    if (!data.courses || data.courses.length === 0) return renderEmpty();

    summaryEl.textContent = `Showing ${data.count} assigned course(s).`;

    const rows = data.courses.map((c) => `
      <tr>
        <td class="num">${c.course_id}</td>
        <td>
          <span class="badge badge--lecturer">
            <span class="badge__dot"></span>${esc(c.code)}
          </span>
        </td>
        <td>${esc(c.name)}</td>
        <td class="u-text-right">
          <!-- QUAN TRỌNG: Truyền course_id sang trang quiz để lọc -->
          <a class="btn btn--ghost btn--sm" 
             href="/ui/html/instructor-quizzes.html?course_id=${c.course_id}">
            View Quizzes
          </a>
        </td>
      </tr>`).join('');

    listArea.innerHTML =
      `<div class="table-wrap">` +
        `<table class="table">` +
          `<thead><tr>` +
            `<th class="num">ID</th><th>Course Code</th><th>Course Name</th>` +
            `<th style="text-align:right;">Actions</th>` +
          `</tr></thead>` +
          `<tbody>${rows}</tbody>` +
        `</table>` +
      `</div>`;
  }

  /* ------------------------------ load ------------------------------ */

  async function load() {
    renderLoading();
    try {
      const data = await Api.get('/api/instructor/courses');
      renderList(data);
    } catch (err) {
      renderError(err);
    }
  }

  /* ------------------------------ boot ------------------------------ */

  refreshBtn.addEventListener('click', load);

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