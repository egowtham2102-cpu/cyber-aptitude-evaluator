const state = {
  sessionId: null,
  questions: [],
  answers: {},
  expiresAt: null,
  timerInterval: null,
  qTimerInterval: null,
  activeQuestionId: null,
  questionTimes: {}, // qid -> seconds spent
  autoSubmitted: false,
  securityViolations: 0,
  isFullscreenEnforced: false,
  jdAnalysis: null,
  analyzedJobDescription: "",
  activeInputTab: "paste",
  uploadedFile: null,
  isPaused: false,
  attempts: [],
};

const setupPanel = document.getElementById("setup-panel");
const testPanel = document.getElementById("test-panel");
const reportPanel = document.getElementById("report-panel");
const adminPanel = document.getElementById("admin-panel");

const setupForm = document.getElementById("setup-form");
const setupStatus = document.getElementById("setup-status");
const testStatus = document.getElementById("test-status");
const questionList = document.getElementById("question-list");
const timerEl = document.getElementById("timer");
const progressFill = document.getElementById("progress-fill");
const progressText = document.getElementById("progress-text");

const submitBtn = document.getElementById("submit-btn");
const generateBtn = document.getElementById("generate-btn");
const analyzeBtn = document.getElementById("analyze-btn");
const jdAnalysisPanel = document.getElementById("jd-analysis-panel");
const skillsGrid = document.getElementById("skills-grid");
const uploadZone = document.getElementById("upload-zone");
const jdFileInput = document.getElementById("jd-file");
const uploadFilename = document.getElementById("upload-filename");
const pasteInputPanel = document.getElementById("paste-input-panel");
const uploadInputPanel = document.getElementById("upload-input-panel");

const adminPanelToggleBtn = document.getElementById("admin-panel-toggle-btn");
const adminBackBtn = document.getElementById("admin-back-btn");
const exportCsvBtn = document.getElementById("export-csv-btn");
const adminSessionsList = document.getElementById("admin-sessions-list");

const pauseBtn = document.getElementById("pause-btn");
const resumeBtn = document.getElementById("resume-btn");
const pauseOverlay = document.getElementById("pause-overlay");

const retakeBtn = document.getElementById("retake-assessment-btn");
const regenerateBtn = document.getElementById("regenerate-assessment-btn");

const authPanel = document.getElementById("auth-panel");

// ── Localhost File & Browser Auth ──────────────────────────────────────
const STORAGE_KEYS = {
  users: "cae_users",
  session: "cae_user_session",
};

function getUsers() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEYS.users) || "[]");
  } catch {
    return [];
  }
}

function saveUsers(users) {
  localStorage.setItem(STORAGE_KEYS.users, JSON.stringify(users));
}

function getSession() {
  try {
    const local = localStorage.getItem(STORAGE_KEYS.session);
    if (local) return JSON.parse(local);
    const session = sessionStorage.getItem(STORAGE_KEYS.session);
    return session ? JSON.parse(session) : null;
  } catch {
    return null;
  }
}

function setSession(user, persistent = true) {
  const payload = JSON.stringify({
    id: user.id || "",
    email: user.email,
    name: user.name,
    department: user.department || "Cybersecurity",
    token: user.token || "",
    loggedInAt: Date.now(),
  });
  if (persistent) {
    localStorage.setItem(STORAGE_KEYS.session, payload);
    sessionStorage.removeItem(STORAGE_KEYS.session);
  } else {
    sessionStorage.setItem(STORAGE_KEYS.session, payload);
    localStorage.removeItem(STORAGE_KEYS.session);
  }
}

function clearSession() {
  localStorage.removeItem(STORAGE_KEYS.session);
  sessionStorage.removeItem(STORAGE_KEYS.session);
}

function isLoggedIn() {
  return Boolean(getSession()?.email);
}

function getInitials(name) {
  return (name || "?")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function switchAuthTab(tab) {
  document.querySelectorAll(".auth-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.authTab === tab);
  });
  document.querySelectorAll(".auth-form").forEach((form) => {
    form.classList.toggle("hidden", form.dataset.authForm !== tab);
    form.classList.toggle("active", form.dataset.authForm === tab);
  });
}

function updateUserUI() {
  const session = getSession();
  const badge = document.getElementById("user-session-badge");

  if (session) {
    authPanel.classList.add("hidden");
    setupPanel.classList.remove("hidden");
    badge.classList.remove("hidden");
    document.getElementById("user-display-name").textContent = session.name;
    document.getElementById("user-avatar").textContent = getInitials(session.name);
    
    const deptTag = document.getElementById("user-dept-tag");
    if (deptTag) deptTag.textContent = session.department || "Cybersecurity";

    const candidateNameInput = document.getElementById("candidate-name");
    if (candidateNameInput && !candidateNameInput.value) {
      candidateNameInput.value = session.name;
    }

    const candidateDeptInput = document.getElementById("candidate-department");
    if (candidateDeptInput && session.department) {
      candidateDeptInput.value = session.department;
    }

    adminPanelToggleBtn.classList.remove("hidden");
    document.querySelector(".step-indicator")?.classList.remove("hidden");
  } else {
    authPanel.classList.remove("hidden");
    setupPanel.classList.add("hidden");
    testPanel.classList.add("hidden");
    reportPanel.classList.add("hidden");
    adminPanel.classList.add("hidden");
    badge.classList.add("hidden");
    adminPanelToggleBtn.classList.add("hidden");
    document.querySelector(".step-indicator")?.classList.add("hidden");
    setStep(1);
  }
}

