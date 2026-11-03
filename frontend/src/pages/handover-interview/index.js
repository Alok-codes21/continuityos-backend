/**
 * ContinuityOS — AI Handover Interview Page
 * Guided structured conversational knowledge extraction for departing engineers.
 */

import {
  getProject,
  getTeamMembers,
  createKnowledgeRecord,
} from '../../services/mock-api.js';
import { MockStore } from '../../data/mock-store.js';

export default async function renderPage(container) {
  const [project, teamMembers] = await Promise.all([
    getProject(),
    getTeamMembers(),
  ]);

  const departingPerson = teamMembers.find(m => m.status === 'departing') || teamMembers[0];

  // 9 Core Interview Sections from Specification
  const sections = [
    { id: 'sec-resp', title: 'Responsibilities', icon: 'bi-briefcase', status: 'completed', questionsAnswered: 3, totalQuestions: 3 },
    { id: 'sec-current', title: 'Current Work & In-Flight PRs', icon: 'bi-kanban', status: 'completed', questionsAnswered: 2, totalQuestions: 2 },
    { id: 'sec-arch', title: 'Architecture & Technical Decisions', icon: 'bi-diagram-3', status: 'in-progress', questionsAnswered: 2, totalQuestions: 4 },
    { id: 'sec-deploy', title: 'Deployment & Operations', icon: 'bi-hdd-network', status: 'in-progress', questionsAnswered: 1, totalQuestions: 3 },
    { id: 'sec-bugs', title: 'Known Bugs & Workarounds', icon: 'bi-bug', status: 'not-started', questionsAnswered: 0, totalQuestions: 3 },
    { id: 'sec-deps', title: 'Dependencies & Integrations', icon: 'bi-link-45deg', status: 'not-started', questionsAnswered: 0, totalQuestions: 2 },
    { id: 'sec-contacts', title: 'Important Contacts & Vendors', icon: 'bi-person-lines-fill', status: 'not-started', questionsAnswered: 0, totalQuestions: 2 },
    { id: 'sec-risks', title: 'Risks & Hidden Gotchas', icon: 'bi-shield-exclamation', status: 'not-started', questionsAnswered: 0, totalQuestions: 3 },
    { id: 'sec-tribal', title: 'Unwritten & Tribal Knowledge', icon: 'bi-chat-heart', status: 'not-started', questionsAnswered: 0, totalQuestions: 2 },
  ];

  let activeSectionId = 'sec-arch';

  // Session messages stored in mock store
  let messages = MockStore.get('interview_messages_' + activeSectionId, [
    {
      id: 'msg-1',
      sender: 'ai',
      text: `Hello Alex! We're focusing on the **Architecture & Technical Decisions** of Project Atlas. In ADR-007, you decided on Apache Kafka over RabbitMQ. Could you explain the exact partitioning strategy and topic retention settings you configured for the data pipeline?`,
      timestamp: '10:14 AM',
      citations: ['ADR-007 (Architecture Log)'],
    },
    {
      id: 'msg-2',
      sender: 'user',
      text: `We use 12 topics with 4 partitions each. Message retention is set to 7 days on the raw-events topic, and log compaction is enabled on the entity-state topic. Consumer groups are keyed by service name.`,
      timestamp: '10:16 AM',
      isConfirmed: true,
    },
    {
      id: 'msg-3',
      sender: 'ai',
      text: `That matches what we see in the Terraform scripts! One critical follow-up: When large batches cause Celery workers to crash (Bug #001), what is the manual recovery procedure you perform in Kubernetes before the automatic DLQ is deployed?`,
      timestamp: '10:17 AM',
      isFollowUp: true,
    },
  ]);

  function render() {
    // Progress calculation
    const totalQ = sections.reduce((acc, s) => acc + s.totalQuestions, 0);
    const answeredQ = sections.reduce((acc, s) => acc + s.questionsAnswered, 0);
    const progressPercent = Math.round((answeredQ / totalQ) * 100);

    const activeSec = sections.find(s => s.id === activeSectionId) || sections[0];

    container.innerHTML = `
      <div class="handover-interview-page">
        <!-- ── Top Header ────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">AI Handover Interview Workspace</h1>
              <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-mic-fill me-1"></i>Active Knowledge Extraction
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Conducting structured transition debrief with <strong>${departingPerson.name}</strong> (${departingPerson.role}).
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button class="cos-btn cos-btn-secondary" id="btn-save-draft">
              <i class="bi bi-save"></i> Save Draft
            </button>
            <button class="cos-btn cos-btn-primary" id="btn-export-interview">
              <i class="bi bi-journal-arrow-up"></i> Promote to Knowledge Ledger
            </button>
          </div>
        </div>

        <!-- ── Progress Summary Bar ──────────────────────────────────── -->
        <div class="cos-card p-3 mb-4 bg-white">
          <div class="d-flex align-items-center justify-content-between mb-2">
            <div class="d-flex align-items-center gap-2">
              <span style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: var(--text-secondary);">
                Handover Interview Progress:
              </span>
              <span class="fw-bold text-dark" style="font-size: 13px;">${answeredQ} of ${totalQ} questions answered (${progressPercent}%)</span>
            </div>
            <span class="badge bg-warning text-dark" style="font-size: 11px;">11 Days to Transition</span>
          </div>
          <div class="progress" style="height: 8px;">
            <div class="progress-bar bg-primary" role="progressbar" style="width: ${progressPercent}%;" aria-valuenow="${progressPercent}" aria-valuemin="0" aria-valuemax="100"></div>
          </div>
        </div>

        <!-- ── Interview Layout Grid ─────────────────────────────────── -->
        <div class="row g-4 mb-4">
          <!-- Left: 9 Interview Sections Navigator -->
          <div class="col-12 col-lg-4">
            <div class="cos-card">
              <div class="cos-card-header">
                <div class="cos-card-title"><i class="bi bi-list-check text-primary me-2"></i>Debrief Modules</div>
                <span style="font-size: 11px; color: var(--text-muted);">9 Sections</span>
              </div>
              <div class="list-group list-group-flush" id="section-list">
                ${sections.map(s => `
                  <button class="list-group-item list-group-item-action p-3 d-flex align-items-center justify-content-between section-nav-btn ${s.id === activeSectionId ? 'active' : ''}" data-id="${s.id}">
                    <div class="d-flex align-items-center gap-2">
                      <div class="section-icon" style="width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 13px; background: ${s.id === activeSectionId ? '#ffffff' : 'var(--main-bg)'}; color: ${s.id === activeSectionId ? 'var(--primary)' : 'var(--text-secondary)'};">
                        <i class="bi ${s.icon}"></i>
                      </div>
                      <div class="text-start">
                        <div style="font-weight: 600; font-size: 12px;">${s.title}</div>
                        <div style="font-size: 10px; opacity: 0.8;">${s.questionsAnswered} / ${s.totalQuestions} answered</div>
                      </div>
                    </div>
                    <div>
                      ${s.status === 'completed' 
                        ? '<span class="badge bg-success" style="font-size: 9px;"><i class="bi bi-check-lg"></i></span>'
                        : s.status === 'in-progress'
                        ? '<span class="badge bg-warning text-dark" style="font-size: 9px;">In Progress</span>'
                        : '<span class="badge bg-light text-muted border" style="font-size: 9px;">Pending</span>'
                      }
                    </div>
                  </button>
                `).join('')}
              </div>
            </div>
          </div>

          <!-- Right: Interactive Chat / Q&A Canvas -->
          <div class="col-12 col-lg-8">
            <div class="cos-card d-flex flex-column" style="height: 560px;">
              <!-- Chat Header -->
              <div class="cos-card-header bg-white border-bottom">
                <div class="d-flex align-items-center gap-2">
                  <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary-lighter); display: flex; align-items: center; justify-content: center; color: var(--primary);">
                    <i class="bi bi-robot"></i>
                  </div>
                  <div>
                    <div class="fw-bold text-dark" style="font-size: 13px;">${activeSec.title}</div>
                    <div style="font-size: 11px; color: var(--text-muted);">ContinuityOS Knowledge Extraction Agent</div>
                  </div>
                </div>
                <div class="d-flex align-items-center gap-2">
                  <button class="cos-btn cos-btn-ghost btn-sm" id="btn-add-note">
                    <i class="bi bi-sticky me-1"></i> Add Scratchpad Note
                  </button>
                </div>
              </div>

              <!-- Message Stream -->
              <div class="cos-card-body p-4 flex-grow-1 overflow-auto" id="chat-stream" style="background: var(--main-bg);">
                ${messages.map(m => `
                  <div class="d-flex ${m.sender === 'user' ? 'justify-content-end' : 'justify-content-start'} mb-3">
                    <div class="message-bubble p-3 rounded" style="max-width: 82%; ${m.sender === 'user' ? 'background: #ffffff; border: 1px solid var(--border); box-shadow: var(--card-shadow);' : 'background: #ffffff; border-left: 3px solid var(--primary); box-shadow: var(--card-shadow);'}">
                      <div class="d-flex align-items-center justify-content-between mb-1 gap-3">
                        <span class="fw-bold" style="font-size: 11px; color: ${m.sender === 'user' ? 'var(--text-primary)' : 'var(--primary)'};">
                          ${m.sender === 'user' ? 'Alex Rivera (You)' : '<i class="bi bi-stars me-1"></i>ContinuityOS AI Interviewer'}
                        </span>
                        <span class="text-muted" style="font-size: 10px;">${m.timestamp}</span>
                      </div>
                      <div style="font-size: 13px; line-height: 1.5; color: var(--text-primary);">
                        ${m.text}
                      </div>

                      ${m.citations ? `
                        <div class="mt-2 pt-2 border-top d-flex align-items-center gap-1" style="font-size: 10px; color: var(--text-muted);">
                          <i class="bi bi-link-45deg text-primary"></i> Context: <strong>${m.citations.join(', ')}</strong>
                        </div>
                      ` : ''}

                      ${m.sender === 'user' ? `
                        <div class="mt-2 pt-2 border-top d-flex align-items-center justify-content-between" style="font-size: 11px;">
                          <span class="text-success"><i class="bi bi-check-circle-fill me-1"></i>Captured as Draft Knowledge</span>
                          <button class="btn btn-link btn-sm p-0 text-decoration-none text-primary fw-bold btn-promote-msg" data-text="${m.text.replace(/"/g, '&quot;')}" style="font-size: 11px;">
                            Promote to Ledger <i class="bi bi-arrow-right"></i>
                          </button>
                        </div>
                      ` : ''}
                    </div>
                  </div>
                `).join('')}
              </div>

              <!-- Message Input Footer -->
              <div class="p-3 bg-white border-top">
                <form id="interview-input-form" class="d-flex gap-2">
                  <input
                    type="text"
                    class="form-control"
                    id="interview-answer-input"
                    placeholder="Type your response to the interviewer (e.g. 'We scale Celery workers with...')"
                    autocomplete="off"
                  >
                  <button type="submit" class="cos-btn cos-btn-primary" style="white-space: nowrap;">
                    <i class="bi bi-send-fill me-1"></i> Submit Answer
                  </button>
                </form>
                <div class="d-flex align-items-center justify-content-between mt-2" style="font-size: 11px; color: var(--text-muted);">
                  <span><i class="bi bi-shield-check me-1"></i>Answers will be tagged "Inferred" until human-verified.</span>
                  <button class="btn btn-link btn-sm p-0 text-muted" id="btn-skip-q" style="font-size: 11px;">Skip question for now</button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Captured Answers Review Table ─────────────────────────── -->
        <div class="cos-card mb-4">
          <div class="cos-card-header">
            <div>
              <div class="cos-card-title"><i class="bi bi-journal-check text-success me-2"></i>Captured Institutional Knowledge in this Session</div>
              <div class="cos-card-subtitle">Review and approve answers before final handover signoff</div>
            </div>
            <span class="badge bg-success-subtle text-success">3 Approved Items</span>
          </div>
          <div class="table-responsive">
            <table class="table cos-table mb-0 align-middle">
              <thead>
                <tr>
                  <th style="width: 25%;">Section</th>
                  <th style="width: 45%;">Captured Knowledge Statement</th>
                  <th style="width: 15%;">State in Ledger</th>
                  <th style="width: 15%; text-align: right;">Review Action</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <span class="fw-bold" style="font-size: 12px;">Architecture</span>
                    <div style="font-size: 10px; color: var(--text-muted);">Kafka Topic Partitioning</div>
                  </td>
                  <td style="font-size: 12px;">
                    12 topics with 4 partitions each. Message retention 7 days on raw-events; entity-state uses log compaction.
                  </td>
                  <td>
                    <span class="badge-verified"><i class="bi bi-check-circle-fill me-1"></i>Verified</span>
                  </td>
                  <td style="text-align: right;">
                    <span class="text-success fw-bold" style="font-size: 11px;"><i class="bi bi-check2"></i> Confirmed</span>
                  </td>
                </tr>
                <tr>
                  <td>
                    <span class="fw-bold" style="font-size: 12px;">Deployment</span>
                    <div style="font-size: 10px; color: var(--text-muted);">pgBouncer Connection Pool</div>
                  </td>
                  <td style="font-size: 12px;">
                    pgBouncer max connections set to 80 in transaction mode to prevent RDS pool exhaustion.
                  </td>
                  <td>
                    <span class="badge-evidence-backed"><i class="bi bi-link-45deg me-1"></i>Evidence-Backed</span>
                  </td>
                  <td style="text-align: right;">
                    <span class="text-success fw-bold" style="font-size: 11px;"><i class="bi bi-check2"></i> Confirmed</span>
                  </td>
                </tr>
                <tr>
                  <td>
                    <span class="fw-bold" style="font-size: 12px;">Current Work</span>
                    <div style="font-size: 10px; color: var(--text-muted);">Pipeline OOM Fix</div>
                  </td>
                  <td style="font-size: 12px;">
                    Chunked batching script in progress under branch feature/oom-chunking. Needs unit tests before merge.
                  </td>
                  <td>
                    <span class="badge-inferred"><i class="bi bi-lightning-charge me-1"></i>Inferred</span>
                  </td>
                  <td style="text-align: right;">
                    <button class="cos-btn cos-btn-ghost btn-xs text-primary" onclick="alert('Promoted to verified institutional record in Uncertainty Ledger.')">
                      Approve Fact
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────
    container.querySelectorAll('.section-nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeSectionId = btn.getAttribute('data-id');
        render();
      });
    });

    const form = container.querySelector('#interview-input-form');
    const input = container.querySelector('#interview-answer-input');
    if (form && input) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        // User answer message
        messages.push({
          id: `msg-${Date.now()}`,
          sender: 'user',
          text,
          timestamp: 'Just now',
          isConfirmed: false,
        });

        // AI follow up response
        setTimeout(() => {
          messages.push({
            id: `msg-${Date.now() + 1}`,
            sender: 'ai',
            text: `Thank you, Alex. I have logged that in the transition ledger. Could you also confirm who has root SSH access to the secondary bastion host in AWS?`,
            timestamp: 'Just now',
            isFollowUp: true,
          });
          MockStore.set('interview_messages_' + activeSectionId, messages);
          render();
          const stream = container.querySelector('#chat-stream');
          if (stream) stream.scrollTop = stream.scrollHeight;
        }, 500);

        MockStore.set('interview_messages_' + activeSectionId, messages);
        render();
      });
    }

    container.querySelectorAll('.btn-promote-msg').forEach(btn => {
      btn.addEventListener('click', async () => {
        const text = btn.getAttribute('data-text');
        await createKnowledgeRecord({
          claim: text,
          component: 'data-pipeline',
          classification: 'verified',
          confidence: 90,
          sourceLabel: 'AI Handover Interview (Alex Rivera)',
          lastVerified: new Date().toISOString().split('T')[0],
          verifiedBy: 'Alex Rivera',
        });
        alert('Answer promoted directly to Uncertainty Ledger as Verified claim!');
      });
    });

    const btnSave = container.querySelector('#btn-save-draft');
    if (btnSave) {
      btnSave.addEventListener('click', () => {
        MockStore.set('interview_messages_' + activeSectionId, messages);
        alert('Interview progress saved to local storage.');
      });
    }

    const btnPromoteAll = container.querySelector('#btn-export-interview');
    if (btnPromoteAll) {
      btnPromoteAll.addEventListener('click', () => {
        window.location.hash = '#/uncertainty-ledger';
      });
    }
  }

  render();
}
