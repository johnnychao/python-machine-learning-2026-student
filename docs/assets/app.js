(function () {
  "use strict";

  document.documentElement.classList.add("js");

  const manifest = window.COURSE_MANIFEST;
  const assetBase = document.body.dataset.assetBase || "";
  const actRoman = ["I", "II", "III", "IV"];
  const actChinese = ["一", "二", "三", "四"];

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function assetUrl(value) {
    const path = String(value);
    return /^(?:https?:|data:|\/)/.test(path) ? path : `${assetBase}${path}`;
  }

  function storyTemplate(story, index) {
    const evidence = story.evidence
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");
    const roman = actRoman[index] || String(index + 1);
    const chinese = actChinese[index] || String(index + 1);
    const titleId = `story-${escapeHtml(story.id)}-title`;

    return `
      <article class="story-card reveal" id="story-${escapeHtml(story.id)}" aria-labelledby="${titleId}" data-sequence="${escapeHtml(story.sequence)}" data-act="ACT ${roman}" style="--story-accent: ${escapeHtml(story.accent)}">
        <figure class="story-figure">
          <div class="story-scene-meta" aria-hidden="true"><span>ACT ${roman}</span><span>SCENE ${escapeHtml(story.sequence)}</span></div>
          <img src="${escapeHtml(assetUrl(story.image))}" alt="${escapeHtml(story.imageAlt)}" width="960" height="720" loading="lazy">
          <figcaption><span>場景字幕</span>${escapeHtml(story.sceneCaption)}</figcaption>
        </figure>
        <div class="story-copy">
          <p class="chapter-label"><span>第 ${chinese} 幕</span><span aria-hidden="true">／</span>${escapeHtml(story.model)}</p>
          <h3 id="${titleId}">${escapeHtml(story.title)}</h3>
          <p class="story-lede"><strong>委託人：</strong>${escapeHtml(story.client)}<br>${escapeHtml(story.story)}</p>
          <p class="story-mission"><strong>本幕任務</strong>${escapeHtml(story.mission)}</p>
          <ul class="evidence-list" aria-label="完成本幕後要留下的證據">${evidence}</ul>
          <p class="data-note"><strong>判讀焦點：</strong>${escapeHtml(story.learningFocus)}<br><strong>題目出處：</strong>${escapeHtml(story.dataSource.name)}。${escapeHtml(story.dataSource.note)}</p>
          <div class="story-actions">
            <a class="button button--primary" href="${escapeHtml(story.links.colab)}" target="_blank" rel="noopener noreferrer">進入 Colab，開始這一幕 <span aria-hidden="true">↗</span></a>
            <span class="secondary-links">
              <a class="origin-link" href="${escapeHtml(story.dataSource.kaggleUrl)}" target="_blank" rel="noopener noreferrer">查看 Kaggle 題目出處 <span aria-hidden="true">↗</span></a>
              <a class="origin-link" href="${escapeHtml(story.links.local)}" download>下載 Notebook</a>
              <small>資料由 Colab 直接載入；查看出處不是實作必要步驟。</small>
            </span>
          </div>
        </div>
      </article>`;
  }

  function renderCourse() {
    if (!manifest || !Array.isArray(manifest.stories)) {
      const storyList = document.querySelector("#story-list");
      if (storyList) {
        storyList.innerHTML = "<p>教材資料暫時無法載入，請重新整理頁面或從 GitHub 開啟 Notebook。</p>";
      }
      return;
    }

    document.title = `${manifest.courseTitle}｜恩恩統計家教`;

    const subtitle = document.querySelector("#course-subtitle");
    if (subtitle) subtitle.textContent = manifest.courseSubtitle;

    const repoLink = document.querySelector("#repo-link");
    if (repoLink) repoLink.href = manifest.repo.url;

    const preflightColab = document.querySelector("#preflight-colab");
    const preflightLocal = document.querySelector("#preflight-local");
    if (preflightColab) preflightColab.href = manifest.preflight.links.colab;
    if (preflightLocal) preflightLocal.href = manifest.preflight.links.local;

    const storyList = document.querySelector("#story-list");
    if (storyList) storyList.innerHTML = manifest.stories.map(storyTemplate).join("");
  }

  function bindPageNavigation() {
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const inPageLinks = document.querySelectorAll('a[href^="#"]');

    inPageLinks.forEach((link) => {
      link.addEventListener("click", (event) => {
        const target = document.querySelector(link.getAttribute("href"));
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({ behavior: reducedMotionQuery.matches ? "auto" : "smooth", block: "start" });
      });
    });

    if (!("IntersectionObserver" in window)) return;

    const navLinks = Array.from(document.querySelectorAll('.main-nav a[href^="#"]'));
    const sections = navLinks
      .map((link) => document.querySelector(link.getAttribute("href")))
      .filter(Boolean);

    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;

      navLinks.forEach((link) => {
        const isCurrent = link.getAttribute("href") === `#${visible.target.id}`;
        if (isCurrent) link.setAttribute("aria-current", "true");
        else link.removeAttribute("aria-current");
      });
    }, { rootMargin: "-24% 0px -56%", threshold: [0, 0.2, 0.5] });

    sections.forEach((section) => observer.observe(section));
  }

  function bindSceneReveals() {
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const items = Array.from(document.querySelectorAll(".reveal"));

    function showAll() {
      items.forEach((item) => item.classList.add("is-visible"));
    }

    if (reducedMotionQuery.matches || !("IntersectionObserver" in window)) {
      showAll();
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting && entry.boundingClientRect.top >= 0) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -10%", threshold: 0.12 });

    items.forEach((item) => observer.observe(item));
    reducedMotionQuery.addEventListener("change", (event) => {
      if (event.matches) showAll();
    });
  }

  function bindFilmProgress() {
    const progress = document.querySelector("#film-progress-bar");
    if (!progress) return;

    let pending = false;

    function update() {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      const ratio = scrollable > 0 ? Math.min(Math.max(window.scrollY / scrollable, 0), 1) : 0;
      progress.style.transform = `scaleX(${ratio})`;
      pending = false;
    }

    window.addEventListener("scroll", () => {
      if (pending) return;
      pending = true;
      window.requestAnimationFrame(update);
    }, { passive: true });

    update();
  }

  function setCurrentYear() {
    const year = document.querySelector("#current-year");
    if (year) year.textContent = String(new Date().getFullYear());
  }

  renderCourse();
  bindPageNavigation();
  bindSceneReveals();
  bindFilmProgress();
  setCurrentYear();
}());
