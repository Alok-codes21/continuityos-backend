const token = sessionStorage.getItem("access_token");

const projectSelect = document.getElementById("projectSelect");
const userIdInput = document.getElementById("userId");
const simulateButton = document.getElementById("simulateButton");
const formError = document.getElementById("formError");

function escapeText(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;",
        '"': "&quot;", "'": "&#039;"
    })[char]);
}

async function apiRequest(path) {
    const response = await fetch(path, {
        headers: { Authorization: `Bearer ${token}` }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || data.message || `Request failed (${response.status})`);
    }

    return data;
}

function findArray(data, keys) {
    if (Array.isArray(data)) return data;

    for (const key of keys) {
        if (Array.isArray(data?.[key])) return data[key];
    }

    return [];
}

function findAffectedRecords(data) {
    const possibleKeys = [
        "affected_knowledge",
        "affected_knowledge_items",
        "impacted_knowledge",
        "knowledge_items",
        "affected_records",
        "items",
        "records"
    ];

    for (const key of possibleKeys) {
        if (Array.isArray(data?.[key])) return data[key];
    }

    // Handle an API response that nests its result.
    for (const value of Object.values(data || {})) {
        if (value && typeof value === "object" && !Array.isArray(value)) {
            const nested = findAffectedRecords(value);
            if (nested.length) return nested;
        }
    }

    return [];
}

function renderAffectedRecords(records) {
    const container = document.getElementById("affectedList");

    if (!records.length) {
        container.innerHTML = `
            <div class="empty-state">
                No affected knowledge records were returned by the API.
            </div>`;
        return;
    }

    container.innerHTML = records.map(record => {
        const title = record.title || record.name || record.category || "Knowledge record";
        const description = record.content || record.description ||
            record.statement || "No description returned.";
        const status = record.status || record.review_status || "Not specified";

        return `
            <article class="affected-record">
                <strong>${escapeText(title)}</strong>
                <p>${escapeText(description)}</p>
                <small>Status: ${escapeText(status)}</small>
            </article>
        `;
    }).join("");
}

function showResults(data) {
    const records = findAffectedRecords(data);

    document.getElementById("emptyState").classList.add("d-none");
    document.getElementById("resultsSection").classList.remove("d-none");

    document.getElementById("impactCount").textContent =
        data.affected_count ?? data.impact_count ?? records.length;

    document.getElementById("impactStatus").textContent =
        data.risk_level || data.status || "Simulation completed";

    document.getElementById("resultTimestamp").textContent =
        `Run at ${new Date().toLocaleString()}`;

    document.getElementById("rawResponse").textContent =
        JSON.stringify(data, null, 2);

    renderAffectedRecords(records);
}

async function loadProjects() {
    try {
        const result = await apiRequest("/api/projects/");
        const projects = findArray(result, ["projects", "items"]);

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

        simulateButton.disabled = false;
    } catch (error) {
        projectSelect.innerHTML = `<option value="">Could not load projects</option>`;
        formError.textContent = error.message;
    }
}

async function runSimulation() {
    const projectId = projectSelect.value;
    const userId = userIdInput.value.trim();

    formError.textContent = "";

    if (!projectId) {
        formError.textContent = "Select a project first.";
        return;
    }

    if (!userId) {
        formError.textContent = "Enter the departing member's user ID.";
        userIdInput.focus();
        return;
    }

    simulateButton.disabled = true;
    simulateButton.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Running...`;

    try {
        const params = new URLSearchParams({ user_id: userId });
        const result = await apiRequest(
            `/api/projects/${encodeURIComponent(projectId)}/departure-impact?${params}`
        );

        showResults(result);
    } catch (error) {
        formError.textContent = error.message;
    } finally {
        simulateButton.disabled = false;
        simulateButton.innerHTML = `<i class="bi bi-play-fill me-1"></i> Run simulation`;
    }
}

function logout() {
    sessionStorage.removeItem("access_token");
    window.location.href = "/";
}

simulateButton.addEventListener("click", runSimulation);

if (!token) {
    window.location.href = "/";
} else {
    loadProjects();
}