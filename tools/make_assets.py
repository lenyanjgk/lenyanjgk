# -*- coding: utf-8 -*-
"""生成 README 所需的全部自绘 SVG（浅色主题，按访客系统主题分两档明度）。

设计取向：白底单色系 + 单一强调色（白金=象牙白+香槟金 / 白钻=冷白+钢蓝，
见 ACTIVE_THEME）。
- 两套素材**都是浅底**。dark/light 两个键对应访客的系统主题，不是底色深浅：
  light 键给接近纯白的瓷面，dark 键稍暗稍暖，避免深色页面上刺眼。
- 不用极光光斑、不用星点、不用彩虹渐变。整页只有一个强调色，
  图表用同一色相的明度阶梯，避免「拼贴感」。
- 动效只保留三类：淡入、一道慢速扫光、进度条生长。慢 = 高级。
- 所有 SVG 只用 SMIL / 内联动效，不引用任何外部资源
  （GitHub 通过 camo 代理以 <img> 渲染，外部字体、脚本、外链都不可用）。

本文件分两部分：make_assets.py 是主逻辑，_assets_lib.py 是绘图原语。
"""
from __future__ import annotations

import colorsys
import json
import os
import unicodedata
import xml.sax.saxutils as sx
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "profile.json")
OUT = os.path.join(ROOT, "assets")

# 手动补充的常量数据：抓不到、或不适合自动抓的那部分。
MANUAL = {
    "csdn_reads": "23W+",
    "csdn_url": "https://blog.csdn.net/jgk666666",
    "wechat_mp": "https://mp.weixin.qq.com/s/utI7LVBN0JyXdZyqhRA_ww",
    "codefather": "https://www.codefather.cn/user/1738833787455823874",
    "leetcode_blog": "https://blog.csdn.net/jgk666666/article/details/137209476",
}

CFG = {
    "name_en": "LENYAN",
    "name_zh": "lenyan",
    "handle": "@lenyanjgk",
    "chips": ["Java 全栈工程师", "开源爱好者", "算法题解"],
    "typing": [
        "用 Spring Boot 与 Vue 把想法做成能跑的产品",
        "刷 LeetCode，也写能被别人复用的框架",
        "Stay hungry, stay foolish.",
    ],
    # 方向自评（0-100）。这组数字是主观占比，按自己的感觉改就行。
    "focus": [
        ("Java 后端 / Spring Boot 3", 100),
        ("前端 Vue 3 / TypeScript", 78),
        ("算法与数据结构（LeetCode）", 85),
        ("AI 应用 / Spring AI · LangGraph", 70),
        ("开源写作与技术分享", 65),
    ],
}

FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
        "'Hiragino Sans GB','Microsoft YaHei','Helvetica Neue',Arial,sans-serif")

# ---------------------------------------------------------------------------
# 颜色工具（WCAG 相对亮度 / 对比度）
# ---------------------------------------------------------------------------
def hex_rgb(h: str) -> tuple[int, int, int]:
    """'#RRGGBB' -> (r, g, b)，0-255。"""
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _srgb_channel(c: float) -> float:
    """单通道线性化。入参必须是 0-1 归一化值，不是 0-255。"""
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def rel_luminance(h: str) -> float:
    """WCAG 相对亮度。"""
    r, g, b = (x / 255 for x in hex_rgb(h))
    return (0.2126 * _srgb_channel(r) + 0.7152 * _srgb_channel(g)
            + 0.0722 * _srgb_channel(b))


