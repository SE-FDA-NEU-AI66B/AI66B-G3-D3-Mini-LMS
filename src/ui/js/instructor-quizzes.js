/* ==========================================================================
   Mini-LMS — lecturer quiz list page controller
   Served from: src/ui/js/instructor-quizzes.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, fmtDateTime } = window.MiniLMS;

  const listArea  = document.getElementById('list-area');
  const alertArea = document.getElementById('alert-area');
  const refreshBtn = document.getElementById('refresh-btn');

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function clearAlert() { alertArea.innerHTML = ''; }

  /* ------------------------------ helpers --------------------------- */

  function statusClass(status) {
    if (status === 'Published')   return 'badge--published';
    if (status === 'Unpublished') return 'badge--unpublished';
    return 'badge--draft';
  }

  function renderLoading() {
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
      `</div></div>`;
    const retry = document.getElementById('retry-btn');
    if (retry) retry.addEventListener('click', load);
  }

  function renderEmpty() {
    listArea.innerHTML =
      `<div class="state">` +
      `<div class="state__title">No quizzes yet</div>` +
      `<div>Click <strong>New quiz</strong> to create your first one.</div>` +
      `<div class="state__actions">` +
      `<a class="btn btn--primary" href="/ui/html/instructor-quiz-edit.html">New quiz</a>` +
      `</div></div>`;
  }

  function renderList(data) {
    if (!data.quizzes || data.quizzes.length === 0) return renderEmpty();

    const rows = data.quizzes.map(q => `
      <tr>
        <td>${esc(q.title)}</td>
        <td>
          <span class="badge badge--student">
            <span class="badge__dot"></span>${esc(q.course_code)}
          </span>
        </td>
        <td class="num">${esc(fmtDateTime(q.due_at))}</td>
        <td class="num">${q.time_limit_min} min</td>
        <td>
          <span class="badge ${statusClass(q.status)}">
            <span class="badge__dot"></span>${esc(q.status)}
          </span>
          ${q.status === 'Draft' && q.publish_at
            ? `<div class="u-text-sm u-text-muted">⏰ ${esc(fmtDateTime(q.publish_at))}</div>`
            : ''}
        </td>
        <td class="num">${q.question_count}</td>
        <td class="u-text-right">${actionButtons(q)}</td>
      </tr>`).join('');

    listArea.innerHTML =
      `<div class="table-wrap">` +
        `<table class="table">` +
          `<thead><tr>` +
            `<th>Quiz</th><th>Course</th><th>Due</th>` +
            `<th class="num">Limit</th><th>Status</th>` +
            `<th class="num">Questions</th>` +
            `<th style="text-align:right;">Actions</th>` +
          `</tr></thead>` +
          `<tbody>${rows}</tbody>` +
        `</table>` +
      `</div>` +
      `<div class="card__foot u-text-muted u-text-sm">` +
        `Showing <strong>${data.count}</strong> quiz(zes).` +
      `</div>`;
  }

  /* --------------------------- action buttons ----------------------- */

  function actionButtons(q) {
    const edit =
      `<a class="btn btn--ghost btn--sm" ` +
      `href="/ui/html/instructor-quiz-edit.html?quiz_id=${q.quiz_id}">Edit</a>`;

    let statusBtn = '';
    if (q.status === 'Draft') {
      const label = q.publish_at ? 'Publish now' : 'Publish';
      statusBtn =
        `<button class="btn btn--primary btn--sm" type="button" ` +
        `data-action="publish-quiz" data-quiz-id="${q.quiz_id}">${label}</button>`;
    } else if (q.status === 'Unpublished') {
      statusBtn =
        `<button class="btn btn--primary btn--sm" type="button" ` +
        `data-action="publish-quiz" data-quiz-id="${q.quiz_id}">Re-publish</button>`;
    } else {
      statusBtn =
        `<button class="btn btn--ghost btn--sm" type="button" ` +
        `data-action="unpublish-quiz" data-quiz-id="${q.quiz_id}">Unpublish</button>`;
    }

    const del =
      `<button class="btn btn--danger btn--sm" type="button" ` +
      `data-action="delete-quiz" data-quiz-id="${q.quiz_id}" ` +
      `data-quiz-title="${esc(q.title)}">Delete</button>`;

    return `<div class="u-flex u-gap-2" style="justify-content:flex-end;">` +
           `${edit}${statusBtn}${del}</div>`;
  }

  /* ------------------------------- load ----------------------------- */

  async function load() {
    clearAlert();
    renderLoading();
    try {
      const data = await Api.get('/api/instructor/quizzes');
      renderList(data);
    } catch (err) {
      renderError(err);
    }
  }

  /* ------------------------------ actions --------------------------- */

  async function handleDelete(button) {
    const quizId = button.dataset.quizId;
    const title  = button.dataset.quizTitle || ('#' + quizId);

    if (!window.confirm(`Delete quiz "${title}"? This cannot be undone.`)) return;

    button.disabled = true;
    try {
      await Api.del(`/api/instructor/quizzes/${quizId}`);
      showAlert('success', `Quiz "${title}" deleted.`);
      await load();
    } catch (err) {
      showAlert('danger', err.message);
      button.disabled = false;
    }
  }

  async function handleStatus(button, action) {
    const quizId = button.dataset.quizId;
    const verb   = action === 'publish' ? 'publish' : 'unpublish';

    if (!window.confirm(`Are you sure you want to ${verb} this quiz?`)) return;

    button.disabled = true;
    try {
      await Api.post(`/api/instructor/quizzes/${quizId}/${action}`);
      showAlert('success', `Quiz ${action === 'publish' ? 'published' : 'unpublished'}.`);
      await load();
    } catch (err) {
      showAlert('danger', err.message);
      button.disabled = false;
    }
  }

  document.addEventListener('click', (event) => {
    const publishBtn = event.target.closest('button[data-action="publish-quiz"]');
    if (publishBtn) return handleStatus(publishBtn, 'publish');

    const unpublishBtn = event.target.closest('button[data-action="unpublish-quiz"]');
    if (unpublishBtn) return handleStatus(unpublishBtn, 'unpublish');
    
    const btn = event.target.closest('button[data-action="delete-quiz"]');
    if (btn) handleDelete(btn);
  });

  refreshBtn.addEventListener('click', load);

  /* ------------------------------- boot ----------------------------- */

  load();
})();