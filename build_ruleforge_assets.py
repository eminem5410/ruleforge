#!/usr/bin/env python3
"""build_ruleforge_assets.py — Generates 3 PNG assets and patches rebuild_readmes.py."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path.cwd()
ASSETS_DIR = REPO_ROOT / "docs" / "assets"

LOGO_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --primary: #1E40AF; --accent: #3B82F6; --bg: #FFFFFF; --text: #0F172A;
    --layer-1: #DBEAFE; --layer-2: #93C5FD; --layer-3: #60A5FA; --layer-4: #3B82F6;
  }
  body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif; background: var(--bg); -webkit-font-smoothing: antialiased; }
  #root { width: 512px; height: 512px; padding: 56px 64px; display: flex; flex-direction: column; justify-content: space-between; position: relative; background: var(--bg); }
  .brand { text-align: center; margin-bottom: 8px; }
  .brand-name { font-size: 36px; font-weight: 700; color: var(--text); letter-spacing: -0.02em; }
  .brand-tag { font-size: 11px; font-weight: 500; color: #64748B; letter-spacing: 0.18em; text-transform: uppercase; margin-top: 4px; }
  .stack { display: flex; flex-direction: column; gap: 6px; flex: 1; justify-content: center; margin: 16px 0; }
  .layer { height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; letter-spacing: 0.04em; color: #0F172A; }
  .layer-1 { background: var(--layer-1); }
  .layer-2 { background: var(--layer-2); width: 88%; align-self: center; }
  .layer-3 { background: var(--layer-3); width: 76%; align-self: center; color: #FFFFFF; }
  .layer-4 { background: var(--layer-4); width: 64%; align-self: center; color: #FFFFFF; }
  .convergence { position: relative; height: 32px; display: flex; justify-content: center; align-items: flex-start; }
  .convergence svg { width: 100%; height: 100%; }
  .decision { width: 80px; height: 80px; border-radius: 16px; background: var(--primary); color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; letter-spacing: 0.06em; margin: 0 auto; box-shadow: 0 4px 12px rgba(30, 64, 175, 0.18); }
  .footer { text-align: center; margin-top: 8px; }
  .footer-text { font-size: 10px; font-weight: 500; color: #94A3B8; letter-spacing: 0.16em; text-transform: uppercase; }
</style>
</head>
<body>
<div id="root">
  <div class="brand"><div class="brand-name">RuleForge</div><div class="brand-tag">Deterministic Rule Engine</div></div>
  <div class="stack"><div class="layer layer-1">LEXER</div><div class="layer layer-2">PARSER</div><div class="layer layer-3">SEMANTIC</div><div class="layer layer-4">EVALUATOR</div></div>
  <div class="convergence"><svg viewBox="0 0 200 32" preserveAspectRatio="none"><line x1="100" y1="0" x2="100" y2="32" stroke="#94A3B8" stroke-width="2"/></svg></div>
  <div class="decision">DECISION</div>
  <div class="footer"><div class="footer-text">v12.0.0</div></div>
</div>
</body>
</html>'''

BANNER_HTML = r'''<!DOCTYPE html>
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
  #root { width: 1280px; height: 320px; padding: 40px 64px; background: var(--bg); display: flex; align-items: center; gap: 48px; position: relative; overflow: hidden; }
  #root::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: linear-gradient(180deg, var(--primary), var(--accent)); }
  .logo { width: 200px; height: 200px; display: flex; flex-direction: column; gap: 6px; justify-content: center; flex-shrink: 0; }
  .logo .layer { height: 30px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; letter-spacing: 0.06em; color: #0F172A; }
  .logo .layer-1 { background: var(--layer-1); }
  .logo .layer-2 { background: var(--layer-2); width: 86%; align-self: center; }
  .logo .layer-3 { background: var(--layer-3); width: 72%; align-self: center; color: #FFFFFF; }
  .logo .layer-4 { background: var(--layer-4); width: 58%; align-self: center; color: #FFFFFF; }
  .logo .decision-dot { width: 24px; height: 24px; border-radius: 6px; background: var(--primary); margin: 8px auto 0; }
  .text-block { flex: 1; display: flex; flex-direction: column; gap: 8px; }
  .title { font-size: 56px; font-weight: 700; color: var(--text); letter-spacing: -0.025em; line-height: 1.05; }
  .tagline { font-size: 18px; font-weight: 400; color: var(--text-sub); line-height: 1.4; max-width: 620px; }
  .meta { display: flex; gap: 16px; margin-top: 12px; align-items: center; }
  .meta-item { display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500; color: var(--text-muted); letter-spacing: 0.04em; }
  .meta-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
  .version-badge { position: absolute; top: 32px; right: 32px; background: #FFFFFF; border: 1px solid #E2E8F0; color: var(--primary); font-size: 12px; font-weight: 600; letter-spacing: 0.06em; padding: 6px 12px; border-radius: 6px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }
</style>
</head>
<body>
<div id="root">
  <div class="logo"><div class="layer layer-1">LEXER</div><div class="layer layer-2">PARSER</div><div class="layer layer-3">SEMANTIC</div><div class="layer layer-4">EVALUATOR</div><div class="decision-dot"></div></div>
  <div class="text-block"><div class="title">RuleForge</div><div class="tagline">Deterministic, typed, sandboxed, and auditable rule execution for applications that need predictable policy decisions.</div><div class="meta"><div class="meta-item"><span class="meta-dot"></span>Python + C#</div><div class="meta-item"><span class="meta-dot"></span>Cross-language parity</div><div class="meta-item"><span class="meta-dot"></span>69/69 conformance</div></div></div>
  <div class="version-badge">v12.0.0</div>
</div>
</body>
</html>'''

ARCHITECTURE_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root {
    --primary: #1E40AF; --accent: #3B82F6; --bg: #FFFFFF; --surface: #F8FAFC;
    --text: #0F172A; --text-sub: #475569; --text-muted: #94A3B8; --border: #E2E8F0;
    --node-bg: #EFF6FF; --node-border: #1E40AF; --accent-node-bg: #1E40AF; --accent-node-text: #FFFFFF;
    --connector: #94A3B8; --schema-tag: #FEF3C7; --schema-tag-border: #F59E0B; --schema-tag-text: #92400E;
  }
  body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif; background: var(--bg); -webkit-font-smoothing: antialiased; }
  #root { width: 1200px; padding: 48px 64px; background: var(--bg); display: flex; flex-direction: column; align-items: center; gap: 0; }
  .header { text-align: center; margin-bottom: 40px; }
  .header-title { font-size: 22px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; }
  .header-sub { font-size: 13px; font-weight: 500; color: var(--text-muted); letter-spacing: 0.06em; text-transform: uppercase; margin-top: 6px; }
  .pipeline { display: flex; flex-direction: column; align-items: center; gap: 0; }
  .node { background: var(--node-bg); border: 2px solid var(--node-border); border-radius: 10px; padding: 16px 32px; min-width: 280px; text-align: center; position: relative; }
  .node .node-title { font-size: 15px; font-weight: 700; color: var(--text); letter-spacing: 0.02em; }
  .node .node-desc { font-size: 12px; font-weight: 400; color: var(--text-sub); margin-top: 4px; }
  .node.source { background: var(--accent-node-bg); border-color: var(--primary); border-radius: 24px; padding: 14px 36px; }
  .node.source .node-title { color: var(--accent-node-text); }
  .compiler-note { margin-top: 24px; padding: 12px 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; font-size: 12px; color: var(--text-sub); text-align: center; max-width: 540px; }
  .compiler-note strong { color: var(--text); font-weight: 600; }
  .connector { width: 2px; height: 24px; background: var(--connector); margin: 0; position: relative; }
  .connector::after { content: ''; position: absolute; bottom: -2px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid var(--connector); }
  .node-with-tag { position: relative; }
  .schema-tag { position: absolute; right: -140px; top: 50%; transform: translateY(-50%); background: var(--schema-tag); border: 1px solid var(--schema-tag-border); color: var(--schema-tag-text); font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 4px; letter-spacing: 0.04em; white-space: nowrap; }
  .schema-tag::before { content: ''; position: absolute; left: -10px; top: 50%; transform: translateY(-50%); width: 10px; height: 1px; background: var(--schema-tag-border); }
  .branch { display: flex; gap: 32px; justify-content: center; margin-top: 0; padding-top: 0; position: relative; }
  .branch-node { background: var(--node-bg); border: 2px solid var(--node-border); border-radius: 10px; padding: 16px 24px; min-width: 180px; text-align: center; }
  .branch-node .branch-title { font-size: 14px; font-weight: 700; color: var(--text); }
  .branch-node .branch-desc { font-size: 11px; color: var(--text-sub); margin-top: 4px; }
  .split { position: relative; width: 540px; height: 32px; display: flex; justify-content: center; align-items: flex-start; }
  .split::before { content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 2px; height: 12px; background: var(--connector); }
  .split::after { content: ''; position: absolute; top: 12px; left: 50px; right: 50px; height: 2px; background: var(--connector); }
  .split-arrow { position: absolute; bottom: 0; width: 2px; height: 16px; background: var(--connector); }
  .split-arrow::after { content: ''; position: absolute; bottom: -2px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid var(--connector); }
  .split-arrow.s1 { left: 90px; }
  .split-arrow.s2 { left: 50%; transform: translateX(-50%); }
  .split-arrow.s3 { right: 90px; }
  .layer-label { position: absolute; left: -120px; top: 50%; transform: translateY(-50%); font-size: 11px; font-weight: 600; color: var(--text-muted); letter-spacing: 0.12em; text-transform: uppercase; text-align: right; width: 100px; }
  .node-with-layer { position: relative; }
  .legend { margin-top: 40px; padding: 12px 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; display: flex; gap: 32px; justify-content: center; font-size: 12px; color: var(--text-sub); }
  .legend-item { display: flex; align-items: center; gap: 8px; }
  .legend-dot { width: 12px; height: 12px; border-radius: 3px; border: 2px solid; }
  .legend-dot.source { background: var(--primary); border-color: var(--primary); }
  .legend-dot.normal { background: var(--node-bg); border-color: var(--node-border); }
  .legend-dot.output { background: var(--node-bg); border-color: var(--node-border); }
</style>
</head>
<body>
<div id="root">
  <div class="header"><div class="header-title">RuleForge Architecture</div><div class="header-sub">Compilation Pipeline</div></div>
  <div class="pipeline">
    <div class="node source"><div class="node-title">Rule Source</div></div>
    <div class="connector"></div>
    <div class="node node-with-layer"><div class="layer-label">Frontend</div><div class="node-title">Lexer</div><div class="node-desc">Tokenizes RuleForge source code</div></div>
    <div class="connector"></div>
    <div class="node node-with-layer"><div class="layer-label">Frontend</div><div class="node-title">Parser</div><div class="node-desc">Recursive descent &rarr; Abstract Syntax Tree</div></div>
    <div class="connector"></div>
    <div class="node node-with-layer node-with-tag"><div class="layer-label">Validation</div><div class="node-title">Semantic Analyzer</div><div class="node-desc">Validates structure, types, MATCH/CASE</div><div class="schema-tag">+ Schema</div></div>
    <div class="connector"></div>
    <div class="node node-with-layer"><div class="layer-label">Runtime</div><div class="node-title">Evaluator</div><div class="node-desc">Deterministic execution of the AST</div></div>
    <div class="split"><div class="split-arrow s1"></div><div class="split-arrow s2"></div><div class="split-arrow s3"></div></div>
    <div class="branch"><div class="branch-node"><div class="branch-title">Decision</div><div class="branch-desc">Policy outcome</div></div><div class="branch-node"><div class="branch-title">Trace</div><div class="branch-desc">Structured audit log</div></div><div class="branch-node"><div class="branch-title">Patches</div><div class="branch-desc">State updates</div></div></div>
  </div>
  <div class="compiler-note"><strong>Compiler path</strong> provides optimized execution while preserving the same observable semantics as the interpreter.</div>
  <div class="legend"><div class="legend-item"><span class="legend-dot source"></span>Source</div><div class="legend-item"><span class="legend-dot normal"></span>Pipeline stage</div><div class="legend-item"><span class="legend-dot output"></span>Observable outputs</div></div>
</div>
</body>
</html>'''

BANNER_REF = '<p align="center">\n  <img src="docs/assets/ruleforge-banner.png" alt="RuleForge" width="800">\n</p>\n\n'
ARCH_REF = '<img src="docs/assets/ruleforge-architecture.png" alt="RuleForge Architecture" width="800">\n\n'

async def render_html(html_content, output_path, vw, vh):
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    html_path = ASSETS_DIR / f".{output_path.stem}.html"
    html_path.write_text(html_content, encoding="utf-8")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": vw, "height": vh}, device_scale_factor=2)
        await page.goto(f"file://{html_path}", wait_until="networkidle")
        await page.wait_for_timeout(400)
        bbox = await page.locator("#root").bounding_box()
        if bbox:
            await page.set_viewport_size({"width": max(vw, int(bbox["width"] + 80)), "height": int(bbox["height"] + 80)})
            await page.wait_for_timeout(200)
        await page.locator("#root").screenshot(path=str(output_path))
        await browser.close()
    html_path.unlink(missing_ok=True)
    print(f"OK {output_path.name} ({output_path.stat().st_size/1024:.0f}KB)")

async def generate_assets():
    print("Generating 3 PNG assets in docs/assets/...")
    await render_html(LOGO_HTML, ASSETS_DIR / "ruleforge-logo.png", 512, 512)
    await render_html(BANNER_HTML, ASSETS_DIR / "ruleforge-banner.png", 1280, 320)
    await render_html(ARCHITECTURE_HTML, ASSETS_DIR / "ruleforge-architecture.png", 1200, 1200)

def patch_rebuild_script():
    script_path = REPO_ROOT / "rebuild_readmes.py"
    if not script_path.exists():
        print(f"ERROR: {script_path} not found.")
        return False
    s = script_path.read_text(encoding="utf-8")
    if "ruleforge-banner.png" in s and "ruleforge-architecture.png" in s:
        print("rebuild_readmes.py: already patched, skipping.")
        return True
    sw_en = "[English](./README.md) | [Español](./README.es.md)\n\n<p align=\"center\">\n  <strong>Deterministic, typed, sandboxed, and auditable rule execution<br>\n  for applications that need predictable policy decisions.</strong>"
    new_sw_en = "[English](./README.md) | [Español](./README.es.md)\n\n" + BANNER_REF + "<p align=\"center\">\n  <strong>Deterministic, typed, sandboxed, and auditable rule execution<br>\n  for applications that need predictable policy decisions.</strong>"
    sw_es = "[English](./README.md) | [Español](./README.es.md)\n\n<p align=\"center\">\n  <strong>Ejecución de reglas determinista, tipada, aislada y auditable<br>\n  para aplicaciones que necesitan decisiones de política predecibles.</strong>"
    new_sw_es = "[English](./README.md) | [Español](./README.es.md)\n\n" + BANNER_REF + "<p align=\"center\">\n  <strong>Ejecución de reglas determinista, tipada, aislada y auditable<br>\n  para aplicaciones que necesitan decisiones de política predecibles.</strong>"
    if s.count(sw_en) != 1:
        print(f"ERROR: EN switcher block count = {s.count(sw_en)} (expected 1).")
        return False
    if s.count(sw_es) != 1:
        print(f"ERROR: ES switcher block count = {s.count(sw_es)} (expected 1).")
        return False
    s = s.replace(sw_en, new_sw_en)
    s = s.replace(sw_es, new_sw_es)
    ascii_block = "```text\n                         Rule Source\n                              |\n                              v\n                       +--------------+\n                       |    Lexer     |\n                       +------+-------+\n                              |\n                              v\n                       +--------------+\n                       |    Parser    |\n                       +------+-------+\n                              |\n                              v\n                  +--------------------------+\n                  |    Semantic Analyzer     |\n                  |                          |\n                  |        + Schema          |\n                  +------------+-------------+\n                               |\n                               v\n                       +---------------+\n                       |   Evaluator   |\n                       +-------+-------+\n                               |\n                +--------------+--------------+\n                |              |              |\n                v              v              v\n            Decision         Trace        Patches\n```"
    if ascii_block in s:
        s = s.replace(ascii_block, ARCH_REF, 1)
        print("EN: replaced ASCII architecture with image.")
    if ascii_block in s:
        s = s.replace(ascii_block, ARCH_REF, 1)
        print("ES: replaced ASCII architecture with image.")
    script_path.write_text(s, encoding="utf-8")
    print("rebuild_readmes.py: patched.")
    return True

async def main():
    print(f"Repo root: {REPO_ROOT}")
    print(f"Assets dir: {ASSETS_DIR}\n")
    await generate_assets()
    print()
    patch_rebuild_script()

if __name__ == "__main__":
    asyncio.run(main())
