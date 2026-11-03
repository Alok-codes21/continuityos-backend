
const API = "";

let token = sessionStorage.getItem("continuity_token");
let projects = [];

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
    const response = await fetch(`${API}${path}`, {
        ...options,
        headers: {
            ...(options.headers || {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(options.body ? { "Content-Type": "application/json" } : {})
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        if (response.status === 401) logout();
        throw new Error(data.error || data.message || "Request failed");
    }

    return data;
}

function showApp() {
    $("loginScreen").classList.add("d-none");
    $("appShell").classList.remove("d-none");
    loadDashboard();
}

function logout() {
    sessionStorage.removeItem("continuity_token");
    token = null;
    $("appShell").classList.add("d-none");
    $("loginScreen").classList.remove("d-none");
}

$("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    $("loginError").textContent = "";

    try {
        const result = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({
                email: $("email").value.trim(),
                password: $("password").value
            })
        });

        token = result.access_token;

        if (!token) {
            throw new Error("Login response did not include an access token.");
        }

        sessionStorage.setItem("continuity_token", token);

        const user = result.user || {};
        $("userName").textContent = user.name || user.email || "Workspace user";
        $("userRole").textContent = user.role || "Member";
        $("userAvatar").textContent =
            (user.name || user.email || "U").charAt(0).toUpperCase();

        showApp();
    } catch (error) {
        $("loginError").textContent = error.message;
    }
});

$("logoutButton").addEventListener("click", logout);

async function loadDashboard() {
    try {
        const result = await api("/api/projects/");
        projects = Array.isArray(result) ? result : (result.projects || []);

        $("projectCount").textContent = projects.length;
        renderProjects();

        const totals = {
            knowledge: 0,
            review: 0,
            verified: 0,
            inferred: 0,
            conflicting: 0,
            missing: 0,
            transitions: 0
        };

        for (const project of projects) {
            try {
                const [knowledge, ledger] = await Promise.all([
                    api(`/api/projects/${project.id}/knowledge`),
                    api(`/api/projects/${project.id}/continuity`)
                ]);

                const items = knowledge.items || [];
                totals.knowledge += items.length;
                totals.review += items.filter(
                    item => item.status === "needs_review"
                ).length;
                totals.verified += items.filter(
                    item => item.uncertainty === "verified"
                ).length;
                totals.inferred += items.filter(
                    item => item.uncertainty === "inferred"
                ).length;
                totals.conflicting += items.filter(
                    item => item.uncertainty === "conflicting"
                ).length;
                totals.missing += items.filter(
                    item => ["missing", "outdated"].includes(item.uncertainty)
                ).length;

                totals.transitions += (ledger.events || []).filter(
                    event => event.event_type.startsWith("handover.")
                ).length;
            } catch (error) {
                console.warn(`Could not load metrics for ${project.name}`, error);
            }
        }

        $("knowledgeCount").textContent = totals.knowledge;
        $("reviewCount").textContent = totals.review;
        $("verifiedCount").textContent = totals.verified;
        $("inferredCount").textContent = totals.inferred;
        $("conflictingCount").textContent = totals.conflicting;
        $("missingCount").textContent = totals.missing;
        $("transitionCount").textContent = totals.transitions;

        if (projects.length) {
            await loadLatestActivity(projects[0]);
        }
    } catch (error) {
        $("projectList").innerHTML =
            `<div class="empty-state">${escapeHtml(error.message)}</div>`;
    }
}

function renderProjects() {
    const container = $("projectList");

    if (!projects.length) {
        container.innerHTML = `
            <div class="empty-state">
                No projects yet. Create your first project to get started.
            </div>`;
        return;
    }

    container.innerHTML = projects.map(project => `
        <div class="project-row" data-project-id="${escapeHtml(project.id)}">
            <div class="project-symbol"><i class="bi bi-folder2"></i></div>
            <div class="project-main">
                <div class="project-name">${escapeHtml(project.name)}</div>
                <div class="project-description">
                    ${escapeHtml(project.description || "No description added")}
                </div>
            </div>
            <span class="project-status">${escapeHtml(project.status || "active")}</span>
            <i class="bi bi-chevron-right text-muted"></i>
        </div>
    `).join("");

    container.querySelectorAll(".project-row").forEach(row => {
        row.addEventListener("click", () => {
            const project = projects.find(p => p.id === row.dataset.projectId);
            if (project) openProject(project);
        });
    });
}

async function loadLatestActivity(project) {
    try {
        const result = await api(
            `/api/projects/${project.id}/continuity?limit=8`
        );

        const events = result.events || [];

        $("activityList").innerHTML = events.length
            ? events.map(event => `
                <div class="activity-item">
                    <div class="activity-icon">
                        <i class="bi bi-activity"></i>
                    </div>
                    <div>
                        <div class="activity-title">${escapeHtml(event.summary)}</div>
                        <div class="activity-meta">
                            ${escapeHtml(event.event_type)} ·
                            ${formatDate(event.created_at)}
                        </div>
                    </div>
                </div>
            `).join("")
            : `<div class="empty-state">No continuity events recorded yet.</div>`;
    } catch {
        $("activityList").innerHTML =
            `<div class="empty-state">Activity is not available for this project.</div>`;
    }
}

