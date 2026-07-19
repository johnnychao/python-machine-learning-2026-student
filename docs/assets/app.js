(function () {
  "use strict";

  const manifest = window.COURSE_MANIFEST;

  if (!manifest || !Array.isArray(manifest.stations)) {
    document.body.insertAdjacentHTML(
      "afterbegin",
      '<div class="noscript-note" role="alert">課程設定檔載入失敗。請確認 assets/course-manifest.js 與本頁位於同一個 docs 資料夾。</div>'
    );
    return;
  }

  const STORAGE_KEY = `ai-solution-lab:${manifest.schemaVersion}`;
  const STATION_STEPS = [
    { id: "ran", label: "已完成核心執行" },
    { id: "compared", label: "已修改一項並比較前後" },
    { id: "recorded", label: "已記錄證據與失敗情境" }
  ];
  const EXPERIMENT_FIELDS = ["changed", "beforeResult", "afterResult", "reason", "failure", "nextStep"];
  const totalSeconds = Number(manifest.rotationMinutes || 30) * 60;
  let timerTick = null;
  let saveTick = null;
  let activeExperimentStation = "";
  let storageEnabled = true;

  const $ = (selector, parent = document) => parent.querySelector(selector);
  const $$ = (selector, parent = document) => Array.from(parent.querySelectorAll(selector));

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "'": "&#39;",
      '"': "&quot;"
    }[character]));
  }

  function createDefaultExperiment() {
    return {
      changed: "",
      beforeResult: "",
      afterResult: "",
      reason: "",
      failure: "",
      nextStep: ""
    };
  }

  function createDefaultState() {
    const preflight = {};
    const stationProgress = {};
    const experiments = {};

    manifest.preflight.checklist.forEach((item) => {
      preflight[item.id] = false;
    });

    manifest.stations.forEach((station) => {
      stationProgress[station.id] = { ran: false, compared: false, recorded: false };
      experiments[station.id] = createDefaultExperiment();
    });

    return {
      version: manifest.schemaVersion,
      preflight,
      stationProgress,
      selectedProject: "",
      experiments,
      teamName: "",
      timer: {
        remaining: totalSeconds,
        running: false,
        endAt: null,
        activeStation: ""
      }
    };
  }

  function mergeState(raw) {
    const fresh = createDefaultState();

    if (!raw || typeof raw !== "object") {
      return fresh;
    }

    Object.keys(fresh.preflight).forEach((key) => {
      fresh.preflight[key] = Boolean(raw.preflight && raw.preflight[key]);
    });

    manifest.stations.forEach((station) => {
      STATION_STEPS.forEach((step) => {
        fresh.stationProgress[station.id][step.id] = Boolean(
          raw.stationProgress &&
          raw.stationProgress[station.id] &&
          raw.stationProgress[station.id][step.id]
        );
      });

      EXPERIMENT_FIELDS.forEach((field) => {
        const value = raw.experiments && raw.experiments[station.id] && raw.experiments[station.id][field];
        fresh.experiments[station.id][field] = typeof value === "string" ? value : "";
      });
    });

    if (manifest.stations.some((station) => station.id === raw.selectedProject)) {
      fresh.selectedProject = raw.selectedProject;
    }

    fresh.teamName = typeof raw.teamName === "string" ? raw.teamName : "";

    if (raw.timer && typeof raw.timer === "object") {
      const remaining = Number(raw.timer.remaining);
      fresh.timer.remaining = Number.isFinite(remaining)
        ? Math.max(0, Math.min(totalSeconds, Math.round(remaining)))
        : totalSeconds;
      fresh.timer.running = Boolean(raw.timer.running);
      fresh.timer.endAt = Number.isFinite(Number(raw.timer.endAt)) ? Number(raw.timer.endAt) : null;
      fresh.timer.activeStation = manifest.stations.some((station) => station.id === raw.timer.activeStation)
        ? raw.timer.activeStation
        : "";
    }

    if (fresh.timer.running && !fresh.timer.endAt) {
      fresh.timer.running = false;
    }

    return fresh;
  }

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return mergeState(raw ? JSON.parse(raw) : null);
    } catch (error) {
      storageEnabled = false;
      return createDefaultState();
    }
  }

  let state = loadState();

  function persistState() {
    if (!storageEnabled) {
      return false;
    }

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch (error) {
      storageEnabled = false;
      return false;
    }
  }

  function stationById(id) {
    return manifest.stations.find((station) => station.id === id);
  }

  function isLocalRuntime() {
    const hostname = window.location.hostname.toLowerCase();
    return window.location.protocol === "file:" ||
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname === "::1" ||
      hostname.endsWith(".localhost");
  }

  function notebookDownloadUrl(notebookPath, localHref) {
    if (isLocalRuntime()) return localHref;
    const repoUrl = manifest.repo.url.replace(/\/$/, "");
    const branch = encodeURIComponent(manifest.repo.branch);
    const encodedPath = notebookPath.split("/").map(encodeURIComponent).join("/");
    return `${repoUrl}/raw/${branch}/${encodedPath}`;
  }

  function stationProgressCount(id) {
    const progress = state.stationProgress[id];
    return STATION_STEPS.reduce((count, step) => count + Number(Boolean(progress[step.id])), 0);
  }

  function completedStationCount() {
    return manifest.stations.reduce(
      (count, station) => count + Number(stationProgressCount(station.id) === STATION_STEPS.length),
      0
    );
  }

  function checkedPreflightCount() {
    return manifest.preflight.checklist.reduce(
      (count, item) => count + Number(Boolean(state.preflight[item.id])),
      0
    );
  }

  function renderManifestMeta() {
    $("#course-subtitle").textContent = manifest.courseSubtitle;
    $("#repo-link").href = manifest.repo.url;
    $("#publication-title").textContent = manifest.publication.label;
    $("#publication-copy").textContent = manifest.publication.note;
    $("#preflight-title").textContent = manifest.preflight.title.replace("00｜", "");
    $("#preflight-colab").href = manifest.preflight.links.colab;
    $("#preflight-local").href = notebookDownloadUrl(
      manifest.preflight.notebookPath,
      manifest.preflight.links.local
    );
  }

  function renderPreflight() {
    const container = $("#preflight-list");
    container.replaceChildren();

    manifest.preflight.checklist.forEach((item, index) => {
      const label = document.createElement("label");
      label.className = "check-row";
      label.htmlFor = `preflight-${item.id}`;

      const input = document.createElement("input");
      input.type = "checkbox";
      input.id = `preflight-${item.id}`;
      input.dataset.preflightId = item.id;
      input.checked = Boolean(state.preflight[item.id]);

      const text = document.createElement("span");
      text.textContent = `${String(index + 1).padStart(2, "0")}｜${item.label}`;

      label.append(input, text);
      container.append(label);
    });

    container.addEventListener("change", (event) => {
      const input = event.target.closest("input[data-preflight-id]");
      if (!input) return;
      state.preflight[input.dataset.preflightId] = input.checked;
      persistState();
      updateProgressDisplay();
    });
  }

  function renderRhythm() {
    const container = $("#rhythm-list");
    container.innerHTML = manifest.rotationRhythm.map((item) => `
      <li>
        <time>${escapeHtml(item.minute)}</time>
        <strong>${escapeHtml(item.label)}</strong>
        <span>${escapeHtml(item.detail)}</span>
      </li>
    `).join("");
  }

  function stationCardTemplate(station) {
    const changeItems = station.changeOptions.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    const evidenceItems = station.evidence.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
    const scopeNote = station.scopeNote ? `
      <div class="scope-note">
        <span>SCOPE BOUNDARY／實作界線</span>
        <p>${escapeHtml(station.scopeNote)}</p>
      </div>
    ` : "";
    const checks = STATION_STEPS.map((step) => `
      <label class="station-check">
        <input type="checkbox" data-station="${escapeHtml(station.id)}" data-step="${escapeHtml(step.id)}">
        <span>${escapeHtml(step.label)}</span>
      </label>
    `).join("");

    return `
      <article class="station-card" id="station-${escapeHtml(station.id)}" style="--station-accent: ${escapeHtml(station.accent)}">
        <header class="station-card__header">
          <span class="station-code" aria-hidden="true">${escapeHtml(station.shortCode)}</span>
          <div>
            <span class="station-number">STATION ${escapeHtml(station.sequence)}／${escapeHtml(station.focus)}</span>
            <h3>${escapeHtml(station.title)}</h3>
            <p class="station-client">CLIENT／${escapeHtml(station.client)}</p>
          </div>
        </header>
        <div class="station-card__body">
          <p class="story-brief">${escapeHtml(station.story)}</p>
          <div class="mission-order">
            <span>30 MIN<br>ORDER</span>
            <p>${escapeHtml(station.mission)}</p>
          </div>
          <div class="data-ticket">
            <span>KAGGLE DATA SOURCE</span>
            <strong>${escapeHtml(station.data)}</strong>
            <small>${escapeHtml(station.dataDetail)}</small>
          </div>
          <div class="station-links" aria-label="${escapeHtml(station.shortCode)} 學習資源">
            <a href="${escapeHtml(station.links.kaggle)}" target="_blank" rel="noopener noreferrer"><small>DATA</small>Kaggle ↗</a>
            <a href="${escapeHtml(station.links.colab)}" target="_blank" rel="noopener noreferrer"><small>RUN</small>Colab ↗</a>
            <a href="${escapeHtml(notebookDownloadUrl(station.notebookPath, station.links.local))}" download><small>BACKUP</small>下載 notebook</a>
          </div>
          <p class="link-advisory">${escapeHtml(manifest.publication.note)}</p>
          ${scopeNote}
          <div class="station-columns">
            <div>
              <h4>CHANGE ONE THING</h4>
              <ul>${changeItems}</ul>
            </div>
            <div>
              <h4>LEAVE EVIDENCE</h4>
              <ul>${evidenceItems}</ul>
            </div>
          </div>
          <div class="cpu-fallback">
            <h4>NO GPU／CPU 備援</h4>
            <p>${escapeHtml(station.cpuFallback)}</p>
          </div>
          <div class="station-checks">
            <h4>LEAVE-STATION CHECK</h4>
            <div class="station-check-list">${checks}</div>
          </div>
          <div class="station-card__actions">
            <button type="button" class="button button--station" data-start-station="${escapeHtml(station.id)}">啟動本站 30:00</button>
            <span class="station-progress-label" data-station-progress="${escapeHtml(station.id)}">0/3 READY</span>
          </div>
        </div>
      </article>
    `;
  }

  function renderStations() {
    const container = $("#station-grid");
    container.innerHTML = manifest.stations.map(stationCardTemplate).join("");

    manifest.stations.forEach((station) => updateStationCard(station.id));

    container.addEventListener("change", (event) => {
      const checkbox = event.target.closest("input[data-station][data-step]");
      if (!checkbox) return;
      state.stationProgress[checkbox.dataset.station][checkbox.dataset.step] = checkbox.checked;
      persistState();
      updateStationCard(checkbox.dataset.station);
      updateProgressDisplay();
    });

    container.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-start-station]");
      if (!button) return;
      startStationTimer(button.dataset.startStation);
      button.textContent = "本站計時已啟動";
      window.setTimeout(() => {
        button.textContent = "重新啟動本站 30:00";
      }, 1800);
    });
  }

  function updateStationCard(stationId) {
    const card = $(`#station-${stationId}`);
    if (!card) return;
    const count = stationProgressCount(stationId);
    card.dataset.complete = String(count === STATION_STEPS.length);
    STATION_STEPS.forEach((step) => {
      const input = $(`input[data-station="${stationId}"][data-step="${step.id}"]`, card);
      if (input) input.checked = Boolean(state.stationProgress[stationId][step.id]);
    });
    const label = $(`[data-station-progress="${stationId}"]`, card);
    if (label) label.textContent = `${count}/${STATION_STEPS.length} ${count === STATION_STEPS.length ? "CLEARED" : "READY"}`;
  }

  function renderProjectChoices() {
    const container = $("#project-choices");
    container.innerHTML = manifest.stations.map((station) => `
      <div class="project-option" style="--station-accent: ${escapeHtml(station.accent)}">
        <input type="radio" id="project-${escapeHtml(station.id)}" name="deep-dive-project" value="${escapeHtml(station.id)}" ${state.selectedProject === station.id ? "checked" : ""}>
        <label for="project-${escapeHtml(station.id)}">
          <span>
            <span class="project-option__code">${escapeHtml(station.sequence)}／${escapeHtml(station.shortCode)}</span>
            <strong>${escapeHtml(station.title)}</strong>
            <small>${escapeHtml(station.focus)}</small>
          </span>
          <span class="project-option__state">${state.selectedProject === station.id ? "SELECTED／已選定" : "SELECT／選擇此案"}</span>
        </label>
      </div>
    `).join("");

    container.addEventListener("change", (event) => {
      const input = event.target.closest('input[name="deep-dive-project"]');
      if (!input) return;
      state.selectedProject = input.value;
      persistState();
      renderProjectChoices();
      setExperimentStation(input.value);
      updateProgressDisplay();
    }, { once: true });
  }

  function renderExperimentStationOptions() {
    const select = $("#experiment-station");
    select.innerHTML = manifest.stations.map((station) => `
      <option value="${escapeHtml(station.id)}">${escapeHtml(station.sequence)}／${escapeHtml(station.shortCode)}｜${escapeHtml(station.title)}</option>
    `).join("");

    activeExperimentStation = state.selectedProject || manifest.stations[0].id;
    loadExperimentForm();

    select.addEventListener("change", () => {
      activeExperimentStation = select.value;
      loadExperimentForm();
    });
  }

  function loadExperimentForm() {
    const station = stationById(activeExperimentStation) || manifest.stations[0];
    activeExperimentStation = station.id;
    $("#experiment-station").value = station.id;
    $("#team-name").value = state.teamName;
    $("#record-id").textContent = `LAB-${station.shortCode}-${station.sequence}`;

    EXPERIMENT_FIELDS.forEach((field) => {
      const input = $(`[name="${field}"]`, $("#experiment-form"));
      if (input) input.value = state.experiments[station.id][field] || "";
    });

    setSaveState("loaded");
  }

  function setExperimentStation(stationId) {
    if (!stationById(stationId)) return;
    activeExperimentStation = stationId;
    loadExperimentForm();
  }

  function setSaveState(mode) {
    const output = $("#save-state");

    if (!storageEnabled) {
      output.dataset.saved = "false";
      output.textContent = "此瀏覽器禁止本機保存；請先下載 Markdown";
      return;
    }

    if (mode === "saving") {
      output.dataset.saved = "false";
      output.innerHTML = '<i aria-hidden="true"></i> 儲存中…';
      return;
    }

    const hasContent = state.teamName.trim() || Object.values(state.experiments[activeExperimentStation]).some((value) => value.trim());
    output.dataset.saved = hasContent ? "true" : "false";
    output.innerHTML = hasContent
      ? '<i aria-hidden="true"></i> 已自動存到本機'
      : '<i aria-hidden="true"></i> 尚未輸入';
  }

  function scheduleExperimentSave(event) {
    const target = event.target;
    if (target.id === "experiment-station") return;

    if (target.name === "teamName") {
      state.teamName = target.value;
    } else if (EXPERIMENT_FIELDS.includes(target.name)) {
      state.experiments[activeExperimentStation][target.name] = target.value;
    } else {
      return;
    }

    setSaveState("saving");
    window.clearTimeout(saveTick);
    saveTick = window.setTimeout(() => {
      persistState();
      setSaveState("saved");
    }, 260);
  }

  function updateProgressDisplay() {
    const preflightDone = checkedPreflightCount();
    const stationsDone = completedStationCount();
    const selectionDone = Number(Boolean(state.selectedProject));
    const totalItems = manifest.preflight.checklist.length + (manifest.stations.length * STATION_STEPS.length) + 1;
    const doneItems = preflightDone + manifest.stations.reduce(
      (sum, station) => sum + stationProgressCount(station.id),
      0
    ) + selectionDone;
    const percentage = Math.round((doneItems / totalItems) * 100);

    $("#preflight-count").textContent = `${preflightDone}/${manifest.preflight.checklist.length}`;
    $("#station-count").textContent = `${stationsDone}/${manifest.stations.length}`;
    $("#selection-count").textContent = `${selectionDone}/1`;
    $("#progress-percent").textContent = `${percentage}%`;
    $("#mission-progress").value = percentage;
    $("#mission-progress").textContent = `${percentage}%`;

    const preflightStatus = $("#preflight-status");
    const preflightReady = preflightDone === manifest.preflight.checklist.length;
    preflightStatus.textContent = preflightReady ? "READY" : `${preflightDone}/${manifest.preflight.checklist.length}`;
    preflightStatus.dataset.ready = String(preflightReady);

    let message = "先完成起飛檢查，再啟動第一站。";
    if (preflightReady && stationsDone === 0) message = "環境就緒。從任一站啟動 30 分鐘。";
    if (stationsDone > 0 && stationsDone < manifest.stations.length) message = `已清除 ${stationsDone} 站；下一站仍只改一個變因。`;
    if (stationsDone === manifest.stations.length && !selectionDone) message = "四站完成。現在選一案進入完整實作。";
    if (stationsDone === manifest.stations.length && selectionDone) message = "輪轉與選案完成。用實驗卡留下能被驗證的證據。";
    if (percentage === 100) message = "MISSION READY：已完成本頁所有檢核。";
    $("#mission-message").textContent = message;
  }

  function syncTimerFromClock() {
    if (!state.timer.running || !state.timer.endAt) return;
    const remaining = Math.max(0, Math.ceil((state.timer.endAt - Date.now()) / 1000));
    state.timer.remaining = remaining;

    if (remaining === 0) {
      state.timer.running = false;
      state.timer.endAt = null;
      persistState();
      stopTimerLoop();
    }
  }

  function formatTime(seconds) {
    const safeSeconds = Math.max(0, Math.round(seconds));
    const minutes = Math.floor(safeSeconds / 60);
    const remainder = safeSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
  }

  function updateTimerDisplay() {
    syncTimerFromClock();
    const station = stationById(state.timer.activeStation);
    const display = formatTime(state.timer.remaining);
    const consoleElement = $(".timer-console");

    $("#timer-display").textContent = display;
    $("#timer-progress-bar").style.width = `${Math.max(0, (state.timer.remaining / totalSeconds) * 100)}%`;
    $("#active-station-label").textContent = station ? `${station.sequence}／${station.shortCode}` : "未指定站別";
    consoleElement.dataset.state = state.timer.remaining === 0 ? "finished" : (state.timer.running ? "running" : "paused");

    const toggle = $("#timer-toggle");
    toggle.textContent = state.timer.running ? "暫停" : (state.timer.remaining === 0 ? "再開一輪" : "開始／繼續");

    let status = "準備好後，從任一站啟動 30 分鐘。";
    if (station && state.timer.running) status = `${station.title}進行中；到點前完成比較與紀錄。`;
    if (station && !state.timer.running && state.timer.remaining > 0 && state.timer.remaining < totalSeconds) status = `${station.title}已暫停，可從剩餘時間繼續。`;
    if (state.timer.remaining === 0) status = "本輪結束：先填實驗卡，再移動到下一站。";
    $("#timer-status").textContent = status;

    const headerTimer = $("#header-timer");
    if (headerTimer) {
      headerTimer.textContent = `◷ ${display}`;
      headerTimer.dataset.running = String(state.timer.running);
      headerTimer.setAttribute("aria-label", `${station ? station.shortCode : "輪轉"}計時器 ${display}，點選前往計時器`);
    }
  }

  function startTimerLoop() {
    stopTimerLoop();
    timerTick = window.setInterval(updateTimerDisplay, 500);
  }

  function stopTimerLoop() {
    if (timerTick) window.clearInterval(timerTick);
    timerTick = null;
  }

  function startStationTimer(stationId) {
    state.timer.activeStation = stationId;
    state.timer.remaining = totalSeconds;
    state.timer.running = true;
    state.timer.endAt = Date.now() + (totalSeconds * 1000);
    persistState();
    startTimerLoop();
    updateTimerDisplay();
  }

  function toggleTimer() {
    syncTimerFromClock();

    if (state.timer.running) {
      state.timer.running = false;
      state.timer.endAt = null;
      stopTimerLoop();
    } else {
      if (state.timer.remaining <= 0) state.timer.remaining = totalSeconds;
      state.timer.running = true;
      state.timer.endAt = Date.now() + (state.timer.remaining * 1000);
      startTimerLoop();
    }

    persistState();
    updateTimerDisplay();
  }

  function resetTimer() {
    state.timer.remaining = totalSeconds;
    state.timer.running = false;
    state.timer.endAt = null;
    stopTimerLoop();
    persistState();
    updateTimerDisplay();
  }

  function markdownValue(value) {
    return value && value.trim() ? value.trim() : "（尚未填寫）";
  }

  function buildMarkdown() {
    syncTimerFromClock();
    const selected = stationById(state.selectedProject);
    const now = new Date();
    const lines = [
      `# ${manifest.courseTitle}｜學習紀錄`,
      "",
      `- 匯出時間：${now.toLocaleString("zh-TW", { hour12: false })}`,
      `- 小組／姓名：${markdownValue(state.teamName)}`,
      `- 完整實作案：${selected ? `${selected.sequence}／${selected.shortCode}｜${selected.title}` : "（尚未選擇）"}`,
      `- 計時器：${formatTime(state.timer.remaining)}${state.timer.activeStation ? `（${stationById(state.timer.activeStation).shortCode}）` : ""}`,
      "",
      "## 00｜起飛前檢查",
      ""
    ];

    manifest.preflight.checklist.forEach((item) => {
      lines.push(`- [${state.preflight[item.id] ? "x" : " "}] ${item.label}`);
    });

    lines.push("", "## 四站輪轉進度", "");
    manifest.stations.forEach((station) => {
      lines.push(`### ${station.sequence}／${station.shortCode}｜${station.title}`, "");
      STATION_STEPS.forEach((step) => {
        lines.push(`- [${state.stationProgress[station.id][step.id] ? "x" : " "}] ${step.label}`);
      });
      if (station.scopeNote) lines.push(`- 實作界線：${station.scopeNote}`);
      lines.push(`- CPU 備援：${station.cpuFallback}`, "");
    });

    lines.push("## 迷你實驗卡", "");
    manifest.stations.forEach((station) => {
      const record = state.experiments[station.id];
      const hasContent = Object.values(record).some((value) => value.trim());
      if (!hasContent && station.id !== state.selectedProject && station.id !== activeExperimentStation) return;

      lines.push(
        `### ${station.sequence}／${station.shortCode}｜${station.title}`,
        "",
        `- **我修改了：** ${markdownValue(record.changed)}`,
        `- **原本結果：** ${markdownValue(record.beforeResult)}`,
        `- **修改後結果：** ${markdownValue(record.afterResult)}`,
        `- **可能原因：** ${markdownValue(record.reason)}`,
        `- **目前最大的失敗情境：** ${markdownValue(record.failure)}`,
        `- **下一步與人工介入規則：** ${markdownValue(record.nextStep)}`,
        ""
      );
    });

    lines.push(
      "## 最後提醒",
      "",
      "> 模型在哪些情況不能被信任？請用測試證據回答，而不是只報最高分數。",
      ""
    );

    return lines.join("\n");
  }

  function safeFilenamePart(value) {
    const cleaned = String(value || "student")
      .trim()
      .replace(/[\\/:*?"<>|\s]+/g, "-")
      .replace(/^-+|-+$/g, "");
    return cleaned || "student";
  }

  function downloadMarkdown() {
    const markdown = buildMarkdown();
    const date = new Date();
    const stamp = [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
      "-",
      String(date.getHours()).padStart(2, "0"),
      String(date.getMinutes()).padStart(2, "0")
    ].join("");
    const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `ai-solution-lab_${safeFilenamePart(state.teamName)}_${stamp}.md`;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    $("#save-state").dataset.saved = "true";
    $("#save-state").innerHTML = '<i aria-hidden="true"></i> Markdown 已下載';
  }

  async function copySummary() {
    const text = buildMarkdown();
    let copied = false;

    try {
      await navigator.clipboard.writeText(text);
      copied = true;
    } catch (error) {
      const helper = document.createElement("textarea");
      helper.value = text;
      helper.setAttribute("readonly", "");
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.append(helper);
      helper.select();
      copied = document.execCommand("copy");
      helper.remove();
    }

    const button = $("#copy-summary");
    const original = "複製摘要";
    button.textContent = copied ? "已複製" : "無法複製，請下載";
    window.setTimeout(() => { button.textContent = original; }, 1800);
  }

  function openResetDialog() {
    const dialog = $("#reset-dialog");
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
      return;
    }

    if (window.confirm("確定清除所有本機紀錄？此動作無法復原。")) {
      resetAllData();
    }
  }

  function resetAllData() {
    stopTimerLoop();
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      // The in-memory reset below still works when localStorage is unavailable.
    }
    state = createDefaultState();
    window.location.reload();
  }

  function bindStaticEvents() {
    $("#experiment-form").addEventListener("input", scheduleExperimentSave);
    $("#timer-toggle").addEventListener("click", toggleTimer);
    $("#timer-reset").addEventListener("click", resetTimer);
    $("#download-markdown").addEventListener("click", downloadMarkdown);
    $("#copy-summary").addEventListener("click", copySummary);
    $("#open-reset-dialog").addEventListener("click", openResetDialog);
    $("#confirm-reset").addEventListener("click", (event) => {
      event.preventDefault();
      resetAllData();
    });

    const headerTimer = $("#header-timer");
    if (headerTimer) {
      headerTimer.addEventListener("click", () => {
        $(".timer-console").scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) updateTimerDisplay();
    });
  }

  function initialize() {
    renderManifestMeta();
    renderPreflight();
    renderRhythm();
    renderStations();
    renderProjectChoices();
    renderExperimentStationOptions();
    bindStaticEvents();
    updateProgressDisplay();
    updateTimerDisplay();
    setSaveState("loaded");

    if (state.timer.running) startTimerLoop();
  }

  initialize();
}());
