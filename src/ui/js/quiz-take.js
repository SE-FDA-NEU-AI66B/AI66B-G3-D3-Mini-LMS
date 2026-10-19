/* ==========================================================================
   Mini-LMS — take-quiz page controller (US03)

   NEW in this version:
     - Persistent device_id (localStorage) — one per browser
     - All mutating calls include device_id
     - Heartbeat loop (every 10 s) keeps the lease fresh
     - If another device takes over: show "taken over" screen with
       [Take back control] button
     - If this device opens a quiz held by another device: show
       "Another device is taking this quiz" with [Continue here] button
     - beforeunload → sendBeacon releases the lease immediately
   Served from: src/ui/js/quiz-take.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc } = window.MiniLMS;

  const params = new URLSearchParams(window.location.search);
  const QUIZ_ID = params.get('quiz_id') ? Number(params.get('quiz_id')) : null;

  /* ---------------------- device_id persistence --------------------- */

  const DEVICE_ID_KEY = 'minilms.device_id';

  function getOrCreateDeviceId() {
    let id = null;
    try { id = localStorage.getItem(DEVICE_ID_KEY); } catch (e) { /* ignore */ }
    if (id && id.length >= 8) return id;
    id = (window.crypto && typeof window.crypto.randomUUID === 'function')
      ? window.crypto.randomUUID()
      : 'dev-' + Date.now() + '-' + Math.random().toString(36).slice(2, 10);
    try { localStorage.setItem(DEVICE_ID_KEY, id); } catch (e) { /* ignore */ }
    return id;
  }

  const DEVICE_ID = getOrCreateDeviceId();

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

  let attempt        = null;
  let currentIndex   = 0;
  let serverRemaining = 0;
  let clientStart    = 0;
  let remainingSec   = 0;
  let timerId        = null;
  let heartbeatId    = null;
  let submitting     = false;
  let lastTabSwitchAt = 0;

  const answers     = {};
  const saveTimers  = {};

  /* --------------------------- helpers ----------------------------- */

  function showAlert(kind, msg) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(msg)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
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

  /* --------------------- stopped-page screens ---------------------- */

  function hideQuizUI() {
    timerCard.hidden     = true;
    navigatorCard.hidden = true;
    questionCard.hidden  = true;
    stateCard.hidden     = false;
  }

  function renderError(msg, resumeQuizId) {
    hideQuizUI();
    let buttons =
      `<a class="btn btn--ghost" href="/ui/html/student-dashboard.html">` +
      `  Back to dashboard` +
      `</a>`;
    if (resumeQuizId) {
      buttons =
        `<a class="btn btn--primary" ` +
        `   href="/ui/html/quiz-take.html?quiz_id=${resumeQuizId}">` +
        `  Resume active quiz` +
        `</a>` + buttons;
    }
    stateArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not start quiz</div>` +
        `<div>${esc(msg)}</div>` +
        `<div class="state__actions u-flex u-gap-2" ` +
        `     style="justify-content:center; flex-wrap:wrap;">` +
          buttons +
        `</div>` +
      `</div>`;
  }

  function renderDeviceConflict(msg) {
    hideQuizUI();
    stateArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Another device is taking this quiz</div>` +
        `<div>${esc(msg)}</div>` +
        `<div class="state__actions u-flex u-gap-2" ` +
        `     style="justify-content:center; flex-wrap:wrap;">` +
          `<button class="btn btn--primary" type="button" id="takeover-btn">` +
            `Continue on this device` +
          `</button>` +
          `<a class="btn btn--ghost" href="/ui/html/student-dashboard.html">` +
            `Back to dashboard` +
          `</a>` +
        `</div>` +
      `</div>`;
    const btn = document.getElementById('takeover-btn');
    if (btn) btn.addEventListener('click', () => boot(true));
  }

  function showTakenOverScreen(msg) {
    stopHeartbeat();
    if (timerId) { clearInterval(timerId); timerId = null; }
    submitting = true;
    hideQuizUI();
    stateArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">This quiz was taken over on another device</div>` +
        `<div>${esc(msg || 'Your attempt is now active on another device.')}</div>` +
        `<div>Your answers up to this point are saved.</div>` +
        `<div class="state__actions u-flex u-gap-2" ` +
        `     style="justify-content:center; flex-wrap:wrap;">` +
          `<button class="btn btn--primary" type="button" id="retakeover-btn">` +
            `Take back control` +
          `</button>` +
          `<a class="btn btn--ghost" href="/ui/html/student-dashboard.html">` +
            `Back to dashboard` +
          `</a>` +
        `</div>` +
      `</div>`;
    const btn = document.getElementById('retakeover-btn');
    if (btn) btn.addEventListener('click', () => boot(true));
  }

  function handleAttemptError(err, action) {
    const payload = err.payload || {};
    if (payload.device_conflict) {
      return showTakenOverScreen(err.message);
    }
    if (err.status === 409 && /already submitted/i.test(err.message)) {
      window.location.href =
        `/ui/html/quiz-result.html?attempt_id=${attempt.attempt_id}`;
      return;
    }
    if (err.status === 409 && /time/i.test(err.message)) {
      autoSubmit('Time is up.');
      return;
    }
    showAlert('danger', `Could not ${action}: ${err.message}`);
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
      const body = { device_id: DEVICE_ID };
      if (chosenOptionId != null) body.chosen_option_id = chosenOptionId;
      if (textAnswer != null)     body.text_answer = textAnswer;
      Api.put(`/api/attempts/${attempt.attempt_id}/answers/${qid}`, body)
        .catch((err) => handleAttemptError(err, 'save answer'));
    };
    if (debounce) saveTimers[qid] = setTimeout(doSave, 500);
    else doSave();
  }

  /* ------------------------------ render --------------------------- */

  function renderNavigator() {
    if (!navigatorEl || !attempt) return;
    const total = attempt.questions.length;
    const answeredCount =
      attempt.questions.filter(q => isAnswered(q.question_id)).length;
    if (progressEl) progressEl.textContent =
      `${answeredCount} of ${total} answered`;

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
    if (!questionBody || !attempt) return;
    const q = attempt.questions[currentIndex];
    if (!q) {
      questionBody.innerHTML = '<div class="state">No question to show.</div>';
      return;
    }
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
      const opts = (q.options || []).map((opt) => {
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
      if (ta) {                                    // <-- guard added
        ta.addEventListener('input', () => {
          onAnswerChange(q.question_id, null, ta.value, true);
        });
      }
    }
  }

  function updateNavButtons() {
    if (!attempt) return;
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
    if (serverRemaining <= 0) { autoSubmit('Time is up.'); return; }
    updateTimerDisplay();
    timerId = setInterval(checkTime, 1000);
  }

  /* ---------------------------- heartbeat -------------------------- */

  function startHeartbeat() {
    if (heartbeatId) return;
    heartbeatId = setInterval(async () => {
      if (submitting || !attempt) return;
      try {
        const res = await Api.post(
          `/api/attempts/${attempt.attempt_id}/heartbeat`,
          { device_id: DEVICE_ID }
        );
        if (typeof res.remaining_seconds === 'number') {
          const clientElapsed = Math.floor((Date.now() - clientStart) / 1000);
          const clientRemaining = Math.max(0, serverRemaining - clientElapsed);
          if (Math.abs(clientRemaining - res.remaining_seconds) > 10) {
            serverRemaining = res.remaining_seconds;
            clientStart     = Date.now();
            updateTimerDisplay();
          }
        }
      } catch (err) {
        const payload = err.payload || {};
        if (payload.device_conflict) {
          showTakenOverScreen(err.message);
        }
      }
    }, 10000);
  }

  function stopHeartbeat() {
    if (heartbeatId) { clearInterval(heartbeatId); heartbeatId = null; }
  }

  /* ------------------------------ submit --------------------------- */

  async function doSubmit(auto) {
    if (submitting) return;
    submitting = true;
    if (timerId) { clearInterval(timerId); timerId = null; }
    stopHeartbeat();
    clearAlert();

    try {
      const res = await Api.post(
        `/api/attempts/${attempt.attempt_id}/submit`,
        { device_id: DEVICE_ID, auto_submitted: !!auto }
      );
      window.location.href =
        `/ui/html/quiz-result.html?attempt_id=${res.attempt_id}`;
    } catch (err) {
      const payload = err.payload || {};
      if (payload.device_conflict) {
        return showTakenOverScreen(err.message);
      }
      showAlert('danger', 'Submit failed: ' + err.message);
      submitting = false;
      if (!auto && remainingSec > 0 && !timerId) {
        timerId = setInterval(checkTime, 1000);
      }
      startHeartbeat();
    }
  }

  function autoSubmit(notice) {
    showAlert('warning', notice || 'Time is up.');
    doSubmit(true);
  }

  submitBtn.addEventListener('click', () => {
    if (!attempt) return;
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
    if (now - lastTabSwitchAt < 500) return;
    lastTabSwitchAt = now;

    Api.post(
      `/api/attempts/${attempt.attempt_id}/tab-switch`,
      { device_id: DEVICE_ID }
    )
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
      .catch((err) => {
        const payload = err.payload || {};
        if (payload.device_conflict) showTakenOverScreen(err.message);
      });
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) onTabSwitch();
    else if (!submitting) checkTime();
  });

  /* -------------------------- release on unload -------------------- */

  window.addEventListener('beforeunload', () => {
    if (!attempt || !navigator.sendBeacon) return;
    try {
      navigator.sendBeacon(
        `/api/attempts/${attempt.attempt_id}/release` +
        `?device_id=${encodeURIComponent(DEVICE_ID)}`
      );
    } catch (e) { /* ignore */ }
  });

  /* ------------------------------ boot ----------------------------- */

  async function boot(takeoverOverride) {
    // Reset state (retry / takeover flow re-enters this function)
    submitting = false;
    stopHeartbeat();
    if (timerId) { clearInterval(timerId); timerId = null; }
    Object.keys(answers).forEach(k => delete answers[k]);
    Object.keys(saveTimers).forEach(k => clearTimeout(saveTimers[k]));
    currentIndex = 0;
    clearAlert();

    const takeover = !!takeoverOverride || params.get('takeover') === '1';

    const user = await Session.init();
    if (!user || user.role !== 'Student') return;

    if (!QUIZ_ID) return renderError('Missing quiz_id parameter.', null);

    hideQuizUI();
    stateArea.innerHTML =
      `<div class="state">` +
        `<span class="spinner" aria-hidden="true"></span>` +
        `<div class="state__title u-mt-2">Loading attempt…</div>` +
      `</div>`;

    try {
      attempt = await Api.post(
        `/api/quizzes/${QUIZ_ID}/attempts`,
        { device_id: DEVICE_ID, takeover: takeover }
      );
    } catch (err) {
      const payload = err.payload || {};
      if (payload.device_conflict) {
        return renderDeviceConflict(err.message);
      }
      if (payload.active_quiz_id) {
        return renderError(err.message, payload.active_quiz_id);
      }
      return renderError(err.message || 'Could not start the quiz.', null);
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
    startHeartbeat();
  }

  prevBtn.addEventListener('click', () => {
    if (attempt && currentIndex > 0) { currentIndex -= 1; render(); }
  });
  nextBtn.addEventListener('click', () => {
    if (attempt && currentIndex < attempt.questions.length - 1) {
      currentIndex += 1; render();
    }
  });

  boot();
})();