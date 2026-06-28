# -*- coding: utf-8 -*-
"""render_snapshot.py —— 抓"当前"概念资金流渲染一张静态桑基图。
盘中(15:00前)输出 snapshot_前缀 + 标题"盘中";收盘后输出 close_前缀 + 标题"收盘"。
用法:python render_snapshot.py [YYYY-MM-DD]
"""
import json
import sys
import datasource
import snapshots
import sankey
import config
from run_window import date_label

# ── 日期推断 ──
_today = snapshots.today_str()
_date_str = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else _today

if not (len(sys.argv) > 1 and sys.argv[1].strip()):
    try:
        from collector import is_trading_day
        if not is_trading_day(_today):
            from datetime import datetime, timedelta
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(config.TZ)
            dt = datetime.strptime(_today, "%Y-%m-%d").replace(tzinfo=tz)
            for i in range(1, 11):
                prev = (dt - timedelta(days=i)).strftime("%Y-%m-%d")
                if is_trading_day(prev):
                    _date_str = prev
                    print(f"今天({_today})非交易日，标题使用最近交易日: {_date_str}")
                    break
    except Exception:
        pass

date_str = _date_str
print("日期:", date_str)

# ── 判断盘中还是收盘 ──
now = snapshots.now_tz()
now_min = now.hour * 60 + now.minute
# 收盘时间 = 15:00 = 900 分钟；收盘后在 15:00 之后
IS_CLOSE = now_min >= 15 * 60   # 15:00 及之后算收盘
prefix = "close" if IS_CLOSE else "snapshot"
session_key = "close" if IS_CLOSE else "midday"     # 传给 sankey.prepare_scene
session_label = "收盘" if IS_CLOSE else "盘中"        # 仅用于 meta
clock_str = "15:00" if IS_CLOSE else now.strftime("%H:%M")
print(f"当前 {now.strftime('%H:%M')} → 模式={session_label} 前缀={prefix} 时钟={clock_str}")

# ── 抓数据 ──
boards, src = datasource.fetch_snapshot("concept")
print("主图数据 OK,来源:", src, "(em=东财自动Top-N / ths=同花顺套白名单) 板块数:", len(boards))
top = sorted(boards.items(), key=lambda kv: kv[1], reverse=True)[:5]
print("流入Top5:", [(n, round(v, 1)) for n, v in top])
print("=== 东财全部板块(整段发我做映射)BEGIN ===")
print(" / ".join(f"{n}{v:+.0f}" for n, v in sorted(boards.items(), key=lambda kv: kv[1], reverse=True)))
print("=== END ===")

mkf = []
try:
    mo = datasource.fetch_market_overview()
    mkf = [(1.0, mo["up"], mo["down"], mo["turnover"])]
    print("氛围条 OK:", mo)
except Exception as e:
    print("氛围条失败(忽略,不影响主图):", e)

# ── 渲染 ──
kf = [(1.0, boards, clock_str)]
label = date_label(date_str)   # 只传纯日期，prepare_scene 内部拼 SESSION_LABEL
scene = sankey.prepare_scene(kf, session_key, label, src, mkf, [])
out = config.OUT_DIR / f"{prefix}_{date_str}.png"
sankey.draw_frame(scene, config.TOTAL_FRAMES - 1).save(out)
print("已生成静态图:", out)

# ── meta.json (供发邮件读取) ──
meta = {
    "date": date_str,
    "date_label": date_label(date_str),
    "session": prefix,                     # "close" 或 "snapshot"
    "session_label": session_label,         # "收盘" 或 "盘中"
    "kind": "concept",
    "out": str(out),
    "inflow_top": scene.get("inflow", []),
    "outflow_top": scene.get("outflow", []),
}
meta_path = config.OUT_DIR / f"{prefix}_{date_str}.meta.json"
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print("已生成 meta:", meta_path)
