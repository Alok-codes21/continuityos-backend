const API_BASE = "";
const token = sessionStorage.getItem("access_token");

const projectSelect = document.getElementById("projectSelect");
const knowledgeList = document.getElementById("knowledgeList");
const graphCanvas = document.getElementById("graphCanvas");
const graphDetails = document.getElementById("graphDetails");

let currentRecords = [];
let currentNodes = [];
let currentEdges = [];

function escapeText(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;",
        '"': "&quot;", "'": "&#039;"
    })[char]);
}

async function request(path) {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: { Authorization: `Bearer ${token}` }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || data.message || `Request failed (${response.status})`);
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

function recordStatus(record) {
    return String(
        record.status || record.review_status || record.confidence_status || "unknown"
    ).toLowerCase();
}

function statusClass(status) {
    if (["approved", "verified"].includes(status)) return "status-approved";
    if (["inferred", "pending", "awaiting_review"].includes(status)) return "status-inferred";
    if (status.includes("conflict")) return "status-conflicting";
    if (status.includes("missing")) return "status-missing";
    return "status-unknown";
}

function renderRecords(records) {
    currentRecords = records;

    const verified = records.filter(r =>
        ["approved", "verified"].includes(recordStatus(r))
    ).length;

    const awaiting = records.filter(r =>
        ["inferred", "pending", "awaiting_review"].includes(recordStatus(r))
    ).length;

    const uncertain = records.filter(r =>
        ["conflicting", "missing"].some(s => recordStatus(r).includes(s))
    ).length;

    document.getElementById("totalRecords").textContent = records.length;
    document.getElementById("verifiedRecords").textContent = verified;
    document.getElementById("reviewRecords").textContent = awaiting;
    document.getElementById("uncertainRecords").textContent = uncertain;

    filterAndDisplayRecords();
}

function filterAndDisplayRecords() {
    const query = document.getElementById("knowledgeSearch").value.toLowerCase();

    const filtered = currentRecords.filter(record => {
        const searchable = [
            record.title,
            record.content,
            record.description,
            record.category,
            record.statement,
            record.evidence
        ].filter(Boolean).join(" ").toLowerCase();

        return searchable.includes(query);
    });

    if (!filtered.length) {
        knowledgeList.innerHTML = `<div class="empty-state">No matching knowledge records found.</div>`;
        return;
    }

    knowledgeList.innerHTML = filtered.map(record => {
        const title = record.title || record.name || record.category || "Untitled knowledge";
        const content = record.content || record.description || record.statement || "No description provided.";
        const status = recordStatus(record);
        const evidence = record.evidence || record.evidence_snippet || "";
        const source = record.source_name || record.document_name || record.source_id || "Source not specified";

        return `
            <article class="knowledge-record">
                <div>
                    <h6>${escapeText(title)}</h6>
                    <p>${escapeText(content)}</p>
                    ${evidence ? `<p><strong>Evidence:</strong> ${escapeText(evidence)}</p>` : ""}
                    <div class="record-meta">
                        ${escapeText(record.category || "General")}
                        &nbsp;·&nbsp; Source: ${escapeText(source)}
                    </div>
                </div>
                <span class="status-pill ${statusClass(status)}">${escapeText(status.replaceAll("_", " "))}</span>
            </article>
        `;
    }).join("");
}

function renderGraph(nodes, edges) {
    currentNodes = nodes;
    currentEdges = edges;

    if (!nodes.length) {
        graphCanvas.innerHTML = `<div class="empty-state">No graph nodes were returned for this project.</div>`;
        graphDetails.textContent = "There are no relationships to inspect.";
        return;
    }

    graphCanvas.innerHTML = nodes.map((node, index) => {
        const type = String(node.type || node.node_type || "knowledge").toLowerCase();
        const title = node.label || node.title || node.name || node.id || `Node ${index + 1}`;

        return `
            <button class="graph-node ${escapeText(type)}"
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
        `${nodes.length} nodes and ${edges.length} relationships returned by the project graph API. Select a node to inspect its details.`;
}

function showNodeDetails(node) {
    const nodeId = node.id;
    const relatedEdges = currentEdges.filter(edge =>
        edge.source === nodeId ||
        edge.target === nodeId ||
        edge.from === nodeId ||
        edge.to === nodeId
    );

    const title = node.label || node.title || node.name || node.id || "Graph node";

    graphDetails.innerHTML = `
        <strong>${escapeText(title)}</strong>
        <div class="mt-2">Type: ${escapeText(node.type || node.node_type || "Not specified")}</div>
        <div class="mt-1">Relationships: ${relatedEdges.length}</div>
        ${relatedEdges.length
            ? `<ul class="mt-2 mb-0">${relatedEdges.map(edge => `
                <li>${escapeText(edge.label || edge.type || "Related to")}</li>
              `).join("")}</ul>`
            : `<div class="mt-2">No relationships were returned for this node.</div>`
        }
    `;
}

async function loadProjectData(projectId) {
    if (!projectId) return;

    knowledgeList.innerHTML = `<div class="empty-state">Loading knowledge records...</div>`;
    graphCanvas.innerHTML = `<div class="empty-state">Loading graph...</div>`;

    try {
        const [knowledgeResult, graphResult] = await Promise.all([
            request(`/api/projects/${projectId}/knowledge`),
            request(`/api/projects/${projectId}/graph`)
        ]);

        renderRecords(getArray(knowledgeResult, ["items", "knowledge", "records"]));

        renderGraph(
            getArray(graphResult, ["nodes"]),
            getArray(graphResult, ["edges", "relationships"])
        );
    } catch (error) {
        knowledgeList.innerHTML = `<div class="empty-state">${escapeText(error.message)}</div>`;
        graphCanvas.innerHTML = `<div class="empty-state">${escapeText(error.message)}</div>`;
    }
}

async function loadProjects() {
    try {
        const result = await request("/api/projects/");
        const projects = getArray(result, ["projects", "items"]);

        projectSelect.innerHTML = "";

        if (!projects.length) {
            projectSelect.innerHTML = `<option value="">No projects available</option>`;
            return;
        }

        projects.forEach(project => {
            const option = document.createElement("option");
            option.value = project.id;
            option.textContent = project.name || project.title || "Untitled project";
            projectSelect.appendChild(option);
        });

        await loadProjectData(projectSelect.value);
    } catch (error) {
        projectSelect.innerHTML = `<option value="">Could not load projects</option>`;
        knowledgeList.innerHTML = `<div class="empty-state">${escapeText(error.message)}</div>`;
    }
}

document.querySelectorAll(".knowledge-tab").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".knowledge-tab").forEach(tab =>
            tab.classList.remove("active")
        );

        button.classList.add("active");

        const showLedger = button.dataset.tab === "ledger";
        document.getElementById("ledgerPanel").classList.toggle("d-none", !showLedger);
        document.getElementById("graphPanel").classList.toggle("d-none", showLedger);
    });
});

projectSelect.addEventListener("change", () => loadProjectData(projectSelect.value));

document.getElementById("knowledgeSearch").addEventListener("input", filterAndDisplayRecords);

function logout() {
    sessionStorage.removeItem("access_token");
    window.location.href = "/";
}

if (!token) {
    window.location.href = "/";
} else {
    loadProjects();
}