def contrast_ratio(a: str, b: str) -> float:
    """WCAG 对比度，1.0 ~ 21.0。"""
    l1, l2 = sorted((rel_luminance(a), rel_luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def blend_over(fg: str, bg: str, opacity: float) -> str:
    """fg 以 opacity 叠在 bg 上的实际渲染色。

    校验热力图零贡献格时要用：那一格叠了 opacity 0.55，
    按原始色值算对比度会高估。
    """
    f, b = hex_rgb(fg), hex_rgb(bg)
    return "#%02X%02X%02X" % tuple(
        round(x * opacity + y * (1 - opacity)) for x, y in zip(f, b))


# ---------------------------------------------------------------------------
# 配色主题
# ---------------------------------------------------------------------------
# 全页浅色。两套候选（白金 / 白钻），改 ACTIVE_THEME 一行即可切换，
# 两套的字段名完全一一对应，绘图代码不感知具体是哪一套。
#
# 关于 dark / light 两个键：它们对应 GitHub 访问者的系统主题，
# **不是**「深色底 / 浅色底」。两套都画成浅色，区别只在明度：
#   light 键 -> 访问者用浅色 GitHub：接近纯白的瓷面
#   dark  键 -> 访问者用深色 GitHub：稍暖稍暗的象牙白
# 深色模式下若直接给纯白，从 #0d1117 的页面底色切过来会刺眼，
# 所以压一档明度、加一点暖调，让卡片像「贴在深色页面上的纸」。
ACTIVE_THEME = "gold"          # "gold" = 白金 | "diamond" = 白钻

THEMES = {
    # 象牙白瓷面 + 香槟金。延续原「石墨 + 铜金」的金色血统，只把底翻成白的。
    "gold": {
        "dark": {
            "bg1": "#F7F4EE", "bg2": "#F0EBE1",
            "stroke": "#DFD8C8", "text": "#2A2519", "muted": "#5D5649",
            # dim 按更暗的 chipBg 校准，而非 bg1：它也用在面板上
            # （项目卡 topic 标签、链接卡说明），只看 bg1 会漏掉一档。
            "dim": "#6F6759",
            "accent": "#96781A", "accent2": "#A8862A", "accentSoft": "#A38A40",
            "grid": "#EBE5D9", "chipBg": "#EFE9DC",
            "badgeBg": "#EDE6D6", "badgeAccent": "#8F7215", "badgeMuted": "#7A6A5A",
            # 扫光：白底上半透明白完全不可见（原深色版的扫光会静默失效），
            # 改用强调色的低不透明度，光带才有影子。
            "sheenColor": "#8A6E14", "sheenOpacity": "0.13",
        },
        "light": {
            "bg1": "#FDFCF9", "bg2": "#F8F5EF",
            "stroke": "#E5DFD1", "text": "#1A1712", "muted": "#5D5647",
            "dim": "#726B5E",
            "accent": "#8F7215", "accent2": "#9A7B18", "accentSoft": "#A88F46",
            "grid": "#EFEADC", "chipBg": "#F4EFE4",
            "badgeBg": "#F0EADA", "badgeAccent": "#8A6E14", "badgeMuted": "#75675A",
            "sheenColor": "#8A6E14", "sheenOpacity": "0.11",
        },
    },
    # 冷白瓷面 + 钢蓝。钻石那种冷白光感：底色偏冷灰白，强调色是低饱和钢青。
    # 与白金（暖调）互为对照，一暖一冷。
    "diamond": {
        "dark": {
            "bg1": "#F4F7FA", "bg2": "#EDF1F6",
            "stroke": "#D6DEE7", "text": "#1B2430", "muted": "#4E5A68",
            # dim 按更暗的 chipBg 校准，而非 bg1（同 gold 的理由）。
            "dim": "#626D7A",
            "accent": "#33698E", "accent2": "#43799E", "accentSoft": "#6F92AD",
            "grid": "#E6EBF1", "chipBg": "#EAEFF4",
            "badgeBg": "#E4EAF1", "badgeAccent": "#2C6086", "badgeMuted": "#5A6875",
            "sheenColor": "#2C6086", "sheenOpacity": "0.13",
        },
        "light": {
            "bg1": "#FCFDFE", "bg2": "#F5F8FB",
            "stroke": "#DFE5EC", "text": "#12181F", "muted": "#4E5A68",
            "dim": "#67717D",
            "accent": "#2E6488", "accent2": "#3D7CA6", "accentSoft": "#7296B5",
            "grid": "#EDF1F5", "chipBg": "#F2F6F9",
            "badgeBg": "#EEF2F7", "badgeAccent": "#2A5F82", "badgeMuted": "#55636F",
            "sheenColor": "#2A5F82", "sheenOpacity": "0.11",
        },
    },
}

# 热力图 / 环形图的明度阶梯：同一强调色，只变明度与不透明度。
# 这是「高级感」的关键——单色相阶梯比多色相更耐看。
# 阶梯从「几乎融进底色」到「最深的强调色」，保证零贡献格与满贡献格
# 之间有足够的明度跨度，稀疏数据也读得出节奏。
#
# 低档位为什么必须压深：activity() 给零贡献格叠了 opacity 0.55，
# 浅底上这会让 heat[0] 几乎融进背景（实测 1.09:1，低于 GitHub 官方的 1.17:1），
# 而 heat[0]→heat[1] 的档间对比也会掉到 1.15:1，格子糊成一片。
# 下面四组都按「实际渲染色」（heat[0] 计 0.55 透明度）校准过：
# 相邻档间 >= 1.33:1，零贡献格 vs 底色 >= 1.15:1，
# 参照系是 GitHub 官方浅色贡献墙的 1.32 / 1.17。
HEATMAPS = {
    "gold": {
        "dark":  ["#E1D8C0", "#D6C28C", "#C09F4E", "#9F7F1A", "#7A610F"],
        "light": ["#E4DCC6", "#DCCB9E", "#CBAF62", "#A8862A", "#7E6410"],
    },
    "diamond": {
        "dark":  ["#C2DAEA", "#94BFDB", "#5F9EC9", "#397BA8", "#285776"],
        "light": ["#CADFED", "#9CC3DD", "#67A3CB", "#3B81AF", "#2B5C7E"],
    },
}

# 语言环形图配色：低饱和、同明度区间，彼此不打架。
#
# 明度按「深浅交替」分带（JavaScript/HTML/Markdown 浅，TypeScript/CSS/Vue 深），
# 这样占比排序变化后任意相邻两段都尽量拉开。原深色版把所有语言压在
# 同一中等明度上，实测相邻段区分度只有 1.07:1，环形图糊成一圈。
#
# 只列 light 一套值：dark 由 _lang_colors_for() 派生，避免维护两份
# 几乎相同的表（改了 light 忘了 dark，两套就会悄悄不一致）。
# Java 不在此列——它吃主题强调色，由派生函数填。
LANG_BASE = {
    "gold": {
        "JavaScript": "#968F83", "TypeScript": "#5F6977", "Vue": "#5B856E",
        "Python": "#685B80", "HTML": "#B3836F", "CSS": "#536B83",
        "Shell": "#6E7D7B", "Markdown": "#949084", "Dockerfile": "#507086",
        "Go": "#577E89", "Kotlin": "#765B80", "PowerShell": "#4B6A81",
        "Dart": "#4E887E", "SCSS": "#8F5C74", "C++": "#895858", "SQL": "#637E63",
    },
    # 冷白底：语言色整体偏冷，只留 HTML 一个暖陶色做区分。
    "diamond": {
        "JavaScript": "#8F9298", "TypeScript": "#55667A", "Vue": "#4E7C6A",
        "Python": "#5F5A7C", "HTML": "#9C7A6A", "CSS": "#4A6C86",
        "Shell": "#66797A", "Markdown": "#8C8F94", "Dockerfile": "#4A6A82",
        "Go": "#4E7684", "Kotlin": "#6A5A7E", "PowerShell": "#43637C",
        "Dart": "#457C74", "SCSS": "#86576E", "C++": "#7E5555", "SQL": "#5C7A5C",
    },
}


def _lang_colors_for(theme: str, mode: str) -> dict[str, str]:
    """派生某主题某模式下的完整语言配色。

    dark 模式的底色（#F7F4EE）比 light（#FDFCF9）暗一档，同一个前景色放上去
    对比度会掉。这里把不达标的颜色沿自身色相压深到刚好够（浅底上拉对比
    只能往深走）。刻意只修不达标的少数几个——若整体平移明度，原本
    刻意拉开的「深浅交替」带会被压平，反而丢掉区分度。
    """
    p = THEMES[theme][mode]
    bg, floor = p["bg1"], 3.05
    out = {"Java": p["accent"]}          # 主语言吃强调色，作整圈的视觉锚点
    for name, base in LANG_BASE[theme].items():
        out[name] = _darken_to(base, bg, floor)
    return out


def _darken_to(color: str, bg: str, target: float) -> str:
    """保持色相与饱和度，二分搜索明度，使前景在 bg 上的对比度刚好 >= target。

    已达标就原样返回，不做多余改动。
    """
    if contrast_ratio(color, bg) >= target:
        return color
    h, l, s = colorsys.rgb_to_hls(*[x / 255 for x in hex_rgb(color)])
    lo, hi = 0.0, l
    for _ in range(40):
        mid = (lo + hi) / 2
        cand = "#%02X%02X%02X" % tuple(
            round(x * 255) for x in colorsys.hls_to_rgb(h, mid, s))
        if contrast_ratio(cand, bg) >= target:
            lo = mid
        else:
            hi = mid
    return "#%02X%02X%02X" % tuple(
        round(x * 255) for x in colorsys.hls_to_rgb(h, lo, s))


# 展开成 {theme: {mode: {lang: hex}}}，绘图代码直接查两级即可。
LANG_COLORS = {t: {m: _lang_colors_for(t, m) for m in ("light", "dark")}
               for t in THEMES}

# 当前生效的三张表。函数体里一律引用这三个模块级名字，
# 所以切换主题只需要重新绑定它们（set_theme 干的就是这件事）。
PAL = THEMES[ACTIVE_THEME]
HEAT = HEATMAPS[ACTIVE_THEME]
LANG_COLOR = LANG_COLORS[ACTIVE_THEME]


def set_theme(name: str) -> None:
    """切换配色主题。对比预览脚本靠它在不改源码的前提下渲染两套。"""
    global ACTIVE_THEME, PAL, HEAT, LANG_COLOR
    if name not in THEMES:
        raise SystemExit(f"未知主题 {name!r}，可选: {', '.join(THEMES)}")
    ACTIVE_THEME = name
    PAL = THEMES[name]
    HEAT = HEATMAPS[name]
    LANG_COLOR = LANG_COLORS[name]


# ---------------------------------------------------------------------------
# 绘图原语
# ---------------------------------------------------------------------------
def esc(s: str) -> str:
    return sx.escape(str(s), {'"': "&quot;"})


def text_w(s: str, size: float) -> float:
    """粗略估算渲染宽度：CJK 按 1.0em，其余按 0.55em。

    GitHub 渲染 SVG 时用的是访问者本机字体，无法精确测量，只能估。
    估宽用于换行和排版对齐，差一点看不出来；差很多才会露馅。
    """
    units = sum(1.0 if unicodedata.east_asian_width(c) in "WF" else 0.55 for c in str(s))
    return units * size


def wrap(text: str, max_w: float, size: float) -> list[str]:
    out, cur = [], ""
    for ch in text:
        if text_w(cur + ch, size) > max_w and cur:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


def svg(w: int, h: int, label: str, defs: str, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" fill="none" role="img" aria-label="{esc(label)}">'
            f'<defs>{defs}</defs>{body}</svg>')


def bg_grad(p: dict, pid: str) -> str:
    """卡片底：极缓的对角渐变。两端色差刻意很小，避免「彩虹」观感。"""
    return (f'<linearGradient id="{pid}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{p["bg1"]}"/>'
            f'<stop offset="1" stop-color="{p["bg2"]}"/></linearGradient>')


def panel(p: dict, pid: str, w: int, h: int, rx: int = 16) -> str:
    """圆角底板 + 1px 内描边。描边画在 0.5 偏移上，避免被 viewBox 裁掉一半。"""
    return (f'<rect width="{w}" height="{h}" rx="{rx}" fill="url(#{pid})"/>'
            f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="{rx}" '
            f'stroke="{p["stroke"]}" stroke-opacity="0.85"/>')


def accent_grad(p: dict, pid: str) -> str:
    return (f'<linearGradient id="{pid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{p["accent"]}"/>'
            f'<stop offset="1" stop-color="{p["accent2"]}"/></linearGradient>')


def sheen(p: dict, pid: str = "sheen",
          color: str | None = None, opacity: str | None = None) -> str:
    """扫光的渐变定义：中间一条半透明色带，两侧全透明。

    原版写死半透明白——那是深色底的写法。翻成浅色底后，白底上的半透明白
    等于没有，divider / header / 项目卡的扫光会「照常运行但完全看不见」，
    属于静默失效（动画还在跑，肉眼以为丢了特效）。
    所以颜色与强度都从调色板取：浅底改用强调色的低不透明度。

    color / opacity 可显式覆盖，用于扫光不落在浅底上的场合——
    例如 banner 把扫光裁进名字的字形轮廓里，光带其实走在深色渐变字上，
    那里仍然该用白色（见 banner()）。
    """
    c = color or p.get("sheenColor", "#FFFFFF")
    o = opacity or p.get("sheenOpacity", "0.16")
    return (f'<linearGradient id="{pid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{c}" stop-opacity="0"/>'
            f'<stop offset="0.5" stop-color="{c}" stop-opacity="{o}"/>'
            f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></linearGradient>')


def sweep(w: int, h: int, dur: float = 9.0, clip: str = "") -> str:
    """一道慢速扫光。dur 给到 9s 以上——快扫光显得廉价，慢扫光才有质感。

    clip 传 clipPath id 时把扫光裁在指定区域内（例如裁进文字轮廓）。
    """
    g = f'<g clip-path="url(#{clip})">' if clip else '<g>'
    return (f'{g}<rect x="{-w//3}" y="-40" width="{w//3}" height="{h+80}" '
            f'fill="url(#sheen)" transform="skewX(-18)">'
            f'<animate attributeName="x" values="{-w//3};{w}" dur="{dur}s" '
            f'repeatCount="indefinite"/></rect></g>')


def fadein(inner: str, delay: float = 0.0, dur: float = 0.7) -> str:
    """淡入包装。整页统一用这一种入场，节奏一致才不散。"""
    return (f'<g opacity="0"><animate attributeName="opacity" values="0;1" '
            f'dur="{dur}s" begin="{delay:.2f}s" fill="freeze"/>{inner}</g>')


def pulse(cx: float, cy: float, color: str, r: float = 3.0, dur: float = 3.4) -> str:
    """一个呼吸圆点。全页只在少数几处用，用来标记「实时/在线」语义。"""
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{color}"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{color}" opacity="0.45">'
            f'<animate attributeName="r" values="{r};{r*3.2:.1f};{r}" dur="{dur}s" '
            f'repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.45;0;0.45" dur="{dur}s" '
            f'repeatCount="indefinite"/></circle>')


# ---------------------------------------------------------------------------
# 自绘线条图标
# ---------------------------------------------------------------------------
# 不用 emoji：emoji 在不同系统上字形差异极大，Windows/macOS/Android 各一个样，
# 而且彩色 emoji 会破坏单色调。线条图标在任何环境下都一致。
ICONS = {
    "about": ['<circle cx="12" cy="7.8" r="3.5"/>',
              '<path d="M5 20.2c0-3.9 3.1-6.2 7-6.2s7 2.3 7 6.2"/>'],
    "stack": ['<path d="M12 2.8 20.6 7.4 12 12 3.4 7.4Z"/>',
              '<path d="M3.4 12 12 16.6 20.6 12"/>',
              '<path d="M3.4 16.6 12 21.2 20.6 16.6"/>'],
    "projects": ['<path d="M12 2.6 20.4 7.3v9.4L12 21.4 3.6 16.7V7.3Z"/>',
                 '<path d="M3.6 7.3 12 12l8.4-4.7"/>', '<path d="M12 12v9.4"/>'],
    "stats": ['<path d="M3.6 20.4h16.8"/>',
              '<path d="M7.4 20.4v-6.2"/><path d="M12 20.4V8.2"/><path d="M16.6 20.4v-4"/>'],
    "focus": ['<circle cx="12" cy="12" r="8.6"/>', '<circle cx="12" cy="12" r="4.8"/>',
              '<circle cx="12" cy="12" r="1.5" fill="ACC" stroke="none"/>'],
    "links": ['<circle cx="12" cy="12" r="8.6"/>', '<path d="M3.4 12h17.2"/>',
              '<path d="M12 3.4c4.2 4.8 4.2 12.4 0 17.2-4.2-4.8-4.2-12.4 0-17.2Z"/>'],
    "terminal": ['<rect x="2.6" y="4.4" width="18.8" height="15.2" rx="2.2"/>',
                 '<path d="M6.6 10.2 9.2 12l-2.6 1.8"/>', '<path d="M11.6 14.6h5.4"/>'],
}


def icon(name: str, x: float, y: float, size: float, color: str,
         sw: float = 1.6, opacity: float = 1.0) -> str:
    """把 24x24 的线条图标画到指定位置。ACC 占位符会被替换成当前色。

    必须显式写 stroke 颜色：SVG 根元素是 fill="none"，不写就会继承成
    none 而完全不可见（这个坑在原项目里踩过一次）。
    """
    parts = []
    for d in ICONS[name]:
        parts.append(d.replace("ACC", color))
    inner = "".join(parts)
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({size/24:.4f})" '
            f'stroke="{color}" stroke-width="{sw}" fill="none" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}">'
            f'{inner}</g>')


def all_repos(data: dict) -> list[dict]:
    """参与数据统计的全部仓库：排除同名 profile 仓与空仓，但**不**受白名单限制。

    与 project_repos 的区别：project_repos 决定「主页上画哪些项目卡」，
    all_repos 决定「获得星标 / 被 Fork 这些汇总数字怎么算」。
    两者必须分开——白名单外的仓库（学习笔记、课程作业）不该占展示位，
    但它们拿到的 star 是真实收获，从总数里剔掉会少算。
    同名 profile 仓要排除：那是别人给主页点的赞，不是给项目的。
    """
    login = data["user"]["login"].lower()
    return [r for r in data["repos"]
            if r["name"].lower() != login and not r.get("empty")]


def project_repos(data: dict) -> list[dict]:
    """要画成项目卡的仓库。排除三类：

    1. 与用户名同名的仓库（lenyanjgk）—— 那是主页 README 的载体，不是项目。
       不排除的话主页上会冒出一张「关于主页仓库自己」的项目卡。
    2. 空仓库（一个文件都没有）—— 没内容可描述，卡片是空壳。
    3. 未收录进 REPO_META 白名单的 —— 学习笔记、课程作业这类仓库
       不该占展示位（但它们的 star 仍计入汇总，见 all_repos）。
    """
    login = data["user"]["login"].lower()
    out = []
    for r in data["repos"]:
        if r["name"].lower() == login or r.get("empty"):
            continue
        if r["name"] not in REPO_META:
            continue
        out.append(r)
    # 按 REPO_META 里的声明顺序展示（人工排过的重要性顺序），而非 star 数。
    order = {n: i for i, n in enumerate(REPO_META)}
    out.sort(key=lambda r: order.get(r["name"], 999))
    return out


# ---------------------------------------------------------------------------
# 项目白名单
# ---------------------------------------------------------------------------
# 为什么用白名单而不是「按 star 数自动取前 N」：
# 自动排序会把学习笔记、课程作业这类仓库顶上来，挤掉真正想展示的项目。
# 白名单让展示顺序 = 你心里的优先级，代价是新增项目要来这里加一行。
# blurb 优先于仓库 description：仓库描述常常堆满 emoji 和关键词，
# 放在单色调卡片上会很吵，所以这里重写成一句干净的话。
REPO_META = {
    "len-ai-agent": {
        "display": "lenAI · 超级智能体",
        "blurb": "Spring Boot 3.4 + Java 21 + Spring AI 构建的智能体平台，"
                 "支持多模型编排、工具调用与会话记忆管理。",
    },
    "lendada": {
        "display": "lendada · 智慧答题平台",
        "blurb": "Vue 3 + Spring Boot + Redis + AI 的在线答题系统，"
                 "含题目管理、智能判分与答题记录分析。",
    },
    "lenrpc": {
        "display": "lenRPC · 轻量级 RPC 框架",
        "blurb": "基于 Vert.x 的自研 RPC 框架：服务注册发现、多格式配置热更新、"
                 "负载均衡与异步网络通信。",
    },
    "leetcode-solution": {
        "display": "LeetCode 解题仓库",
        "blurb": "按专题归档的算法题解，每题配思路与复杂度分析，"
                 "与 CSDN 专栏同步更新。",
    },
    "zhidangtong": {
        "display": "智档通 · RAG 知识库",
        "blurb": "LangGraph + FastAPI 构建的企业级 RAG 知识问答系统，"
                 "覆盖文档解析、向量检索与多轮问答编排。",
    },
    "cloudmusic": {
        "display": "韵动轨迹 · 云音乐",
        "blurb": "微信小程序 + 云开发的音乐应用，提供在线播放、歌单管理与听歌轨迹。",
    },
}


# ---------------------------------------------------------------------------
# 1) 头图
# ---------------------------------------------------------------------------
def banner(mode: str) -> str:
    p = PAL[mode]
    W, H = 1000, 300
    # 这里的扫光显式用白色：它被裁进名字的字形轮廓，实际走在 accent→accent2
    # 的深金渐变字上（不是浅底），白色才有「金属高光」的观感。
    # 不透明度从 0.16 提到 0.30——原值是为深色版那两个亮金调的，
    # 浅色系把强调色压深后，0.16 在白底衬托下几乎看不见。
    defs = (bg_grad(p, "bg") + accent_grad(p, "nameGrad")
            + sheen(p, color="#FFFFFF", opacity="0.30")
            + f'<clipPath id="round"><rect width="{W}" height="{H}" rx="20"/></clipPath>'
            # 把扫光裁进中文名的字形轮廓里：光只在字上走，不糊满整张图。
            + '<clipPath id="nameClip">'
              f'<text x="500" y="192" text-anchor="middle" font-family="{FONT}" '
              f'font-size="76" font-weight="800" letter-spacing="1">'
              f'{esc(CFG["name_zh"])}</text></clipPath>')

    n = len(CFG["chips"])
    # chip 宽度按文字实测量，而不是写死——中英文混排下写死会留白或截断
    widths = [max(text_w(c, 14) + 40, 96) for c in CFG["chips"]]
    gap = 10
    x0 = (W - (sum(widths) + gap * (n - 1))) / 2
    chips, cx = [], x0
    for i, (chip, cw) in enumerate(zip(CFG["chips"], widths)):
        chips.append(fadein(
            f'<rect x="{cx:.0f}" y="232" width="{cw:.0f}" height="32" rx="16" '
            f'fill="{p["accent"]}" fill-opacity="0.07" '
            f'stroke="{p["accent"]}" stroke-opacity="0.40"/>'
            f'<text x="{cx + cw/2:.0f}" y="253" text-anchor="middle" '
            f'font-family="{FONT}" font-size="14" fill="{p["muted"]}">{esc(chip)}</text>',
            delay=0.9 + i * 0.14))
        cx += cw + gap

    body = (
        f'<g clip-path="url(#round)">'
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>'
        # 顶部一条极细的强调色高光线，替代整片极光
        f'<rect x="0" y="0" width="{W}" height="1.5" fill="url(#nameGrad)" opacity="0.55"/>'
        # 上：英文小字（大字距，克制的排印感）
        + fadein(
            f'<text x="500" y="96" text-anchor="middle" font-family="{FONT}" '
            f'font-size="15" font-weight="600" letter-spacing="9" '
            f'fill="{p["accent"]}">{esc(CFG["name_en"])}</text>', 0.15)
        # 中：主名（渐变字）
        + fadein(
            f'<text x="500" y="192" text-anchor="middle" font-family="{FONT}" '
            f'font-size="76" font-weight="800" letter-spacing="1" '
            f'fill="url(#nameGrad)">{esc(CFG["name_zh"])}</text>', 0.4)
        # 扫光裁进字形
        + sweep(W, H, dur=9.0, clip="nameClip")
        # 下：handle + chips
        + fadein(
            f'<text x="500" y="216" text-anchor="middle" font-family="{FONT}" '
            f'font-size="13" letter-spacing="2" fill="{p["dim"]}">'
            f'{esc(CFG["handle"])}</text>', 0.62)
        + "".join(chips)
        + '</g>'
        + f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="20" '
          f'stroke="{p["stroke"]}" stroke-opacity="0.9"/>'
    )
    return svg(W, H, f'{CFG["name_zh"]} · {CFG["handle"]}', defs, body)


# ---------------------------------------------------------------------------
# 2) 打字机
# ---------------------------------------------------------------------------
def typing(mode: str) -> str:
    p = PAL[mode]
    W, H = 1000, 92
    phrases = CFG["typing"]
    n = len(phrases)
    cycle = 3.6 * n
    x0, size = 76, 21
    defs = [bg_grad(p, "tbg"), accent_grad(p, "tline"), sheen(p)]
    body = [panel(p, "tbg", W, H, 16),
            # 左侧竖条：整张图唯一的强调色块，做视觉锚点
            f'<rect x="26" y="24" width="3" height="44" rx="1.5" fill="url(#tline)">'
            f'<animate attributeName="height" values="44;28;44" dur="4.2s" '
            f'repeatCount="indefinite"/>'
            f'<animate attributeName="y" values="24;32;24" dur="4.2s" '
            f'repeatCount="indefinite"/></rect>',
            f'<text x="46" y="58" font-family="{FONT}" font-size="20" font-weight="700" '
            f'fill="{p["accent"]}">&#10095;</text>']
    for i, ph in enumerate(phrases):
        tw = text_w(ph, size)
        start, type_end = i / n, i / n + 0.09
        hold_end = (i + 1) / n - 0.04
        reset_end = hold_end + 0.014
        # 关键：收缩必须瞬时完成。若把收缩的 keyTime 一路拉到 1.0，
        # 收缩会横跨整个周期，导致多句文字长时间重叠。
        kt = f"0;{start:.3f};{type_end:.3f};{hold_end:.3f};{reset_end:.3f};1"
        if i == 0:  # 首句起点与 0 重合，keyTimes 必须严格递增
            kt = f"0.000;0.001;{type_end:.3f};{hold_end:.3f};{reset_end:.3f};1"
        defs.append(
            f'<clipPath id="tc{i}"><rect x="{x0}" y="16" width="0" height="58">'
            f'<animate attributeName="width" '
            f'values="0;0;{tw:.0f};{tw + 10:.0f};0;0" '
            f'keyTimes="{kt}" dur="{cycle}s" repeatCount="indefinite"/></rect></clipPath>')
        body.append(
            f'<g clip-path="url(#tc{i})">'
            f'<text x="{x0}" y="58" font-family="{FONT}" font-size="{size}" '
            f'fill="{p["text"]}">{esc(ph)}</text>'
            f'<rect x="{x0 + tw + 5:.0f}" y="34" width="2" height="25" fill="{p["accent"]}">'
            f'<animate attributeName="opacity" values="1;0;1;0" dur="1.2s" '
            f'repeatCount="indefinite"/></rect></g>')
    return svg(W, H, "自我介绍打字动效", "".join(defs), "".join(body))


# ---------------------------------------------------------------------------
# 3) 分隔线
# ---------------------------------------------------------------------------
def divider(mode: str) -> str:
    p = PAL[mode]
    W, H = 1000, 24
    defs = (f'<linearGradient id="dline" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{p["stroke"]}" stop-opacity="0"/>'
            f'<stop offset="0.5" stop-color="{p["accent"]}" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="{p["stroke"]}" stop-opacity="0"/></linearGradient>'
            + sheen(p, "dsheen"))
    body = (f'<rect x="0" y="11" width="{W}" height="1.5" rx="0.75" fill="url(#dline)"/>'
            '<rect x="-140" y="10" width="140" height="4" rx="2" fill="url(#dsheen)">'
            '<animate attributeName="x" values="-140;1000" dur="7s" '
            'repeatCount="indefinite"/></rect>')
    return svg(W, H, "分隔线", defs, body)


# ---------------------------------------------------------------------------
# 4) 数据卡
# ---------------------------------------------------------------------------
def stats(mode: str, data: dict) -> str:
    """四项核心数据。

    刻意不放「近一年公开贡献」：实测过去一年只有 11 次，
    放进头版数据卡等于把最弱的指标摆在最显眼的位置。
    换成 CSDN 阅读量（23W+）——这是真实且体面的数字，只是抓不到，写死。
    """
    p = PAL[mode]
    W, H = 1000, 118
    every = all_repos(data)
    stars = sum(r["stars"] for r in every)
    forks = sum(r["forks"] for r in every)
    items = [
        ("获得星标", f"{stars}", "★", p["accent"]),
        ("开源项目", f"{len(every)}", "▣", p["accent"]),
        ("被 Fork", f"{forks}", "⑂", p["accent"]),
        ("CSDN 阅读", MANUAL["csdn_reads"], "▤", p["accent"]),
    ]
    defs = bg_grad(p, "sbg") + sheen(p)
    body = [panel(p, "sbg", W, H, 16)]
    bw = W / len(items)
    for i, (label, value, mark, color) in enumerate(items):
        cx = bw * (i + 0.5)
        if i:
            body.append(f'<line x1="{bw*i:.0f}" y1="28" x2="{bw*i:.0f}" y2="{H-28}" '
                        f'stroke="{p["stroke"]}" stroke-opacity="0.75"/>')
        # 数字字号按字符数自适应：23W+ 有 4 个字符，30 号会挤，缩到 26
        fs = 30 if len(value) <= 3 else 25
        body.append(fadein(
            f'<text x="{cx:.0f}" y="{H/2 - 4:.0f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="{fs}" font-weight="800" '
            f'fill="{color}">{esc(value)}</text>'
            f'<text x="{cx:.0f}" y="{H/2 + 26:.0f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="13" fill="{p["muted"]}">{esc(label)}</text>'
            f'<text x="{cx:.0f}" y="{H/2 + 46:.0f}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="11" fill="{p["dim"]}" opacity="0.7">'
            f'{esc(mark)}</text>', delay=0.12 * i))
    # 顶缘一道呼吸光点，表示「数据由 Action 每日刷新」
    body.append(pulse(bw * 0.5, 14, p["accent"], r=2.4, dur=4.0))
    return svg(W, H, "数据概览", defs, "".join(body))


# ---------------------------------------------------------------------------
# 5) 贡献热力图（方格，非柱状）
# ---------------------------------------------------------------------------
def activity(mode: str, data: dict) -> str:
    """过去一年逐日贡献，画成 GitHub 风格的方格热力图。

    为什么不是柱状图（原项目用的是柱状图）：
    柱状图假设数据密集。原项目账号注册 24 天、56 次贡献，柱子是满的；
    本账号近一年 369 天里只有 10 天有提交，画成柱状图会得到
    369 根柱子中 359 根为零高度——那不是「数据少」，是「图坏了」。
    热力图对稀疏是正常语义（GitHub 自己的贡献墙就是这样），
    同样的数据换成方格，观感从破图变成「有节奏的活跃」。
    """
    p = PAL[mode]
    heat = HEAT[mode]
    W = 1000
    pl, pr, pt, pb = 40, 40, 62, 44
    pw = W - pl - pr
    c = data["contributions"]
    days = c.get("days") or []

    # 补齐到整周：GitHub 贡献墙按周分列，缺的日期用空格子占位，
    # 否则第一列/最后一列会错位，月份标签也跟着错。
    if days:
        first = date.fromisoformat(days[0]["date"])
        first -= timedelta(days=first.weekday())
        by_date = {d["date"]: d["count"] for d in days}
        grid = []
        cur = first
        while cur.isoformat() <= days[-1]["date"]:
            iso = cur.isoformat()
            grid.append((iso, by_date.get(iso, 0)))
            cur += timedelta(days=1)
    else:
        grid = []

    weeks = [grid[i:i + 7] for i in range(0, len(grid), 7)]
    nw = len(weeks) or 1
    step = min(pw / nw, 17.0)
    cell = max(step - 3.0, 4.0)
    H = int(pt + step * 7 + pb)

    maxc = max([n for _, n in grid] + [1])
    total = sum(n for _, n in grid)
    active = sum(1 for _, n in grid if n > 0)

    defs = bg_grad(p, "abg") + sheen(p)
    body = [panel(p, "abg", W, H, 16)]
    body.append(
        f'<text x="{pl}" y="28" font-family="{FONT}" font-size="15" font-weight="700" '
        f'fill="{p["text"]}">贡献轨迹</text>'
        f'<text x="{W-pr}" y="28" text-anchor="end" font-family="{FONT}" font-size="12" '
        f'fill="{p["muted"]}">近一年 {total} 次提交 · {active} 天活跃</text>')
    body.append(
        f'<text x="{pl}" y="47" font-family="{FONT}" font-size="11" fill="{p["dim"]}">'
        f'开源产出集中在项目迭代期，而非每日打卡</text>')

    # 方格：按列（周）绘制，列内 7 行（周一到周日）
    maxlvl = max(len(heat) - 1, 1)
    for wi, wk in enumerate(weeks):
        x = pl + wi * step
        for di, (iso, cnt) in enumerate(wk):
            y = pt + di * step
            # 颜色按 count 在 [0, maxc] 内归一到 0-4 档。
            # 不直接用 GitHub 给的 data-level：它按全站历史分位算，
            # 对「一年只有 10 天有提交」这种分布会把所有活跃日压到最低档，
            # 热力图会看起来全灰，读不出节奏。
            # 加了 0.5 的偏置，保证只要非零就至少落到中档，格子明显可见。
            lvl = min(int(cnt / maxc * maxlvl + 0.5), maxlvl) if cnt else 0
            col = heat[lvl]
            op = 1.0 if cnt else 0.55
            body.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" '
                f'rx="{min(cell/4, 3):.1f}" fill="{col}" opacity="{op}">'
                f'<animate attributeName="opacity" from="0" to="{op}" dur="0.5s" '
                f'begin="{min(wi * 0.014, 1.0):.2f}s" fill="freeze"/></rect>')

    # 月份标签：只在月份变化时打一次，避免 53 个标签糊成一团
    prev = None
    for wi, wk in enumerate(weeks):
        if not wk:
            continue
        m = wk[0][0][5:7]
        if m != prev:
            x = pl + wi * step
            if x < W - pr - 20:
                body.append(f'<text x="{x:.1f}" y="{pt - 10}" font-family="{FONT}" '
                            f'font-size="10" fill="{p["dim"]}">{int(m)}月</text>')
            prev = m

    # 右下：图例（少 → 多），跟 GitHub 一致，降低阅读门槛
    lx = W - pr - 5 * (cell + 4) - 34
    ly = pt + step * 7 + 14
    body.append(f'<text x="{lx - 8}" y="{ly + cell - 1:.1f}" text-anchor="end" '
                f'font-family="{FONT}" font-size="10" fill="{p["dim"]}">少</text>')
    for i in range(len(heat)):
        body.append(f'<rect x="{lx + i * (cell + 4):.1f}" y="{ly:.1f}" '
                    f'width="{cell:.1f}" height="{cell:.1f}" rx="{min(cell/4,3):.1f}" '
                    f'fill="{heat[i]}" opacity="{1.0 if i else 0.55}"/>')
    body.append(f'<text x="{lx + len(heat) * (cell + 4) + 2:.1f}" y="{ly + cell - 1:.1f}" '
                f'font-family="{FONT}" font-size="10" fill="{p["dim"]}">多</text>')
    return svg(W, H, "贡献热力图", defs, "".join(body))


