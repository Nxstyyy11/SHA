/**
 * Smart Healthcare Analytics - Frontend JavaScript
 * Dashboard, auth, personal prediction history, and ML model insights.
 */

const API = "";
const TOKEN_KEY = "sha_auth_token";

let authToken = localStorage.getItem(TOKEN_KEY) || "";
let currentUsername = "";
let myPredictionsCache = []; // for CSV export

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: "#a8b2d8", font: { family: "Inter" } } },
    tooltip: {
      backgroundColor: "#1a1d2e",
      titleColor: "#f0f2ff",
      bodyColor: "#a8b2d8",
      borderColor: "rgba(255,255,255,0.08)",
      borderWidth: 1,
    },
  },
};

function authHeaders(extra = {}) {
  const headers = { ...extra };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  return headers;
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) message = body.detail;
    } catch (_) { }
    throw new Error(message);
  }
  return res.json();
}

// ─── STATS ───────────────────────────────────────────────
async function loadStats() {
  try {
    const d = await apiFetch("/api/stats");
    const set = (id, val) => {
      const card = document.getElementById(id);
      card.querySelector(".stat-value").textContent = val;
      card.classList.remove("loading");
    };
    set("statTotal", d.total_patients.toLocaleString());
    set("statDiabetic", `${d.diabetic_count} (${d.diabetic_percent}%)`);
    set("statNonDiabetic", d.non_diabetic_count.toLocaleString());
    set("statGlucose", d.avg_glucose);
    set("statBMI", d.avg_bmi);
    set("statAge", `${d.avg_age} yrs`);
  } catch (e) {
    console.error("Stats error:", e);
  }
}

async function loadModelAccuracy() {
  try {
    const d = await apiFetch("/api/model/accuracy");
    const card = document.getElementById("statAccuracy");
    card.querySelector(".stat-value").textContent = `${d.accuracy}%`;
    card.classList.remove("loading");
  } catch (e) {
    console.error("Accuracy error:", e);
  }
}

// ─── CHARTS ──────────────────────────────────────────────
let chartInstances = {};

async function loadCharts() {
  await Promise.all([chartOutcome(), chartFeatures(), chartGlucose(), chartBmi()]);
}

async function chartOutcome() {
  try {
    const d = await apiFetch("/api/charts/distribution");
    if (chartInstances.outcome) chartInstances.outcome.destroy();
    chartInstances.outcome = new Chart(document.getElementById("chartOutcome"), {
      type: "doughnut",
      data: {
        labels: d.labels,
        datasets: [{
          data: d.values,
          backgroundColor: d.colors,
          borderColor: "#0d0f1a",
          borderWidth: 3,
          hoverOffset: 8,
        }],
      },
      options: {
        ...CHART_DEFAULTS,
        cutout: "65%",
        plugins: {
          ...CHART_DEFAULTS.plugins,
          legend: { ...CHART_DEFAULTS.plugins.legend, position: "bottom" },
        },
      },
    });
  } catch (e) { console.error("Outcome chart error:", e); }
}