async function openProject(project) {
    $("breadcrumb").textContent = project.name;
    $("pageHeading").textContent = "Project intelligence";

    $("pageContent").innerHTML = `
        <div class="welcome-row">
            <div>
                <div class="eyebrow">PROJECT INTELLIGENCE</div>
                <h2>${escapeHtml(project.name)}</h2>
                <p>${escapeHtml(project.description || "Project knowledge and continuity.")}</p>
            </div>
            <button class="btn btn-teal" id="uploadButton">
                <i class="bi bi-upload me-2"></i> Upload source
            </button>
        </div>

        <div class="content-grid">
            <div class="panel">
                <div class="panel-heading">
                    <div><h5>Knowledge records</h5><p>Extracted project knowledge</p></div>
                </div>
                <div id="projectKnowledge">Loading...</div>
            </div>
            <div class="panel">
                <div class="panel-heading">
                    <div><h5>Project graph</h5><p>Documents and evidence relationships</p></div>
                </div>
                <div id="projectGraph">Loading...</div>
            </div>
        </div>

        <div class="panel">
            <div class="panel-heading">
                <div><h5>Continuity history</h5><p>Recorded project events</p></div>
            </div>
            <div id="projectLedger">Loading...</div>
        </div>

        <input type="file" id="sourceFile" hidden accept=".pdf,.docx,.txt,.csv">
    `;

    $("uploadButton").addEventListener("click", () => $("sourceFile").click());

    $("sourceFile").addEventListener("change", async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const form = new FormData();
        form.append("file", file);

        try {
            const response = await fetch(
                `/api/projects/${project.id}/sources/upload`,
                { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: form }
            );

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Upload failed");

            alert("Source uploaded successfully.");
            openProject(project);
        } catch (error) {
            alert(error.message);
        }
    });

    try {
        const [knowledge, graph, ledger] = await Promise.all([
            api(`/api/projects/${project.id}/knowledge`),
            api(`/api/projects/${project.id}/graph`),
            api(`/api/projects/${project.id}/continuity`)
        ]);

        $("projectKnowledge").innerHTML = (knowledge.items || []).length
            ? knowledge.items.map(item => `
                <div class="project-row">
                    <div class="project-symbol"><i class="bi bi-lightbulb"></i></div>
                    <div class="project-main">
                        <div class="project-name">${escapeHtml(item.title)}</div>
                        <div class="project-description">
                            ${escapeHtml(item.type)} · ${escapeHtml(item.evidence || "")}
                        </div>
                    </div>
                    <span class="project-status">${escapeHtml(item.uncertainty)}</span>
                </div>
            `).join("")
            : `<div class="empty-state">No knowledge extracted yet.</div>`;

        $("projectGraph").innerHTML = `
            <div class="stat-value">${graph.nodes.length}</div>
            <div class="stat-foot">Nodes</div>
            <div class="stat-value mt-3">${graph.edges.length}</div>
            <div class="stat-foot">Evidence relationships</div>
        `;

        $("projectLedger").innerHTML = (ledger.events || []).length
            ? ledger.events.map(event => `
                <div class="activity-item">
                    <div class="activity-icon"><i class="bi bi-clock-history"></i></div>
                    <div>
                        <div class="activity-title">${escapeHtml(event.summary)}</div>
                        <div class="activity-meta">${formatDate(event.created_at)}</div>
                    </div>
                </div>
            `).join("")
            : `<div class="empty-state">No continuity events recorded.</div>`;
    } catch (error) {
        $("projectKnowledge").textContent = error.message;
    }
}

$("newProjectButton").addEventListener("click", () => {
    $("projectError").textContent = "";
    bootstrap.Modal.getOrCreateInstance($("projectModal")).show();
});

$("projectForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("projectError").textContent = "";

    try {
        await api("/api/projects/", {
            method: "POST",
            body: JSON.stringify({
                name: $("projectName").value.trim(),
                description: $("projectDescription").value.trim()
            })
        });

        bootstrap.Modal.getOrCreateInstance($("projectModal")).hide();
        $("projectForm").reset();
        await loadDashboard();
    } catch (error) {
        $("projectError").textContent = error.message;
    }
});

document.querySelectorAll("[data-page]").forEach(link => {
    link.addEventListener("click", event => {
        event.preventDefault();

        document.querySelectorAll("[data-page]").forEach(item =>
            item.classList.remove("active")
        );
        link.classList.add("active");

        const page = link.dataset.page;

        if (page === "overview") {
            $("pageHeading").textContent = "Organisation overview";
            $("breadcrumb").textContent = "Overview";
            $("pageContent").innerHTML = `
                <div class="empty-state">Loading overview...</div>`;
            loadDashboard();
            return;
        }

        if (page === "projects") {
            $("pageHeading").textContent = "Projects";
            $("breadcrumb").textContent = "Projects";
            $("pageContent").innerHTML = `
                <div class="welcome-row">
                    <div><div class="eyebrow">WORKSPACE</div><h2>Your projects</h2>
                    <p>Choose a project to inspect its knowledge and continuity history.</p></div>
                </div><div class="panel"><div id="projectList"></div></div>`;
            renderProjects();
            return;
        }

        $("pageHeading").textContent = link.textContent.trim();
        $("breadcrumb").textContent = link.textContent.trim();
        $("pageContent").innerHTML = `
            <div class="panel">
                <h5>${escapeHtml(link.textContent.trim())}</h5>
                <p class="text-muted mt-2">
                    This workspace module is being connected to the backend.
                </p>
            </div>`;
    });
});

document.querySelectorAll("[data-page-link]").forEach(button => {
    button.addEventListener("click", () => {
        document.querySelector('[data-page="projects"]').click();
    });
});

function formatDate(value) {
    if (!value) return "Date unavailable";
    return new Date(value).toLocaleString();
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

if (token) {
    showApp();
}
