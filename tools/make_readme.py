# -*- coding: utf-8 -*-
"""从 data/profile.json 生成 README.md。

为什么 README 也要生成而不是手写：
项目卡是按仓库逐个生成的素材，手写 README 意味着每加一个仓库
都要手动补一段 <picture> 块（漏了就会出现「有素材但主页不显示」）。
生成之后，新增仓库会被每天定时运行的 Action 自动带进主页。

静态文案（关于我、技术栈徽章等）集中在本文件的常量里，改内容改这里。
"""
from __future__ import annotations

import json
import os
import re
import sys

# 让 `python -I tools/make_readme.py` 也能工作：隔离模式不会把脚本目录
# 放进 sys.path，而本文件要 import 同目录的 make_assets（两者共享 CFG、
# project_repos、slug 等，必须单一来源，不能复制粘贴一份）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from make_assets import (CFG, DATA, LINK_ROWS, MANUAL, ROOT, display_name,
                         project_repos, slug)
# 模块引用（而非 from-import）：下面要读 make_assets.PAL，而 PAL 会被
# set_theme() 重新绑定成新字典。若写成 `from make_assets import PAL`，
# 拿到的只是绑定当时那一个字典，切主题后徽章色不会跟着变。
import make_assets as _ma

OUT = os.path.join(ROOT, "README.md")

# 徽章底色 / 强调色不写死，取自当前主题的调色板——SVG 素材和徽章必须同色系，
# 否则浅底卡片旁边挂着一排深灰黑徽章，割裂感非常明显。
# {BG} = 徽章底，{ACC} = 强调色（深底段 + 部分 logo 颜色），
# {MUT} = 次要深底段。
# 注意 shields.io 会自动按底色明暗决定文字色：浅底给 #333，深底给 #fff，
# 无需手动指定（实测 textColor 参数在 flat-square 下不生效）。
# 因此凡是「深底段」的颜色都必须深到能撑起白字 4.5:1——原版用的
# 9AA1AC 只有 2.60:1，白字发虚，这里换成 {MUT} 修到 AA。
def _theme_colors() -> tuple[str, str, str]:
    p = _ma.PAL["light"]
    strip = lambda v: v.lstrip("#")
    return strip(p["badgeBg"]), strip(p["badgeAccent"]), strip(p["badgeMuted"])


def _badge(tmpl: str) -> str:
    bg, acc, mut = _theme_colors()
    return tmpl.format(BG=bg, ACC=acc, MUT=mut)

# 「关于我」：短句 + 每条一个观点。
# 原 README 是四行密集链接墙（一行七八个 <a>），信息量大但读不进去；
# 这里只讲「我是谁、我在做什么、我怎么想」，链接统一收进「找到我」板块。
BULLETS = [
    "👋 我是 **lenyan**，广州的 **Java 全栈工程师**，后端 Spring Boot、前端 Vue 3 都写",
    "🤖 最近在做 **AI 应用**：Spring AI 智能体、LangGraph RAG 知识库，把模型接进真实业务",
    "🧩 长期更新 **LeetCode 题解**，按专题归档，每题都配思路与复杂度分析",
    "🛠 喜欢把踩过的坑沉淀成**能复用的框架**，而不是一次性脚本（比如自研的 lenRPC）",
    "📚 写博客也写代码：CSDN 累计 **23W+ 阅读**，公众号「程序员凯凯」同步更新",
    "🚀 信奉「**先做出来，再做好**」",
]

