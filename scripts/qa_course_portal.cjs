const fs = require("node:fs");
const path = require("node:path");

const requestedBaseUrl = process.argv[2] || "http://127.0.0.1:8765/";
const playwrightModule = process.argv[3] || "playwright";
const { chromium } = require(playwrightModule);

function normalizeSiteRoot(value) {
  const url = new URL(value);
  url.hash = "";
  url.search = "";
  if (!url.pathname.endsWith("/")) url.pathname += "/";
  return url.href;
}

const siteRoot = normalizeSiteRoot(requestedBaseUrl);
const siteRootUrl = new URL(siteRoot);
const repoRoot = path.resolve(__dirname, "..");
const outputDir = path.join(repoRoot, "output", "playwright");
fs.mkdirSync(outputDir, { recursive: true });

const repoSlug = "johnnychao/python-machine-learning-2026-student";
const routeSpecs = [
  { route: "", kind: "home", chapters: 0, notebooks: 0 },
  { route: "day-1/", kind: "day", chapters: 3, notebooks: 3 },
  { route: "day-2/", kind: "day", chapters: 3, notebooks: 3 },
  { route: "day-3/", kind: "day", chapters: 3, notebooks: 3 },
  { route: "day-4/", kind: "day", chapters: 3, notebooks: 3 },
  { route: "day-5/", kind: "day", chapters: 3, notebooks: 9 },
  { route: "extension/", kind: "extension", chapters: 3, notebooks: 5 },
];

const notebookFiles = [
  ...Array.from({ length: 12 }, (_, index) => `ch${String(index + 1).padStart(2, "0")}_ch${String(index + 1).padStart(2, "0")}_colab.ipynb`),
  "ch13_ch13_part1_colab.ipynb",
  "ch13_ch13_part2_colab.ipynb",
  "ch13_ch13_part3_colab.ipynb",
  "ch14_ch14_part1_colab.ipynb",
  "ch14_ch14_part2_colab.ipynb",
  "ch14_ch14_part3_colab.ipynb",
  "ch15_ch15_part1_colab.ipynb",
  "ch15_ch15_part2_colab.ipynb",
  "ch15_downloading-celeba_downloading-celeba_colab.ipynb",
  "ch16_ch16_part1_colab.ipynb",
  "ch16_ch16_part2_colab.ipynb",
  "ch17_ch17_part1_colab.ipynb",
  "ch17_ch17_part2_colab.ipynb",
  "ch18_ch18_colab.ipynb",
];
const expectedColabHrefs = notebookFiles.map(
  (file) => `https://colab.research.google.com/github/${repoSlug}/blob/main/notebooks/colab_ready/${file}`,
);
const expectedHandoutHrefs = Array.from(
  { length: 18 },
  (_, index) => new URL(`handouts/ch${String(index + 1).padStart(2, "0")}.pdf`, siteRoot).href,
);
const expectedPortalRouteHrefs = [
  siteRoot,
  ...Array.from({ length: 5 }, (_, index) => new URL(`day-${index + 1}/`, siteRoot).href),
  new URL("extension/", siteRoot).href,
  new URL("practicum/", siteRoot).href,
];
const prohibitedFontPattern = /DFKai-SB|BiauKai|KaiTi|標楷體/i;
const day6Pattern = /\bday[\s_-]*0?6\b|\bd6\b/i;
const checks = [];

function check(name, passed, detail) {
  checks.push({ name, status: passed ? "pass" : "fail", detail });
}

function routeUrl(route) {
  return new URL(route.replace(/^\/+/, ""), siteRoot).href;
}

function isInternal(urlValue) {
  const url = new URL(urlValue);
  return url.origin === siteRootUrl.origin && url.pathname.startsWith(siteRootUrl.pathname);
}

function withoutFragment(urlValue) {
  const url = new URL(urlValue);
  url.hash = "";
  return url.href;
}

