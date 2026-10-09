# -*- coding: utf-8 -*-
"""从 data/profile.json 生成 README.md。

为什么 README 也要生成而不是手写：
项目卡是按仓库逐个生成的素材，手写 README 意味着每加一个仓库
都要手动补一段 <picture> 块（漏了就会出现「有素材但主页不显示」）。
生成之后，新增仓库会被每月定时运行的 Action 自动带进主页。

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

from make_assets import CFG, DATA, MANUAL, ROOT, display_name, project_repos, slug

OUT = os.path.join(ROOT, "README.md")

# 静态文案（与具体数据无关、用户希望固定展示的内容）
# 这些写死后，每月 Action 刷新时都会原样复刻。
ABOUT_LINE_BLOG = (
    f'- 📖博客：[CSDN📚]({MANUAL["csdn_url"]})（{MANUAL["csdn_reads"]}阅读）、'
    f'公众号:[程序员凯凯]({MANUAL["wechat_mp"]})、'
    f'[编程导航🌟]({MANUAL["codefather"]})（知识分享和日常记录）'
)

ABOUT_LINE_PROJECTS = (
    '- ⚔️实践项目：<a href="https://github.com/lenyanjgk/lendada" target="_blank">lendada-智慧答应用答题平台</a>  | '
    '<a href="https://github.com/lenyanjgk/len-ai-agent" target="_blank">lenAI-超级智能体</a> | '
    '<a href="https://github.com/lenyanjgk/lenrpc" target="_blank">lenRPC-轻量级框架</a> | '
    '<a href="https://github.com/lenyanjgk/cloudmusic" target="_blank">韵动轨迹-云音乐</a> |  '
    '<a href="https://github.com/lenyanjgk?tab=repositories" target="_blank">更多开源项目</a>'
)

ABOUT_LINE_ALGO = (
    '- 🧩算法分享：<a href="https://github.com/lenyanjgk/leetcode-solution" target="_blank">LeetCode-len解题仓库</a> | '
    '<a href="https://blog.csdn.net/jgk666666/category_12430743.html" target="_blank">CSDN：LeetCode专题</a> | '
    '<a href="https://blog.csdn.net/jgk666666/category_12435114.html" target="_blank">CSDN：蓝桥杯专题</a> | '
    '<a href="https://blog.csdn.net/jgk666666/article/details/137209476" target="_blank">lenyan-算法笔记</a>'
)


def pic(name: str, alt: str, width: str = "100%") -> str:
    """双源图片块。GitHub 按访问者的系统主题自动选一张。"""
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


def build(data: dict) -> str:
    repos = project_repos(data)
    project_cards = '\n\n\n'.join(
        linked_pic(f"proj-{slug(r['name'])}", r["url"], display_name(r))
        for r in repos
    )

    return f"""<div align="center">

{pic("banner", f'{CFG["name_zh"]} · {CFG["handle"]}')}


{pic("typing", "正在做的事")}

<br>

