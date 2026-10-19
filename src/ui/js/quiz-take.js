/* ==========================================================================
   Mini-LMS — take-quiz page controller (US03)
   - Starts (or resumes) an attempt on load
   - One question at a time with navigator
   - Live countdown timer, server-authoritative remaining_seconds
   - Autosaves answers (PUT /answers/{qid})
   - Tab-switch detection (BR10) via POST /tab-switch
   - Submits manually or automatically at 00:00 → redirects to result page
   Served from: src/ui/js/quiz-take.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc } = window.MiniLMS;

  const params = new URLSearchParams(window.location.search);
  const QUIZ_ID = params.get('quiz_id') ? Number(params.get('quiz_id')) : null;

  /* ------------------------------ element refs ---------------------- */

  const $ = (id) => document.getElementById(id);
  const quizTitleEl   = $('quiz-title');
  const quizSubEl     = $('quiz-sub');
  const timerDisplay  = $('timer-display');
  const timerCard     = $('timer-card');
  const submitBtn     = $('submit-btn');
  const alertArea     = $('alert-area');
  const navigatorCard = $('navigator-card');
  const navigatorEl   = $('navigator');
  const progressEl    = $('progress-summary');
  const questionCard  = $('question-card');
  const questionBody  = $('question-body');
  const prevBtn       = $('prev-btn');
  const nextBtn       = $('next-btn');
  const stateCard     = $('state-card');
  const stateArea     = $('state-area');

  /* ------------------------------ state ---------------------------- */

  let attempt       = null;
  let currentIndex  = 0;
  let serverRemaining = 0;
  let clientStart   = 0;
  let remainingSec  = 0;
  let timerId       = null;
  let submitting    = false;
  let lastTabSwitchAt = 0;

  const answers     = {};   // questionId -> {question_id, chosen_option_id, text_answer}
  const saveTimers  = {};   // questionId -> timeout id (debounce)

  /* --------------------------- small helpers ----------------------- */

  function showAlert(kind, msg) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(msg)}</div></div>`;
  }
  function clearAlert() { alertArea.innerHTML = ''; }

  function fmtTime(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  }

  function updateTimerDisplay() {
    timerDisplay.textContent = fmtTime(Math.max(0, remainingSec));
    timerDisplay.style.color =
      remainingSec <= 300 ? 'var(--color-danger-fg)' : '';
  }

  function renderError(msg) {
    timerCard.hidden = true;
    navigatorCard.hidden = true;
    questionCard.hidden = true;
    stateCard.hidden = false;
    stateArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not start quiz</div>` +
        `<div>${esc(msg)}</div>` +
        `<div class="state__actions">` +
          `<a class="btn btn--ghost" href="/ui/html/student-dashboard.html">` +
            `Back to dashboard` +
          `</a>` +
        `</div>` +
      `</div>`;
  }

  /* ------------------------------ answering ------------------------ */

  function isAnswered(qid) {
    const a = answers[qid];
    if (!a) return false;
    return a.chosen_option_id != null ||
           (a.text_answer != null && a.text_answer.trim() !== '');
  }

  function onAnswerChange(qid, chosenOptionId, textAnswer, debounce) {
    answers[qid] = {
      question_id: qid,
      chosen_option_id: chosenOptionId,
      text_answer: textAnswer,
    };
    renderNavigator();

    clearTimeout(saveTimers[qid]);
    const doSave = () => {
      const body = {};
      if (chosenOptionId != null) body.chosen_option_id = chosenOptionId;
      if (textAnswer != null)     body.text_answer = textAnswer;
      Api.put(`/api/attempts/${attempt.attempt_id}/answers/${qid}`, body)
        .catch((err) => {
          if (err.status === 409 && /time/i.test(err.message)) {
            autoSubmit('Time is up.');
          } else {
            showAlert('danger', 'Could not save answer: ' + err.message);
          }
        });
    };
    if (debounce) saveTimers[qid] = setTimeout(doSave, 500);
    else doSave();
  }

  /* ------------------------------ render --------------------------- */

  function renderNavigator() {
    const total = attempt.questions.length;
    const answeredCount =
      attempt.questions.filter(q => isAnswered(q.question_id)).length;
    progressEl.textContent = `${answeredCount} of ${total} answered`;

    navigatorEl.innerHTML = attempt.questions.map((q, i) => {
      const answered = isAnswered(q.question_id);
      const active   = i === currentIndex;
      const cls = active ? 'btn btn--primary btn--sm' : 'btn btn--ghost btn--sm';
      return `<button class="${cls}" type="button" data-idx="${i}"
                      style="min-width: 40px;">
                ${i + 1}${answered ? ' ✓' : ''}
              </button>`;
    }).join('');

    navigatorEl.querySelectorAll('button[data-idx]').forEach((b) => {
      b.addEventListener('click', () => {
        currentIndex = Number(b.dataset.idx);
        render();
      });
    });
  }

  function renderQuestion() {
    const q = attempt.questions[currentIndex];
    const a = answers[q.question_id] || {};

    const header =
      `<div class="u-flex u-justify-between u-items-center">` +
        `<div class="u-text-sm u-text-muted">` +
          `Question ${currentIndex + 1} of ${attempt.questions.length}` +
        `</div>` +
        `<span class="badge badge--student">` +
          `<span class="badge__dot"></span>${esc(q.question_type)}` +
        `</span>` +
      `</div>` +
      `<div class="u-mt-2" style="font-size:16px;">` +
        `<strong>Q${q.position}.</strong> ${esc(q.prompt)}` +
      `</div>`;

    if (q.question_type === 'MCQ') {
      const opts = q.options.map((opt) => {
        const checked = a.chosen_option_id === opt.option_id;
        return `
          <label class="u-flex u-items-center u-gap-2 u-mt-2"
                 style="cursor: pointer;">
            <input type="radio" name="q-${q.question_id}"
                   value="${opt.option_id}" ${checked ? 'checked' : ''} />
            <span><strong>${esc(opt.label)}.</strong> ${esc(opt.text)}</span>
          </label>`;
      }).join('');
      questionBody.innerHTML = header + `<div class="u-mt-4">${opts}</div>`;
      questionBody.querySelectorAll('input[type="radio"]').forEach((r) => {
        r.addEventListener('change', () => {
          if (r.checked) {
            onAnswerChange(q.question_id, Number(r.value), null, false);
          }
        });
      });
    } else {
      questionBody.innerHTML =
        header +
        `<div class="u-mt-4">` +
          `<textarea class="textarea" rows="4"` +
          `          id="ans-text-${q.question_id}"` +
          `          placeholder="Your answer...">${esc(a.text_answer || '')}</textarea>` +
        `</div>`;
      const ta = questionBody.querySelector(`#ans-text-${q.question_id}`);
      ta.addEventListener('input', () => {
        onAnswerChange(q.question_id, null, ta.value, true);
      });
    }
  }

  function updateNavButtons() {
    prevBtn.disabled = currentIndex === 0;
    nextBtn.disabled = currentIndex === attempt.questions.length - 1;
  }

  function render() {
    renderNavigator();
    renderQuestion();
    updateNavButtons();
  }

  /* ------------------------------ timer ---------------------------- */

  function checkTime() {
    const elapsed = Math.floor((Date.now() - clientStart) / 1000);
    remainingSec = Math.max(0, serverRemaining - elapsed);
    updateTimerDisplay();
    if (remainingSec <= 0 && !submitting) {
      if (timerId) { clearInterval(timerId); timerId = null; }
      autoSubmit('Time is up.');
    }
  }

  function startTimer() {
    if (serverRemaining <= 0) {
      autoSubmit('Time is up.');
      return;
    }
    updateTimerDisplay();
    timerId = setInterval(checkTime, 1000);
  }

  /* ------------------------------ submit --------------------------- */

  async function doSubmit(auto) {
    if (submitting) return;
    submitting = true;
    if (timerId) { clearInterval(timerId); timerId = null; }
    clearAlert();

    try {
      const res = await Api.post(
        `/api/attempts/${attempt.attempt_id}/submit`,
        { auto_submitted: !!auto }
      );
      window.location.href =
        `/ui/html/quiz-result.html?attempt_id=${res.attempt_id}`;
    } catch (err) {
      showAlert('danger', 'Submit failed: ' + err.message);
      submitting = false;
      if (!auto && remainingSec > 0 && !timerId) {
        timerId = setInterval(checkTime, 1000);
      }
    }
  }

  function autoSubmit(notice) {
    showAlert('warning', notice || 'Time is up.');
    doSubmit(true);
  }

  submitBtn.addEventListener('click', () => {
    const total = attempt.questions.length;
    const answered =
      attempt.questions.filter(q => isAnswered(q.question_id)).length;
    const unanswered = total - answered;

    let msg = `Submit your quiz?`;
    if (unanswered > 0) {
      msg += `\n\nYou have ${unanswered} unanswered question(s). ` +
             `Unanswered = 0 points.`;
    }
    if (window.confirm(msg)) doSubmit(false);
  });

  /* --------------------------- tab-switch (BR10) ------------------- */

  function onTabSwitch() {
    if (submitting || !attempt) return;
    const now = Date.now();
    if (now - lastTabSwitchAt < 500) return;   // debounce blur+visibility pairs
    lastTabSwitchAt = now;

    Api.post(`/api/attempts/${attempt.attempt_id}/tab-switch`, {})
      .then((res) => {
        const n = res.tab_switch_count;
        if (res.flagged) {
          showAlert('danger',
            `Your attempt has been flagged (${n} tab switch` +
            `${n === 1 ? '' : 'es'}). Your lecturer will see this.`);
        } else {
          showAlert('warning',
            `Warning: tab switch detected (${n}/3). After 3, ` +
            `your attempt will be flagged.`);
        }
      })
      .catch(() => { /* non-critical */ });
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      onTabSwitch();
    } else if (!submitting) {
      checkTime();  // re-sync after returning to the tab
    }
  });

  /* ------------------------------ boot ----------------------------- */

  async function boot() {
    const user = await Session.init();
    if (!user) return;                  // session.js is redirecting
    if (user.role !== 'Student') return; // role gate already navigating

    if (!QUIZ_ID) return renderError('Missing quiz_id parameter.');

    try {
      attempt = await Api.post(`/api/quizzes/${QUIZ_ID}/attempts`, {});
    } catch (err) {
      return renderError(err.message || 'Could not start the quiz.');
    }

    quizTitleEl.textContent = attempt.quiz_title;
    quizSubEl.textContent =
      `${attempt.course_code} · ` +
      `${attempt.questions.length} question(s) · ` +
      `${attempt.time_limit_min} min`;

    (attempt.saved_answers || []).forEach((a) => { answers[a.question_id] = a; });

    serverRemaining = attempt.remaining_seconds;
    clientStart     = Date.now();
    remainingSec    = serverRemaining;

    stateCard.hidden     = true;
    timerCard.hidden     = false;
    navigatorCard.hidden = false;
    questionCard.hidden  = false;

    if (attempt.tab_switch_count > 0) {
      const n = attempt.tab_switch_count;
      if (attempt.flagged) {
        showAlert('danger',
          `Your attempt has been flagged (${n} tab switch` +
          `${n === 1 ? '' : 'es'}). Your lecturer will see this.`);
      } else {
        showAlert('warning',
          `Warning: tab switch count ${n}/3. After 3, ` +
          `your attempt will be flagged.`);
      }
    }

    render();
    startTimer();
  }

  prevBtn.addEventListener('click', () => {
    if (currentIndex > 0) { currentIndex -= 1; render(); }
  });
  nextBtn.addEventListener('click', () => {
    if (currentIndex < attempt.questions.length - 1) {
      currentIndex += 1; render();
    }
  });

  boot();
})();