async function inspectViewport(browser, label, viewport) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const badResponses = [];
  const requestFailures = [];
  const internalHrefs = new Set();
  const routeResults = [];
  const allColabHrefs = [];
  const allHandoutHrefs = [];

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => requestFailures.push(`${request.failure()?.errorText || "failed"} ${request.url()}`));
  page.on("response", (response) => {
    if (isInternal(response.url()) && response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  for (const spec of routeSpecs) {
    const url = routeUrl(spec.route);
    const response = await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForSelector('[data-testid="portal-page"]');
    if (spec.kind === "home") {
      await page.waitForSelector('[data-testid="day-card"]:nth-of-type(5)');
    } else {
      await page.waitForSelector('[data-testid="chapter-card"]:nth-of-type(3)');
    }
    const images = page.locator("img");
    for (let index = 0; index < await images.count(); index += 1) {
      const image = images.nth(index);
      await image.scrollIntoViewIfNeeded();
      await image.evaluate((element) => element.decode().catch(() => undefined));
    }
    await page.keyboard.press("Home");

    const state = await page.evaluate(() => {
      const chapterCards = Array.from(document.querySelectorAll('[data-testid="chapter-card"]'));
      const dayCards = Array.from(document.querySelectorAll('[data-testid="day-card"]'));
      const colabLinks = Array.from(document.querySelectorAll('[data-testid="colab-link"]'), (link) => link.href);
      const handoutLinks = Array.from(document.querySelectorAll('[data-testid="handout-link"]'), (link) => link.href);
      const practicumLinks = Array.from(document.querySelectorAll('[data-testid="practicum-link"]'), (link) => link.href);
      const internalCandidates = Array.from(document.querySelectorAll("a[href]"), (link) => link.href);
      const visibleOverflow = Array.from(document.body.querySelectorAll("*"))
        .filter((element) => {
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden" && rect.width > 1 && rect.height > 1;
        })
        .filter((element) => {
          const rect = element.getBoundingClientRect();
          const clippedByContainer = (() => {
            let parent = element.parentElement;
            while (parent && parent !== document.body) {
              const overflowX = getComputedStyle(parent).overflowX;
              if (["auto", "scroll", "hidden", "clip"].includes(overflowX)) return true;
              parent = parent.parentElement;
            }
            return false;
          })();
          return !clippedByContainer && (rect.left < -1 || rect.right > window.innerWidth + 1);
        })
        .slice(0, 12)
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return `${element.tagName}.${element.className || ""}:${rect.left.toFixed(1)}..${rect.right.toFixed(1)}`;
        });
      const tapTargets = Array.from(
        document.querySelectorAll(
          '[data-testid="day-card"]:is(a, button), [data-testid="day-card"] a, '
          + '[data-testid="colab-link"], [data-testid="handout-link"], '
          + '[data-testid="practicum-link"], button',
        ),
        (element) => {
          const rect = element.getBoundingClientRect();
          return { text: element.textContent.trim().slice(0, 36), width: rect.width, height: rect.height };
        },
      );
      const images = Array.from(document.images, (image) => ({
        src: image.src,
        complete: image.complete,
        naturalWidth: image.naturalWidth,
        naturalHeight: image.naturalHeight,
      }));
      const fontFamilies = [document.body, document.querySelector("h1"), ...document.querySelectorAll("h2, h3")]
        .filter(Boolean)
        .map((element) => getComputedStyle(element).fontFamily);
      return {
        title: document.title,
        h1: document.querySelector("h1")?.innerText.trim() || "",
        bodyText: document.body.innerText,
        dayCards: dayCards.length,
        chapterCards: chapterCards.length,
        chapterNumbers: chapterCards.map((card) => Number(card.dataset.chapter || card.getAttribute("data-chapter"))),
        colabLinks,
        handoutLinks,
        practicumLinks,
        internalCandidates,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        visibleOverflow,
        tapTargets,
        images,
        fontFamilies,
      };
    });

    for (const href of state.internalCandidates) {
      if (isInternal(href)) internalHrefs.add(withoutFragment(href));
    }
    allColabHrefs.push(...state.colabLinks);
    allHandoutHrefs.push(...state.handoutLinks.map(withoutFragment));
    routeResults.push({ route: spec.route || "/", url, ...state });

    check(`${label}:${spec.route || "home"}:http`, Boolean(response?.ok()), response ? `${response.status()} ${response.url()}` : "no response");
    check(`${label}:${spec.route || "home"}:heading`, Boolean(state.title && state.h1), JSON.stringify({ title: state.title, h1: state.h1 }));
    check(`${label}:${spec.route || "home"}:chapter_count`, state.chapterCards === spec.chapters, `expected=${spec.chapters}; actual=${state.chapterCards}`);
    check(`${label}:${spec.route || "home"}:notebook_count`, state.colabLinks.length === spec.notebooks, `expected=${spec.notebooks}; actual=${state.colabLinks.length}`);
    check(`${label}:${spec.route || "home"}:no_day_6`, !day6Pattern.test(state.bodyText), "visible text checked");
    check(`${label}:${spec.route || "home"}:no_horizontal_overflow`, state.scrollWidth <= state.clientWidth && state.visibleOverflow.length === 0, JSON.stringify({ root: `${state.scrollWidth}/${state.clientWidth}`, elements: state.visibleOverflow }));
    check(`${label}:${spec.route || "home"}:tap_targets`, state.tapTargets.every((target) => target.height >= 43.5), JSON.stringify(state.tapTargets));
    check(`${label}:${spec.route || "home"}:images_loaded`, state.images.every((image) => image.complete && image.naturalWidth > 0), JSON.stringify(state.images));
    check(`${label}:${spec.route || "home"}:no_prohibited_font`, state.fontFamilies.every((family) => !prohibitedFontPattern.test(family)), JSON.stringify(state.fontFamilies));

    if (spec.kind === "home") {
      check(`${label}:home:five_day_cards`, state.dayCards === 5, `dayCards=${state.dayCards}`);
      check(`${label}:home:practicum_route`, state.practicumLinks.some((href) => withoutFragment(href) === routeUrl("practicum/")), JSON.stringify(state.practicumLinks));
    }

    if (spec.route === "") {
      await page.screenshot({ path: path.join(outputDir, `course-portal-${label}.png`), fullPage: true });
    }
  }

  check(
    `${label}:eighteen_chapters`,
    routeResults.reduce((total, item) => total + item.chapterCards, 0) === 18,
    JSON.stringify(routeResults.map((item) => ({ route: item.route, chapters: item.chapterCards }))),
  );
  check(
    `${label}:eighteen_handout_links`,
    JSON.stringify(allHandoutHrefs) === JSON.stringify(expectedHandoutHrefs) && new Set(allHandoutHrefs).size === 18,
    `count=${allHandoutHrefs.length}; unique=${new Set(allHandoutHrefs).size}`,
  );
  check(
    `${label}:twenty_six_colab_links`,
    JSON.stringify(allColabHrefs) === JSON.stringify(expectedColabHrefs) && new Set(allColabHrefs).size === 26,
    `count=${allColabHrefs.length}; unique=${new Set(allColabHrefs).size}`,
  );

  const internalResults = [];
  for (const href of [...internalHrefs].sort()) {
    const response = await context.request.get(href, { failOnStatusCode: false });
    internalResults.push({ href, status: response.status(), ok: response.ok() });
  }
  const routeCoverage = expectedPortalRouteHrefs.every((href) => internalHrefs.has(href));
  const pdfCoverage = expectedHandoutHrefs.every((href) => internalHrefs.has(href));
  check(`${label}:internal_route_coverage`, routeCoverage, JSON.stringify(expectedPortalRouteHrefs.filter((href) => !internalHrefs.has(href))));
  check(`${label}:internal_handout_coverage`, pdfCoverage, JSON.stringify(expectedHandoutHrefs.filter((href) => !internalHrefs.has(href))));
  check(`${label}:internal_links_http`, internalResults.length >= 26 && internalResults.every((item) => item.ok), JSON.stringify(internalResults.filter((item) => !item.ok)));
  check(`${label}:console`, consoleErrors.length === 0 && pageErrors.length === 0, JSON.stringify({ consoleErrors, pageErrors }));
  check(`${label}:network`, badResponses.length === 0 && requestFailures.length === 0, JSON.stringify({ badResponses, requestFailures }));

  await context.close();
  return {
    label,
    viewport,
    routes: routeResults.map((item) => ({ route: item.route, url: item.url, title: item.title, h1: item.h1 })),
    internalLinks: internalResults.length,
  };
}