async function handleSignup(event) {
  event.preventDefault();
  const name = document.getElementById("signup-name").value.trim();
  const email = document.getElementById("signup-email").value.trim().toLowerCase();
  const department = document.getElementById("signup-dept")?.value || "Cybersecurity";
  const password = document.getElementById("signup-password").value;
  const confirm = document.getElementById("signup-confirm").value;
  const errorEl = document.getElementById("signup-error");
  const submitBtn = document.getElementById("signup-submit-btn");

  hideStatus(errorEl);

  if (password !== confirm) {
    showStatus(errorEl, "Passwords do not match.", "error");
    return;
  }
  if (password.length < 6) {
    showStatus(errorEl, "Password must be at least 6 characters.", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.innerHTML = "<span>Creating Account...</span>";

  try {
    const res = await fetch("/api/user/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, department }),
    });

    const data = await res.json();
    if (!res.ok) {
      showStatus(errorEl, data.error || "Failed to create account.", "error");
      submitBtn.disabled = false;
      submitBtn.innerHTML = "<span>Create Account &amp; Save Profile</span>";
      return;
    }

    setSession({ ...data.user, token: data.token }, true);
    
    const users = getUsers();
    if (!users.some((u) => u.email === email)) {
      users.push({ name, email, password, department, createdAt: Date.now() });
      saveUsers(users);
    }

    document.getElementById("user-signup-form").reset();
    updateUserUI();
  } catch (err) {
    const users = getUsers();
    if (users.some((u) => u.email === email)) {
      showStatus(errorEl, "An account with this email already exists.", "error");
    } else {
      const newUser = { name, email, password, department, createdAt: Date.now() };
      users.push(newUser);
      saveUsers(users);
      setSession(newUser, true);
      document.getElementById("user-signup-form").reset();
      updateUserUI();
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = "<span>Create Account &amp; Save Profile</span>";
  }
}

async function handleUserLogin(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value.trim().toLowerCase();
  const password = document.getElementById("login-password").value;
  const errorEl = document.getElementById("login-error");
  const remember = document.getElementById("remember-me").checked;
  const submitBtn = document.getElementById("login-submit-btn");

  hideStatus(errorEl);
  submitBtn.disabled = true;
  submitBtn.innerHTML = "<span>Verifying...</span>";

  try {
    const res = await fetch("/api/user/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      showStatus(errorEl, data.error || "Invalid email or password.", "error");
      submitBtn.disabled = false;
      submitBtn.innerHTML = "<span>Sign In</span>";
      return;
    }

    setSession({ ...data.user, token: data.token }, remember);
    document.getElementById("user-login-form").reset();
    updateUserUI();
  } catch (err) {
    const user = getUsers().find((u) => u.email === email && u.password === password);
    if (!user) {
      showStatus(errorEl, "Invalid email or password.", "error");
    } else {
      setSession(user, remember);
      document.getElementById("user-login-form").reset();
      updateUserUI();
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = "<span>Sign In</span>";
  }
}

async function handleUserLogout() {
  try {
    await fetch("/api/user/logout", { method: "POST" });
  } catch (e) {
    // ignore
  }
  clearSession();
  resetApp();
  updateUserUI();
}

function toggleUserPasswordVisibility(button) {
  const input = document.getElementById(button.dataset.toggle);
  if (!input) return;
  input.type = input.type === "password" ? "text" : "password";
  button.textContent = input.type === "password" ? "👁️" : "🙈";
}

function seedDemoUser() {
  const users = getUsers();
  if (!users.some((u) => u.email === "demo@test.com")) {
    users.push({
      name: "Demo Candidate",
      email: "demo@test.com",
      password: "demo123",
      department: "Cybersecurity",
      createdAt: Date.now(),
    });
    saveUsers(users);
  }
}

async function openUserHistoryModal() {
  const session = getSession();
  if (!session) return;

  const modal = document.getElementById("user-history-modal");
  document.getElementById("modal-user-avatar").textContent = getInitials(session.name);
  document.getElementById("modal-user-name").textContent = session.name;
  document.getElementById("modal-user-email").textContent = session.email;
  document.getElementById("modal-user-dept").textContent = session.department || "Cybersecurity";

  const rowsContainer = document.getElementById("user-modal-history-rows");
  rowsContainer.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:16px;">Loading attempts...</td></tr>';

  modal.classList.remove("hidden");

  try {
    const res = await fetch(`/api/user/history?email=${encodeURIComponent(session.email)}&name=${encodeURIComponent(session.name)}`);
    const history = await res.json();

    if (!Array.isArray(history) || history.length === 0) {
      rowsContainer.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:16px; color:var(--muted);">No prior assessment attempts found for this profile.</td></tr>';
      return;
    }

    rowsContainer.innerHTML = history.map((item) => {
      const dateStr = item.submitted_at ? new Date(item.submitted_at).toLocaleString() : "In Progress";
      const scoreStr = item.score !== null && item.score !== undefined ? `${item.score} / ${item.max_score} (${item.percentage}%)` : "—";
      const statusBadge = item.status === "graded" ? '<span class="badge" style="background:rgba(16,185,129,0.15);color:var(--success);">Graded</span>' : '<span class="badge" style="background:rgba(245,158,11,0.15);color:var(--warning);">In Progress</span>';
      
      return `
        <tr>
          <td><strong>${item.job_title}</strong></td>
          <td>${item.department || "Cybersecurity"}</td>
          <td>${statusBadge}</td>
          <td><strong>${scoreStr}</strong></td>
          <td style="font-size:12px; color:var(--muted);">${dateStr}</td>
        </tr>
      `;
    }).join("");
  } catch (e) {
    rowsContainer.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--danger); padding:16px;">Unable to load history from server files.</td></tr>';
  }
}

function closeUserHistoryModal() {
  document.getElementById("user-history-modal")?.classList.add("hidden");
}

function initAuthEnhancements() {
  document.querySelectorAll(".demo-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      switchAuthTab("login");
      const emailInput = document.getElementById("login-email");
      const passInput = document.getElementById("login-password");
      if (emailInput) emailInput.value = pill.dataset.email;
      if (passInput) passInput.value = pill.dataset.pass;
    });
  });

  const pwdInput = document.getElementById("signup-password");
  const strengthWrap = document.getElementById("password-strength-wrap");
  const strengthBar = document.getElementById("password-strength-bar");
  const strengthLabel = document.getElementById("password-strength-label");

  if (pwdInput && strengthWrap && strengthBar) {
    pwdInput.addEventListener("input", () => {
      const val = pwdInput.value;
      if (!val) {
        strengthWrap.classList.add("hidden");
        return;
      }
      strengthWrap.classList.remove("hidden");
      if (val.length < 6) {
        strengthBar.className = "strength-bar weak";
        strengthLabel.textContent = "Weak (min 6 chars)";
      } else if (val.length < 10 || !/[A-Z]/.test(val) || !/[0-9]/.test(val)) {
        strengthBar.className = "strength-bar medium";
        strengthLabel.textContent = "Medium (add uppercase & numbers)";
      } else {
        strengthBar.className = "strength-bar strong";
        strengthLabel.textContent = "Strong password";
      }
    });
  }

  document.getElementById("user-history-btn")?.addEventListener("click", openUserHistoryModal);
  document.getElementById("close-history-modal-btn")?.addEventListener("click", closeUserHistoryModal);
  document.getElementById("user-history-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "user-history-modal") closeUserHistoryModal();
  });
}

const SKILL_SECTIONS = [
  { key: "required_skills", label: "Required Skills", icon: "★" },
  { key: "preferred_skills", label: "Preferred Skills", icon: "◆" },
  { key: "responsibilities", label: "Responsibilities", icon: "▸" },
  { key: "programming_languages", label: "Programming Languages", icon: "{}" },
  { key: "databases", label: "Databases", icon: "DB" },
  { key: "cloud_platforms", label: "Cloud Platforms", icon: "☁" },
  { key: "devops", label: "DevOps", icon: "⚙" },
  { key: "security_domains", label: "Security Domains", icon: "⛨" },
  { key: "networking", label: "Networking", icon: "⛓" },
  { key: "operating_systems", label: "Operating Systems", icon: "OS" },
  { key: "frameworks", label: "Frameworks", icon: "▣" },
  { key: "certifications", label: "Certifications", icon: "✓" },
];

