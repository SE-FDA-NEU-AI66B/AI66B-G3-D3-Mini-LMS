/* ==========================================================================
   Mini-LMS — lecturer quiz list page controller
   Served from: src/ui/js/instructor-quizzes.js
   Updated: Filter by course, Back button, dynamic titles, and "Past Due" badges.
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, fmtDateTime } = window.MiniLMS;

  const listArea  = document.getElementById('list-area');
  const alertArea = document.getElementById('alert-area');
  const refreshBtn = document.getElementById('refresh-btn');
  
  // Đọc course_id và code từ URL
  const urlParams = new URLSearchParams(window.location.search);
  const courseIdFilter = urlParams.get('course_id');
  const courseCodeFilter = urlParams.get('code');

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
    let msg = "Click <strong>New quiz</strong> to create your first one.";
    let btnHref = "/ui/html/instructor-quiz-edit.html";
    
    if (courseIdFilter) {
      msg = `This course has no quizzes yet.`;
      btnHref += `?course_id=${courseIdFilter}`;
    }

    listArea.innerHTML =
      `<div class="state">` +
      `<div class="state__title">No quizzes found</div>` +
      `<div>${msg}</div>` +
      `<div class="state__actions">` +
      `<a class="btn btn--primary" href="${btnHref}">New quiz</a>` +
      `</div></div>`;
  }

  function renderList(data) {
    // 1. Lọc danh sách nếu đang ở trong một course cụ thể
    let quizzes = data.quizzes;
    if (courseIdFilter) {
      quizzes = quizzes.filter(q => String(q.course_id) === String(courseIdFilter));
    }

    // 2. Cập nhật giao diện (Title, Nút Back, Nút New Quiz) nếu đang lọc
    if (courseIdFilter) {
      // Hiển thị nút Back
      const backLink = document.getElementById('back-link-container');
      if (backLink) backLink.hidden = false;

      // Xác định tên môn học (Ưu tiên lấy từ URL, nếu không có thì lấy từ data)
      const displayCode = courseCodeFilter || (quizzes.length > 0 ? quizzes[0].course_code : 'Course');
      
      const titleEl = document.getElementById('page-title');
      const subEl = document.getElementById('page-sub');
      const cardTitleEl = document.getElementById('card-title');
      
      // Cập nhật tiêu đề giống hệt ảnh
      if (titleEl) titleEl.textContent = `Quizzes for ${displayCode}`;
      if (subEl) subEl.textContent = `Found ${quizzes.length} quiz(zes) in this course.`;
      if (cardTitleEl) cardTitleEl.textContent = `Quizzes in ${displayCode}`;

      // Cập nhật link của nút "+ New quiz"
      const newQuizBtn = document.getElementById('new-quiz-btn');
      if (newQuizBtn) newQuizBtn.href = `/ui/html/instructor-quiz-edit.html?course_id=${courseIdFilter}`;
    }

    if (!quizzes || quizzes.length === 0) return renderEmpty();

    let filterBanner = '';
    if (courseIdFilter) {
      filterBanner = `
        <div class="alert alert--info" style="margin-bottom: 16px; display:flex; justify-content:space-between; align-items:center;">
          <div>Showing quizzes for <strong>${esc(courseCodeFilter || quizzes[0].course_code)}</strong> only.</div>
          <a href="/ui/html/instructor-quizzes.html" class="btn btn--ghost btn--sm">View all quizzes</a>
        </div>`;
    }

    // 3. Render từng dòng trong bảng
    const rows = quizzes.map(q => {
      const isPastDue = new Date(q.due_at) < new Date();
      const pastDueBadge = isPastDue 
        ? `<span class="badge badge--danger" style="margin-left: 8px; font-size: 10px;">Past Due</span>` 
        : '';

      return `
      <tr>
        <td>${esc(q.title)}</td>
        <td>
          <span class="badge badge--student">
            <span class="badge__dot"></span>${esc(q.course_code)}
          </span>
        </td>
        <td class="num">
          ${esc(fmtDateTime(q.due_at))}
          ${pastDueBadge}
        </td>
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
      </tr>`;
    }).join('');

    // 4. Vẽ bảng ra màn hình
    listArea.innerHTML =
      filterBanner +
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
        `Showing <strong>${quizzes.length}</strong> quiz(zes).` +
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