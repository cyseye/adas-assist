#!/usr/bin/env python3
"""zhipu 配额官方 API 单源助手（finish-check 2026-09-19 双实现收敛）。

读 ~/data/task/zhipu/credentials 的 ZHIPU_API_KEY → GET
open.bigmodel.cn/api/monitor/usage/quota/limit → stdout 单行 JSON：
{tokens_pct, tokens_reset_ms, search_pct, usage_details, ok}
任何失败输出 {"ok": false} 且退出 0（fail-closed，读者自行降级）。
消费者：weekly-eval.py _quota_api_recon / scripts/quota-tracker.sh quota_api()。
"""
import json
import sys
import urllib.request
from pathlib import Path

FAIL = {"ok": False}


def main() -> int:
    try:
        key = ""
        for ln in (Path.home() / "data/task/zhipu/credentials").read_text().splitlines():
            if ln.startswith("ZHIPU_API_KEY="):
                key = ln.split("=", 1)[1].strip()
                break
        if not key:
            print(json.dumps(FAIL))
            return 0
        req = urllib.request.Request(
            "https://open.bigmodel.cn/api/monitor/usage/quota/limit",
            headers={"Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            limits = json.load(r)["data"]["limits"]
        # unit 锚定（I3 对表 glm-quota 2026-09-19：unit=3=5h 窗 / unit=6=周级 token——
        # 服务端返回顺序无保证，裸取「第一条 TOKENS_LIMIT」有 5h/周拿反风险；实测锚 unit=3）
        tokens = next((l for l in limits if l.get("type") == "TOKENS_LIMIT" and l.get("unit") == 3),
                      next((l for l in limits if l.get("type") == "TOKENS_LIMIT"), None))
        weekly = next(l for l in limits if l.get("type") == "TIME_LIMIT")
        out = {
            "ok": True,
            "tokens_pct": tokens.get("percentage", 0),
            "tokens_reset_ms": tokens["nextResetTime"],
            "search_pct": weekly.get("percentage", 0),
            "usage_details": {u.get("modelCode", "?"): u.get("usage", "?")
                              for u in weekly.get("usageDetails", [])},
        }
        print(json.dumps(out, ensure_ascii=False))
    except Exception as e:  # 网络/解析/凭据任何失败一律降级
        print(json.dumps({**FAIL, "error": type(e).__name__}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
