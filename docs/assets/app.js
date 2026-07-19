(function () {
  "use strict";

  const manifest = window.COURSE_MANIFEST;

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function storyTemplate(story) {
    const evidence = story.evidence
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");

    return `
      <article class="story-card" id="story-${escapeHtml(story.id)}" data-sequence="${escapeHtml(story.sequence)}" style="--story-accent: ${escapeHtml(story.accent)}">
        <figure class="story-figure">
          <img src="${escapeHtml(story.image)}" alt="${escapeHtml(story.imageAlt)}" width="960" height="720" loading="lazy">
          <figcaption>${escapeHtml(story.sceneCaption)}</figcaption>
        </figure>
        <div class="story-copy">
          <p class="chapter-label"><span>故事 ${escapeHtml(story.sequence)}</span><span aria-hidden="true">・</span>${escapeHtml(story.model)}</p>
          <h3>${escapeHtml(story.title)}</h3>
          <p class="story-lede"><strong>誰需要幫忙：</strong>${escapeHtml(story.client)}<br>${escapeHtml(story.story)}</p>
          <p class="story-mission"><strong>這一回合要做什麼？</strong>${escapeHtml(story.mission)}</p>
          <ul class="evidence-list" aria-label="完成故事後要留下的證據">${evidence}</ul>
          <p class="data-note"><strong>練習重點：</strong>${escapeHtml(story.learningFocus)}<br><strong>題目出處：</strong>${escapeHtml(story.dataSource.name)}。${escapeHtml(story.dataSource.note)}</p>
          <div class="story-actions">
            <a class="button button--primary" href="${escapeHtml(story.links.colab)}" target="_blank" rel="noopener noreferrer">打開 Colab，開始故事 <span aria-hidden="true">↗</span></a>
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
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const inPageLinks = document.querySelectorAll('a[href^="#"]');

    inPageLinks.forEach((link) => {
      link.addEventListener("click", (event) => {
        const target = document.querySelector(link.getAttribute("href"));
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      });
    });

    if (!("IntersectionObserver" in window)) return;

    const navLinks = Array.from(document.querySelectorAll(".main-nav a"));
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
    }, { rootMargin: "-25% 0px -55%", threshold: [0, 0.2, 0.5] });

    sections.forEach((section) => observer.observe(section));
  }

  function setCurrentYear() {
    const year = document.querySelector("#current-year");
    if (year) year.textContent = String(new Date().getFullYear());
  }

  renderCourse();
  bindPageNavigation();
  setCurrentYear();
}());