# ---------------------------------------------------------------------------
# 6) 章节标题
# ---------------------------------------------------------------------------
SECTIONS = [
    ("about", "about", "关于我", "About"),
    ("stack", "stack", "技术栈", "Tech Stack"),
    ("projects", "projects", "在做的东西", "Projects"),
    ("stats", "stats", "数据与轨迹", "Stats & Activity"),
    ("focus", "focus", "方向与投入", "Focus"),
    ("links", "links", "找到我", "Find Me"),
]


def header(icon_name: str, zh: str, en: str, mode: str) -> str:
    p = PAL[mode]
    W, H = 1000, 88
    defs = (f'<linearGradient id="hzh" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{p["text"]}"/>'
            f'<stop offset="1" stop-color="{p["accent"]}"/></linearGradient>'
            f'<linearGradient id="hrule" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{p["accent"]}" stop-opacity="0.7"/>'
            f'<stop offset="0.35" stop-color="{p["stroke"]}" stop-opacity="0.9"/>'
            f'<stop offset="1" stop-color="{p["stroke"]}" stop-opacity="0"/></linearGradient>'
            + sheen(p, "hsheen")
            + f'<clipPath id="hbox"><rect x="0" y="16" width="52" height="52" rx="14"/></clipPath>')
    body = [
        # 图标胶囊：细描边 + 极淡底，不做填充色块（填充色块会显得像 App 图标）
        f'<rect x="0.5" y="16.5" width="51" height="51" rx="14" '
        f'fill="{p["accent"]}" fill-opacity="0.06" '
        f'stroke="{p["accent"]}" stroke-opacity="0.35"/>',
        icon(icon_name, 14, 28, 24, p["accent"], sw=1.7),
        # 中文大标题：从主文字色渐变到强调色，只有这一处用渐变
        f'<text x="72" y="47" font-family="{FONT}" font-size="28" font-weight="800" '
        f'fill="url(#hzh)">{esc(zh)}</text>'
        # 英文小标：大字距，压在主标题下方
        f'<text x="74" y="67" font-family="{FONT}" font-size="10.5" font-weight="600" '
        f'letter-spacing="3.4" fill="{p["dim"]}">{esc(en.upper())}</text>'
        # 底部细线 + 慢扫光
        f'<rect x="0" y="85" width="{W}" height="1.5" rx="0.75" fill="url(#hrule)"/>'
        '<rect x="-200" y="84" width="200" height="4" rx="2" fill="url(#hsheen)">'
        '<animate attributeName="x" values="-200;1000" dur="7s" '
        'repeatCount="indefinite"/></rect>',
    ]
    return svg(W, H, f'{zh} · {en}', defs, "".join(body))


