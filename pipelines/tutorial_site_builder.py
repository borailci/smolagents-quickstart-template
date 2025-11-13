"""Build a lightweight HTML viewer for generated tutorials."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from loguru import logger


class TutorialSiteBuilder:
    def __init__(self, tutorials_root: str | Path) -> None:
        self.tutorials_root = Path(tutorials_root).expanduser().resolve()

    def build(self) -> Path:
        tutorial_files = sorted(self.tutorials_root.glob("*.md"))
        if not tutorial_files:
            raise FileNotFoundError(
                f"No markdown tutorials found in {self.tutorials_root}"
            )

        entries = [self._load_tutorial(path) for path in tutorial_files]
        html = self._render(entries)
        output_path = self.tutorials_root / "index.html"
        output_path.write_text(html, encoding="utf-8")
        logger.info("Wrote tutorial navigation site to {}", output_path)
        return output_path

    def _load_tutorial(self, path: Path) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8")
        title = self._extract_title(content, fallback=path.stem)
        return {"filename": path.name, "title": title, "content": content}

    @staticmethod
    def _extract_title(content: str, fallback: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        pretty = fallback.replace("_", " ").strip().title()
        return pretty or "Untitled Tutorial"

    def _render(self, entries: Sequence[dict[str, Any]]) -> str:
        payload = json.dumps(entries).replace("</", "<\\/")
        return (
            """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Project Tutorials</title>
    <link rel="preconnect" href="https://cdn.jsdelivr.net" />
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
      :root {
        color-scheme: light dark;
        --background: #0f1418;
        --panel: #161b22;
        --text: #f7fafc;
        --link: #5ec7ff;
        --accent: #8fb8ff;
        --border: #1f2933;
        --shadow: rgba(15, 20, 24, 0.4);
        font-family: "Inter", "Segoe UI", system-ui, sans-serif;
      }

      body {
        margin: 0;
        min-height: 100vh;
        display: flex;
        background: var(--background);
        color: var(--text);
      }

      aside {
        width: 320px;
        background: var(--panel);
        border-right: 1px solid var(--border);
        padding: 24px;
        box-sizing: border-box;
        overflow-y: auto;
        box-shadow: 4px 0 16px var(--shadow);
      }

      main {
        flex: 1;
        padding: 32px clamp(32px, 5vw, 64px);
        box-sizing: border-box;
        overflow-y: auto;
      }

      h1 {
        font-size: clamp(1.8rem, 2.4vw, 2.4rem);
        margin-top: 0;
      }

      nav h2 {
        margin: 0 0 12px 0;
        font-size: 1.1rem;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        color: var(--accent);
      }

      ul#tutorial-nav {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      ul#tutorial-nav li {
        margin: 0;
      }

      button.nav-item {
        all: unset;
        width: 100%;
        padding: 12px 14px;
        border-radius: 8px;
        cursor: pointer;
        transition: background 0.2s ease, transform 0.2s ease;
        color: inherit;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border: 1px solid transparent;
      }

      button.nav-item span.index {
        opacity: 0.6;
        font-size: 0.85rem;
        margin-right: 12px;
      }

      button.nav-item span.title {
        flex: 1;
        text-align: left;
      }

      button.nav-item:hover {
        background: rgba(143, 184, 255, 0.12);
        transform: translateX(4px);
        border-color: rgba(143, 184, 255, 0.4);
      }

      button.nav-item.active {
        background: rgba(94, 199, 255, 0.18);
        border-color: rgba(94, 199, 255, 0.7);
        box-shadow: 0 4px 16px rgba(94, 199, 255, 0.25);
      }

      .nav-footer {
        margin-top: 24px;
        display: flex;
        gap: 12px;
      }

      .nav-footer button {
        all: unset;
        flex: 1;
        padding: 10px 12px;
        text-align: center;
        border-radius: 6px;
        cursor: pointer;
        background: rgba(143, 184, 255, 0.12);
        border: 1px solid rgba(143, 184, 255, 0.3);
      }

      .nav-footer button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      article {
        max-width: 900px;
        margin: 0 auto;
      }

      article h2 {
        margin-top: 2.4rem;
      }

      article pre {
        background: rgba(15, 20, 24, 0.9);
        color: #e0f2ff;
        padding: 16px;
        border-radius: 8px;
        overflow-x: auto;
        border: 1px solid rgba(94, 199, 255, 0.15);
      }

      article code {
        font-family: "Fira Code", "SFMono-Regular", "Consolas", monospace;
      }

      article a {
        color: var(--link);
      }

      @media (max-width: 960px) {
        body {
          flex-direction: column;
        }

        aside {
          width: 100%;
          border-right: none;
          border-bottom: 1px solid var(--border);
          box-shadow: none;
        }

        .nav-footer button {
          padding: 14px 12px;
        }
      }
    </style>
  </head>
  <body>
    <aside>
      <nav>
        <h2>Tutorials</h2>
        <ul id="tutorial-nav"></ul>
        <div class="nav-footer">
          <button id="prev-btn" type="button">Previous</button>
          <button id="next-btn" type="button">Next</button>
        </div>
      </nav>
    </aside>
    <main>
      <article>
        <h1 id="tutorial-title">Select a tutorial</h1>
        <div id="tutorial-content">
          <p>Pick a tutorial from the list to view its content.</p>
        </div>
      </article>
    </main>
    <script id="tutorial-data" type="application/json">"""
            + payload
            + """</script>
    <script>
      const tutorials = JSON.parse(document.getElementById("tutorial-data").textContent);
      const navList = document.getElementById("tutorial-nav");
      const titleEl = document.getElementById("tutorial-title");
      const contentEl = document.getElementById("tutorial-content");
      const prevBtn = document.getElementById("prev-btn");
      const nextBtn = document.getElementById("next-btn");

      let activeIndex = -1;

      function renderNav() {
        navList.innerHTML = "";
        tutorials.forEach((tutorial, index) => {
          const item = document.createElement("li");
          const button = document.createElement("button");
          button.className = "nav-item";
          button.setAttribute("type", "button");

          const indexSpan = document.createElement("span");
          indexSpan.className = "index";
          indexSpan.textContent = String(index + 1).padStart(2, "0");

          const titleSpan = document.createElement("span");
          titleSpan.className = "title";
          titleSpan.textContent = tutorial.title;

          button.appendChild(indexSpan);
          button.appendChild(titleSpan);
          button.addEventListener("click", () => loadTutorial(index));
          item.appendChild(button);
          navList.appendChild(item);
        });
      }

      function loadTutorial(index) {
        const tutorial = tutorials[index];
        activeIndex = index;
        titleEl.textContent = tutorial.title;
        contentEl.innerHTML = window.marked.parse(tutorial.content);
        updateNavState();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }

      function updateNavState() {
        const buttons = navList.querySelectorAll("button.nav-item");
        buttons.forEach((button, index) => {
          button.classList.toggle("active", index === activeIndex);
        });

        prevBtn.disabled = activeIndex <= 0;
        nextBtn.disabled = activeIndex === tutorials.length - 1;
      }

      prevBtn.addEventListener("click", () => {
        if (activeIndex > 0) {
          loadTutorial(activeIndex - 1);
        }
      });

      nextBtn.addEventListener("click", () => {
        if (activeIndex < tutorials.length - 1) {
          loadTutorial(activeIndex + 1);
        }
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
          prevBtn.click();
        } else if (event.key === "ArrowRight") {
          nextBtn.click();
        }
      });

      renderNav();
      if (tutorials.length) {
        loadTutorial(0);
      }
    </script>
  </body>
</html>
"""
        )


__all__ = ["TutorialSiteBuilder"]
