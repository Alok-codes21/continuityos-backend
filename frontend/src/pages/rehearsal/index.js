/**
 * ContinuityOS — Rehearsal Module Page
 * Guided scenario-based comprehension practice for incoming engineers.
 */

import {
  getTeamMembers,
} from '../../services/mock-api.js';

export default async function renderPage(container) {
  const teamMembers = await getTeamMembers();

  // Scenarios for incoming engineer practice
  const scenarios = [
    {
      id: 'scen-1',
      title: 'Scenario 1: Production Pipeline Worker OOM Crash on Kafka Batch >100k',
      component: 'Data Pipeline Service',
      difficulty: 'High',
      context: `During peak traffic (18:00–21:00 UTC), a massive event batch arrives on the raw-events Kafka topic. The Celery worker hits its 2Gi container memory limit and Kubernetes OOM-kills the pod. The consumer group lag begins escalating rapidly.`,
      question: `As the on-call engineer, what is the documented manual mitigation procedure before the permanent chunking fix in Sprint 24?`,
      options: [
        { id: 'opt-a', text: 'Increase RDS database connection pool directly in PostgreSQL configuration', correct: false, explanation: 'Incorrect. RDS is not the bottleneck here; the issue is in-memory worker array deserialization.' },
        { id: 'opt-b', text: 'Execute the /admin/split-batch endpoint to partition large Kafka batches into sub-25k chunks', correct: true, explanation: 'Correct! This is Alex Rivera\'s documented workaround in Bug #001 until Sprint 24 chunked streaming is deployed.' },
        { id: 'opt-c', text: 'Delete the consumer group to skip the message queue', correct: false, explanation: 'Incorrect! This causes permanent loss of enterprise transaction events.' },
      ],
      userAnswer: null,
      isUnderstood: null,
      expertContact: 'Alex Rivera (Author of Pipeline)',
    },
    {
      id: 'scen-2',
      title: 'Scenario 2: Intermittent 401 Unauthorised Errors on Multi-Tenant Auth Service',
      component: 'Auth Service',
      difficulty: 'Medium',
      context: `An enterprise client reports that their analytics service randomly gets 401 errors every few hours, even though their OAuth JWT token has not expired according to its timestamp.`,
      question: `What architectural consideration explains this behavior according to the ContinuityOS knowledge records?`,
      options: [
        { id: 'opt-a', text: 'Istio mTLS proxy expires certificates every 60 seconds', correct: false, explanation: 'Incorrect. Istio certificates rotate on a 24-hour cycle and do not reject valid JWTs.' },
        { id: 'opt-b', text: 'A suspected race condition in JWT token refresh during the clock-skew validation window (Bug #002)', correct: true, explanation: 'Correct! Documented in Bug #002. Clients are advised to retry with exponential backoff while awaiting security log access.' },
        { id: 'opt-c', text: 'The client is exceeding the 100 req/min Redis rate limit', correct: false, explanation: 'Incorrect. Rate limiting returns HTTP 429 Too Many Requests, not HTTP 401.' },
      ],
      userAnswer: null,
      isUnderstood: null,
      expertContact: 'Alex Rivera (Auth Service Lead)',
    },
    {
      id: 'scen-3',
      title: 'Scenario 3: Adding a New Consumer to the Kafka Event Bus',
      component: 'Event Bus (Kafka)',
      difficulty: 'Medium',
      context: `A new microservice requires real-time access to the user-signup stream. You need to register a new consumer group without degrading partition throughput.`,
      question: `What partitioning constraint was established in ADR-007?`,
      options: [
        { id: 'opt-a', text: 'Consumers must share a single static consumer ID', correct: false, explanation: 'Incorrect. Static single consumer IDs bottleneck message consumption to 1 partition.' },
        { id: 'opt-b', text: 'Each topic has exactly 4 partitions; consumer group concurrency should not exceed 4 parallel instances per topic', correct: true, explanation: 'Correct! Configured per ADR-007. Additional workers beyond 4 will remain idle unless partitions are scaled.' },
        { id: 'opt-c', text: 'Kafka requires manual partition rebalancing on every new connection', correct: false, explanation: 'Incorrect. Kafka consumer coordinator handles rebalancing automatically.' },
      ],
      userAnswer: null,
      isUnderstood: null,
      expertContact: 'Alex Rivera (Kafka Architect)',
    },
  ];

  let currentScenarioIdx = 0;

  function render() {
    const scen = scenarios[currentScenarioIdx];
    const completedScenarios = scenarios.filter(s => s.userAnswer !== null).length;
    const progressPercent = Math.round((completedScenarios / scenarios.length) * 100);

    container.innerHTML = `
      <div class="rehearsal-page">
        <!-- ── Top Header ────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Transition Readiness Rehearsal</h1>
              <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-mortarboard me-1"></i>Scenario-Based Verification
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Interactive practice scenarios simulating real-world operational events for incoming engineers.
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-light text-dark border px-2 py-1" style="font-size: 11px;">
              <i class="bi bi-shield-check text-success me-1"></i>Readiness Aid (No Performance Penalty)
            </span>
          </div>
        </div>

        <!-- ── Progress Bar ──────────────────────────────────────────── -->
        <div class="cos-card p-3 mb-4 bg-white">
          <div class="d-flex align-items-center justify-content-between mb-2">
            <span style="font-size: 12px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
              Rehearsal Practice Progress:
            </span>
            <span class="fw-bold text-primary" style="font-size: 12px;">${completedScenarios} of ${scenarios.length} Completed (${progressPercent}%)</span>
          </div>
          <div class="progress" style="height: 6px;">
            <div class="progress-bar bg-primary" style="width: ${progressPercent}%;"></div>
          </div>
        </div>

        <!-- ── Main Scenario Card ────────────────────────────────────── -->
        <div class="row g-4 mb-4">
          <!-- Left: Scenarios List -->
          <div class="col-12 col-lg-4">
            <div class="cos-card">
              <div class="cos-card-header">
                <div class="cos-card-title"><i class="bi bi-collection-play text-primary me-2"></i>Scenarios</div>
              </div>
              <div class="list-group list-group-flush">
                ${scenarios.map((s, idx) => `
                  <button class="list-group-item list-group-item-action p-3 scenario-select-btn ${idx === currentScenarioIdx ? 'active' : ''}" data-idx="${idx}">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                      <span class="badge ${s.difficulty === 'High' ? 'bg-danger-subtle text-danger' : 'bg-warning-subtle text-warning'}" style="font-size: 9px;">
                        ${s.difficulty}
                      </span>
                      ${s.userAnswer !== null ? '<span class="badge bg-success" style="font-size: 9px;"><i class="bi bi-check"></i> Practiced</span>' : '<span class="badge bg-light text-muted border" style="font-size: 9px;">Unattempted</span>'}
                    </div>
                    <div class="fw-bold" style="font-size: 12px;">${s.title}</div>
                    <div style="font-size: 10px; opacity: 0.8; margin-top: 2px;">Component: ${s.component}</div>
                  </button>
                `).join('')}
              </div>
            </div>
          </div>

          <!-- Right: Interactive Exercise Workspace -->
          <div class="col-12 col-lg-8">
            <div class="cos-card p-4 bg-white">
              <div class="d-flex align-items-center justify-content-between border-bottom pb-3 mb-3">
                <div>
                  <span class="badge bg-light text-secondary border mb-1" style="font-size: 10px;">${scen.component}</span>
                  <h2 class="fw-bold fs-5 text-dark m-0">${scen.title}</h2>
                </div>
                <button class="cos-btn cos-btn-ghost btn-sm text-primary" id="btn-request-help">
                  <i class="bi bi-question-circle me-1"></i> Request Expert Help
                </button>
              </div>

              <!-- Context Box -->
              <div class="p-3 rounded border mb-4" style="background: #f8fafc; font-size: 13px; line-height: 1.5; color: var(--text-primary);">
                <div class="fw-bold text-dark mb-1"><i class="bi bi-info-circle text-primary me-1"></i>Incident Context:</div>
                ${scen.context}
              </div>

              <!-- Question -->
              <div class="fw-bold fs-6 text-dark mb-3">
                ${scen.question}
              </div>

              <!-- Interactive Options -->
              <div class="d-flex flex-column gap-2 mb-4">
                ${scen.options.map(opt => {
                  const isSelected = scen.userAnswer === opt.id;
                  const showFeedback = scen.userAnswer !== null;
                  let optClass = 'bg-white border';
                  if (showFeedback) {
                    if (opt.correct) optClass = 'bg-success-subtle border-success text-success';
                    else if (isSelected && !opt.correct) optClass = 'bg-danger-subtle border-danger text-danger';
                  }

                  return `
                    <div class="p-3 rounded ${optClass} option-choice-box" data-id="${opt.id}" style="cursor: ${showFeedback ? 'default' : 'pointer'}; transition: all 0.2s;">
                      <div class="d-flex align-items-start gap-2">
                        <span class="badge bg-light text-dark border fw-bold" style="font-size: 11px;">${opt.id.toUpperCase().replace('OPT-', '')}</span>
                        <div class="flex-grow-1" style="font-size: 13px; font-weight: 500;">
                          ${opt.text}
                        </div>
                        ${showFeedback && opt.correct ? '<i class="bi bi-check-circle-fill text-success fs-5"></i>' : ''}
                        ${showFeedback && isSelected && !opt.correct ? '<i class="bi bi-x-circle-fill text-danger fs-5"></i>' : ''}
                      </div>

                      ${showFeedback && (isSelected || opt.correct) ? `
                        <div class="mt-2 pt-2 border-top text-dark" style="font-size: 11px;">
                          <strong>Feedback:</strong> ${opt.explanation}
                        </div>
                      ` : ''}
                    </div>
                  `;
                }).join('')}
              </div>

              <!-- Comprehension Self-Assessment -->
              <div class="p-3 rounded border bg-light d-flex align-items-center justify-content-between flex-wrap gap-2">
                <div style="font-size: 12px; color: var(--text-secondary);">
                  How clear do you feel on this operational runbook?
                </div>
                <div class="d-flex align-items-center gap-2">
                  <button class="cos-btn ${scen.isUnderstood === true ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm btn-mark-understood">
                    <i class="bi bi-hand-thumbs-up me-1"></i> Clear & Understood
                  </button>
                  <button class="cos-btn ${scen.isUnderstood === false ? 'cos-btn-danger' : 'cos-btn-ghost'} btn-sm btn-mark-unclear">
                    <i class="bi bi-hand-thumbs-down me-1"></i> Needs Follow-up Discussion
                  </button>
                </div>
              </div>

              <!-- Next Scenario Button -->
              <div class="d-flex justify-content-between align-items-center mt-4 pt-3 border-top">
                <button class="cos-btn cos-btn-ghost btn-sm" id="btn-prev-scenario" ${currentScenarioIdx === 0 ? 'disabled' : ''}>
                  ← Previous Scenario
                </button>
                <button class="cos-btn cos-btn-primary btn-sm" id="btn-next-scenario" ${currentScenarioIdx === scenarios.length - 1 ? 'disabled' : ''}>
                  Next Scenario →
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────
    container.querySelectorAll('.scenario-select-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        currentScenarioIdx = parseInt(btn.getAttribute('data-idx'), 10);
        render();
      });
    });

    container.querySelectorAll('.option-choice-box').forEach(box => {
      box.addEventListener('click', () => {
        if (scen.userAnswer !== null) return;
        scen.userAnswer = box.getAttribute('data-id');
        render();
      });
    });

    const btnUnderstood = container.querySelector('.btn-mark-understood');
    if (btnUnderstood) {
      btnUnderstood.addEventListener('click', () => {
        scen.isUnderstood = true;
        render();
      });
    }

    const btnUnclear = container.querySelector('.btn-mark-unclear');
    if (btnUnclear) {
      btnUnclear.addEventListener('click', () => {
        scen.isUnderstood = false;
        alert(`Flagged as a knowledge gap for review with ${scen.expertContact}.`);
        render();
      });
    }

    const btnReqHelp = container.querySelector('#btn-request-help');
    if (btnReqHelp) {
      btnReqHelp.addEventListener('click', () => {
        alert(`Help request dispatched to authorized owner: ${scen.expertContact}. A pairing invite has been logged.`);
      });
    }

    const btnPrev = container.querySelector('#btn-prev-scenario');
    if (btnPrev) {
      btnPrev.addEventListener('click', () => {
        if (currentScenarioIdx > 0) {
          currentScenarioIdx--;
          render();
        }
      });
    }

    const btnNext = container.querySelector('#btn-next-scenario');
    if (btnNext) {
      btnNext.addEventListener('click', () => {
        if (currentScenarioIdx < scenarios.length - 1) {
          currentScenarioIdx++;
          render();
        }
      });
    }
  }

  render();
}
