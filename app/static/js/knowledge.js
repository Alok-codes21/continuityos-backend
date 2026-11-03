
const API_BASE = "";
const token = sessionStorage.getItem("access_token");

const projectSelect = document.getElementById("projectSelect");
const knowledgeList = document.getElementById("knowledgeList");
const graphCanvas = document.getElementById("graphCanvas");
const graphDetails = document.getElementById("graphDetails");
const extractButton = document.getElementById("extractKnowledgeBtn");
const notice = document.getElementById("knowledgeNotice");

let currentRecords = [];
let currentNodes = [];
let currentEdges = [];

function escapeText(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

async function request(path, options = {}) {
    const headers = {
        Authorization: `Bearer ${token}`,
        ...(options.body ? { "Content-Type": "application/json" } : {})
    };

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            data.error || data.message || `Request failed (${response.status})`
        );
    }

    return data;
}

function getArray(data, possibleKeys) {
    if (Array.isArray(data)) return data;

    for (const key of possibleKeys) {
        if (Array.isArray(data?.[key])) return data[key];
    }

    return [];
}

function showNotice(message, type = "success") {
    notice.className = `knowledge-notice ${type}`;
    notice.textContent = message;
}

function hideNotice() {
    notice.className = "knowledge-notice d-none";
    notice.textContent = "";
}

function recordStatus(record) {
    return String(record.status || "unknown").toLowerCase();
}

function statusClass(status) {
    if (["approved", "verified"].includes(status)) {
        return "status-approved";
    }

    if (["inferred", "pending", "awaiting_review", "needs_review"].includes(status)) {
        return "status-inferred";
    }

    if (status.includes("reject")) {
        return "status-rejected";
    }

    if (status.includes("conflict")) {
        return "status-conflicting";
    }

    if (status.includes("missing")) {
        return "status-missing";
    }

    return "status-unknown";
}

function renderRecords(records) {
    currentRecords = records;

    const verified = records.filter(record =>
        ["approved", "verified"].includes(recordStatus(record))
    ).length;

    const awaiting = records.filter(record =>
        ["needs_review", "inferred", "pending", "awaiting_review"]
            .includes(recordStatus(record))
    ).length;

    const uncertain = records.filter(record =>
        ["conflicting", "missing"].some(status =>
            String(record.uncertainty || "").includes(status)
        )
    ).length;

    document.getElementById("totalRecords").textContent = records.length;
    document.getElementById("verifiedRecords").textContent = verified;
    document.getElementById("reviewRecords").textContent = awaiting;
    document.getElementById("uncertainRecords").textContent = uncertain;

    filterAndDisplayRecords();
}

function filterAndDisplayRecords() {
    const query = document
        .getElementById("knowledgeSearch")
        .value
        .toLowerCase();

    const filtered = currentRecords.filter(record => {
        const searchable = [
            record.title,
            record.description,
            record.type,
            record.status,
            record.uncertainty,
            record.evidence
        ].filter(Boolean).join(" ").toLowerCase();

        return searchable.includes(query);
    });

    if (!filtered.length) {
        knowledgeList.innerHTML = `
            <div class="empty-state">
                No knowledge records found.
                Upload project documents and run knowledge extraction to get started.
            </div>
        `;
        return;
    }

    knowledgeList.innerHTML = filtered.map(record => {
        const status = recordStatus(record);
        const needsReview = status === "needs_review";
        const source = record.document_id
            ? `Document ${record.document_id.slice(0, 8)}`
            : "Source not specified";

        return `
            <article class="knowledge-record">
                <div class="record-main">
                    <div class="record-title-row">
                        <h6>${escapeText(record.title)}</h6>
                        <span class="status-pill ${statusClass(status)}">
                            ${escapeText(status.replaceAll("_", " "))}
                        </span>
                    </div>

                    <p>${escapeText(record.description || "No description provided.")}</p>

                    ${record.evidence ? `
                        <div class="evidence-block">
                            <strong>Source evidence</strong>
                            <p>${escapeText(record.evidence)}</p>
                        </div>
                    ` : ""}

                    <div class="record-meta">
                        ${escapeText(record.type || "General")}
                        · ${escapeText(source)}
                        · Confidence: ${escapeText(record.uncertainty || "unknown")}
                    </div>

                    ${needsReview ? `
                        <div class="record-actions">
                            <button
                                class="btn btn-sm btn-approve"
                                data-review-id="${escapeText(record.id)}"
                                data-decision="approve">
                                <i class="bi bi-check2 me-1"></i> Approve
                            </button>

                            <button
                                class="btn btn-sm btn-reject"
                                data-review-id="${escapeText(record.id)}"
                                data-decision="reject">
                                <i class="bi bi-x-lg me-1"></i> Reject
                            </button>
                        </div>
                    ` : ""}
                </div>
            </article>
        `;
    }).join("");

    knowledgeList.querySelectorAll("[data-review-id]").forEach(button => {
        button.addEventListener("click", () => {
            reviewKnowledge(
                button.dataset.reviewId,
                button.dataset.decision,
                button
            );
        });
    });
}

async function reviewKnowledge(itemId, decision, button) {
    const projectId = projectSelect.value;
    if (!projectId) return;

    button.disabled = true;

    try {
        await request(
            `/api/projects/${projectId}/knowledge/${itemId}/review`,
            {
                method: "POST",
                body: JSON.stringify({ decision })
            }
        );

        showNotice(
            decision === "approve"
                ? "Knowledge record approved."
                : "Knowledge record rejected."
        );

        await loadProjectData(projectId);
    } catch (error) {
        showNotice(error.message, "error");
        button.disabled = false;
    }
}

