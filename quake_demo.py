#!/usr/bin/env python3
"""
Демо: жер сілкінісін бақылау мониторы (USGS ашық дереккөзі).

Тек Python стандартты кітапханасы — пакеттерді орнатудың қажеті жоқ.

Мысалдар:
  python quake_demo.py --check
  python quake_demo.py --check --radius-km 100000 --min-mag 5.0
  python quake_demo.py --watch --lat 43.238 --lon 76.955 --radius-km 800 --min-mag 4.5 --interval 60
"""
import argparse
import json
import math
import sys
import time
import urllib.request
from datetime import datetime, timezone

# Windows: консольді UTF-8 режиміне ауыстырамыз (қазақ әріптері үшін)
if sys.platform == "win32":
    try:
        import os
        os.system("chcp 65001 >nul")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


def haversine_km(lat1, lon1, lat2, lon2):
    """Екі нүкте арасындағы қашықтық (км)."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def fetch_feed(url=FEED_URL, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "quake-demo/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fmt_time(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def find_quakes(data, lat, lon, radius_km, min_mag):
    out = []
    for f in data.get("features", []):
        p = f["properties"]
        coords = f["geometry"]["coordinates"]
        dist = haversine_km(lat, lon, coords[1], coords[0])
        mag = p.get("mag") or 0.0
        if dist <= radius_km and mag >= min_mag:
            out.append({
                "id": f["id"],
                "mag": mag,
                "place": p.get("place") or "?",
                "time": fmt_time(p["time"]),
                "dist": round(dist, 1),
                "url": p.get("url", ""),
            })
    out.sort(key=lambda q: q["time"], reverse=True)
    return out


def print_quake(q, new=False):
    mark = " [ЖАҢА!]" if new else ""
    print(f"  M {q['mag']:.1f}  {q['dist']:>8.1f} км  {q['time']}  {q['place']}{mark}")
    if q["url"]:
        print(f"            -> {q['url']}")


def main():
    ap = argparse.ArgumentParser(description="Демо: жер сілкініс мониторы (USGS open data)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="бір реттік тексеру (әдепкі)")
    mode.add_argument("--watch", action="store_true", help="бақылау режимі (цикл)")
    ap.add_argument("--lat", type=float, default=43.1667, help="ендік (әдепкі: Қарғалы 43.1667)")
    ap.add_argument("--lon", type=float, default=76.4167, help="меридиан (әдепкі: Қарғалы 76.4167)")
    ap.add_argument("--radius-km", type=float, default=500.0, help="радиус, км")
    ap.add_argument("--min-mag", type=float, default=4.0, help="минималды магнитуда")
    ap.add_argument("--interval", type=int, default=60, help="опрос интервалы, сек (watch)")
    args = ap.parse_args()

    print(f"Жер сілкініс мониторы (демо) — дереккөз: USGS")
    print(f"Нүкте: {args.lat}, {args.lon} | Радиус: {args.radius_km:.0f} км | M >= {args.min_mag}")

    if args.watch:
        seen = set()
        first = True
        try:
            while True:
                data = fetch_feed()
                quakes = find_quakes(data, args.lat, args.lon, args.radius_km, args.min_mag)
                if first:
                    print(f"\n[{fmt_time(time.time() * 1000)}] Соңғы 24 сағат ішіндегі оқиғалар: {len(quakes)}")
                    for q in quakes[:20]:
                        print_quake(q)
                    seen.update(q["id"] for q in quakes)
                    first = False
                else:
                    fresh = [q for q in quakes if q["id"] not in seen]
                    if fresh:
                        print(f"\n[{fmt_time(time.time() * 1000)}] ЖАҢА ЖЕР СІЛКІНІСІ!")
                        for q in fresh:
                            print_quake(q, new=True)
                        print("\a")  # дыбыстық сигналы
                        seen.update(q["id"] for q in fresh)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nТоқтатылды (Ctrl+C).")
    else:
        try:
            data = fetch_feed()
        except Exception as e:
            print(f"Feed-ті жүктеу қатесі: {e}")
            raise SystemExit(1)
        quakes = find_quakes(data, args.lat, args.lon, args.radius_km, args.min_mag)
        print(f"Соңғы 24 сағат ішінде табылды: {len(quakes)} оқиға\n")
        if not quakes:
            print("Таңдалған шеңберде жер сілкінісі жоқ (радиусты/магнитуданы өзгертіп көріңіз).")
        for q in quakes[:25]:
            print_quake(q)


if __name__ == "__main__":
    main()