async function chartFeatures() {
  try {
    const d = await apiFetch("/api/charts/features");
    if (chartInstances.features) chartInstances.features.destroy();
    chartInstances.features = new Chart(document.getElementById("chartFeatures"), {
      type: "bar",
      data: {
        labels: d.labels,
        datasets: [
          { label: "No Diabetes", data: d.no_diabetes, backgroundColor: "rgba(78,205,196,0.7)", borderColor: "#4ecdc4", borderWidth: 1, borderRadius: 4 },
          { label: "Diabetes", data: d.diabetes, backgroundColor: "rgba(255,107,107,0.7)", borderColor: "#ff6b6b", borderWidth: 1, borderRadius: 4 },
        ],
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          x: { ticks: { color: "#a8b2d8" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#a8b2d8" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    });
  } catch (e) { console.error("Features chart error:", e); }
}

async function chartGlucose() {
  try {
    const d = await apiFetch("/api/charts/glucose_histogram");
    if (chartInstances.glucose) chartInstances.glucose.destroy();
    chartInstances.glucose = new Chart(document.getElementById("chartGlucose"), {
      type: "bar",
      data: {
        labels: d.labels,
        datasets: [{ label: "Patient Count", data: d.counts, backgroundColor: "rgba(108,99,255,0.65)", borderColor: "#6c63ff", borderWidth: 1, borderRadius: 4 }],
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          x: { ticks: { color: "#a8b2d8", maxRotation: 45 }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#a8b2d8" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    });
  } catch (e) { console.error("Glucose chart error:", e); }
}

async function chartBmi() {
  try {
    const d = await apiFetch("/api/charts/bmi_histogram");
    if (chartInstances.bmi) chartInstances.bmi.destroy();
    chartInstances.bmi = new Chart(document.getElementById("chartBmi"), {
      type: "bar",
      data: {
        labels: d.labels,
        datasets: [{ label: "Patient Count", data: d.counts, backgroundColor: "rgba(247,183,49,0.65)", borderColor: "#f7b731", borderWidth: 1, borderRadius: 4 }],
      },
      options: {
        ...CHART_DEFAULTS,
        scales: {
          x: { ticks: { color: "#a8b2d8", maxRotation: 45 }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#a8b2d8" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    });
  } catch (e) { console.error("BMI chart error:", e); }
}

// ─── MODEL INSIGHTS ──────────────────────────────────────
async function loadModelInsights() {
  await Promise.all([chartFeatureImportance(), loadModelComparison()]);
}

async function chartFeatureImportance() {
  try {
    const d = await apiFetch("/api/charts/feature_importance");
    if (chartInstances.featureImportance) chartInstances.featureImportance.destroy();
    chartInstances.featureImportance = new Chart(document.getElementById("chartFeatureImportance"), {
      type: "bar",
      data: {
        labels: d.labels,
        datasets: [{
          label: "Importance (%)",
          data: d.values,
          backgroundColor: d.values.map((_, i) => `hsla(${200 + i * 20}, 70%, 60%, 0.75)`),
          borderColor: d.values.map((_, i) => `hsl(${200 + i * 20}, 70%, 60%)`),
          borderWidth: 1,
          borderRadius: 5,
        }],
      },
      options: {
        ...CHART_DEFAULTS,
        indexAxis: "y",
        scales: {
          x: { ticks: { color: "#a8b2d8", callback: v => v + "%" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#a8b2d8" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
        plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } },
      },
    });
  } catch (e) { console.error("Feature importance chart error:", e); }
}

async function loadModelComparison() {
  const container = document.getElementById("modelComparisonTable");
  try {
    const d = await apiFetch("/api/model/metrics");
    const metrics = ["accuracy", "precision", "recall", "f1_score", "auc_roc"];
    const metricLabels = { accuracy: "Accuracy", precision: "Precision", recall: "Recall", f1_score: "F1 Score", auc_roc: "AUC-ROC" };

    let html = `<table class="data-table model-metrics-table">
      <thead><tr><th>Metric</th>`;
    d.models.forEach(m => { html += `<th>${m.model}</th>`; });
    html += `</tr></thead><tbody>`;

    metrics.forEach(key => {
      html += `<tr><td><strong>${metricLabels[key]}</strong></td>`;
      d.models.forEach(m => {
        const val = m[key] ?? "–";
        const best = d.models.reduce((a, b) => (b[key] > a[key] ? b : a));
        const isBest = m.model === best.model;
        html += `<td class="${isBest ? "metric-best" : ""}">${val}%</td>`;
      });
      html += `</tr>`;
    });
    html += `</tbody></table>`;
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<div class="loading-row">Failed to load model metrics.</div>`;
    console.error("Model comparison error:", e);
  }
}

// ─── PATIENTS TABLE ───────────────────────────────────────
let currentPage = 1;
let currentOutcome = "";

async function loadPatients(page = 1, outcome = "") {
  currentPage = page;
  currentOutcome = outcome;
  let url = `/api/patients?page=${page}&limit=10`;
  if (outcome !== "") url += `&outcome=${outcome}`;
  try {
    const d = await apiFetch(url);
    const tbody = document.getElementById("patientBody");
    tbody.innerHTML = "";
    d.data.forEach(p => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${p.id}</td><td>${p.pregnancies}</td><td>${p.glucose}</td>
        <td>${p.blood_pressure}</td><td>${p.skin_thickness}</td><td>${p.insulin}</td>
        <td>${p.bmi}</td><td>${p.dpf.toFixed(3)}</td><td>${p.age}</td>
        <td>${p.outcome === 1 ? '<span class="badge badge--yes">Diabetic</span>' : '<span class="badge badge--no">Healthy</span>'}</td>
      `;
      tbody.appendChild(tr);
    });
    document.getElementById("pageInfo").textContent =
      `Showing ${(page - 1) * 10 + 1}–${Math.min(page * 10, d.total)} of ${d.total}`;
    renderPagination(page, d.pages);
  } catch (e) {
    console.error("Patients error:", e);
    document.getElementById("patientBody").innerHTML =
      `<tr><td colspan="10" class="loading-row">Failed to load data.</td></tr>`;
  }
}

function renderPagination(current, total) {
  const pag = document.getElementById("pagination");
  pag.innerHTML = "";
  const addBtn = (label, page, active = false) => {
    const btn = document.createElement("button");
    btn.className = "page-btn" + (active ? " active" : "");
    btn.textContent = label;
    btn.onclick = () => loadPatients(page, currentOutcome);
    pag.appendChild(btn);
  };
  if (current > 1) addBtn("Prev", current - 1);
  for (let i = Math.max(1, current - 2); i <= Math.min(total, current + 2); i++) addBtn(i, i, i === current);
  if (current < total) addBtn("Next", current + 1);
}

document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    loadPatients(1, btn.dataset.outcome);
  });
});

// ─── AUTH ─────────────────────────────────────────────────
function setAuthStatus(text, isError = false) {
  const status = document.getElementById("authStatus");
  status.textContent = text;
  status.style.color = isError ? "#ff6b6b" : "#a8b2d8";
}

function updateAuthUi() {
  const loginBtn = document.getElementById("loginBtn");
  const registerBtn = document.getElementById("registerBtn");
  const logoutBtn = document.getElementById("logoutBtn");
  const exportBtn = document.getElementById("exportCsvBtn");
  if (authToken && currentUsername) {
    setAuthStatus(`Logged in as ${currentUsername}`);
    if (loginBtn) loginBtn.style.display = "none";
    if (registerBtn) registerBtn.style.display = "none";
    logoutBtn.style.display = "inline-block";
    exportBtn.style.display = "inline-block";
  } else {
    setAuthStatus("Not logged in.");
    if (loginBtn) loginBtn.style.display = "inline-block";
    if (registerBtn) registerBtn.style.display = "inline-block";
    logoutBtn.style.display = "none";
    exportBtn.style.display = "none";
  }
}

let authMode = "login";

function setAuthModalStatus(text, isError = false) {
  const status = document.getElementById("authModalStatus");
  if (!status) return;
  status.textContent = text;
  status.style.color = isError ? "#ff6b6b" : "#a8b2d8";
}

function setAuthMode(mode) {
  authMode = mode;
  const title = document.getElementById("authModalTitle");
  const subtitle = document.getElementById("authModalSubtitle");
  const submitBtn = document.getElementById("authSubmitBtn");
  const passwordInput = document.getElementById("modalPassword");
  document.querySelectorAll(".modal-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });
  if (title) title.textContent = mode === "login" ? "Login" : "Register";
  if (subtitle) {
    subtitle.textContent = mode === "login"
      ? "Welcome back. Sign in to continue."
      : "Create your account to save predictions and history.";
  }
  if (submitBtn) submitBtn.textContent = mode === "login" ? "Login" : "Register";
  if (passwordInput) passwordInput.autocomplete = mode === "login" ? "current-password" : "new-password";
  setAuthModalStatus("");
}

function openAuthModal(mode = "login") {
  const modal = document.getElementById("authModal");
  if (!modal) return;
  setAuthMode(mode);
  modal.classList.add("is-open");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  const usernameInput = document.getElementById("modalUsername");
  if (usernameInput) usernameInput.focus();
}

function closeAuthModal() {
  const modal = document.getElementById("authModal");
  if (!modal) return;
  modal.classList.remove("is-open");
  modal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  const usernameInput = document.getElementById("modalUsername");
  const passwordInput = document.getElementById("modalPassword");
  if (usernameInput) usernameInput.value = "";
  if (passwordInput) passwordInput.value = "";
  setAuthModalStatus("");
}

async function bootstrapAuth() {
  if (!authToken) { updateAuthUi(); return; }
  try {
    const me = await apiFetch("/api/auth/me", { headers: authHeaders() });
    currentUsername = me.username;
    updateAuthUi();
    await loadMyPredictionSlide();
  } catch (err) {
    authToken = "";
    currentUsername = "";
    localStorage.removeItem(TOKEN_KEY);
    updateAuthUi();
  }
}

async function loginOrRegister(mode, username, password) {
  if (!username || !password) {
    setAuthModalStatus("Username and password are required.", true);
    setAuthStatus("Username and password are required.", true);
    return;
  }
  try {
    const data = await apiFetch(`/api/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    authToken = data.token;
    currentUsername = data.username;
    localStorage.setItem(TOKEN_KEY, authToken);
    updateAuthUi();
    await loadMyPredictionSlide();
    closeAuthModal();
  } catch (err) {
    setAuthModalStatus(err.message, true);
    setAuthStatus(err.message, true);
  }
}

async function logout() {
  if (!authToken) return;
  try { await apiFetch("/api/auth/logout", { method: "POST", headers: authHeaders() }); } catch (_) { }
  authToken = "";
  currentUsername = "";
  localStorage.removeItem(TOKEN_KEY);
  updateAuthUi();
  clearMyPredictionSlide();
}

// ─── MY PREDICTIONS ──────────────────────────────────────
function clearMyPredictionSlide() {
  document.getElementById("myPredCount").textContent = "0";
  document.getElementById("myPredLatestRisk").textContent = "-";
  document.getElementById("myPredLatestProb").textContent = "-";
  document.getElementById("myPredCompare").textContent = "-";
  document.getElementById("myPredictionBody").innerHTML =
    '<tr><td colspan="7" class="loading-row">Login to view your prediction history.</td></tr>';
  myPredictionsCache = [];
}

function renderMyPredictionRows(rows) {
  myPredictionsCache = rows;
  const body = document.getElementById("myPredictionBody");
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="7" class="loading-row">No predictions yet. Submit one below.</td></tr>';
    return;
  }
  body.innerHTML = "";
  rows.forEach(p => {
    const dt = new Date(p.created_at).toLocaleString();
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${dt}</td>
      <td>${p.prediction === 1 ? "Diabetic" : "Non-Diabetic"}</td>
      <td>${p.risk_level}</td>
      <td>${p.probability}%</td>
      <td>${p.glucose}</td>
      <td>${p.bmi}</td>
      <td>${p.age}</td>
    `;
    body.appendChild(tr);
  });
}

async function loadMyPredictionSlide() {
  if (!authToken) { clearMyPredictionSlide(); return; }
  try {
    const [summary, list] = await Promise.all([
      apiFetch("/api/predictions/summary", { headers: authHeaders() }),
      apiFetch("/api/predictions?page=1&limit=10", { headers: authHeaders() }),
    ]);
    document.getElementById("myPredCount").textContent = summary.total_predictions;
    document.getElementById("myPredLatestRisk").textContent = summary.latest ? summary.latest.risk_level : "-";
    document.getElementById("myPredLatestProb").textContent = summary.latest ? `${summary.latest.probability}%` : "-";
    if (summary.probability_change === null || summary.probability_change === undefined) {
      document.getElementById("myPredCompare").textContent = "-";
    } else {
      const sign = summary.probability_change > 0 ? "+" : "";
      document.getElementById("myPredCompare").textContent = `${sign}${summary.probability_change}%`;
    }
    renderMyPredictionRows(list.data || []);
  } catch (err) {
    setAuthStatus(err.message, true);
    clearMyPredictionSlide();
  }
}

// ─── CSV EXPORT ───────────────────────────────────────────
document.getElementById("exportCsvBtn").addEventListener("click", () => {
  if (!myPredictionsCache.length) return;
  const headers = ["Date", "Prediction", "Risk", "Probability (%)", "Glucose", "Blood Pressure", "BMI", "Age", "Insulin", "Pregnancies", "Skin Thickness", "DPF"];
  const rows = myPredictionsCache.map(p => [
    new Date(p.created_at).toLocaleString(),
    p.prediction === 1 ? "Diabetic" : "Non-Diabetic",
    p.risk_level,
    p.probability,
    p.glucose,
    p.blood_pressure,
    p.bmi,
    p.age,
    p.insulin,
    p.pregnancies,
    p.skin_thickness,
    p.dpf,
  ]);
  const csv = [headers, ...rows].map(r => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `diabetes_predictions_${currentUsername}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});

// ─── INPUT VALIDATION ─────────────────────────────────────
const INPUT_RULES = {
  f_pregnancies: { min: 0, max: 17, warnMsg: "Unusual value — dataset range is 0–17" },
  f_glucose: { min: 44, max: 199, warnMsg: "Normal fasting glucose is 70–100 mg/dL; value seems extreme" },
  f_bp: { min: 24, max: 122, warnMsg: "Normal diastolic BP is 60–80 mm Hg; value seems extreme" },
  f_skin: { min: 7, max: 99, warnMsg: "Typical triceps skin fold is 10–40 mm" },
  f_insulin: { min: 14, max: 846, warnMsg: "Typical 2hr insulin is 16–166 μU/mL" },
  f_bmi: { min: 18.0, max: 67.1, warnMsg: "Healthy BMI is 18.5–24.9; value seems extreme" },
  f_dpf: { min: 0.078, max: 2.42, warnMsg: "DPF range in dataset: 0.078–2.42" },
  f_age: { min: 21, max: 81, warnMsg: "Dataset age range: 21–81 years" },
};

const WARN_IDS = {
  f_pregnancies: "warn_pregnancies",
  f_glucose: "warn_glucose",
  f_bp: "warn_bp",
  f_skin: "warn_skin",
  f_insulin: "warn_insulin",
  f_bmi: "warn_bmi",
  f_dpf: "warn_dpf",
  f_age: "warn_age",
};

Object.entries(INPUT_RULES).forEach(([fieldId, rule]) => {
  const input = document.getElementById(fieldId);
  const warnEl = document.getElementById(WARN_IDS[fieldId]);
  if (!input || !warnEl) return;
  input.addEventListener("input", () => {
    const v = parseFloat(input.value);
    if (isNaN(v) || v < rule.min || v > rule.max) {
      warnEl.textContent = "⚠ " + rule.warnMsg;
    } else {
      warnEl.textContent = "";
    }
  });
});

// ─── HEALTH TIPS ──────────────────────────────────────────
const HEALTH_TIPS = {
  High: [
    "🏥 Consult a doctor or endocrinologist promptly.",
    "🍎 Reduce sugar and refined carbohydrate intake significantly.",
    "🚶 Aim for at least 150 minutes of moderate aerobic activity per week.",
    "⚖️ Target a healthy BMI (18.5–24.9) through diet and exercise.",
    "🩺 Monitor fasting blood glucose levels regularly.",
    "💧 Stay well-hydrated and limit alcohol consumption.",
  ],
  Medium: [
    "🥗 Adopt a balanced diet rich in fibre, vegetables, and whole grains.",
    "📊 Monitor blood glucose levels every 3–6 months.",
    "🏃 Increase daily physical activity — even a 30-minute walk helps.",
    "⚖️ Aim to maintain or reach a healthy BMI.",
    "😴 Ensure 7–9 hours of quality sleep per night.",
    "🧘 Manage stress through mindfulness or relaxation techniques.",
  ],
  Low: [
    "✅ Great result! Maintain your current healthy lifestyle.",
    "🥦 Continue eating a balanced, nutritious diet.",
    "🏋️ Keep up regular physical activity.",
    "📅 Schedule routine health check-ups annually.",
    "🚭 Avoid smoking and limit alcohol for long-term health.",
  ],
};

function showHealthTips(riskLevel) {
  const tips = HEALTH_TIPS[riskLevel] || HEALTH_TIPS.Low;
  const tipsList = document.getElementById("tipsList");
  tipsList.innerHTML = tips.map(t => `<li>${t}</li>`).join("");
  document.getElementById("healthTips").style.display = "block";
}

// ─── PREDICTION FORM ──────────────────────────────────────
document.getElementById("loginBtn").addEventListener("click", () => openAuthModal("login"));
document.getElementById("registerBtn").addEventListener("click", () => openAuthModal("register"));
document.getElementById("logoutBtn").addEventListener("click", logout);

document.getElementById("authModalClose").addEventListener("click", closeAuthModal);
document.querySelectorAll(".modal-tab").forEach(tab => {
  tab.addEventListener("click", () => setAuthMode(tab.dataset.mode));
});
document.getElementById("authModalForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("modalUsername").value.trim();
  const password = document.getElementById("modalPassword").value;
  await loginOrRegister(authMode, username, password);
});
document.getElementById("authModal").addEventListener("click", (e) => {
  if (e.target && e.target.dataset && e.target.dataset.close) closeAuthModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAuthModal();
});

document.getElementById("predictForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  if (!authToken) {
    setAuthStatus("Please login first to save and compare predictions.", true);
    location.hash = "#auth";
    return;
  }

  const btn = document.getElementById("predictBtn");
  btn.querySelector(".predict-btn-text").style.display = "none";
  btn.querySelector(".predict-btn-spinner").style.display = "inline";
  btn.disabled = true;

  const payload = {
    pregnancies: parseFloat(document.getElementById("f_pregnancies").value),
    glucose: parseFloat(document.getElementById("f_glucose").value),
    blood_pressure: parseFloat(document.getElementById("f_bp").value),
    skin_thickness: parseFloat(document.getElementById("f_skin").value),
    insulin: parseFloat(document.getElementById("f_insulin").value),
    bmi: parseFloat(document.getElementById("f_bmi").value),
    dpf: parseFloat(document.getElementById("f_dpf").value),
    age: parseFloat(document.getElementById("f_age").value),
  };

  try {
    const d = await apiFetch("/api/predict", {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    showResult(d);
    await loadMyPredictionSlide();
    await loadStats();
    await loadCharts();
    await loadPatients(currentPage, currentOutcome);
  } catch (err) {
    setAuthStatus(err.message, true);
  } finally {
    btn.querySelector(".predict-btn-text").style.display = "inline";
    btn.querySelector(".predict-btn-spinner").style.display = "none";
    btn.disabled = false;
  }
});

function showResult(d) {
  const resultBox = document.getElementById("predictResult");
  resultBox.style.display = "block";

  const pct = d.probability;
  const gaugeFill = document.getElementById("gaugeFill");
  const gaugeText = document.getElementById("gaugeText");
  const circumference = Math.PI * 80;
  const offset = circumference * (1 - pct / 100);
  gaugeFill.style.strokeDasharray = `${circumference - offset} ${offset}`;
  gaugeText.textContent = `${pct}%`;

  const riskClass = { Low: "risk-low", Medium: "risk-medium", High: "risk-high" }[d.risk_level] || "risk-medium";
  document.getElementById("resultStatus").innerHTML = `<span class="${riskClass}">${d.risk_level} Risk</span>`;
  document.getElementById("resultDetail").innerHTML =
    `Predicted outcome: <strong>${d.prediction === 1 ? "Diabetic" : "Non-Diabetic"}</strong><br/>` +
    `Risk probability: <strong>${pct}%</strong><br/>` +
    `<span style="color:#4ecdc4;font-size:0.85em;margin-top:6px;display:inline-block;">✓ Record added to dataset — charts & stats updated</span>`;

  showHealthTips(d.risk_level);
  resultBox.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// ─── INIT ─────────────────────────────────────────────────
(async () => {
  await loadStats();
  await loadModelAccuracy();
  await loadCharts();
  await loadModelInsights();
  await loadPatients();
  await bootstrapAuth();
})();