const fullscreenLockOverlay = document.getElementById("fullscreen-lock-overlay");
const resumeFullscreenBtn = document.getElementById("resume-fullscreen-btn");
const proctorToast = document.getElementById("proctor-toast");
const downloadReportBtn = document.getElementById("download-report-btn");

function setStep(step) {
  document.querySelectorAll(".step-dot").forEach((dot) => {
    dot.classList.toggle("active", Number(dot.dataset.step) <= step);
  });
}

function showStatus(el, message, type = "info") {
  el.textContent = message;
  el.className = `status-banner ${type}`;
  el.classList.remove("hidden");
}

function hideStatus(el) {
  el.classList.add("hidden");
}

function formatTime(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function updateProgress() {
  const total = state.questions.length;
  const answered = state.questions.filter((q) => {
    const value = state.answers[q.id];
    if (value === undefined || value === null) return false;
    if (typeof value === "string") return value.trim().length > 0;
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === "object") return Object.keys(value).length > 0;
    return true;
  }).length;
  const pct = total ? Math.round((answered / total) * 100) : 0;
  progressFill.style.width = `${pct}%`;
  progressText.textContent = `${answered} / ${total} answered`;
}

// Live Score API update
const updateLiveScore = debounce(async () => {
  if (!state.sessionId) return;
  try {
    const response = await fetch(`/api/sessions/${state.sessionId}/live-stats`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: state.answers }),
    });
    if (response.ok) {
      const stats = await response.json();
      document.getElementById("live-score").textContent = `${stats.current_score} / ${stats.max_score}`;
      document.getElementById("live-pct").textContent = `${stats.current_percentage}%`;
      document.getElementById("live-accuracy").textContent = `${stats.accuracy}%`;
      document.getElementById("live-correct").textContent = stats.correct;
      document.getElementById("live-wrong").textContent = stats.wrong;
      document.getElementById("live-remaining").textContent = stats.remaining;
    }
  } catch (err) {
    console.error("Live stats error:", err);
  }
}, 300);

// Rendering active question cards based on type
function renderQuestions() {
  questionList.innerHTML = "";
  state.questions.forEach((question, index) => {
    const card = document.createElement("article");
    card.className = "question-card";
    card.dataset.questionId = question.id;
    if (state.activeQuestionId === question.id) {
      card.classList.add("active-focus");
    }

    const cleanType = question.type.replace("_", " ").toUpperCase();
    const artifactHtml = question.artifact
      ? `<div class="artifact-box">${escapeHtml(question.artifact)}</div>`
      : "";

    card.innerHTML = `
      <div class="question-head">
        <span class="badge">Q${index + 1}</span>
        <span class="badge ${getBadgeClass(question.type)}">${cleanType}</span>
        <span class="badge">${escapeHtml(question.category)}</span>
        <span class="badge">${question.points} pts</span>
      </div>
      <p>${escapeHtml(question.prompt)}</p>
      ${artifactHtml}
      <div class="answer-container" id="ans-container-${question.id}"></div>
    `;

    const container = card.querySelector(`#ans-container-${question.id}`);

    // Click/focus triggers active question timer
    card.addEventListener("click", () => {
      if (state.activeQuestionId !== question.id) {
        state.activeQuestionId = question.id;
        document.querySelectorAll(".question-card").forEach(c => c.classList.remove("active-focus"));
        card.classList.add("active-focus");
        
        // Reset q-timer display to time spent on this question
        const qTimerEl = document.getElementById("q-timer");
        if (qTimerEl) {
          qTimerEl.textContent = formatTime(state.questionTimes[question.id] || 0);
        }
      }
    });

    // 1. Multiple Choice / True False / Aptitude MCQ
    if (question.type === "mcq" || question.type === "true_false" || question.type === "aptitude" || 
       (question.options && question.options.length > 0 && question.type !== "multi_select")) {
      const options = document.createElement("div");
      options.className = "options";
      
      const qOptions = question.options || ["True", "False"];
      qOptions.forEach((option) => {
        const label = document.createElement("label");
        label.className = "option";
        const isSelected = state.answers[question.id] === option;
        if (isSelected) {
          label.classList.add("selected");
        }
        label.innerHTML = `
          <input type="radio" name="${question.id}" value="${escapeAttr(option)}" ${isSelected ? "checked" : ""} />
          <span>${escapeHtml(option)}</span>
        `;
        
        label.querySelector("input").addEventListener("change", () => {
          state.answers[question.id] = option;
          options.querySelectorAll(".option").forEach((node) => node.classList.remove("selected"));
          label.classList.add("selected");
          updateProgress();
          updateLiveScore();
        });
        options.appendChild(label);
      });
      container.appendChild(options);

    // 2. Multiple Select (Checkboxes)
    } else if (question.type === "multi_select") {
      const checkList = document.createElement("div");
      checkList.className = "checkbox-list";
      
      const savedAnswers = state.answers[question.id] || [];
      question.options.forEach((option) => {
        const label = document.createElement("label");
        label.className = "checkbox-option";
        const isChecked = savedAnswers.includes(option);
        if (isChecked) {
          label.classList.add("selected");
        }
        label.innerHTML = `
          <input type="checkbox" value="${escapeAttr(option)}" ${isChecked ? "checked" : ""} />
          <span>${escapeHtml(option)}</span>
        `;
        
        label.querySelector("input").addEventListener("change", (e) => {
          const current = state.answers[question.id] || [];
          if (e.target.checked) {
            if (!current.includes(option)) current.push(option);
            label.classList.add("selected");
          } else {
            const idx = current.indexOf(option);
            if (idx > -1) current.splice(idx, 1);
            label.classList.remove("selected");
          }
          state.answers[question.id] = current;
          updateProgress();
          updateLiveScore();
        });
        checkList.appendChild(label);
      });
      container.appendChild(checkList);

    // 3. Fill in the Blank
    } else if (question.type === "fill_blank") {
      const input = document.createElement("input");
      input.type = "text";
      input.className = "fill-blank-input";
      input.placeholder = "Type your answer here...";
      input.value = state.answers[question.id] || "";
      
      input.addEventListener("input", (e) => {
        state.answers[question.id] = e.target.value;
        updateProgress();
        updateLiveScore();
      });
      container.appendChild(input);

    // 4. Match the Following
    } else if (question.type === "match_following") {
      const matchList = document.createElement("div");
      matchList.className = "match-list";
      
      const currentMatch = state.answers[question.id] || {};
      const pairs = question.match_pairs || [];
      const matchOptions = question.match_options || [];
      
      pairs.forEach((pair) => {
        const row = document.createElement("div");
        row.className = "match-row";
        
        const leftSpan = document.createElement("span");
        leftSpan.className = "match-left";
        leftSpan.textContent = pair.left;
        
        const select = document.createElement("select");
        select.className = "match-select";
        select.innerHTML = `<option value="">Select matching term...</option>`;
        
        matchOptions.forEach((opt) => {
          const isSel = currentMatch[pair.id] === opt;
          select.innerHTML += `<option value="${escapeAttr(opt)}" ${isSel ? "selected" : ""}>${escapeHtml(opt)}</option>`;
        });
        
        select.addEventListener("change", (e) => {
          const matchState = state.answers[question.id] || {};
          if (e.target.value) {
            matchState[pair.id] = e.target.value;
          } else {
            delete matchState[pair.id];
          }
          state.answers[question.id] = matchState;
          updateProgress();
          updateLiveScore();
        });
        
        row.appendChild(leftSpan);
        row.appendChild(select);
        matchList.appendChild(row);
      });
      container.appendChild(matchList);

    // 5. Open Ended Response / Scenarios
    } else {
      const textarea = document.createElement("textarea");
      textarea.className = "answer-input";
      textarea.placeholder = "Describe your response in detail, providing rationales...";
      textarea.value = state.answers[question.id] || "";
      
      textarea.addEventListener("input", (e) => {
        state.answers[question.id] = e.target.value;
        updateProgress();
        updateLiveScore();
      });
      container.appendChild(textarea);
    }

    questionList.appendChild(card);
  });
  
  if (state.questions.length > 0 && !state.activeQuestionId) {
    state.activeQuestionId = state.questions[0].id;
    const firstCard = questionList.querySelector(".question-card");
    if (firstCard) firstCard.classList.add("active-focus");
  }
  
  updateProgress();
  updateLiveScore();
}