# (标题, 徽章 markdown 列表)。分成两组，用双列表格排，避免一长条徽章挤成一行。
#
# 串里的 {BG} / {ACC} 是配色占位符，由 _badge() 用当前主题的色值填充。
# 品牌 logo 色（Spring 绿、Vue 绿、MySQL 蓝…）保持各技术官方色不动——
# 那是识别信息，不该跟着主题走。唯一例外是 Vue 的 4FC08D：
# 那是为深底挑的浅绿，在白底上会发虚，这里压深成 3AA876。
STACK_GROUPS = [
    ("后端 · 主力", [
        "![Java](https://img.shields.io/badge/Java-{BG}?style=flat-square&logo=openjdk&logoColor={ACC})",
        "![Spring Boot](https://img.shields.io/badge/Spring_Boot_3-{BG}?style=flat-square&logo=springboot&logoColor=6DB33F)",
        "![Spring AI](https://img.shields.io/badge/Spring_AI-{BG}?style=flat-square&logo=spring&logoColor=6DB33F)",
        "![MySQL](https://img.shields.io/badge/MySQL-{BG}?style=flat-square&logo=mysql&logoColor=4479A1)",
        "![Redis](https://img.shields.io/badge/Redis-{BG}?style=flat-square&logo=redis&logoColor=DC382D)",
        "![Vert.x](https://img.shields.io/badge/Vert.x-{BG}?style=flat-square&logo=eclipsevertx&logoColor=782CE8)",
    ]),
    ("前端 · 工程 · AI", [
        "![Vue 3](https://img.shields.io/badge/Vue_3-{BG}?style=flat-square&logo=vuedotjs&logoColor=3AA876)",
        "![TypeScript](https://img.shields.io/badge/TypeScript-{BG}?style=flat-square&logo=typescript&logoColor=3178C6)",
        "![Python](https://img.shields.io/badge/Python-{BG}?style=flat-square&logo=python&logoColor=3776AB)",
        "![LangGraph](https://img.shields.io/badge/LangGraph-{BG}?style=flat-square&logo=langchain&logoColor={ACC})",
        "![Docker](https://img.shields.io/badge/Docker-{BG}?style=flat-square&logo=docker&logoColor=2496ED)",
        "![Git](https://img.shields.io/badge/Git-{BG}?style=flat-square&logo=git&logoColor=F05032)",
    ]),
]

TOP_BADGES = [
    "![Java](https://img.shields.io/badge/Java-{BG}?style=for-the-badge&logo=openjdk&logoColor={ACC})",
    "![Spring Boot](https://img.shields.io/badge/Spring_Boot-{BG}?style=for-the-badge&logo=springboot&logoColor=6DB33F)",
    "![Vue](https://img.shields.io/badge/Vue_3-{BG}?style=for-the-badge&logo=vuedotjs&logoColor=3AA876)",
    "![AI](https://img.shields.io/badge/Spring_AI-{BG}?style=for-the-badge&logo=langchain&logoColor={ACC})",
    "![广州](https://img.shields.io/badge/📍_广州-{BG}?style=for-the-badge)",
]

FOOT_BADGES = [
    "![Status](https://img.shields.io/badge/status-building-{ACC}?style=flat-square&labelColor={BG}&color={ACC})",
    "![PRs](https://img.shields.io/badge/PRs-welcome-{MUT}?style=flat-square&labelColor={BG}&color={MUT})",
    "![Made with](https://img.shields.io/badge/自绘_SVG-无第三方图床-{ACC}?style=flat-square&labelColor={BG}&color={ACC})",
]


def pic(name: str, alt: str, width: str = "100%") -> str:
    """双源图片块。GitHub 按访问者的系统主题自动选一张。

    注意两个 srcset 指向的素材**都是浅色底**，区别只在明度：
    -dark.svg 稍暗稍暖（避免在深色页面上刺眼），-light.svg 接近纯白。
    保留双源结构而不是合并成一张，是为了让深色访客看到压暗过的那版。
    """
    return (f'<picture>\n'
            f'  <source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">\n'
            f'  <source media="(prefers-color-scheme: light)" srcset="assets/{name}-light.svg">\n'
            f'  <img src="assets/{name}-dark.svg" alt="{alt}" width="{width}">\n'
            f'</picture>')


def linked_pic(name: str, href: str, alt: str) -> str:
    """整张图可点击的项目卡。"""
    return (f'<p align="center">\n  <a href="{href}">\n'
            f'    <picture>\n'
            f'      <source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">\n'
            f'      <source media="(prefers-color-scheme: light)" srcset="assets/{name}-light.svg">\n'
            f'      <img src="assets/{name}-dark.svg" alt="{alt}" width="100%">\n'
            f'    </picture>\n  </a>\n</p>')


def hdr(slugname: str, alt: str) -> str:
    return pic(f"hdr-{slugname}", alt)


def link_row(title: str, href: str) -> str:
    bg, acc, _mut = _theme_colors()
    return (f'<a href="{href}"><img src="https://img.shields.io/badge/{title}-{acc}'
            f'?style=flat-square&labelColor={bg}&color={acc}" alt="{title}"></a>')