async function extractKnowledge() {
    const projectId = projectSelect.value;

    if (!projectId) {
        showNotice("Select a project first.", "error");
        return;
    }

    extractButton.disabled = true;
    extractButton.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2"></span>
        Extracting...
    `;

    hideNotice();

    try {
        const result = await request(
            `/api/projects/${projectId}/knowledge/extract`,
            { method: "POST" }
        );

        showNotice(
            `Extraction complete. ${result.created || 0} new records created; ` +
            `${result.skipped_existing || 0} existing records skipped.`
        );

        await loadProjectData(projectId);
    } catch (error) {
        showNotice(error.message, "error");
    } finally {
        extractButton.disabled = false;
        extractButton.innerHTML = `
            <i class="bi bi-stars me-1"></i>
            Extract knowledge
        `;
    }
}

function renderGraph(nodes, edges) {
    currentNodes = nodes;
    currentEdges = edges;

    if (!nodes.length) {
        graphCanvas.innerHTML = `
            <div class="empty-state">
                No graph nodes found for this project.
            </div>
        `;
        graphDetails.textContent = "No relationships to inspect.";
        return;
    }

    graphCanvas.innerHTML = nodes.map((node, index) => {
        const type = String(node.type || "knowledge").toLowerCase();
        const title = node.label || node.title || node.id || `Node ${index + 1}`;

        return `
            <button
                class="graph-node ${escapeText(type)}"
                data-node-index="${index}">
                <small>${escapeText(type)}</small>
                <strong>${escapeText(title)}</strong>
            </button>
        `;
    }).join("");

    graphCanvas.querySelectorAll(".graph-node").forEach(button => {
        button.addEventListener("click", () => {
            const node = currentNodes[Number(button.dataset.nodeIndex)];

            graphCanvas.querySelectorAll(".graph-node").forEach(item =>
                item.classList.remove("selected")
            );

            button.classList.add("selected");
            showNodeDetails(node);
        });
    });

    graphDetails.textContent =
        `${nodes.length} nodes and ${edges.length} relationships. Select a node to inspect it.`;
}

function showNodeDetails(node) {
    const nodeId = node.id;

    const relatedEdges = currentEdges.filter(edge =>
        edge.source === nodeId ||
        edge.target === nodeId ||
        edge.from === nodeId ||
        edge.to === nodeId
    );

    graphDetails.innerHTML = `
        <strong>${escapeText(node.label || node.title || node.id)}</strong>
        <div class="mt-2">
            Type: ${escapeText(node.type || "Not specified")}
        </div>
        <div class="mt-1">
            Status: ${escapeText(node.status || "Not specified")}
        </div>
        <div class="mt-1">
            Relationships: ${relatedEdges.length}
        </div>
        ${relatedEdges.length ? `
            <ul class="mt-2 mb-0">
                ${relatedEdges.map(edge => `
                    <li>${escapeText(edge.type || "Related to")}</li>
                `).join("")}
            </ul>
        ` : ""}
    `;
}

async function loadProjectData(projectId) {
    if (!projectId) return;

    knowledgeList.innerHTML = `
        <div class="empty-state">Loading knowledge records...</div>
    `;

    graphCanvas.innerHTML = `
        <div class="empty-state">Loading graph...</div>
    `;

    try {
        const [knowledgeResult, graphResult] = await Promise.all([
            request(`/api/projects/${projectId}/knowledge`),
            request(`/api/projects/${projectId}/graph`)
        ]);

        renderRecords(
            getArray(knowledgeResult, ["items", "knowledge", "records"])
        );

        renderGraph(
            getArray(graphResult, ["nodes"]),
            getArray(graphResult, ["edges", "relationships"])
        );
    } catch (error) {
        knowledgeList.innerHTML = `
            <div class="empty-state">${escapeText(error.message)}</div>
        `;

        graphCanvas.innerHTML = `
            <div class="empty-state">${escapeText(error.message)}</div>
        `;
    }
}

async function loadProjects() {
    try {
        const result = await request("/api/projects/");
        const projects = getArray(result, ["projects", "items"]);

        projectSelect.innerHTML = "";

        if (!projects.length) {
            projectSelect.innerHTML = `
                <option value="">No projects available</option>
            `;
            return;
        }

        projects.forEach(project => {
            const option = document.createElement("option");
            option.value = project.id;
            option.textContent = project.name || "Untitled project";
            projectSelect.appendChild(option);
        });

        await loadProjectData(projectSelect.value);
    } catch (error) {
        projectSelect.innerHTML = `
            <option value="">Could not load projects</option>
        `;
        showNotice(error.message, "error");
    }
}

document.querySelectorAll(".knowledge-tab").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".knowledge-tab").forEach(tab =>
            tab.classList.remove("active")
        );

        button.classList.add("active");

        const showLedger = button.dataset.tab === "ledger";

        document.getElementById("ledgerPanel")
            .classList.toggle("d-none", !showLedger);

        document.getElementById("graphPanel")
            .classList.toggle("d-none", showLedger);
    });
});

projectSelect.addEventListener("change", () => {
    hideNotice();
    loadProjectData(projectSelect.value);
});

document.getElementById("knowledgeSearch")
    .addEventListener("input", filterAndDisplayRecords);

extractButton.addEventListener("click", extractKnowledge);

function logout() {
    sessionStorage.removeItem("access_token");
    window.location.href = "/";
}

if (!token) {
    window.location.href = "/";
} else {
    loadProjects();
}
