# -*- coding: utf-8 -*-
"""抓取 lenyanjgk 的真实公开数据，输出 data/profile.json。

设计要点：
- 贡献日历走公开贡献页 HTML 解析（https://github.com/users/<login>/contributions），
  不需要令牌，也不受 REST API 速率限制影响。
- 仓库信息走公开 REST API；带令牌时会顺带拿每个仓库的语言构成。
- REST 撞限额时不整体失败：保留上一次成功抓到的 repos，只刷新能刷新的部分，
  并把 stale 字段标出来。本地开发反复跑不会因为 60 次/小时的限额而中断。
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

LOGIN = "lenyanjgk"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUT = os.path.join(DATA_DIR, "profile.json")

UA = "Mozilla/5.0 (lenyan-profile-readme)"
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""


class RateLimited(Exception):
    pass


def http_get(url: str, accept: str = "text/html") -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": accept,
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise RateLimited(f"{e.code} on {url}") from None
        raise


def fetch_json(url: str):
    return json.loads(http_get(url, accept="application/vnd.github+json"))


def load_previous() -> dict:
    if not os.path.exists(OUT):
        return {}
    try:
        with open(OUT, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def fetch_user() -> dict:
    u = fetch_json(f"https://api.github.com/users/{LOGIN}")
    return {
        "login": u["login"],
        "avatar": u["avatar_url"],
        "followers": u["followers"],
        "following": u["following"],
        "public_repos": u["public_repos"],
        "created_at": u["created_at"],
        "location": u.get("location") or "",
        "blog": u.get("blog") or "",
        "bio": u.get("bio") or "",
    }


def fetch_repos() -> list[dict]:
    repos = fetch_json(
        f"https://api.github.com/users/{LOGIN}/repos?per_page=100&sort=pushed"
    )
    out = []
    for r in repos:
        if r["fork"] or r["archived"]:
            continue
        langs = {}
        try:
            langs = fetch_json(r["languages_url"])
        except Exception:
            # 语言构成是锦上添花，拿不到就用主语言字段兜底，不值得让整个流程失败
            pass
        out.append({
            "name": r["name"],
            "desc": r["description"] or "",
            "lang": r["language"] or "",
            "stars": r["stargazers_count"],
            "forks": r["forks_count"],
            "license": (r["license"] or {}).get("spdx_id"),
            "url": r["html_url"],
            "topics": r.get("topics", []),
            "pushed_at": r["pushed_at"],
            "langs": langs,
            # 用根目录 contents 是否 404 判定空仓库。
            # 不能用 REST 的 size 字段：刚推送的仓库 size 会滞后为 0。
            "empty": is_empty_repo(r["contents_url"]),
        })
    out.sort(key=lambda x: (-x["stars"], _neg_time(x["pushed_at"]), x["name"]))
    return out


def _neg_time(iso: str) -> float:
    """用于「最近更新优先」的排序键（取负，配合升序排序）。"""
    try:
        return -datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def is_empty_repo(contents_url: str) -> bool:
    url = contents_url.replace("{+path}", "")
    try:
        data = fetch_json(url)
        return not isinstance(data, list) or len(data) == 0
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True  # GitHub 对空仓库返回 "This repository is empty."
        raise


def fetch_contributions() -> dict:
    """解析公开贡献页，得到逐日贡献数。"""
    html = http_get(f"https://github.com/users/{LOGIN}/contributions")
    cell_re = re.compile(r'<td[^>]*class="[^"]*ContributionCalendar-day[^"]*"[^>]*>')
    days = []
    for tag in cell_re.finditer(html):
        t = tag.group(0)
        d = re.search(r'data-date="([\d-]+)"', t)
        if not d:
            continue
        lvl = re.search(r'data-level="(\d)"', t)
        cid = re.search(r'id="([^"]+)"', t)
        days.append({
            "date": d.group(1),
            "level": int(lvl.group(1)) if lvl else 0,
            "id": cid.group(1) if cid else "",
        })
    # tooltip: <tool-tip for="cell-N">5 contributions on September 25th.</tool-tip>
    tip_re = re.compile(r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', re.S)
    counts = {}
    for m in tip_re.finditer(html):
        txt = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        n = re.match(r"(\d+|No)\b", txt)
        cnt = 0 if not n or n.group(1) == "No" else int(n.group(1))
        counts[m.group(1)] = cnt
    # 关键：贡献页的 DOM 按「星期几」分组输出（先所有周日、再所有周一…），
    # 不是按日期顺序，直接使用会让时间轴错乱，必须显式排序。
    days.sort(key=lambda d: d["date"])
    for d in days:
        d["count"] = counts.get(d["id"], 0)
    total_match = re.search(r"([\d,]+)\s*contributions?\s+in the last year", html, re.I)
    total = int(total_match.group(1).replace(",", "")) if total_match else sum(d["count"] for d in days)
    return {
        "total": total,
        "days": days,
        "max": max([d["count"] for d in days], default=0),
        "active_days": sum(1 for d in days if d["count"] > 0),
    }


def main() -> int:
    os.makedirs(DATA_DIR, exist_ok=True)
    prev = load_previous()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale: list[str] = []

    # 贡献页不走 REST 限额，优先刷新它
    try:
        contributions = fetch_contributions()
    except Exception as e:
        contributions = prev.get("contributions") or {"total": 0, "days": [], "max": 0, "active_days": 0}
        stale.append(f"contributions({e})")

    try:
        user = fetch_user()
    except Exception as e:
        user = prev.get("user") or {"login": LOGIN, "created_at": "2023-03-18T00:00:00Z"}
        stale.append(f"user({e})")

    try:
        repos = fetch_repos()
    except Exception as e:
        repos = prev.get("repos") or []
        stale.append(f"repos({e})")

    data = {"generated_at": now, "user": user, "repos": repos,
            "contributions": contributions}
    if stale:
        data["stale"] = stale

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    c = contributions
    print(f"wrote {OUT}")
    print(f"  repos={len(repos)}  days={len(c.get('days', []))}  total={c.get('total')}  "
          f"active_days={c.get('active_days')}  max/day={c.get('max')}")
    if stale:
        print(f"  STALE(沿用上次结果): {'; '.join(stale)}")
        print("  提示: REST API 有 60 次/小时的匿名限额，GitHub Action 里带 GITHUB_TOKEN 不受影响。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
