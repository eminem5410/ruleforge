#!/usr/bin/env python3
"""extend_assets.py — Adds OG image (1200x630) and Development Setup section to READMEs."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path.cwd()
ASSETS_DIR = REPO_ROOT / "docs" / "assets"

OG_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --primary: #1E40AF; --accent: #3B82F6; --bg: #F8FAFC; --text: #0F172A;
    --text-sub: #475569; --text-muted: #94A3B8;
    --layer-1: #DBEAFE; --layer-2: #93C5FD; --layer-3: #60A5FA; --layer-4: #3B82F6;
  }
  body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif; background: var(--bg); -webkit-font-smoothing: antialiased; }
  #root { width: 1200px; height: 630px; padding: 60px 80px; background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%); display: flex; align-items: center; gap: 56px; position: relative; overflow: hidden; }
  #root::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 6px; background: linear-gradient(180deg, var(--primary), var(--accent)); }
  #root::after { content: ''; position: absolute; right: -120px; bottom: -120px; width: 440px; height: 440px; background-image: radial-gradient(circle, #3B82F6 2px, transparent 2px); background-size: 24px 24px; opacity: 0.07; border-radius: 50%; }
  .logo { width: 240px; height: 240px; display: flex; flex-direction: column; gap: 8px; justify-content: center; flex-shrink: 0; z-index: 1; }
  .logo .layer { height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; letter-spacing: 0.08em; color: #0F172A; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }
  .logo .layer-1 { background: var(--layer-1); }
  .logo .layer-2 { background: var(--layer-2); width: 86%; align-self: center; }
  .logo .layer-3 { background: var(--layer-3); width: 72%; align-self: center; color: #FFFFFF; }
  .logo .layer-4 { background: var(--layer-4); width: 58%; align-self: center; color: #FFFFFF; }
  .logo .decision-dot { width: 32px; height: 32px; border-radius: 8px; background: var(--primary); margin: 12px auto 0; box-shadow: 0 4px 12px rgba(30, 64, 175, 0.25); }
  .text-block { flex: 1; display: flex; flex-direction: column; gap: 12px; z-index: 1; }
  .title { font-size: 80px; font-weight: 800; color: var(--text); letter-spacing: -0.03em; line-height: 1.0; }
  .tagline { font-size: 22px; font-weight: 400; color: var(--text-sub); line-height: 1.4; max-width: 620px; }
  .meta { display: flex; gap: 24px; margin-top: 20px; align-items: center; flex-wrap: wrap; }
  .meta-item { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 500; color: var(--text-muted); letter-spacing: 0.04em; }
  .meta-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); }
  .version-badge { position: absolute; top: 48px; right: 48px; background: #FFFFFF; border: 1px solid #E2E8F0; color: var(--primary); font-size: 14px; font-weight: 700; letter-spacing: 0.08em; padding: 8px 16px; border-radius: 8px; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06); z-index: 2; }
</style>
</head>
<body>
<div id="root">
  <div class="logo"><div class="layer layer-1">LEXER</div><div class="layer layer-2">PARSER</div><div class="layer layer-3">SEMANTIC</div><div class="layer layer-4">EVALUATOR</div><div class="decision-dot"></div></div>
  <div class="text-block"><div class="title">RuleForge</div><div class="tagline">Deterministic, typed, sandboxed, and auditable rule execution for predictable policy decisions.</div><div class="meta"><div class="meta-item"><span class="meta-dot"></span>Python + C#</div><div class="meta-item"><span class="meta-dot"></span>Cross-language parity</div><div class="meta-item"><span class="meta-dot"></span>69/69 conformance</div></div></div>
  <div class="version-badge">v12.0.0</div>
</div>
</body>
</html>'''

DEV_SETUP_EN = """## Development Setup

To regenerate visual assets and READMEs from the baseline content:

```bash
# 1. Create the local environment
python3 -m venv .venv
.venv/bin/pip install playwright
.venv/bin/playwright install chromium

# 2. Generate PNG assets (logo, banner, architecture diagram, OG image)
.venv/bin/python build_ruleforge_assets.py

# 3. Regenerate README.md and README.es.md
.venv/bin/python rebuild_readmes.py
```

The `.venv/` directory is gitignored. Each contributor must create their own local environment after cloning.

---

## Architectural Baseline"""

DEV_SETUP_ES = """## Configuración de desarrollo

Para regenerar los assets visuales y los READMEs desde el contenido baseline:

```bash
# 1. Crear el entorno local
python3 -m venv .venv
.venv/bin/pip install playwright
.venv/bin/playwright install chromium

# 2. Generar los assets PNG (logo, banner, diagrama de arquitectura, imagen OG)
.venv/bin/python build_ruleforge_assets.py

# 3. Regenerar README.md y README.es.md
.venv/bin/python rebuild_readmes.py
```

El directorio `.venv/` está gitignored. Cada contribuidor debe crear su propio entorno local después de clonar.

---

## Architectural Baseline"""


async def render_og():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    html_path = ASSETS_DIR / ".ruleforge-og.html"
    html_path.write_text(OG_HTML, encoding="utf-8")
    output_path = ASSETS_DIR / "ruleforge-og.png"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=2)
        await page.goto(f"file://{html_path}", wait_until="networkidle")
        await page.wait_for_timeout(400)
        await page.locator("#root").screenshot(path=str(output_path))
        await browser.close()
    html_path.unlink(missing_ok=True)
    print(f"OK ruleforge-og.png ({output_path.stat().st_size/1024:.0f}KB)")


def patch_rebuild_script():
    script_path = REPO_ROOT / "rebuild_readmes.py"
    if not script_path.exists():
        print(f"ERROR: {script_path} not found.")
        return False
    s = script_path.read_text(encoding="utf-8")
    if "## Development Setup" in s:
        print("rebuild_readmes.py: already patched with Development Setup, skipping.")
        return True
    count = s.count("## Architectural Baseline")
    if count != 2:
        print(f"ERROR: expected 2 '## Architectural Baseline' occurrences (EN + ES), found {count}.")
        return False
    # Sentinel approach: avoids bug where DEV_SETUP_EN (which ends with "## Architectural Baseline")
    # creates a new occurrence that the second replace would incorrectly target.
    SENTINEL = "\x00ARCH_BASELINE_PLACEHOLDER\x00"
    s = s.replace("## Architectural Baseline", SENTINEL)
    s = s.replace(SENTINEL, DEV_SETUP_EN, 1)
    s = s.replace(SENTINEL, DEV_SETUP_ES, 1)
    if SENTINEL in s:
        print("ERROR: sentinel remained after patching.")
        return False
    script_path.write_text(s, encoding="utf-8")
    print("rebuild_readmes.py: added Development Setup section (EN + ES).")
    return True


async def main():
    print(f"Repo root: {REPO_ROOT}")
    print(f"Assets dir: {ASSETS_DIR}\n")
    print("Generating OG image (1200x630) for social preview...")
    await render_og()
    print()
    print("Patching rebuild_readmes.py with Development Setup section...")
    patch_rebuild_script()
    print()
    print("Next steps:")
    print("  .venv/bin/python rebuild_readmes.py")
    print("  git add . && git commit -m \"docs: add OG image and Development Setup section\"")
    print("  git push origin main")


if __name__ == "__main__":
    asyncio.run(main())