# ---------------------------------------------------------------------------
# 7) 终端卡片（逐行打字）
# ---------------------------------------------------------------------------
TERM_LINES = [
    ("$ whoami", "cmd"),
    ("lenyan · Java 全栈工程师 @ 广州", "out"),
    ("$ cat stack.txt", "cmd"),
    ("Java 21 · Spring Boot 3 · Vue 3 · MySQL · Redis", "out"),
    ("$ ls ~/projects", "cmd"),
    ("len-ai-agent/   lendada/   lenrpc/", "out"),
]


def terminal(mode: str) -> str:
    p = PAL[mode]
    W = 1000
    line_h, top = 33, 72
    H = top + line_h * len(TERM_LINES) + 20
    cycle = 14.0
    defs, body = [bg_grad(p, "tmbg"), accent_grad(p, "tmtab"), sheen(p)], []
    body.append(panel(p, "tmbg", W, H, 16))
    # 标题栏：用一条底边线分隔，而不是整条填充色（填充色太重）
    body.append(f'<line x1="0" y1="44" x2="{W}" y2="44" stroke="{p["stroke"]}" '
                f'stroke-opacity="0.8"/>')
    # 三个圆点改成同色不同透明度：红黄绿是 macOS 的语义色，
    # 与单色调冲突，改成强调色的三档明度更统一。
    for i, op in enumerate((0.85, 0.5, 0.28)):
        body.append(f'<circle cx="{32 + i*20}" cy="22" r="5" fill="{p["accent"]}" '
                    f'opacity="{op}"/>')
    body.append(f'<text x="{W/2}" y="27" text-anchor="middle" font-family="{FONT}" '
                f'font-size="12" fill="{p["dim"]}">lenyan@dev — zsh</text>')

    for i, (text, kind) in enumerate(TERM_LINES):
        y = top + i * line_h
        color = p["accent"] if kind == "cmd" else p["text"]
        weight = "600" if kind == "cmd" else "400"
        tw = text_w(text, 15.5) + 10
        t0 = 0.4 + i * 0.66
        dur = 0.36
        kt = f"0;{t0/cycle:.4f};{(t0+dur)/cycle:.4f};0.997;1"
        defs.append(
            f'<clipPath id="tm{i}"><rect x="32" y="{y-18}" width="0" height="26">'
            f'<animate attributeName="width" values="0;0;{tw:.0f};{tw:.0f};0" '
            f'keyTimes="{kt}" dur="{cycle}s" repeatCount="indefinite"/></rect></clipPath>')
        body.append(
            f'<g clip-path="url(#tm{i})"><text x="32" y="{y}" font-family="{FONT}" '
            f'font-size="15.5" font-weight="{weight}" fill="{color}">{esc(text)}</text></g>')
    # 末行闪烁光标
    last_y = top + len(TERM_LINES) * line_h - 16
    body.append(f'<rect x="32" y="{last_y}" width="8.5" height="17" fill="{p["accent"]}">'
                f'<animate attributeName="opacity" values="1;1;0;0;1" '
                f'keyTimes="0;0.44;0.46;0.98;1" dur="{cycle}s" '
                f'repeatCount="indefinite"/></rect>')
    return svg(W, H, "终端卡片", "".join(defs), "".join(body))