function getBadgeClass(qtype) {
  if (qtype === "mcq" || qtype === "aptitude") return "mcq";
  if (["scenario", "incident_response", "threat_hunting"].includes(qtype)) return "scenario";
  return "short";
}

function getBadgeColorClass(score, max) {
  if (score === max) return "correct";
  if (score === 0) return "wrong";
  return "partial";
}

function getResultIcon(score, max) {
  if (score === max) return "✅";
  if (score === 0) return "❌";
  return "⚠";
}

function debounce(fn, delay = 300) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function setInputTab(tab) {
  state.activeInputTab = tab;
  document.querySelectorAll(".input-tab").forEach((button) => {
    const isActive = button.dataset.tab === tab;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", isActive ? "true" : "false");
  });
  pasteInputPanel.classList.toggle("hidden", tab !== "paste");
  uploadInputPanel.classList.toggle("hidden", tab !== "upload");
  invalidateAnalysis();
}

function invalidateAnalysis() {
  state.jdAnalysis = null;
  state.analyzedJobDescription = "";
  generateBtn.disabled = true;
  jdAnalysisPanel.classList.add("hidden");
  skillsGrid.innerHTML = "";
}

function setUploadedFile(file) {
  state.uploadedFile = file || null;
  if (file) {
    uploadFilename.textContent = file.name;
    uploadFilename.classList.remove("hidden");
    uploadZone.classList.add("has-file");
  } else {
    uploadFilename.textContent = "";
    uploadFilename.classList.add("hidden");
    uploadZone.classList.remove("has-file");
    jdFileInput.value = "";
  }
  invalidateAnalysis();
}

function getJobDescriptionPayload() {
  if (state.activeInputTab === "upload") {
    const supplement = document.getElementById("job-description-supplement").value.trim();
    return {
      mode: "upload",
      file: state.uploadedFile,
      supplement,
    };
  }
  return {
    mode: "paste",
    text: document.getElementById("job-description").value.trim(),
  };
}

function renderSkillSection(label, icon, items) {
  if (!items || items.length === 0) return "";
  const chips = items.map((item) => `<span class="skill-chip">${escapeHtml(item)}</span>`).join("");
  return `
    <article class="skill-card">
      <header>
        <span class="skill-icon">${escapeHtml(icon)}</span>
        <h4>${escapeHtml(label)}</h4>
        <span class="skill-count">${items.length}</span>
      </header>
      <div class="skill-chips">${chips}</div>
    </article>
  `;
}

function renderJdAnalysis(data) {
  const analysis = data.analysis;
  state.jdAnalysis = analysis;
  state.analyzedJobDescription = data.job_description;

  document.getElementById("analysis-job-title").textContent = analysis.job_title;
  document.getElementById("analysis-experience").textContent = analysis.experience;
  document.getElementById("analysis-source-badge").textContent = data.source.toUpperCase();
  document.getElementById("analysis-item-count").textContent = `${data.summary.total_extracted_items} items extracted`;

  skillsGrid.innerHTML = SKILL_SECTIONS.map((section) =>
    renderSkillSection(section.label, section.icon, analysis[section.key])
  ).join("");

  jdAnalysisPanel.classList.remove("hidden");
  generateBtn.disabled = false;
  jdAnalysisPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function analyzeJobDescription() {
  hideStatus(setupStatus);
  const payload = getJobDescriptionPayload();

  if (payload.mode === "paste" && payload.text.length < 40) {
    showStatus(setupStatus, "Job description must be at least 40 characters.", "error");
    return;
  }
  if (payload.mode === "upload" && !payload.file) {
    showStatus(setupStatus, "Please upload a PDF, DOCX, or TXT file.", "error");
    return;
  }

  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<span class="loading"><span class="spinner"></span>Analyzing...</span>';

  try {
    let response;
    if (payload.mode === "upload") {
      const formData = new FormData();
      formData.append("file", payload.file);
      if (payload.supplement) {
        formData.append("job_description", payload.supplement);
      }
      response = await fetch("/api/analyze-jd", {
        method: "POST",
        body: formData,
      });
    } else {
      response = await fetch("/api/analyze-jd", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: payload.text }),
      });
    }

    const data = await parseJsonResponse(response);
    if (!response.ok) throw new Error(data.error || "Failed to analyze job description");

    renderJdAnalysis(data);
    showStatus(setupStatus, "Job description analyzed successfully. Review extracted skills, then generate the assessment.", "info");
  } catch (error) {
    showStatus(setupStatus, error.message, "error");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Job Description";
  }
}

async function parseJsonResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    const text = await response.text();
    throw new Error(text.startsWith("<!") ? "Server error - please try again." : text.slice(0, 200));
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}

