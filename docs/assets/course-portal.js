(function () {
  "use strict";

  document.documentElement.classList.add("js");

  const body = document.body;
  const pageId = body.dataset.page || "home";
  const siteRoot = body.dataset.siteRoot || "";
  const catalogUrl = body.dataset.catalogUrl || `${siteRoot}assets/course-catalog.json`;
  const content = document.querySelector("#portal-content");

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function localUrl(path) {
    return `${siteRoot}${path}`;
  }

  function chapterRange(chapters) {
    if (!chapters.length) return "";
    const first = String(chapters[0].number).padStart(2, "0");
    const last = String(chapters.at(-1).number).padStart(2, "0");
    return `CH ${first}–${last}`;
  }

  function renderFilmMarks() {
    return '<span class="film-holes film-holes--top" aria-hidden="true"></span><span class="film-holes film-holes--bottom" aria-hidden="true"></span>';
  }

  function dayCard(day, index) {
    const chapterLabels = day.chapters
      .map((chapter) => `<span>Ch${String(chapter.number).padStart(2, "0")}</span>`)
      .join("");

    return `
      <a class="day-card" data-testid="day-card" href="${escapeHtml(localUrl(day.route))}" style="--day-accent:${escapeHtml(day.accent)}" aria-label="${escapeHtml(day.label)}：${escapeHtml(day.title)}">
        ${renderFilmMarks()}
        <span class="reel-number" aria-hidden="true">0${index + 1}</span>
        <span class="day-card__meta"><b>${escapeHtml(day.reel)}</b><span>${escapeHtml(chapterRange(day.chapters))}</span></span>
        <strong>${escapeHtml(day.title)}</strong>
        <p>${escapeHtml(day.summary)}</p>
        <span class="chapter-chips" aria-label="本日章節">${chapterLabels}</span>
        <span class="day-card__cta">打開這卷課程 <i aria-hidden="true">→</i></span>
      </a>`;
  }

  function renderHome(catalog) {
    const dayCards = catalog.days.map(dayCard).join("");
    const firstDay = catalog.days[0];
    const extension = catalog.extension;

    return `
      <section class="portal-hero" aria-labelledby="page-title">
        <div class="portal-hero__copy">
          <p class="portal-kicker"><span>ENEN STATISTICS</span>・STUDENT SCREENING ROOM</p>
          <h1 id="page-title">把十八章，<br><em>走成一條會前進的路。</em></h1>
          <p class="portal-lede">這裡是五日課程的學生公開入口。每天打開一卷主題，先讀講義、再進 Colab；第五日最後，以四幕故事完成 AI 解決方案綜合實作。</p>
          <div class="portal-actions">
            <a class="portal-button portal-button--primary" href="${escapeHtml(localUrl(firstDay.route))}">從 Day 1 開始 <span aria-hidden="true">→</span></a>
            <a class="portal-button portal-button--ghost" data-testid="practicum-link" href="${escapeHtml(localUrl(catalog.practicum.route))}">前往綜合實作</a>
          </div>
          <dl class="course-stats" aria-label="課程教材數量">
            <div><dt>五日</dt><dd>課程主線</dd></div>
            <div><dt>${escapeHtml(catalog.course.chapterCount)}</dt><dd>章學生講義</dd></div>
            <div><dt>${escapeHtml(catalog.course.notebookCount)}</dt><dd>份 Colab</dd></div>
          </dl>
        </div>
        <aside class="admission-ticket" aria-label="Colab 入場提醒">
          <span class="ticket-code">ADMIT ONE・2026</span>
          <img src="${escapeHtml(localUrl("assets/brand/teacher-check.webp"))}" alt="恩恩老師拿著課前檢查表" width="220" height="220">
          <h2>帶著 Google 帳號，就能入場</h2>
          <ol>
            <li>點開當章 Colab</li>
            <li>先儲存自己的副本</li>
            <li>從第一格依序執行</li>
          </ol>
          <p>Kaggle 只標示題目出處，不需要登入，也不需要 API Token。</p>
        </aside>
      </section>

      <section class="five-days" id="five-days" aria-labelledby="five-days-title">
        <div class="portal-heading">
          <p class="portal-kicker">NOW SHOWING・五卷學習主線</p>
          <h2 id="five-days-title">一天一卷，逐步把模型變成解決方案</h2>
          <p>Day 1–4 建立資料與模型能力；Day 5 進入深度學習，並以綜合實作收束五日主線。</p>
        </div>
        <div class="day-grid">${dayCards}</div>
      </section>

      <section class="feature-marquee" aria-labelledby="feature-title">
        <figure>
          <img src="${escapeHtml(localUrl("assets/illustrations/cover-ai-story-lab.webp"))}" alt="恩恩老師帶著學生走進四個 AI 任務世界" width="1200" height="900" loading="lazy">
          <figcaption>FINAL ACT・五日課程壓軸</figcaption>
        </figure>
        <div>
          <p class="portal-kicker">AI SOLUTION PRACTICUM</p>
          <h2 id="feature-title">模型學過了，接下來換你選擇證據</h2>
          <p>${escapeHtml(catalog.practicum.summary)}</p>
          <ul class="feature-beats"><li>CNN 毛孩照片</li><li>RNN 訊息分流</li><li>風格轉換畫室</li><li>RL 棋盤策略</li></ul>
          <a class="portal-button portal-button--primary" data-testid="practicum-link" href="${escapeHtml(localUrl(catalog.practicum.route))}">進入四幕電影實作 <span aria-hidden="true">→</span></a>
        </div>
      </section>

      <section class="bonus-reel" aria-labelledby="bonus-title" style="--day-accent:${escapeHtml(extension.accent)}">
        ${renderFilmMarks()}
        <div><p class="portal-kicker">${escapeHtml(extension.label)}・${escapeHtml(extension.reel)}</p><h2 id="bonus-title">${escapeHtml(extension.title)}</h2><p>${escapeHtml(extension.summary)}</p></div>
        <a class="portal-button portal-button--ghost" href="${escapeHtml(localUrl(extension.route))}">打開課後延伸 <span aria-hidden="true">→</span></a>
      </section>

      <aside class="teacher-whisper" aria-label="恩恩老師提醒">
        <img src="${escapeHtml(localUrl("assets/brand/enen-teacher.webp"))}" alt="恩恩老師" width="120" height="120" loading="lazy">
        <p><span>恩恩老師的小提醒</span><strong>不用一次跑完所有 Notebook。</strong>先抓住今天要回答的問題，再讓程式和指標幫你找證據。</p>
      </aside>`;
  }

  function notebookLink(notebook) {
    return `<a class="notebook-link" data-testid="colab-link" data-notebook-path="${escapeHtml(notebook.path)}" href="${escapeHtml(notebook.colab)}" target="_blank" rel="noopener noreferrer"><span>${escapeHtml(notebook.label)}</span><b>開啟 Colab <i aria-hidden="true">↗</i></b></a>`;
  }

  function chapterCard(chapter) {
    const number = String(chapter.number).padStart(2, "0");
    const notebooks = chapter.notebooks.map(notebookLink).join("");

    return `
      <article class="chapter-card" data-testid="chapter-card" data-chapter="${escapeHtml(chapter.id)}" aria-labelledby="${escapeHtml(chapter.id)}-title">
        <div class="chapter-card__number" aria-hidden="true"><span>CH</span>${number}</div>
        <div class="chapter-card__body">
          <p class="chapter-card__label">CHAPTER ${number}</p>
          <h2 id="${escapeHtml(chapter.id)}-title">${escapeHtml(chapter.title)}</h2>
          <p class="chapter-outcome"><strong>完成後，你可以：</strong>${escapeHtml(chapter.outcome)}</p>
          <ul class="compute-tags" aria-label="執行條件"><li>${escapeHtml(chapter.compute.runtime)}</li><li>${escapeHtml(chapter.compute.duration)}</li><li>${escapeHtml(chapter.compute.mode)}</li></ul>
        </div>
        <div class="chapter-card__resources">
          <a class="handout-link" data-testid="handout-link" href="${escapeHtml(localUrl(chapter.handout))}" target="_blank" rel="noopener noreferrer"><span>學生講義</span><b>閱讀 PDF <i aria-hidden="true">↗</i></b></a>
          ${notebooks}
        </div>
      </article>`;
  }

  function dayNavigation(catalog, current) {
    const pages = [...catalog.days, catalog.extension];
    const index = pages.findIndex((item) => item.id === current.id);
    const previous = pages[index - 1];
    const next = pages[index + 1];
    return `
      <nav class="day-switcher" aria-label="前後課程">
        ${previous ? `<a href="${escapeHtml(localUrl(previous.route))}"><span>上一站</span><b>← ${escapeHtml(previous.label)}</b></a>` : `<a href="${escapeHtml(localUrl(""))}"><span>返回</span><b>← 課程首頁</b></a>`}
        ${next ? `<a href="${escapeHtml(localUrl(next.route))}"><span>下一站</span><b>${escapeHtml(next.label)} →</b></a>` : `<a href="${escapeHtml(localUrl(catalog.practicum.route))}"><span>五日壓軸</span><b>FINAL ACT →</b></a>`}
      </nav>`;
  }

  function renderLearningPage(catalog, current) {
    const isExtension = current.id === "extension";
    const chapters = current.chapters.map(chapterCard).join("");
    const dayLinks = catalog.days
      .map((day) => `<a href="${escapeHtml(localUrl(day.route))}"${day.id === current.id ? ' aria-current="page"' : ""}>${escapeHtml(day.label.replace(" 0", " "))}</a>`)
      .join("");

    return `
      <section class="day-hero${isExtension ? " day-hero--extension" : ""}" style="--day-accent:${escapeHtml(current.accent)}" aria-labelledby="page-title">
        ${renderFilmMarks()}
        <div class="day-hero__copy">
          <p class="portal-kicker">${escapeHtml(current.label)}・${escapeHtml(current.reel)}</p>
          <p class="day-range">${escapeHtml(chapterRange(current.chapters))}</p>
          <h1 id="page-title">${escapeHtml(current.title)}</h1>
          <p>${escapeHtml(current.summary)}</p>
          <ul class="day-promises"><li>${current.chapters.length} 章學生講義</li><li>${current.chapters.reduce((count, chapter) => count + chapter.notebooks.length, 0)} 份 Colab</li><li>資料直接在 Colab 取得</li></ul>
        </div>
        <img src="${escapeHtml(localUrl(isExtension ? "assets/brand/teacher-magnify.webp" : "assets/brand/teacher-cheer.webp"))}" alt="${isExtension ? "恩恩老師拿著放大鏡探索延伸內容" : "恩恩老師為今天的學習加油"}" width="260" height="260">
      </section>

      <nav class="day-tabs" aria-label="五日課程快速切換">${dayLinks}<a href="${escapeHtml(localUrl(catalog.extension.route))}"${isExtension ? ' aria-current="page"' : ""}>課後延伸</a></nav>

      <section class="chapter-section" aria-labelledby="chapter-section-title">
        <div class="portal-heading portal-heading--compact">
          <p class="portal-kicker">TODAY'S PROGRAM</p>
          <h2 id="chapter-section-title">講義先建立地圖，Colab 再留下證據</h2>
          <p>每章先讀學習成果與執行條件。多段 Notebook 已依建議順序展開，不需要登入 Kaggle。</p>
        </div>
        <div class="chapter-list">${chapters}</div>
      </section>

      ${!isExtension && current.id === "day-5" ? `<section class="day-finale"><div><p class="portal-kicker">FINAL ACT・五日壓軸</p><h2>第五日最後，進入四幕綜合實作</h2><p>四站快速體驗後，選一案完成 Baseline、單一變因比較、失敗案例與人工介入說明。</p></div><a class="portal-button portal-button--primary" data-testid="practicum-link" href="${escapeHtml(localUrl(catalog.practicum.route))}">進入綜合實作 <span aria-hidden="true">→</span></a></section>` : ""}

      ${dayNavigation(catalog, current)}`;
  }

  function renderError() {
    if (!content) return;
    content.setAttribute("aria-busy", "false");
    content.innerHTML = `<section class="portal-error"><p class="portal-kicker">入口暫時無法載入</p><h1>課程資料沒有成功開啟</h1><p>請重新整理頁面，或直接前往公開學生 repo。</p><a class="portal-button portal-button--primary" href="https://github.com/johnnychao/python-machine-learning-2026-student">開啟學生教材 repo</a></section>`;
  }

  function redirectLegacyHash() {
    if (pageId !== "home") return false;
    const legacyHashes = new Set(["#ready", "#story-path", "#final-choice"]);
    if (!legacyHashes.has(window.location.hash)) return false;
    window.location.replace(`${localUrl("practicum/")}${window.location.hash}`);
    return true;
  }

  async function start() {
    if (!content || redirectLegacyHash()) return;

    try {
      const response = await fetch(catalogUrl, { cache: "no-cache" });
      if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
      const catalog = await response.json();
      const current = pageId === "extension"
        ? catalog.extension
        : catalog.days.find((day) => day.id === pageId);

      content.innerHTML = pageId === "home"
        ? renderHome(catalog)
        : renderLearningPage(catalog, current);
      content.setAttribute("aria-busy", "false");
      document.documentElement.style.setProperty("--current-accent", current?.accent || "#F39C12");
    } catch (error) {
      console.error(error);
      renderError();
    }
  }

  const year = document.querySelector("#current-year");
  if (year) year.textContent = String(new Date().getFullYear());
  start();
}());