# ---------------------------------------------------------------------------
# 8) 语言构成环形图
# ---------------------------------------------------------------------------
def lang(mode: str, data: dict) -> str:
    p = PAL[mode]
    W, H = 1000, 232
    repos = project_repos(data)
    agg: dict[str, int] = {}
    for r in repos:
        # langs 抓不到时（REST 限额）退化成用主语言，
        # 否则环形图会因为总字节数为 0 而画出一个空圈。
        langs = r.get("langs") or {}
        if not langs and r.get("lang"):
            langs = {r["lang"]: 1}
        for k, v in langs.items():
            agg[k] = agg.get(k, 0) + v
    items = sorted(agg.items(), key=lambda kv: -kv[1])
    top5, rest = items[:5], sum(v for _, v in items[5:])
    segs = [[n, v] for n, v in top5]
    if rest:
        segs.append(["其他", rest])
    total = sum(v for _, v in segs) or 1

    cx, cy, r, sw = 132, 124, 68, 20
    circ = 2 * 3.141592653589793 * r
    defs, body = [bg_grad(p, "lgbg"), sheen(p)], [panel(p, "lgbg", W, H, 16)]
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{p["stroke"]}" '
                f'stroke-opacity="0.55" stroke-width="{sw}"/>')
    acc = 0.0
    for i, (name, val) in enumerate(segs):
        frac = val / total
        # 段间留 3px 缺口：段与段贴死会糊成一个圈，缺口让每段可读
        seg_len = max(circ * frac - 3.0, 1.0)
        color = LANG_COLOR[mode].get(
            name, p["accentSoft"] if name == "其他" else p["accent"])
        rot = -90 + 360 * acc
        acc += frac
        body.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-dasharray="0 {circ:.1f}" '
            f'transform="rotate({rot:.2f} {cx} {cy})" stroke-linecap="butt" '
            f'opacity="0.92">'
            f'<animate attributeName="stroke-dasharray" values="0 {circ:.1f};{seg_len:.1f} '
            f'{circ-seg_len:.1f}" dur="0.9s" begin="{0.15 + i*0.12:.2f}s" fill="freeze"/>'
            f'</circle>')
    # 圆心：主语言占比
    top_name, top_val = segs[0]
    body.append(f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="29" font-weight="800" fill="{p["accent"]}">'
                f'{top_val*100/total:.0f}%</text>'
                f'<text x="{cx}" y="{cy + 20}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="12" fill="{p["muted"]}">{esc(top_name)}</text>')
    # 右侧图例
    body.append(f'<text x="290" y="50" font-family="{FONT}" font-size="15" font-weight="700" '
                f'fill="{p["text"]}">代码语言构成</text>'
                f'<text x="{W-40}" y="50" text-anchor="end" font-family="{FONT}" '
                f'font-size="12" fill="{p["dim"]}">按仓库字节统计 · '
                f'{len(repos)} 个展示项目</text>')
    body.append(f'<line x1="290" y1="66" x2="{W-40}" y2="66" stroke="{p["stroke"]}" '
                f'stroke-opacity="0.7"/>')
    # 图例比例线按「最大占比」归一，而不是按 100%。
    # 若主语言占 70%，按 100% 归一会画出一条几乎填满的线，
    # 而 3% 的语言线短到看不见，段与段之间失去参照意义。
    max_pct = max((v * 100 / total for _, v in segs), default=1.0) or 1.0
    for i, (name, val) in enumerate(segs):
        col = i % 2
        row = i // 2
        x = 290 + col * 344
        y = 102 + row * 40
        color = LANG_COLOR[mode].get(
            name, p["accentSoft"] if name == "其他" else p["accent"])
        pct = val * 100 / total
        # 色块用圆角方而不是圆点：与整页的方形语言（方格热力图、胶囊标签）一致
        body.append(fadein(
            f'<rect x="{x}" y="{y-10}" width="10" height="10" rx="2.5" fill="{color}"/>'
            f'<text x="{x+20}" y="{y}" font-family="{FONT}" font-size="13.5" '
            f'fill="{p["text"]}">{esc(name)}</text>'
            f'<text x="{x+318}" y="{y}" text-anchor="end" font-family="{FONT}" '
            f'font-size="13" font-weight="700" fill="{p["muted"]}">{pct:.1f}%</text>'
            # 名字后面跟一条细的比例线，让百分比有视觉长度参照
            f'<rect x="{x+20}" y="{y+8}" width="298" height="1.5" rx="0.75" '
            f'fill="{p["stroke"]}" opacity="0.6"/>'
            f'<rect x="{x+20}" y="{y+8}" width="0" height="1.5" rx="0.75" fill="{color}">'
            f'<animate attributeName="width" from="0" '
            f'to="{298 * min(pct / max_pct, 1.0):.1f}" '
            f'dur="0.8s" begin="{0.3+i*0.1:.2f}s" fill="freeze"/></rect>',
            delay=0.25 + i * 0.08))
    return svg(W, H, "代码语言构成", "".join(defs), "".join(body))




