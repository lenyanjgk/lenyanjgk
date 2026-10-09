# -*- coding: utf-8 -*-
"""渲染「白金 / 白钻」两套浅色主题，并排生成一个 HTML 对比页，供人工挑选。

为什么单独写这个脚本，而不是直接改 ACTIVE_THEME 跑 make_assets：
挑配色是审美决策，得肉眼对比才能定。本脚本把两套素材同时渲染出来，
写进 preview/theme-compare.html（该目录已被 .gitignore 排除，不污染仓库），
用浏览器打开即可左右对照。选定之后只需把 make_assets.ACTIVE_THEME
改成对应值，再跑 make_assets.py / make_readme.py 落地。

素材直接内联成 <img src="data:image/svg+xml,..."> 而不是写临时文件，
这样整个对比页是单个自包含 HTML，可以随便挪位置、发给别人看。
"""
from __future__ import annotations

import html
import json
import os
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_assets as ma  # noqa: E402

ROOT = ma.ROOT
DATA = ma.DATA
OUT = os.path.join(ROOT, "preview", "theme-compare.html")

# 要进对比页的素材：覆盖有代表性的几类（头图 / 卡片 / 图表 / 项目卡 / 章节标题），
# 不必全量——全量 21 种 × 2 主题 × 2 模式会让页面长到没法看。
def build_jobs(data: dict) -> dict[str, object]:
    jobs: dict[str, object] = {
        "banner": ma.banner,
        "typing": ma.typing,
        "terminal": ma.terminal,
        "hdr-stack": lambda m: ma.header("stack", "技术栈", "Tech Stack", m),
        "hdr-projects": lambda m: ma.header("projects", "在做的东西", "Projects", m),
        "stats": lambda m: ma.stats(m, data),
        "lang": lambda m: ma.lang(m, data),
        "activity": lambda m: ma.activity(m, data),
        "focus": ma.focus,
        "links": ma.links,
    }
    repos = ma.project_repos(data)
    if repos:
        jobs["proj-首卡"] = (lambda r: (lambda m: ma.project(m, r)))(repos[0])
    return jobs

# GitHub 实际渲染时的页面底色：深色 #0d1117，浅色 #ffffff。
# 对比页必须模拟这两个底色，否则看不出「卡片贴在深色页面上」的效果。
MODE_BG = {"dark": "#0d1117", "light": "#ffffff"}
MODE_LABEL = {"dark": "深色 GitHub（访客系统主题为深色）",
              "light": "浅色 GitHub（访客系统主题为浅色）"}


def data_uri(svg_text: str) -> str:
    """SVG -> data URI。用 quote 而非 base64：可读、体积小、无需 import base64。"""
    return "data:image/svg+xml;charset=utf-8," + quote(svg_text, safe="")


CSS = """
* { box-sizing:border-box; }
body { margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',
       'Microsoft YaHei',sans-serif; background:#e8e6e1; color:#1f1f1f; }
.topbar { position:sticky; top:0; z-index:10; background:#1c1a16; color:#d8d2c4;
          padding:14px 28px; font-size:13.5px; line-height:1.7;
          border-bottom:2px solid #8f7215; }
.topbar b { color:#e3c265; }
.wrap { max-width:1060px; margin:0 auto; padding:28px 24px 80px; }
.themeblock { margin-bottom:56px; }
.themetitle { display:flex; align-items:baseline; gap:14px; margin:0 0 6px;
              font-size:24px; font-weight:800; letter-spacing:.5px; }
.themetitle .en { font-size:12px; font-weight:600; letter-spacing:3px;
                  text-transform:uppercase; opacity:.5; }
.swatches { display:flex; gap:6px; margin:0 0 22px; flex-wrap:wrap; }
.sw { width:64px; height:26px; border-radius:6px; border:1px solid rgba(0,0,0,.16); }
.modesection { margin-bottom:34px; }
.modelabel { font-size:12px; font-weight:700; letter-spacing:1.4px; opacity:.55;
             text-transform:uppercase; margin:0 0 10px; }
.canvas { padding:22px; border-radius:12px; border:1px solid rgba(0,0,0,.14);
          box-shadow:0 2px 10px rgba(0,0,0,.10); }
.canvas img { display:block; width:100%; height:auto; margin:0 0 12px; }
.canvas img:last-child { margin-bottom:0; }
.pick { margin-top:8px; font-size:13px; opacity:.75; }
code { background:rgba(0,0,0,.08); padding:1px 6px; border-radius:4px;
       font-family:ui-monospace,Consolas,monospace; font-size:.92em; }
"""


def swatch_row(theme: str) -> str:
    """把主题的关键色画成一排色卡，方便对照色值本身而不是只看渲染结果。"""
    p = ma.THEMES[theme]["light"]
    keys = [("bg1", "底"), ("chipBg", "面板"), ("stroke", "描边"), ("text", "正文"),
            ("muted", "次要"), ("accent", "强调"), ("accent2", "强调2")]
    out = []
    for k, label in keys:
        v = p[k]
        out.append(f'<div title="{label} {k} = {v}" class="sw" '
                   f'style="background:{v}"></div>')
    return '<div class="swatches">' + "".join(out) + "</div>"


def render_theme(theme: str, jobs: dict[str, object]) -> str:
    ma.set_theme(theme)
    names = {"gold": "白金", "diamond": "白钻"}
    blocks = [
        f'<section class="themeblock">',
        f'<h2 class="themetitle">{names[theme]}'
        f'<span class="en">{theme} · ACTIVE_THEME="{theme}"</span></h2>',
        swatch_row(theme),
    ]
    for mode in ("light", "dark"):
        imgs = []
        for name, fn in jobs.items():
            svg_text = fn(mode)
            imgs.append(f'<img src="{data_uri(svg_text)}" alt="{html.escape(name)}">')
        blocks.append(
            f'<div class="modesection">'
            f'<p class="modelabel">{MODE_LABEL[mode]}</p>'
            f'<div class="canvas" style="background:{MODE_BG[mode]}">'
            + "".join(imgs) + "</div></div>")
    blocks.append(
        f'<p class="pick">选这套：把 <code>tools/make_assets.py</code> 里的 '
        f'<code>ACTIVE_THEME = "{theme}"</code> 保持不变（或改成它），'
        f'再跑 <code>python tools/make_assets.py</code> 与 '
        f'<code>python tools/make_readme.py</code>。</p>')
    blocks.append("</section>")
    return "".join(blocks)


def main() -> None:
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    jobs = build_jobs(data)

    body = [render_theme("gold", jobs), render_theme("diamond", jobs)]
    doc = (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset='utf-8'>"
        "<title>配色对比 · 白金 vs 白钻</title>"
        f"<style>{CSS}</style></head><body>"
        "<div class=\"topbar\">浅色主题对比 · <b>lenyan-profile</b> · "
        "上：白金（象牙白 + 香槟金，暖调）　下：白钻（冷白 + 钢蓝，冷调）<br>"
        "每套都给出「浅色 GitHub」与「深色 GitHub」两种访客环境的渲染——"
        "两套都是浅底，深色环境只是压暗一档避免刺眼。"
        "与 GitHub 实际渲染会有细微字体差异。</div>"
        f"<div class=\"wrap\">{''.join(body)}</div></body></html>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {OUT}  {len(doc.encode('utf-8')) / 1024:.0f} KB")
    print(f"  素材 {len(jobs)} 种 × 2 主题 × 2 模式 = {len(jobs) * 4} 张内联 SVG")


if __name__ == "__main__":
    main()
