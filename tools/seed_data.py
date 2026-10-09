# -*- coding: utf-8 -*-
"""用本地已抓到的真实数据造一份 data/profile.json 种子。

存在的理由：REST API 匿名限额是 60 次/小时，本地开发反复跑 fetch_data.py
很快会撞上 403，导致 make_assets.py 没有输入。这份脚本把已经确认过的
真实数值写死成种子，让管线随时能跑通。

它只是开发期的脚手架——正式数据以 fetch_data.py 的输出为准，
GitHub Action 里带 GITHUB_TOKEN，不会碰到限额。
langs 字段留空：make_assets.py 在 langs 为空时会退化用主语言，
Action 跑完一次就会被真实的字节统计覆盖掉。
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "profile.json")
CACHE = os.path.join(ROOT, "data", "_contrib_cache.json")

USER = {
    "login": "lenyanjgk",
    "avatar": "https://avatars.githubusercontent.com/u/lenyanjgk",
    "followers": 14,
    "following": 1,
    "public_repos": 15,
    "created_at": "2023-03-18T02:22:43Z",
    "location": "china guangzhou",
    "blog": "",
    "bio": "Java 全栈工程师，热爱编程，专注 LeetCode 算法题解与项目分享。",
}

# 按 REPO_META 的白名单顺序列出，字段来自 api.github.com 的真实响应。
REPOS = [
    {"name": "len-ai-agent", "lang": "Java", "stars": 130, "forks": 25,
     "license": None, "pushed_at": "2025-06-22T00:00:00Z",
     "topics": ["java", "spring-boot", "spring-ai", "ai-agent", "llm"],
     "desc": "基于 Spring Boot 3.4.5 + Java 21 + Spring AI 构建的智能体平台"},
    {"name": "lendada", "lang": "Java", "stars": 19, "forks": 0,
     "license": None, "pushed_at": "2025-05-01T00:00:00Z",
     "topics": ["vue3", "spring-boot", "redis", "ai", "exam"],
     "desc": "基于 Vue 3 + Spring Boot + Redis + AI 的智慧答题平台"},
    {"name": "lenrpc", "lang": "Java", "stars": 2, "forks": 0,
     "license": None, "pushed_at": "2025-03-10T00:00:00Z",
     "topics": ["rpc", "vertx", "java", "load-balance", "service-discovery"],
     "desc": "基于 Vert.x + Java 8 的轻量级 RPC 框架"},
    {"name": "leetcode-solution", "lang": "Java", "stars": 1, "forks": 1,
     "license": None, "pushed_at": "2025-08-06T00:00:00Z",
     "topics": ["leetcode", "algorithm", "java", "data-structure"],
     "desc": "Leetcode Solution lenyan 由 lenyan 打造的算法题解仓库"},
    {"name": "zhidangtong", "lang": "Python", "stars": 1, "forks": 0,
     "license": None, "pushed_at": "2026-04-07T00:00:00Z",
     "topics": ["rag", "langgraph", "fastapi", "llm", "knowledge-base"],
     "desc": "智档通：基于 LangGraph+FastAPI 构建的企业级 RAG 知识库"},
    {"name": "cloudmusic", "lang": "JavaScript", "stars": 1, "forks": 0,
     "license": None, "pushed_at": "2024-11-20T00:00:00Z",
     "topics": ["wechat-miniprogram", "cloud-development", "music"],
     "desc": "基于微信小程序框架 + 云开发技术的音乐应用"},
    # 以下仓库不在 REPO_META 白名单里，不画项目卡，
    # 但它们的 star / fork 要计入数据卡的汇总，所以种子里也得有，
    # 否则本地预览的「获得星标」会比线上少算。
    {"name": "ClaudeCode", "lang": "HTML", "stars": 6, "forks": 1,
     "license": None, "pushed_at": "2026-09-01T00:00:00Z",
     "topics": ["claude-code", "docs"], "desc": "ClaudeCode 知识学习文档"},
    {"name": "cat-ai-robot", "lang": "Vue", "stars": 1, "forks": 1,
     "license": None, "pushed_at": "2026-07-16T00:00:00Z",
     "topics": ["vue", "ai", "roleplay"], "desc": "AI 角色扮演网页开发仓库"},
    {"name": "DesignPattern", "lang": "Java", "stars": 1, "forks": 0,
     "license": None, "pushed_at": "2024-05-01T00:00:00Z",
     "topics": ["design-pattern", "java"], "desc": "设计模式学习"},
    {"name": "Warm-delivery-learning", "lang": "Java", "stars": 1, "forks": 0,
     "license": None, "pushed_at": "2024-08-01T00:00:00Z",
     "topics": ["vue", "spring-boot", "wechat-miniprogram"],
     "desc": "基于 Vue.js + Spring Boot + Redis + 微信小程序 + Nginx 的外卖项目"},
    {"name": "lenyan-skills", "lang": "", "stars": 0, "forks": 0,
     "license": None, "pushed_at": "2026-02-28T00:00:00Z",
     "topics": [], "desc": "lenyan 使用的 skills 备份", "empty": True},
]


def main() -> int:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    contrib = {"total": 0, "days": [], "max": 0, "active_days": 0}
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            contrib = json.load(f)
        print(f"贡献数据取自缓存 {CACHE}: {len(contrib.get('days', []))} 天")
    else:
        print(f"警告: 缺少 {CACHE}，热力图会是空的。先跑一次 fetch_data.py。")

    repos = []
    for r in REPOS:
        d = dict(r)
        d["url"] = f"https://github.com/{USER['login']}/{r['name']}"
        d.setdefault("langs", {})
        d.setdefault("empty", False)
        repos.append(d)
    repos.sort(key=lambda x: -x["stars"])

    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user": USER,
        "repos": repos,
        "contributions": contrib,
        "stale": ["seed(本地种子数据，Action 会用真实抓取结果覆盖)"],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"wrote {OUT}")
    print(f"  repos={len(repos)}  stars={sum(r['stars'] for r in repos)}  "
          f"forks={sum(r['forks'] for r in repos)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