# ---------------------------------------------------------------------------
# 9) 方向自评条
# ---------------------------------------------------------------------------
def focus(mode: str) -> str:
    """方向占比条。之所以自绘而不是手写 ASCII：
    █ / ░ 属于东亚「歧义宽度」字符，不同字体下宽度不一致，
    用 ASCII 画的进度条在部分用户机器上会错位得很明显。
    """
    p = PAL[mode]
    rows = CFG["focus"]
    W = 1000
    pad_t, row_h, pad_b = 30, 50, 28
    H = pad_t + row_h * len(rows) + pad_b
    lx, bar_x, bar_w = 40, 322, 520
    defs = [bg_grad(p, "fbg"), accent_grad(p, "fbar"), sheen(p)]
    body = [panel(p, "fbg", W, H, 16)]
    for i, (label, pct) in enumerate(rows):
        y = pad_t + i * row_h
        fill_w = bar_w * pct / 100
        body.append(
            f'<text x="{lx}" y="{y + 16}" font-family="{FONT}" font-size="13.5" '
            f'fill="{p["muted"]}">{esc(label)}</text>'
            # 轨道：细一点（8px），比常见的粗进度条更克制
            f'<rect x="{bar_x}" y="{y + 8}" width="{bar_w}" height="8" rx="4" '
            f'fill="{p["stroke"]}" fill-opacity="0.65"/>'
            f'<rect x="{bar_x}" y="{y + 8}" width="0" height="8" rx="4" fill="url(#fbar)">'
            f'<animate attributeName="width" from="0" to="{fill_w:.1f}" dur="1.1s" '
            f'begin="{0.25 + i * 0.13:.2f}s" fill="freeze" calcMode="spline" '
            f'keySplines="0.2 0 0.2 1"/></rect>'
            f'<circle cx="{bar_x + fill_w:.1f}" cy="{y + 12}" r="3.5" '
            f'fill="{p["accent2"]}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.95" dur="0.4s" '
            f'begin="{1.3 + i * 0.13:.2f}s" fill="freeze"/>'
            f'<animate attributeName="r" values="3.5;5;3.5" dur="3.6s" '
            f'begin="{1.6 + i * 0.13:.2f}s" repeatCount="indefinite"/></circle>'
            f'<text x="{bar_x + bar_w + 92}" y="{y + 17}" text-anchor="end" '
            f'font-family="{FONT}" font-size="13.5" font-weight="700" '
            f'fill="{p["accent"]}">{pct}%</text>'
        )
    return svg(W, H, "方向与投入", defs, "".join(body))