async function inspectKeyboard(browser) {
  const context = await browser.newContext({ viewport: { width: 1024, height: 768 } });
  const page = await context.newPage();
  await page.goto(siteRoot, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="portal-page"]');

  await page.keyboard.press("Tab");
  const firstFocus = await page.evaluate(() => ({
    className: document.activeElement?.className || "",
    testId: document.activeElement?.getAttribute("data-testid") || "",
    text: document.activeElement?.textContent?.trim() || "",
  }));
  const skipFocused = firstFocus.className.split(/\s+/).includes("skip-link") || firstFocus.testId === "skip-link";

  let dayCardFocus = null;
  for (let index = 0; index < 60; index += 1) {
    const focused = await page.evaluate(() => {
      const active = document.activeElement;
      const card = active?.closest?.('[data-testid="day-card"]');
      if (!active || !card) return null;
      const style = getComputedStyle(active);
      return {
        href: active.href || "",
        outlineStyle: style.outlineStyle,
        outlineWidth: style.outlineWidth,
        boxShadow: style.boxShadow,
      };
    });
    if (focused) {
      dayCardFocus = focused;
      break;
    }
    await page.keyboard.press("Tab");
  }

  let enteredDayOne = false;
  if (dayCardFocus) {
    await Promise.all([
      page.waitForURL((url) => url.href === routeUrl("day-1/")),
      page.keyboard.press("Enter"),
    ]);
    await page.waitForSelector('[data-testid="chapter-card"]');
    enteredDayOne = page.url() === routeUrl("day-1/");
  }

  let colabFocus = null;
  if (enteredDayOne) {
    for (let index = 0; index < 80; index += 1) {
      colabFocus = await page.evaluate(() => {
        const active = document.activeElement;
        if (active?.getAttribute("data-testid") !== "colab-link") return null;
        const style = getComputedStyle(active);
        return {
          href: active.href,
          outlineStyle: style.outlineStyle,
          outlineWidth: style.outlineWidth,
          boxShadow: style.boxShadow,
        };
      });
      if (colabFocus) break;
      await page.keyboard.press("Tab");
    }
  }

  const hasVisibleFocus = (state) => Boolean(
    state
      && ((state.outlineStyle !== "none" && state.outlineWidth !== "0px")
        || (state.boxShadow && state.boxShadow !== "none")),
  );
  check("keyboard:skip_link_first", skipFocused, JSON.stringify(firstFocus));
  check("keyboard:day_card_enter", enteredDayOne && hasVisibleFocus(dayCardFocus), JSON.stringify(dayCardFocus));
  check("keyboard:colab_link_reachable", Boolean(colabFocus?.href && expectedColabHrefs.includes(colabFocus.href) && hasVisibleFocus(colabFocus)), JSON.stringify(colabFocus));
  await context.close();
}