// Global & Per-Question Timers
function startTimer(expiresAtEpoch) {
  state.expiresAt = expiresAtEpoch;
  if (state.timerInterval) clearInterval(state.timerInterval);

  const tick = () => {
    if (state.isPaused) return;

    const remaining = Math.max(0, Math.floor(state.expiresAt - Date.now() / 1000));
    timerEl.textContent = formatTime(remaining);
    timerEl.classList.remove("warning", "danger");

    if (remaining <= 600 && remaining > 300) {
      if (!state.warning10) {
        showProctorToast("[WARNING] 10 minutes remaining in assessment!");
        state.warning10 = true;
      }
    }
    if (remaining <= 300 && remaining > 60) {
      timerEl.classList.add("warning");
      if (!state.warning5) {
        showProctorToast("[WARNING] 5 minutes remaining! Work efficiently.");
        state.warning5 = true;
      }
    }
    if (remaining <= 60) {
      timerEl.classList.add("danger");
      if (!state.warning1) {
        showProctorToast("[CRITICAL WARNING] 1 minute remaining! Auto-submission imminent.");
        state.warning1 = true;
      }
    }

    if (remaining <= 0 && !state.autoSubmitted) {
      state.autoSubmitted = true;
      showStatus(testStatus, "Time is up. Submitting your assessment...", "info");
      submitAssessment(true);
    }
  };

  state.warning10 = false;
  state.warning5 = false;
  state.warning1 = false;
  tick();
  state.timerInterval = setInterval(tick, 1000);
}

function startQuestionTimer() {
  if (state.qTimerInterval) clearInterval(state.qTimerInterval);
  
  const qTick = () => {
    if (state.isPaused || !state.activeQuestionId) return;
    if (!state.questionTimes[state.activeQuestionId]) {
      state.questionTimes[state.activeQuestionId] = 0;
    }
    state.questionTimes[state.activeQuestionId]++;
    
    const qTimerEl = document.getElementById("q-timer");
    if (qTimerEl) {
      qTimerEl.textContent = formatTime(state.questionTimes[state.activeQuestionId]);
    }
  };
  
  state.qTimerInterval = setInterval(qTick, 1000);
}

function togglePause() {
  state.isPaused = !state.isPaused;
  if (state.isPaused) {
    pauseBtn.textContent = "Resume";
    pauseOverlay.classList.remove("hidden");
    questionList.classList.add("blur-content");
    showProctorToast("Assessment Paused. Questions hidden.");
  } else {
    pauseBtn.textContent = "Pause";
    pauseOverlay.classList.add("hidden");
    questionList.classList.remove("blur-content");
    showProctorToast("Assessment Resumed.");
  }
}

// Proctoring / Security Violations
function showProctorToast(message) {
  proctorToast.textContent = message;
  proctorToast.className = "proctor-toast visible";
  setTimeout(() => {
    proctorToast.className = "proctor-toast";
  }, 4500);
}

function handleSecurityViolation(reason) {
  if (!state.isFullscreenEnforced) return;
  state.securityViolations++;
  
  if (state.securityViolations >= 3) {
    state.isFullscreenEnforced = false;
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    fullscreenLockOverlay.classList.add("hidden");
    showStatus(testStatus, "Security limit exceeded. Auto-submitting assessment...", "error");
    submitAssessment(true);
  } else {
    showProctorToast(`[INTEGRITY ALERT] (${state.securityViolations}/3): ${reason} detected!`);
  }
}

async function enterFullscreen() {
  try {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen();
    }
  } catch (err) {
    console.error("Fullscreen lock error:", err);
  } finally {
    state.isFullscreenEnforced = true;
    fullscreenLockOverlay.classList.add("hidden");
  }
}

// Proctoring event listeners
document.addEventListener("fullscreenchange", () => {
  if (state.isFullscreenEnforced && !state.isPaused && !document.fullscreenElement) {
    fullscreenLockOverlay.classList.remove("hidden");
    handleSecurityViolation("Exiting fullscreen mode");
  }
});

document.addEventListener("visibilitychange", () => {
  if (state.isFullscreenEnforced && !state.isPaused && document.visibilityState === "hidden") {
    handleSecurityViolation("Tab switching");
  }
});

window.addEventListener("blur", () => {
  if (state.isFullscreenEnforced && !state.isPaused) {
    handleSecurityViolation("Focus loss / switching windows");
  }
});

resumeFullscreenBtn.addEventListener("click", enterFullscreen);