# ---------------------------------------------------------------------------
# 10) 项目卡
# ---------------------------------------------------------------------------
def _chips(p: dict, topics: list[str], x0: float, y: float, max_x: float) -> list[str]:
    """把 topic 画成一排胶囊。宽度不够时最后收一个 +N，避免溢出卡片。

    仓库的 topic 是英文短词，和中文 blurb 混排在单色调卡片上容易显乱，
    所以只取前 4 个，且统一用低饱和描边样式，不给每个 topic 单独配色。
    """
    out: list[str] = []
    x, shown = x0, 0
    topics = topics[:4]
    for i, t in enumerate(topics):
        w = text_w(t, 11) + 22
        # 还有剩余项时，预留出 +N 胶囊的位置
        reserve = 0 if i == len(topics) - 1 else text_w("+9", 11) + 30
        if x + w + reserve > max_x:
            break
        out.append(
            f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="23" rx="11.5" '
            f'fill="{p["chipBg"]}" stroke="{p["stroke"]}"/>'
            f'<text x="{x + w / 2:.0f}" y="{y + 15.5}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="11" fill="{p["dim"]}">{esc(t)}</text>')
        x += w + 7
        shown += 1
    rest = len(topics) - shown
    if rest > 0:
        label = f"+{rest}"
        w = text_w(label, 11) + 22
        out.append(
            f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="23" rx="11.5" '
            f'fill="none" stroke="{p["stroke"]}" stroke-dasharray="3 3"/>'
            f'<text x="{x + w / 2:.0f}" y="{y + 15.5}" text-anchor="middle" '
            f'font-family="{FONT}" font-size="11" fill="{p["dim"]}">{label}</text>')
    return out


