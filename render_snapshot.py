# -*- coding: utf-8 -*-
"""render_snapshot.py —— 抓"当前"概念资金流(收盘后=当日收盘值)渲染一张收盘静态图。
单帧、无需盘中时间序列;在 GitHub(能连同花顺)上跑。用法:python render_snapshot.py [YYYY-MM-DD]
"""
import sys
import datasource
import snapshots
import sankey
import config
from run_window import date_label

_today = snapshots.today_str()
_date_str = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() else _today

# 如果用户没传日期且今天不是交易日，自动推断最近交易日作为标题日期
if not (len(sys.argv) > 1 and sys.argv[1].strip()):
    try:
        from collector import is_trading_day
        if not is_trading_day(_today):
            # 往前找最近交易日（最多回退 10 天）
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
        pass  # 推断失败则退化为当天

date_str = _date_str
print("日期:", date_str)

boards, src = datasource.fetch_snapshot("concept")     # 当前=收盘后即今日收盘累计
print("主图数据 OK,来源:", src, "(em=东财自动Top-N / ths=同花顺套白名单) 板块数:", len(boards))
top = sorted(boards.items(), key=lambda kv: kv[1], reverse=True)[:5]
print("流入Top5:", [(n, round(v, 1)) for n, v in top])
# 一次性打印东财全部板块名(净流入降序),用于把白名单对齐到东财真实叫法
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

kf = [(1.0, boards, "15:00")]                          # 单关键帧=收盘态
scene = sankey.prepare_scene(kf, "close", date_label(date_str), src, mkf, [])
out = config.OUT_DIR / f"close_{date_str}.png"
sankey.draw_frame(scene, config.TOTAL_FRAMES - 1).save(out)
print("已生成静态图:", out)