async function inspectReducedMotion(browser) {
  const context = await browser.newContext({
    viewport: { width: 1024, height: 768 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.goto(siteRoot, { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="portal-page"]');
  const state = await page.evaluate(() => {
    const animated = Array.from(document.querySelectorAll("*"))
      .map((element) => {
        const style = getComputedStyle(element);
        return {
          tag: element.tagName,
          className: element.className || "",
          name: style.animationName,
          duration: style.animationDuration,
        };
      })
      .filter((item) => item.name !== "none" && !item.duration.split(",").every((value) => Number.parseFloat(value) === 0))
      .slice(0, 12);
    return {
      mediaMatches: matchMedia("(prefers-reduced-motion: reduce)").matches,
      scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
      animated,
    };
  });
  check(
    "reduced_motion",
    state.mediaMatches && state.scrollBehavior === "auto" && state.animated.length === 0,
    JSON.stringify(state),
  );
  await context.close();
}

async function main() {
  const browser = await chromium.launch({ headless: true, args: ["--disable-gpu"] });
  try {
    const viewports = [];
    viewports.push(await inspectViewport(browser, "desktop", { width: 1440, height: 1000 }));
    viewports.push(await inspectViewport(browser, "mobile-360", { width: 360, height: 800 }));
    await inspectKeyboard(browser);
    await inspectReducedMotion(browser);

    const failed = checks.filter((item) => item.status === "fail");
    const report = {
      generatedAt: new Date().toISOString(),
      siteRoot,
      viewports,
      summary: { total: checks.length, passed: checks.length - failed.length, failed: failed.length },
      checks,
    };
    fs.writeFileSync(path.join(outputDir, "course-portal-qa-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(report.summary));
    if (failed.length) {
      console.error(JSON.stringify(failed, null, 2));
      process.exitCode = 1;
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