// Test execution functions
async function generateTest(event) {
  event.preventDefault();
  hideStatus(setupStatus);

  if (!state.jdAnalysis || !state.analyzedJobDescription) {
    showStatus(setupStatus, "Analyze the job description before generating the assessment.", "error");
    return;
  }

  const payload = {
    candidate_name: document.getElementById("candidate-name").value.trim(),
    job_title: state.jdAnalysis.job_title,
    job_description: state.analyzedJobDescription,
    department: document.getElementById("candidate-department").value,
  };

  if (!payload.candidate_name) {
    showStatus(setupStatus, "Candidate name is required.", "error");
    return;
  }

  generateBtn.disabled = true;
  generateBtn.innerHTML = '<span class="loading"><span class="spinner"></span>Generating...</span>';

  try {
    const response = await fetch("/api/generate-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await parseJsonResponse(response);
    if (!response.ok) throw new Error(data.error || "Failed to generate test");

    state.sessionId = data.session_id;
    state.questions = data.questions;
    state.answers = {};
    state.autoSubmitted = false;
    state.securityViolations = 0;
    state.questionTimes = {};
    state.isPaused = false;

    const startResponse = await fetch(`/api/sessions/${state.sessionId}/start`, {
      method: "POST",
    });
    const startData = await parseJsonResponse(startResponse);
    if (!startResponse.ok) throw new Error(startData.error || "Failed to start session");

    document.getElementById("test-title").textContent = data.job_title;
    document.getElementById("test-subtitle").textContent = `${data.candidate_name} - ${data.question_count} questions - ${data.duration_minutes} min`;

    setupPanel.classList.add("hidden");
    testPanel.classList.remove("hidden");
    reportPanel.classList.add("hidden");
    adminPanel.classList.add("hidden");
    document.body.classList.add("focus-mode");
    setStep(2);

    renderQuestions();
    startTimer(startData.expires_at_epoch);
    startQuestionTimer();
    
    await enterFullscreen();
  } catch (error) {
    showStatus(setupStatus, error.message, "error");
  } finally {
    generateBtn.disabled = !state.jdAnalysis;
    generateBtn.textContent = "Generate Assessment";
  }
}

async function submitAssessment(forced = false) {
  if (!state.sessionId) return;

  submitBtn.disabled = true;
  hideStatus(testStatus);

  if (!forced) {
    const unanswered = state.questions.filter((q) => {
      const ans = state.answers[q.id];
      if (ans === undefined || ans === null) return true;
      if (typeof ans === "string") return ans.trim() === "";
      if (Array.isArray(ans)) return ans.length === 0;
      if (typeof ans === "object") return Object.keys(ans).length === 0;
      return false;
    }).length;
    
    if (unanswered > 0) {
      const proceed = window.confirm(`${unanswered} question(s) are unanswered. Submit anyway?`);
      if (!proceed) {
        submitBtn.disabled = false;
        return;
      }
    }
  }

  submitBtn.innerHTML = '<span class="loading"><span class="spinner"></span>Grading...</span>';
  
  state.isFullscreenEnforced = false;
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {});
  }
  fullscreenLockOverlay.classList.add("hidden");

  try {
    const response = await fetch(`/api/sessions/${state.sessionId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        answers: state.answers,
        security_violations: state.securityViolations
      }),
    });
    const data = await parseJsonResponse(response);
    if (!response.ok) throw new Error(data.error || "Submission failed");

    if (state.timerInterval) clearInterval(state.timerInterval);
    if (state.qTimerInterval) clearInterval(state.qTimerInterval);

    // Get attempts lists
    const sessDetail = await fetch(`/api/sessions/${state.sessionId}`);
    const details = await sessDetail.json();
    state.attempts = details.attempts || [];

    renderResultsDashboard(data.grading_result);
    
    testPanel.classList.add("hidden");
    reportPanel.classList.remove("hidden");
    adminPanel.classList.add("hidden");
    document.body.classList.remove("focus-mode");
    setStep(3);
  } catch (error) {
    showStatus(testStatus, error.message, "error");
    submitBtn.disabled = false;
    submitBtn.textContent = "Submit Assessment";
  }
}

// Results dashboard renderer
function renderResultsDashboard(grading) {
  document.getElementById("summary-score").textContent = `${grading.total_score} / ${grading.max_score}`;
  document.getElementById("summary-percentage").textContent = `${grading.overall_percentage}%`;
  
  // Calculate Grade
  let grade = "F";
  let color = "red";
  if (grading.overall_percentage >= 85) { grade = "A"; color = "#10b981"; }
  else if (grading.overall_percentage >= 70) { grade = "B"; color = "#84cc16"; }
  else if (grading.overall_percentage >= 55) { grade = "C"; color = "#f59e0b"; }
  
  const gradeBadge = document.getElementById("summary-grade");
  gradeBadge.textContent = `Grade: ${grade}`;
  gradeBadge.style.background = `rgba(${grading.overall_percentage >= 55 ? '16,185,129' : '239,68,68'}, 0.12)`;
  gradeBadge.style.color = color;

  // Interview readiness estimation
  const readiness = Math.round(grading.overall_percentage);
  document.getElementById("summary-readiness").textContent = `${readiness}%`;
  const bar = document.getElementById("readiness-fill");
  bar.style.width = `${readiness}%`;
  bar.style.background = `linear-gradient(90deg, ${color}, #06b6d4)`;

  document.getElementById("summary-recommendation").textContent = grading.recommendation;

  // Populate strengths and weaknesses
  const strongList = document.getElementById("strong-domains-list");
  const weakList = document.getElementById("weak-domains-list");
  strongList.innerHTML = "";
  weakList.innerHTML = "";
  
  grading.category_breakdown.forEach(cat => {
    const item = document.createElement("li");
    item.innerHTML = `${escapeHtml(cat.category)} <span>${cat.percentage}%</span>`;
    if (cat.percentage >= 70) {
      strongList.appendChild(item);
    } else {
      weakList.appendChild(item);
    }
  });
  
  if (strongList.children.length === 0) {
    strongList.innerHTML = "<li>No domain met proceeding strength levels yet.</li>";
  }
  if (weakList.children.length === 0) {
    weakList.innerHTML = "<li>No specific weak areas detected. Outstanding foundation!</li>";
  }

  // Populate History Attempts
  const attemptsBody = document.getElementById("history-attempts-rows");
  attemptsBody.innerHTML = "";
  
  state.attempts.forEach(att => {
    const row = document.createElement("tr");
    const dateStr = new Date(att.date).toLocaleString();
    row.innerHTML = `
      <td>${att.attempt_number}</td>
      <td>${dateStr}</td>
      <td>${att.score} / ${att.max_score}</td>
      <td><span class="badge ${att.percentage >= 70 ? 'mcq' : att.percentage >= 55 ? 'short' : 'scenario'}">${att.percentage}%</span></td>
      <td>Violations: ${att.security_violations} ${att.submitted_late ? '(LATE)' : '(OK)'}</td>
    `;
    attemptsBody.appendChild(row);
  });

  // Populate Question Review list
  const reviewList = document.getElementById("question-review-list");
  reviewList.innerHTML = "";
  
  grading.question_results.forEach((qResult, index) => {
    const qDef = state.questions.find(item => item.id === qResult.id) || {};
    const card = document.createElement("div");
    const res = qResult.result;
    const isCorrectClass = getBadgeColorClass(res.score, res.max_score);
    
    card.className = `review-card ${isCorrectClass}`;
    
    // Formatting answers display
    let candidateAns = qResult.answer;
    if (typeof candidateAns === "object") {
      candidateAns = JSON.stringify(candidateAns);
    }
    
    let correctAns = res.correct_answer;
    if (Array.isArray(correctAns)) {
      correctAns = correctAns.join(", ");
    }
    
    card.innerHTML = `
      <div class="review-header" onclick="toggleReviewCard(this)">
        <div class="review-header-left">
          <span>${getResultIcon(res.score, res.max_score)}</span>
          <strong>Q${index + 1}: ${escapeHtml(qDef.category || "General")}</strong>
        </div>
        <span class="badge">${res.score} / ${res.max_score} pts</span>
      </div>
      <div class="review-body hidden">
        <p><strong>Prompt:</strong> ${escapeHtml(qResult.prompt)}</p>
        <div class="ans-detail ${res.score === res.max_score ? 'correct-bg' : 'wrong-bg'}">
          <strong>Your Response:</strong> ${escapeHtml(candidateAns || "[No response provided]")}
        </div>
        <div class="ans-detail correct-bg">
          <strong>Correct Answer:</strong> ${escapeHtml(correctAns || "N/A")}
        </div>
        <div class="explanation-box">
          <div class="explanation-title">Detailed Explanation</div>
          <p class="exp-text">${escapeHtml(qDef.explanation || res.feedback || "Correct alignment with skill tested.")}</p>
        </div>
        ${qDef.wrong_option_rationale ? `
        <div class="explanation-box">
          <div class="explanation-title">Option Analysis</div>
          <p class="exp-text">${escapeHtml(qDef.wrong_option_rationale)}</p>
        </div>
        ` : ""}
        <p style="font-size:12px;color:var(--muted);margin-bottom:0;">
          <strong>Skill:</strong> ${escapeHtml(qDef.skill_tested || "N/A")} | 
          <strong>Difficulty:</strong> ${escapeHtml(qDef.difficulty || "medium")} | 
          <strong>References:</strong> ${(qDef.references || []).join(", ") || "NIST / MITRE guidelines"}
        </p>
      </div>
    `;
    reviewList.appendChild(card);
  });

  const frame = document.getElementById("report-frame");
  frame.src = `/api/sessions/${state.sessionId}/report`;
}

// Accordion toggle
window.toggleReviewCard = function(header) {
  const body = header.nextElementSibling;
  body.classList.toggle("hidden");
};

// Retakes and Re-randomization shuffles
async function retakeAssessment() {
  if (!state.sessionId) return;
  const proceed = window.confirm("Are you sure you want to retake this assessment? A new attempt will be recorded.");
  if (!proceed) return;

  try {
    const response = await fetch(`/api/sessions/${state.sessionId}/retake`, { method: "POST" });
    const data = await parseJsonResponse(response);
    if (!response.ok) throw new Error(data.error || "Retake failed");

    // Shuffle questions client side as verification of Fisher-Yates
    state.questions = data.questions;
    state.answers = {};
    state.autoSubmitted = false;
    state.securityViolations = 0;
    state.questionTimes = {};
    state.isPaused = false;

    // Start
    const startResponse = await fetch(`/api/sessions/${state.sessionId}/start`, { method: "POST" });
    const startData = await parseJsonResponse(startResponse);
    if (!startResponse.ok) throw new Error(startData.error || "Failed to start retake session");

    setupPanel.classList.add("hidden");
    testPanel.classList.remove("hidden");
    reportPanel.classList.add("hidden");
    adminPanel.classList.add("hidden");
    document.body.classList.add("focus-mode");
    setStep(2);

    renderQuestions();
    startTimer(startData.expires_at_epoch);
    startQuestionTimer();
    await enterFullscreen();
  } catch (err) {
    alert(err.message);
  }
}

async function regenerateAssessment() {
  if (!state.sessionId) return;
  const proceed = window.confirm("Generate a completely new set of questions from the job description? Past attempts will be saved.");
  if (!proceed) return;

  try {
    const response = await fetch(`/api/sessions/${state.sessionId}/regenerate`, { method: "POST" });
    const data = await parseJsonResponse(response);
    if (!response.ok) throw new Error(data.error || "Failed to generate new set");

    state.questions = data.questions;
    state.answers = {};
    state.autoSubmitted = false;
    state.securityViolations = 0;
    state.questionTimes = {};
    state.isPaused = false;

    const startResponse = await fetch(`/api/sessions/${state.sessionId}/start`, { method: "POST" });
    const startData = await parseJsonResponse(startResponse);
    if (!startResponse.ok) throw new Error(startData.error || "Failed to start session");

    setupPanel.classList.add("hidden");
    testPanel.classList.remove("hidden");
    reportPanel.classList.add("hidden");
    adminPanel.classList.add("hidden");
    document.body.classList.add("focus-mode");
    setStep(2);

    renderQuestions();
    startTimer(startData.expires_at_epoch);
    startQuestionTimer();
    await enterFullscreen();
  } catch (err) {
    alert(err.message);
  }
}

// Admin Panel operations
async function loadAdminDashboardData() {
  try {
    const listRes = await fetch("/api/sessions");
    if (!listRes.ok) throw new Error("Failed to load sessions");
    const sessions = await listRes.json();
    
    const analyticsRes = await fetch("/api/admin/analytics");
    if (!analyticsRes.ok) throw new Error("Failed to load analytics");
    const analytics = await analyticsRes.json();

    // Populate stats
    document.getElementById("admin-total-assessments").textContent = analytics.total_assessments;
    document.getElementById("admin-completed-assessments").textContent = analytics.completed_assessments;
    document.getElementById("admin-completion-rate").textContent = `${analytics.completion_rate}%`;
    document.getElementById("admin-average-score").textContent = `${analytics.average_score}%`;

    // Populate weak categories
    const weakList = document.getElementById("admin-weak-categories");
    weakList.innerHTML = "";
    analytics.weak_categories.forEach(c => {
      weakList.innerHTML += `<li>${escapeHtml(c.category)} <span>${c.percentage}%</span></li>`;
    });
    if (analytics.weak_categories.length === 0) {
      weakList.innerHTML = "<li>No assessments graded yet.</li>";
    }

    // Populate missed skills
    const missedList = document.getElementById("admin-missed-skills");
    missedList.innerHTML = "";
    analytics.most_missed_skills.forEach(s => {
      missedList.innerHTML += `<li>${escapeHtml(s.skill)} <span>${s.percentage}%</span></li>`;
    });
    if (analytics.most_missed_skills.length === 0) {
      missedList.innerHTML = "<li>No assessments graded yet.</li>";
    }

    // Populate assessments table
    adminSessionsList.innerHTML = "";
    sessions.forEach(sess => {
      const row = document.createElement("tr");
      const scoreDisp = sess.score !== null ? `${sess.score} / ${sess.max_score} (${sess.percentage}%)` : "—";
      row.innerHTML = `
        <td><strong>${escapeHtml(sess.candidate_name)}</strong></td>
        <td>${escapeHtml(sess.job_title)}</td>
        <td><span class="badge ${sess.status === 'graded' ? 'mcq' : 'short'}">${sess.status.toUpperCase()}</span></td>
        <td>Attempts: ${sess.attempts_count}</td>
        <td>${scoreDisp}</td>
        <td>
          <button type="button" class="btn-secondary" style="padding:6px 12px;font-size:12px;" onclick="viewSessionReport('${sess.session_id}')">View</button>
          <button type="button" class="btn-danger" style="padding:6px 12px;font-size:12px;margin-left:4px;" onclick="deleteSessionRecord('${sess.session_id}')">Delete</button>
        </td>
      `;
      adminSessionsList.appendChild(row);
    });

  } catch (err) {
    alert("Admin load error: " + err.message);
  }
}

async function showAdminPanel() {
  setupPanel.classList.add("hidden");
  testPanel.classList.add("hidden");
  reportPanel.classList.add("hidden");
  adminPanel.classList.remove("hidden");
  setStep(1);

  adminPanelToggleBtn.disabled = true;
  adminPanelToggleBtn.textContent = "Loading Admin...";

  try {
    const authRes = await fetch("/api/admin/check-auth");
    const authData = await authRes.json();

    if (authData.authenticated) {
      document.getElementById("admin-auth-container").classList.add("hidden");
      document.getElementById("admin-dashboard-container").classList.remove("hidden");
      await loadAdminDashboardData();
    } else {
      document.getElementById("admin-auth-container").classList.remove("hidden");
      document.getElementById("admin-dashboard-container").classList.add("hidden");
      hideStatus(document.getElementById("admin-auth-error"));
      document.getElementById("admin-username").value = "";
      document.getElementById("admin-password").value = "";
    }
  } catch (err) {
    console.error("Auth check failed:", err);
  } finally {
    adminPanelToggleBtn.disabled = false;
    adminPanelToggleBtn.textContent = "Admin Dashboard";
  }
}

async function handleAdminLogin(event) {
  event.preventDefault();
  const usernameInput = document.getElementById("admin-username");
  const passwordInput = document.getElementById("admin-password");
  const errorEl = document.getElementById("admin-auth-error");
  const submitBtn = document.getElementById("admin-auth-submit-btn");

  hideStatus(errorEl);
  submitBtn.disabled = true;
  submitBtn.textContent = "Verifying...";

  try {
    const response = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: usernameInput.value,
        password: passwordInput.value
      })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Login failed");

    document.getElementById("admin-auth-container").classList.add("hidden");
    document.getElementById("admin-dashboard-container").classList.remove("hidden");
    usernameInput.value = "";
    passwordInput.value = "";
    
    await loadAdminDashboardData();
  } catch (err) {
    showStatus(errorEl, err.message, "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Verify Credentials";
  }
}

async function handleAdminLogout() {
  try {
    await fetch("/api/admin/logout", { method: "POST" });
    resetApp();
  } catch (err) {
    console.error("Logout failed:", err);
  }
}

function toggleAdminPasswordVisibility() {
  const pwdInput = document.getElementById("admin-password");
  const toggleBtn = document.getElementById("admin-password-toggle");
  if (pwdInput.type === "password") {
    pwdInput.type = "text";
    toggleBtn.textContent = "🙈";
  } else {
    pwdInput.type = "password";
    toggleBtn.textContent = "👁️";
  }
}

window.viewSessionReport = async function(sessionId) {
  try {
    const res = await fetch(`/api/sessions/${sessionId}`);
    const details = await res.json();
    if (!res.ok) throw new Error(details.error || "Failed to load session detail");

    state.sessionId = sessionId;
    state.questions = details.questions;
    state.answers = details.answers;
    state.attempts = details.attempts || [];

    renderResultsDashboard(details.grading_result);
    
    setupPanel.classList.add("hidden");
    testPanel.classList.add("hidden");
    reportPanel.classList.remove("hidden");
    adminPanel.classList.add("hidden");
    setStep(3);
  } catch (err) {
    alert("Report display error: " + err.message);
  }
};

window.deleteSessionRecord = async function(sessionId) {
  const proceed = window.confirm("Are you sure you want to permanently delete this assessment record?");
  if (!proceed) return;
  try {
    const res = await fetch(`/api/sessions/${sessionId}`, { method: "DELETE" });
    if (res.ok) {
      showAdminPanel();
    } else {
      const details = await res.json();
      throw new Error(details.error || "Failed to delete");
    }
  } catch (err) {
    alert(err.message);
  }
};

function exportReportCSV() {
  const rows = [
    ["Candidate Name", "Role Target", "Status", "Attempt Count", "Top Score Percentage"]
  ];
  
  const trs = adminSessionsList.querySelectorAll("tr");
  trs.forEach(tr => {
    const tds = tr.querySelectorAll("td");
    if (tds.length >= 5) {
      rows.push([
        tds[0].innerText,
        tds[1].innerText,
        tds[2].innerText,
        tds[3].innerText,
        tds[4].innerText
      ]);
    }
  });

  let csvContent = "data:text/csv;charset=utf-8,";
  rows.forEach(r => {
    csvContent += r.map(x => `"${x.replace(/"/g, '""')}"`).join(",") + "\r\n";
  });
  
  const encodedUri = encodeURI(csvContent);
  const a = document.createElement("a");
  a.href = encodedUri;
  a.download = `Cyber_Aptitude_Assessments_Summary_${Date.now()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function openReport() {
  const frame = document.getElementById("report-frame");
  frame.classList.remove("hidden");
  frame.scrollIntoView({ behavior: "smooth" });
  window.open(`/api/sessions/${state.sessionId}/report`, "_blank");
}

function downloadReport() {
  window.print();
}

function resetApp() {
  state.sessionId = null;
  state.questions = [];
  state.answers = {};
  state.expiresAt = null;
  state.autoSubmitted = false;
  state.securityViolations = 0;
  state.isFullscreenEnforced = false;
  state.jdAnalysis = null;
  state.analyzedJobDescription = "";
  if (state.timerInterval) clearInterval(state.timerInterval);
  if (state.qTimerInterval) clearInterval(state.qTimerInterval);

  setupPanel.classList.remove("hidden");
  testPanel.classList.add("hidden");
  reportPanel.classList.add("hidden");
  adminPanel.classList.add("hidden");
  document.body.classList.remove("focus-mode");
  setStep(1);
  setupForm.reset();
  setInputTab("paste");
  setUploadedFile(null);
  invalidateAnalysis();
  hideStatus(setupStatus);
  hideStatus(testStatus);
  fullscreenLockOverlay.classList.add("hidden");
  updateUserUI();
}

// Event Listeners
document.querySelectorAll(".input-tab").forEach((button) => {
  button.addEventListener("click", () => setInputTab(button.dataset.tab));
});

uploadZone.addEventListener("click", () => jdFileInput.click());
uploadZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  uploadZone.classList.add("dragover");
});
uploadZone.addEventListener("dragleave", () => uploadZone.classList.remove("dragover"));
uploadZone.addEventListener("drop", (event) => {
  event.preventDefault();
  uploadZone.classList.remove("dragover");
  const file = event.dataTransfer?.files?.[0];
  if (file) setUploadedFile(file);
});

jdFileInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) setUploadedFile(file);
});

document.getElementById("job-description").addEventListener(
  "input",
  debounce(() => invalidateAnalysis(), 400)
);
document.getElementById("job-description-supplement").addEventListener(
  "input",
  debounce(() => invalidateAnalysis(), 400)
);

analyzeBtn.addEventListener("click", analyzeJobDescription);
setupForm.addEventListener("submit", generateTest);
submitBtn.addEventListener("click", () => submitAssessment(false));
document.getElementById("open-report-btn").addEventListener("click", openReport);
downloadReportBtn.addEventListener("click", downloadReport);
document.getElementById("new-assessment-btn").addEventListener("click", resetApp);

adminPanelToggleBtn.addEventListener("click", showAdminPanel);
adminBackBtn.addEventListener("click", resetApp);
exportCsvBtn.addEventListener("click", exportReportCSV);

document.getElementById("admin-login-form").addEventListener("submit", handleAdminLogin);
document.getElementById("admin-auth-cancel-btn").addEventListener("click", resetApp);
document.getElementById("admin-password-toggle").addEventListener("click", toggleAdminPasswordVisibility);
document.getElementById("admin-logout-btn").addEventListener("click", handleAdminLogout);

pauseBtn.addEventListener("click", togglePause);
resumeBtn.addEventListener("click", togglePause);

retakeBtn.addEventListener("click", retakeAssessment);
regenerateBtn.addEventListener("click", regenerateAssessment);

document.querySelectorAll(".auth-tab").forEach((btn) => {
  btn.addEventListener("click", () => switchAuthTab(btn.dataset.authTab));
});
document.getElementById("user-login-form").addEventListener("submit", handleUserLogin);
document.getElementById("user-signup-form").addEventListener("submit", handleSignup);
document.getElementById("user-logout-btn").addEventListener("click", handleUserLogout);
document.querySelectorAll(".btn-password-toggle[data-toggle]").forEach((btn) => {
  btn.addEventListener("click", () => toggleUserPasswordVisibility(btn));
});

seedDemoUser();
initAuthEnhancements();
updateUserUI();
