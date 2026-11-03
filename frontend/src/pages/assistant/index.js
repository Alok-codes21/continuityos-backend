/**
 * ContinuityOS — AI Assistant Page
 * Knowledge Q&A grounded strictly in citations and visible uncertainty labels.
 */

import {
  getProject,
  getDocuments,
} from '../../services/mock-api.js';

export default async function renderPage(container) {
  const [project, documents] = await Promise.all([
    getProject(),
    getDocuments(),
  ]);

  // Suggested prompt chips
  const suggestedPrompts = [
    'What is the root cause of the data pipeline OOM crash?',
    'Who owns the Kafka cluster and what are the topic retention rules?',
    'Explain the decision to use Kafka over RabbitMQ (ADR-007)',
    'What are the unresolved bugs in the Auth Service?',
    'Where is the JWT secret key rotation procedure documented?',
  ];

  // Conversation history
  let messages = [
    {
      id: 'msg-init',
      sender: 'ai',
      text: `Hello! I am your ContinuityOS Knowledge Assistant for **${project.name || 'Project Atlas'}**. Every answer I provide is strictly grounded in project records with evidence citations and confidence indicators. Ask me anything about components, runbooks, bugs, or architecture decisions.`,
      timestamp: 'Just now',
    },
  ];

  // Mock responses for common questions
  const knowledgeBase = {
    'oom': {
      text: `According to **Bug #001**, the data pipeline crashes when Kafka batches exceed 100,000 records because the Celery worker process hits its Kubernetes container limit (2Gi).`,
      classification: 'verified',
      confidence: 96,
      source: 'Bug Report #001',
      date: 'Oct 22, 2026',
      citation: 'doc-004 (Pipeline Runbook Chunk #2)',
      workaround: 'Manual mitigation is available via the <code>/admin/split-batch</code> endpoint until permanent chunked streaming arrives in Sprint 24.',
    },
    'kafka': {
      text: `Per **ADR-007**, Apache Kafka is configured with 12 topics and 4 partitions each. Message retention is set to 7 days on the raw-events topic, and log compaction is enabled on the entity-state topic. Alex Rivera is currently the sole owner.`,
      classification: 'verified',
      confidence: 99,
      source: 'ADR-007 (Architecture Log)',
      date: 'March 14, 2026',
      citation: 'doc-003 (ADR-007)',
    },
    'rabbit': {
      text: `Kafka was selected over RabbitMQ because of its partitioned high-throughput architecture (needed for the 50k events/min requirement), built-in log compaction, and native replay capabilities without third-party plugins.`,
      classification: 'verified',
      confidence: 97,
      source: 'ADR-007',
      date: 'March 14, 2026',
      citation: 'doc-003 (ADR-007)',
    },
    'auth': {
      text: `There is currently **1 high-severity unresolved bug** in Auth Service: **Bug #002** (intermittent 401 token expiry race during clock-skew). Additionally, Task-003 (Redis rate limiting) and Task-013 (multi-tenant RBAC) are pending.`,
      classification: 'evidence-backed',
      confidence: 88,
      source: 'Bug #002 & DEC-002',
      date: 'Oct 28, 2026',
      citation: 'doc-007 (RBAC Design Spec)',
    },
    'jwt': {
      text: `The JWT secret key rotation runbook was **NOT FOUND in available enterprise knowledge**. A missing documentation gap (<code>doc-010</code>) has been recorded in the Uncertainty Ledger. Alex Rivera has been flagged as the single point of failure for this operation.`,
      classification: 'missing',
      confidence: 0,
      isNotFound: true,
      source: 'Uncertainty Ledger Gap #010',
      date: 'Current',
    },
    'outage': {
      text: `Warning: Contradictory records exist for the November 2025 outage. Confluence incident report <code>doc-012</code> attributes the root cause to "Kafka broker partition misconfiguration", whereas Alex Rivera's Slack records attribute it to "PostgreSQL read replica replication lag".`,
      classification: 'conflicting',
      confidence: 30,
      isConflict: true,
      source: 'doc-012 vs Slack #infra-alerts',
      date: 'Nov 2025',
    },
  };

  function render() {
    container.innerHTML = `
      <div class="assistant-page">
        <!-- ── Top Header ────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Grounded Knowledge Assistant</h1>
              <span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-stars me-1 text-primary"></i>Strict Evidence Retrieval (RAG)
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Answers are cited from Project Atlas documents, architecture ADRs, and verified Jira tickets.
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <select class="form-select form-select-sm" style="width: 220px;" disabled>
              <option>${project.name || 'Project Atlas'} (Current Context)</option>
            </select>
            <button class="cos-btn cos-btn-secondary btn-sm" id="btn-clear-chat">
              <i class="bi bi-trash"></i> Clear Session
            </button>
          </div>
        </div>

        <!-- ── Chat Conversation Canvas ──────────────────────────────── -->
        <div class="cos-card d-flex flex-column mb-3" style="height: 560px; background: #ffffff;">
          <!-- Chat Message Feed -->
          <div class="cos-card-body p-4 flex-grow-1 overflow-auto" id="chat-messages-container" style="background: var(--main-bg);">
            ${messages.map(m => `
              <div class="d-flex ${m.sender === 'user' ? 'justify-content-end' : 'justify-content-start'} mb-3">
                <div class="message-card p-3 rounded" style="max-width: 80%; ${m.sender === 'user' ? 'background: #ffffff; border: 1px solid var(--border); box-shadow: var(--card-shadow);' : 'background: #ffffff; border-left: 3px solid var(--primary); box-shadow: var(--card-shadow);'}">
                  <div class="d-flex align-items-center justify-content-between mb-2 gap-3">
                    <span class="fw-bold" style="font-size: 11px; color: ${m.sender === 'user' ? 'var(--text-primary)' : 'var(--primary)'};">
                      ${m.sender === 'user' ? 'You' : '<i class="bi bi-stars text-primary me-1"></i>ContinuityOS Assistant'}
                    </span>
                    <span class="text-muted" style="font-size: 10px;">${m.timestamp}</span>
                  </div>

                  <div style="font-size: 13px; line-height: 1.5; color: var(--text-primary);">
                    ${m.text}
                  </div>

                  <!-- Grounded Citations & Confidence Pill -->
                  ${m.classification ? `
                    <div class="mt-3 pt-2 border-top d-flex align-items-center justify-content-between flex-wrap gap-2" style="font-size: 11px;">
                      <div class="d-flex align-items-center gap-2">
                        ${renderBadge(m.classification)}
                        <span class="badge ${m.confidence >= 80 ? 'bg-success' : m.confidence >= 50 ? 'bg-warning text-dark' : 'bg-danger'} text-white" style="font-size: 10px;">
                          ${m.confidence}% Confidence
                        </span>
                      </div>
                      <div class="text-muted d-flex align-items-center gap-1">
                        <i class="bi bi-file-earmark-text text-primary"></i>
                        <span>Source: <strong>${m.source}</strong> (${m.date})</span>
                      </div>
                    </div>
                  ` : ''}

                  <!-- Conflict Warning Callout -->
                  ${m.isConflict ? `
                    <div class="alert alert-danger p-2 mt-2 mb-0" style="font-size: 11px;">
                      <i class="bi bi-exclamation-triangle-fill me-1"></i>
                      <strong>Source Contradiction:</strong> Review both conflicting records in the Uncertainty Ledger.
                      <a href="#/uncertainty-ledger?classification=conflicting" class="ms-1 fw-bold text-danger text-decoration-none">Open Dispute View →</a>
                    </div>
                  ` : ''}

                  <!-- Not Found Warning Callout -->
                  ${m.isNotFound ? `
                    <div class="alert alert-warning p-2 mt-2 mb-0" style="font-size: 11px;">
                      <i class="bi bi-question-diamond-fill me-1"></i>
                      <strong>Information Hole:</strong> This knowledge has not been authored or recorded in any connected repository.
                    </div>
                  ` : ''}
                </div>
              </div>
            `).join('')}
          </div>

          <!-- Input Footer -->
          <div class="p-3 bg-white border-top">
            <!-- Suggested Prompts Strip -->
            <div class="d-flex align-items-center gap-1 overflow-auto flex-nowrap mb-2 pb-1" style="font-size: 11px;">
              <span class="text-muted text-uppercase fw-bold me-1" style="font-size: 10px;">Suggested:</span>
              ${suggestedPrompts.map(p => `
                <button class="badge bg-light text-secondary border prompt-chip text-nowrap" data-prompt="${p}" style="cursor: pointer; font-weight: 500; padding: 4px 8px;">
                  ${p}
                </button>
              `).join('')}
            </div>

            <form id="assistant-form" class="d-flex gap-2">
              <input
                type="text"
                class="form-control"
                id="assistant-input"
                placeholder="Ask about project architecture, bug workarounds, or owner dependencies..."
                autocomplete="off"
              >
              <button type="submit" class="cos-btn cos-btn-primary" style="white-space: nowrap;">
                <i class="bi bi-send-fill me-1"></i> Ask Assistant
              </button>
            </form>
            <div class="d-flex justify-content-between text-muted mt-2" style="font-size: 11px;">
              <span><i class="bi bi-lock-fill me-1"></i>ContinuityOS Assistant operates strictly under project-level authorization.</span>
              <span>Backend RAG Integration Layer Ready</span>
            </div>
          </div>
        </div>
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────
    const form = container.querySelector('#assistant-form');
    const input = container.querySelector('#assistant-input');
    if (form && input) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        submitQuery(text);
      });
    }

    container.querySelectorAll('.prompt-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const promptText = chip.getAttribute('data-prompt');
        submitQuery(promptText);
      });
    });

    const btnClear = container.querySelector('#btn-clear-chat');
    if (btnClear) {
      btnClear.addEventListener('click', () => {
        messages = [messages[0]];
        render();
      });
    }

    function submitQuery(queryText) {
      messages.push({
        id: `msg-${Date.now()}`,
        sender: 'user',
        text: queryText,
        timestamp: 'Just now',
      });
      render();

      const scrollContainer = container.querySelector('#chat-messages-container');
      if (scrollContainer) scrollContainer.scrollTop = scrollContainer.scrollHeight;

      // Match response logic
      setTimeout(() => {
        const q = queryText.toLowerCase();
        let match = null;
        if (q.includes('oom') || q.includes('crash') || q.includes('batch')) match = knowledgeBase['oom'];
        else if (q.includes('rabbit') || q.includes('decision') || q.includes('adr')) match = knowledgeBase['rabbit'];
        else if (q.includes('kafka') || q.includes('retention') || q.includes('partition')) match = knowledgeBase['kafka'];
        else if (q.includes('auth') || q.includes('bug')) match = knowledgeBase['auth'];
        else if (q.includes('jwt') || q.includes('secret') || q.includes('rotation')) match = knowledgeBase['jwt'];
        else if (q.includes('outage') || q.includes('incident') || q.includes('conflict')) match = knowledgeBase['outage'];
        else {
          match = {
            text: `Based on available project knowledge for Project Atlas, this topic was not explicitly indexed in current architecture ADRs. You can submit an AI Handover Interview prompt or request human verification.`,
            classification: 'inferred',
            confidence: 45,
            source: 'Project Knowledge Store',
            date: 'Nov 2026',
          };
        }

        messages.push({
          id: `msg-${Date.now() + 1}`,
          sender: 'ai',
          text: match.text,
          classification: match.classification,
          confidence: match.confidence,
          source: match.source,
          date: match.date,
          isConflict: match.isConflict,
          isNotFound: match.isNotFound,
          timestamp: 'Just now',
        });

        render();
        const sc = container.querySelector('#chat-messages-container');
        if (sc) sc.scrollTop = sc.scrollHeight;
      }, 400);
    }
  }

  function renderBadge(cls) {
    switch (cls) {
      case 'verified':
        return `<span class="badge-verified"><i class="bi bi-check-circle-fill me-1"></i>Verified</span>`;
      case 'evidence-backed':
        return `<span class="badge-evidence-backed"><i class="bi bi-link-45deg me-1"></i>Evidence-Backed</span>`;
      case 'inferred':
        return `<span class="badge-inferred"><i class="bi bi-lightning-charge me-1"></i>Inferred</span>`;
      case 'conflicting':
        return `<span class="badge-conflicting"><i class="bi bi-exclamation-triangle me-1"></i>Conflicting</span>`;
      case 'missing':
        return `<span class="badge-missing"><i class="bi bi-question-diamond me-1"></i>Missing Gap</span>`;
      default:
        return `<span class="badge bg-light text-dark border">${cls}</span>`;
    }
  }

  render();
}