def build(data: dict) -> str:
    repos = project_repos(data)
    parts: list[str] = []

    # --- 头图区 ---
    parts.append('<div align="center">\n')
    parts.append(pic("banner", f'{CFG["name_zh"]} · {CFG["handle"]}'))
    parts.append("\n")
    parts.append(pic("typing", "正在做的事"))
    parts.append("\n<br>\n")
    parts.append("\n".join(_badge(b) for b in TOP_BADGES))
    parts.append("\n</div>\n")

    parts.append(pic("divider", ""))

    # --- 关于我 ---
    parts.append("\n")
    parts.append(hdr("about", "关于我"))
    parts.append("\n")
    parts.append("\n".join(f"- {b}" for b in BULLETS))
    parts.append("\n")
    parts.append(pic("terminal", "终端名片"))

    # --- 技术栈 ---
    parts.append(hdr("stack", "技术栈"))
    parts.append("\n")
    parts.append(pic("lang", "代码语言构成"))
    parts.append("\n")
    parts.append("<table>\n<tr>")
    for title, badges in STACK_GROUPS:
        parts.append(f'\n<td valign="top" width="{100 // len(STACK_GROUPS)}%">\n')
        parts.append(f"**{title}**\n\n")
        parts.append("\n".join(_badge(b) for b in badges))
        parts.append("\n</td>")
    parts.append("\n</tr>\n</table>")

    # --- 项目 ---
    parts.append(hdr("projects", "在做的东西"))
    parts.append("\n")
    for r in repos:
        parts.append(linked_pic(f"proj-{slug(r['name'])}", r["url"], display_name(r)))
        parts.append("\n")

    # --- 数据 ---
    parts.append(hdr("stats", "数据与轨迹"))
    parts.append("\n")
    parts.append(pic("stats", "数据概览"))
    parts.append("\n")
    parts.append(pic("activity", "贡献轨迹"))
    parts.append("\n")
    parts.append("> 上面的图**不是第三方图床的静态卡片**：数据由本仓库的 GitHub Action "
                 "每天重新抓取并重绘，\n> 素材全部自绘。")

    # --- 方向 ---
    parts.append(hdr("focus", "方向与投入"))
    parts.append("\n")
    parts.append(pic("focus", "方向与投入"))
    parts.append("\n")
    parts.append("> 占比是自评，不是考试成绩，会随手上在做的东西变。")

    # --- 找到我 ---
    parts.append(hdr("links", "找到我"))
    parts.append("\n")
    parts.append(pic("links", "找到我"))
    parts.append("\n")
    # SVG 里的卡片不能带链接（camo 代理下 <a> 无效），所以补一行可点的徽章
    parts.append('<p align="center">\n'
                 + "\n".join(link_row(t, u) for t, _, _, u in LINK_ROWS)
                 + "\n</p>")

    parts.append(pic("divider", ""))
    parts.append("\n<div align=\"center\">\n")
    parts.append("**如果哪个仓库对你有用，点个 ⭐ 就是最好的鼓励。**\n")
    parts.append("\n".join(_badge(b) for b in FOOT_BADGES))
    parts.append("\n</div>")

    return "\n".join(parts) + "\n"


def main() -> None:
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    md = build(data)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(md)

    repos = project_repos(data)
    print(f"wrote {OUT}  {len(md.encode('utf-8'))} bytes")
    print(f"  项目卡 {len(repos)} 个: {', '.join(display_name(r) for r in repos)}")

    # 生成期校验：README 引用的每个素材都必须真实存在，
    # 否则线上就是破图（这个坑在原项目里踩过一次：相对路径写错，整页 SVG 全挂）
    refs = sorted(set(re.findall(r'src(?:set)?="assets/([^"]+\.svg)"', md)))
    missing = [r for r in refs if not os.path.exists(os.path.join(ROOT, "assets", r))]
    print(f"  引用素材 {len(refs)} 个，缺失 {len(missing)} 个")
    for m in missing:
        print(f"    MISSING: {m}")
    if missing:
        raise SystemExit(1)

    if data.get("stale"):
        print(f"  注意: 本次数据部分沿用旧值 -> {data['stale']}")


if __name__ == "__main__":
    main()