def project(mode: str, repo: dict) -> str:
    p = PAL[mode]
    topics = repo.get("topics") or []
    # 有 topic 时卡片高一点，多出一行放标签；没有就不留空白
    W, H = 1000, 200 if topics else 166
    meta = REPO_META.get(repo["name"], {})
    display = meta.get("display", repo["name"])
    blurb = meta.get("blurb") or repo["desc"] or "这个仓库还没有写简介。"
    lic = repo["license"] or "未声明许可"
    updated = repo["pushed_at"][:10]
    # 没识别出主语言时给个中性占位，否则卡片上会出现一个孤零零的色点和空文字
    lang = repo["lang"] or "未识别"
    lcolor = LANG_COLOR[mode].get(repo["lang"], p["accent"])

    defs = (bg_grad(p, "pbg") + accent_grad(p, "pav") + sheen(p, "pshine")
            + f'<clipPath id="pclip"><rect width="{W}" height="{H}" rx="16"/></clipPath>')
    body = [panel(p, "pbg", W, H, 16)]
    # 左侧一道强调色竖条：替代原项目的渐变大色块，视觉重量更轻
    body.append(f'<g clip-path="url(#pclip)">'
                f'<rect x="0" y="0" width="3" height="{H}" fill="url(#pav)" '
                f'opacity="0.85"/></g>')
    # 扫光：慢速，且透明度比原项目低（0.30 -> 0.10），避免闪眼
    body.append(f'<g clip-path="url(#pclip)"><rect x="-260" y="-40" width="200" '
                f'height="{H+80}" fill="url(#pshine)" transform="skewX(-18)">'
                f'<animate attributeName="x" values="-260;1120" dur="11s" begin="0.6s" '
                f'repeatCount="indefinite"/></rect></g>')
    # 首字母方块：细描边 + 淡底，不用实心渐变（实心块在单色调里太跳）
    body.append(f'<rect x="34" y="34" width="66" height="66" rx="16" '
                f'fill="{p["accent"]}" fill-opacity="0.08" '
                f'stroke="{p["accent"]}" stroke-opacity="0.38"/>'
                f'<text x="67" y="80" text-anchor="middle" font-family="{FONT}" '
                f'font-size="30" font-weight="800" fill="{p["accent"]}">'
                f'{esc(display[0].upper())}</text>')
    # 标题
    body.append(f'<text x="122" y="58" font-family="{FONT}" font-size="22" '
                f'font-weight="800" fill="{p["text"]}">{esc(display)}</text>')
    # 元信息行
    mx = 122
    body.append(f'<rect x="{mx}" y="{76-8:.0f}" width="9" height="9" rx="2.5" '
                f'fill="{lcolor}"/>')
    body.append(f'<text x="{mx+15}" y="80" font-family="{FONT}" font-size="12.5" '
                f'fill="{p["muted"]}">{esc(lang)}</text>')
    mx += 15 + text_w(lang, 12.5) + 22
    for ico, val in (("★", repo["stars"]), ("⑂", repo["forks"])):
        body.append(f'<text x="{mx}" y="80" font-family="{FONT}" font-size="12.5" '
                    f'fill="{p["muted"]}">{ico} {val}</text>')
        mx += 14 + text_w(f"{ico} {val}", 12.5) + 20
    body.append(f'<text x="{mx}" y="80" font-family="{FONT}" font-size="12.5" '
                f'fill="{p["dim"]}">{esc(lic)} · 更新于 {updated}</text>')
    # 简介：最多两行，超出截断
    lines = wrap(blurb, 790, 13.5)[:2]
    if len(wrap(blurb, 790, 13.5)) > 2 and lines:
        lines[1] = lines[1].rstrip() + "…"
    for i, line in enumerate(lines):
        body.append(f'<text x="122" y="{112 + i*24}" font-family="{FONT}" '
                    f'font-size="13.5" fill="{p["muted"]}">{esc(line)}</text>')
    if topics:
        body.extend(_chips(p, topics, 122, 152, W - 60))
    # 右上箭头：提示整张图可点
    body.append(f'<text x="{W-34}" y="66" text-anchor="end" font-family="{FONT}" '
                f'font-size="20" fill="{p["accent"]}" opacity="0.75">&#8594;</text>')
    return svg(W, H, f'{display} 项目卡', defs, "".join(body))


# ---------------------------------------------------------------------------
# 11) 链接卡
# ---------------------------------------------------------------------------
LINK_ROWS = [
    ("博客", "CSDN · lenyan~", "23W+ 阅读", "https://blog.csdn.net/jgk666666"),
    ("公众号", "程序员凯凯", "技术分享", "https://mp.weixin.qq.com/s/utI7LVBN0JyXdZyqhRA_ww"),
    ("算法", "LeetCode 解题仓库", "按专题归档", "https://github.com/lenyanjgk/leetcode-solution"),
    ("社区", "编程导航", "知识星球", "https://www.codefather.cn/user/1738833787455823874"),
]


def links(mode: str) -> str:
    """四个外链，画成 2x2 卡片。

    原 README 把博客/公众号/项目/算法全塞进四行密集链接，
    一行七八个 <a>，在手机上根本点不准。改成 2x2 大方格，
    每格一个去处 + 一句说明，点击区域从十几个字变成半屏宽。
    """
    p = PAL[mode]
    W, H = 1000, 216
    defs = [bg_grad(p, "lbg"), accent_grad(p, "lav"), sheen(p)]
    body = [panel(p, "lbg", W, H, 16)]
    cw, ch = 452, 78
    for i, (tag, title, note, _url) in enumerate(LINK_ROWS):
        col, row = i % 2, i // 2
        x = 32 + col * (cw + 32)
        y = 30 + row * (ch + 30)
        body.append(fadein(
            f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="13" '
            f'fill="{p["chipBg"]}" stroke="{p["stroke"]}"/>'
            # 左侧竖条做视觉锚点，与项目卡同一语言
            f'<rect x="{x}" y="{y + 18}" width="2.5" height="{ch - 36}" rx="1.25" '
            f'fill="{p["accent"]}" opacity="0.75"/>'
            f'<text x="{x + 20}" y="{y + 26}" font-family="{FONT}" font-size="10.5" '
            f'font-weight="700" letter-spacing="2" fill="{p["accent"]}">{esc(tag)}</text>'
            f'<text x="{x + 20}" y="{y + 50}" font-family="{FONT}" font-size="16.5" '
            f'font-weight="700" fill="{p["text"]}">{esc(title)}</text>'
            f'<text x="{x + cw - 18}" y="{y + 50}" text-anchor="end" font-family="{FONT}" '
            f'font-size="12" fill="{p["dim"]}">{esc(note)}</text>'
            f'<text x="{x + cw - 18}" y="{y + 27}" text-anchor="end" font-family="{FONT}" '
            f'font-size="14" fill="{p["accent"]}" opacity="0.7">&#8599;</text>',
            delay=0.15 * i))
    return svg(W, H, "找到我", "".join(defs), "".join(body))


# ---------------------------------------------------------------------------
# 工具：命名
# ---------------------------------------------------------------------------
def slug(s: str) -> str:
    """仓库名 -> 素材文件名用的 slug（与 make_readme.py 共用，保持唯一来源）。"""
    return s.lower().replace("-", "").replace(" ", "").replace("_", "")


def display_name(repo: dict) -> str:
    return REPO_META.get(repo["name"], {}).get("display", repo["name"])


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)

    jobs: dict = {
        "banner": lambda m: banner(m),
        "typing": lambda m: typing(m),
        "divider": lambda m: divider(m),
        "terminal": lambda m: terminal(m),
        "stats": lambda m: stats(m, data),
        "activity": lambda m: activity(m, data),
        "lang": lambda m: lang(m, data),
        "focus": lambda m: focus(m),
        "links": lambda m: links(m),
    }
    # 用默认参数绑定循环变量：直接闭包捕获 i/zh/en 会让所有标题都画成最后一个。
    for s, ic, zh, en in SECTIONS:
        jobs[f"hdr-{s}"] = (lambda i, z, e: (lambda m: header(i, z, e, m)))(ic, zh, en)
    for r in project_repos(data):
        jobs[f"proj-{slug(r['name'])}"] = (lambda rr: (lambda m: project(m, rr)))(r)

    total = 0
    expected = set()
    for name, fn in jobs.items():
        for mode in ("dark", "light"):
            fname = f"{name}-{mode}.svg"
            expected.add(fname)
            path = os.path.join(OUT, fname)
            content = fn(mode)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            total += 1
    # 清掉不再生成的旧素材（比如仓库被删/改名后残留的项目卡），
    # 否则 assets/ 里会留下永远不会被引用的孤儿文件
    removed = []
    if os.path.isdir(OUT):
        for f in sorted(os.listdir(OUT)):
            if f.endswith(".svg") and f not in expected:
                os.remove(os.path.join(OUT, f))
                removed.append(f)
    print(f"{total} files -> {OUT}")
    if removed:
        print(f"  清理孤儿素材 {len(removed)} 个: {', '.join(removed)}")


if __name__ == "__main__":
    main()