![Java](https://img.shields.io/badge/Java-F0EADA?style=for-the-badge&logo=openjdk&logoColor=8A6E14)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-F0EADA?style=for-the-badge&logo=springboot&logoColor=6DB33F)
![Vue](https://img.shields.io/badge/Vue_3-F0EADA?style=for-the-badge&logo=vuedotjs&logoColor=3AA876)
![AI](https://img.shields.io/badge/Spring_AI-F0EADA?style=for-the-badge&logo=langchain&logoColor=8A6E14)

</div>

{pic("divider", "")}


{pic("hdr-about", "关于我")}

## 我是lenyan ❄️

- 🌹你好！我是 **lenyan** 🙋‍♂️，一名热爱技术、乐于分享的程序员。
{ABOUT_LINE_BLOG}
{ABOUT_LINE_PROJECTS}
{ABOUT_LINE_ALGO}

<p align="left">
<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=21&pause=1000&color=8239CD&center=%C2%A0%E5%81%87&vCenter=%C2%A0%E5%81%87&repeat=%C2%A0%E7%9C%9F&random=%C2%A0%E5%81%87&width=435&lines=Motto:%20Stay%20hungry,%20stay%20foolish." />
</p>

<h3 align="left">今年汇总 ⭐</h3>
<p align="left">
<img align="" height="137px" src="https://github-readme-stats.vercel.app/api?username=lenyanjgk&hide_title=true&hide_border=true&show_icons=true&include_all_commits=true&line_height=21&bg_color=FF6666,FF9966,FFFF66,66FF66,66FFFF,6666FF,FF66FF&theme=graywhite&locale=cn" />
<img align="" height="137px" src="https://github-readme-stats.vercel.app/api/top-langs/?username=lenyanjgk&hide_title=true&hide_border=true&layout=compact&bg_color=FF99FF,FF99CC,FFFFCC,FFCCCC,FF6666&theme=graywhite&locale=cn" />
<brbrbrbr/>
</p>
{pic("terminal", "终端名片")}



{pic("hdr-stack", "技术栈")}


{pic("lang", "代码语言构成")}


<table>
<tr>
<td valign="top" width="50%">

**后端 · 主力**

![Java](https://img.shields.io/badge/Java-ED8B00?style=flat-square&logo=openjdk&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring_Boot-6DB33F?style=flat-square&logo=springboot&logoColor=white)
![Spring Cloud](https://img.shields.io/badge/Spring_Cloud-6DB33F?style=flat-square&logo=spring&logoColor=white)
![Spring AI](https://img.shields.io/badge/Spring_AI-6DB33F?style=flat-square&logo=spring&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?style=flat-square&logo=langchain&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)
![RabbitMQ](https://img.shields.io/badge/RabbitMQ-FF6600?style=flat-square&logo=rabbitmq&logoColor=white)
![Vert.x](https://img.shields.io/badge/Vert.x-782A90?style=flat-square&logo=vert.x&logoColor=white)

</td>

<td valign="top" width="50%">

**前端 · 工程**

![Vue 3](https://img.shields.io/badge/Vue_3-4FC08D?style=flat-square&logo=vuedotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
![UmiJS](https://img.shields.io/badge/UmiJS-791BE0?style=flat-square)

</td>
</tr>
<tr>
<td valign="top" colspan="2">

**通用 · 工具链**

![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat-square&logo=kubernetes&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black)
![Git](https://img.shields.io/badge/Git-F05032?style=flat-square&logo=git&logoColor=white)
![Maven](https://img.shields.io/badge/Maven-C71A36?style=flat-square&logo=apachemaven&logoColor=white)
![Gradle](https://img.shields.io/badge/Gradle-02303A?style=flat-square&logo=gradle&logoColor=white)

</td>

</tr>
</table>


{pic("hdr-projects", "在做的东西")}


{project_cards}


{pic("hdr-stats", "数据与轨迹")}


{pic("stats", "数据概览")}


{pic("activity", "贡献轨迹")}


{pic("hdr-focus", "方向与投入")}


{pic("focus", "方向与投入")}


{pic("hdr-links", "找到我")}


{pic("links", "找到我")}


<p align="center">
<a href="https://blog.csdn.net/jgk666666"><img src="https://img.shields.io/badge/博客-8A6E14?style=flat-square&labelColor=F0EADA&color=8A6E14" alt="博客"></a>
<a href="https://mp.weixin.qq.com/s/utI7LVBN0JyXdZyqhRA_ww"><img src="https://img.shields.io/badge/公众号-8A6E14?style=flat-square&labelColor=F0EADA&color=8A6E14" alt="公众号"></a>
<a href="https://github.com/lenyanjgk/leetcode-solution"><img src="https://img.shields.io/badge/算法-8A6E14?style=flat-square&labelColor=F0EADA&color=8A6E14" alt="算法"></a>
<a href="https://www.codefather.cn/user/1738833787455823874"><img src="https://img.shields.io/badge/社区-8A6E14?style=flat-square&labelColor=F0EADA&color=8A6E14" alt="社区"></a>
</p>
{pic("divider", "")}

<div align="center">
**如果哪个仓库对你有用，点个 ⭐ 就是最好的鼓励。**
</div>
"""


def main() -> None:
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    md = build(data)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(md)

    repos = project_repos(data)
    print(f"wrote {OUT}  {len(md.encode('utf-8'))} bytes")
    print(f"  项目卡 {len(repos)} 个: {', '.join(display_name(r) for r in repos)}")

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
