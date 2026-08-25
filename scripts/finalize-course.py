#!/usr/bin/env python3
"""跨章去重 + 配額回寫。

存在的理由:curate-chapter 工作流程的 duplicatesAcrossUnits **只比對同一章之內**,
跨章重用完全不會報。Meshtastic 那門課實測 94 個欄位裡有 28 個是跨章重複,
全部要靠這支腳本才抓得到。

去重規則(Meshtastic 實戰調校過):
  - 同一支影片全課最多出現 **2 次**
  - 絕不在同一章出現兩次(含主課)
  - 主課不動(移除主課會讓單元沒有主課);只砍項目
第一版規則是「首次出現者勝」,結果把某一章砍到剩 4 個項目——因為那些片
topically 屬於後面的章,只是前面的章依序號先用掉。同一支影片配上不同的
教學框架(不同 name/target/dose)服務兩個教學目的,不算灌水。

用法:
    python3 scripts/finalize-course.py courses/<name>      # 報告,不改檔
    python3 scripts/finalize-course.py courses/<name> --apply
"""
import json, glob, re, sys, collections, os

def vid(u):
    return u.split("v=")[1][:11] if u and "v=" in u else None

def chapnum(p):
    m = re.search(r'ch(\d+)\.json$', p)
    return int(m.group(1)) if m else 999

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    course = sys.argv[1].rstrip("/")
    apply_ = "--apply" in sys.argv
    files = sorted(glob.glob(f"{course}/data/ch*.json"), key=chapnum)
    if not files:
        sys.exit(f"找不到 {course}/data/ch*.json")

    # 第一輪:主課全部登記(主課本輪不動)
    count = collections.Counter()
    inchap = collections.defaultdict(set)
    for f in files:
        d = json.load(open(f))
        for u in d.get("units", []):
            v = vid((u.get("lesson") or {}).get("url"))
            if v:
                count[v] += 1
                inchap[d["chapter"]].add(v)

    # 主課自己就重複的,回報但不自動處理(需要換片或把項目升為主課)
    lesson_dupes = {v: n for v, n in count.items() if n > 1}

    # 第二輪:逐一決定項目去留
    removed, quotas = [], {}
    for f in files:
        d = json.load(open(f))
        ch = d["chapter"]
        total = 0
        for u in d.get("units", []):
            keep = []
            for dr in u.get("drills", []):
                v = vid(dr.get("url"))
                if v and (count[v] >= 2 or v in inchap[ch]):
                    why = "全課已 2 次" if count[v] >= 2 else "本章已用"
                    removed.append((u["id"], v, dr.get("name", "")[:34], why))
                    continue
                if v:
                    count[v] += 1
                    inchap[ch].add(v)
                keep.append(dr)
            u["drills"] = keep
            total += len(keep)
        quotas[ch] = (len(d.get("units", [])), total,
                      [len(x.get("drills", [])) for x in d.get("units", [])])
        if apply_:
            json.dump(d, open(f, "w"), ensure_ascii=False, indent=1)

    print(f"{'套用' if apply_ else '預覽'}:移除 {len(removed)} 個重複項目\n")
    for uid, v, name, why in removed:
        print(f"  - {uid:<10} {v}  [{why}]  {name}")

    if lesson_dupes:
        print(f"\n⚠️ 有 {len(lesson_dupes)} 支影片被當成多個單元的主課(本腳本不自動處理,需換片或把項目升為主課):")
        for v, n in sorted(lesson_dupes.items(), key=lambda kv: -kv[1]):
            print(f"  {v}  ×{n}")

    print("\n配額(請據此更新 course.config.json 的 chapters[].drills):")
    for ch, (nu, nd, per) in quotas.items():
        warn = "  ⚠ 有單元 <2" if per and min(per) < 2 else ""
        print(f"  {ch}  units {nu}  drills {nd:<3} {per}{warn}")

    uniq = len([v for v in count if count[v] > 0])
    print(f"\n全課去重後實際影片:{uniq} 支")

if __name__ == "__main__":
    main()
