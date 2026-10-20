/* ==========================================================================
   Mini-LMS — student course detail page controller (US2)
   Fetches GET /api/student/courses/{course_id}/quizzes and renders the
   available and overdue quizzes for that specific course.
   Served from: src/ui/js/student-course-detail.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, fmtDateTime } = window.MiniLMS;

  // Get course_id from URL query string (e.g., ?course_id=1)
  const courseId = new URLSearchParams(window.location.search).get('course_id');

  /* --------------------------- element refs ------------------------- */
  const alertArea = document.getElementById('alert-area');
  const refreshBtn = document.getElementById('refresh-btn');
  
  const pageTitle = document.getElementById('page-title');
  const pageSub = document.getElementById('page-sub');
  
  const availableCard = document.getElementById('available-card');
  const availableArea = document.getElementById('available-area');
  
  const overdueCard = document.getElementById('overdue-card');
  const overdueArea = document.getElementById('overdue-area');

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* --------------------------- table builder ------------------------ */

  function renderTable(quizzes, isOverdue) {
    const rows = quizzes.map((q) => `
      <tr>
        <td>${esc(q.title)}</td>
        <td class="num">${esc(fmtDateTime(q.due_at))}</td>
        <td class="num">${q.time_limit_min} min</td>
        <td class="u-text-right">
          ${isOverdue 
            ? `<span class="badge badge--danger">Missed</span>` 
            /* ĐÂY LÀ RANH GIỚI: Chỉ là link chuyển trang, không có logic làm bài */
            : `<a class="btn btn--primary btn--sm" href="/ui/html/quiz-take.html?quiz_id=${q.quiz_id}">Take</a>`
          }
        </td>
      </tr>`).join('');

    return `
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Quiz</th>
              <th>Due</th>
              <th class="num">Limit</th>
              <th style="text-align:right;">Action</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  /* ------------------------------ load ------------------------------ */

  async function load() {
    if (!courseId) {
      showAlert('danger', 'No course ID provided in the URL.');
      pageTitle.textContent = 'Error';
      pageSub.textContent = 'Cannot load quizzes without a course ID.';
      return;
    }

    // Reset UI
    alertArea.innerHTML = '';
    availableCard.hidden = true;
    overdueCard.hidden = true;
    pageSub.textContent = 'Loading course details…';

    try {
      const data = await Api.get(`/api/student/courses/${courseId}/quizzes`);
      
      // Update header based on fetched data
      if (data.quizzes && data.quizzes.length > 0) {
        pageTitle.textContent = `Quizzes for ${data.quizzes[0].course_code}`;
        pageSub.textContent = `Found ${data.count} quiz(zes) in this course.`;
      } else {
        pageTitle.textContent = 'Course Quizzes';
        pageSub.textContent = 'No quizzes found.';
      }

      // Split into available and overdue based on the backend flag
      const available = data.quizzes ? data.quizzes.filter(q => q.availability === 'available') : [];
      const overdue   = data.quizzes ? data.quizzes.filter(q => q.availability === 'overdue') : [];

      // Render Available
      if (available.length > 0) {
        availableCard.hidden = false;
        availableArea.innerHTML = renderTable(available, false);
      }

      // Render Overdue
      if (overdue.length > 0) {
        overdueCard.hidden = false;
        overdueArea.innerHTML = renderTable(overdue, true);
      }

      // Handle completely empty state
      if (available.length === 0 && overdue.length === 0) {
        showAlert('info', 'There are no quizzes for this course yet.');
      }

    } catch (err) {
      pageSub.textContent = 'Failed to load course details.';
      showAlert('danger', 'Failed to load quizzes: ' + err.message);
    }
  }

  /* ------------------------------ boot ------------------------------ */

  refreshBtn.addEventListener('click', load);

  async function boot() {
    try {
      await Session.init(); // Ensure session is ready before API call
      await load();
    } catch (err) {
      showAlert('danger', 'Session error: ' + err.message);
    }
  }

  boot();
})();