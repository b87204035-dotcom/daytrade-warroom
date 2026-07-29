from __future__ import annotations
import json, os, sys, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = json.loads((ROOT / "config" / "strategy.json").read_text(encoding="utf-8"))
TZ = ZoneInfo("Asia/Taipei")
HEADERS = {"User-Agent": "daytrade-warroom/1.0 (+GitHub Actions)"}

def get_json(url: str, timeout: int = 25):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()

def num(v, default=0.0):
    try:
        return float(str(v).replace(",", "").replace("--", "0").strip())
    except Exception:
        return default

def first(row, keys, default=""):
    for k in keys:
        if k in row and row[k] not in (None, ""):
            return row[k]
    return default

def fetch_twse():
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    rows = get_json(url)
    out = []
    for r in rows:
        code = str(first(r, ["Code", "證券代號", "股票代號"])).strip()
        name = str(first(r, ["Name", "證券名稱", "股票名稱"])).strip()
        close = num(first(r, ["ClosingPrice", "收盤價"]))
        volume = int(num(first(r, ["TradeVolume", "成交股數"])))
        change = num(first(r, ["Change", "漲跌價差"]))
        if not code or not name or close <= 0:
            continue
        prev = close - change
        pct = round((change / prev * 100), 2) if prev else 0
        out.append({"code":code,"name":name,"close":close,"volume":volume,"change_pct":pct})
    return out, url

def fetch_taifex():
    base = "https://openapi.taifex.com.tw/v1"
    result = {"foreign_net_oi":0,"trust_net_oi":0,"dealer_net_oi":0,"put_call_ratio":"—"}
    notes = []
    try:
        rows = get_json(base + "/MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate")
        # Schema field names can evolve; locate latest TX row and common bilingual names.
        tx = [r for r in rows if "臺股期貨" in json.dumps(r, ensure_ascii=False) or '"TX"' in json.dumps(r)]
        latest = tx[0] if tx else (rows[0] if rows else {})
        blob = {str(k).lower(): v for k,v in latest.items()}
        # Keep zero rather than fabricate when a field is not found.
        for k,v in blob.items():
            ks = k.lower()
            if "未沖銷" in k and ("多空淨額" in k or "net" in ks):
                val = int(num(v))
                if "外資" in k or "foreign" in ks: result["foreign_net_oi"] = val
                elif "投信" in k or "trust" in ks: result["trust_net_oi"] = val
                elif "自營" in k or "dealer" in ks: result["dealer_net_oi"] = val
    except Exception as e:
        notes.append("三大法人：" + str(e)[:80])
    try:
        rows = get_json(base + "/PutCallRatio")
        if rows:
            r = rows[0]
            value = first(r, ["PutCallRatioByOpenInterest", "未平倉量賣買權比率", "PutCallRatio"], "—")
            result["put_call_ratio"] = value
    except Exception as e:
        notes.append("PCR：" + str(e)[:80])
    return result, base, notes

def score_stocks(stocks):
    candidates=[]
    for s in stocks:
        if s["volume"] < CONFIG["min_volume_shares"]: continue
        if not (CONFIG["min_price"] <= s["close"] <= CONFIG["max_price"]): continue
        if not (CONFIG["long_min_change_pct"] <= s["change_pct"] <= CONFIG["long_max_change_pct"]): continue
        score = min(100, round(40 + min(s["change_pct"], 8)*5 + min(s["volume"]/1_000_000, 20)))
        candidates.append({**s, "volume_ratio":"—", "foreign_net":0, "score":score,
                           "reason":"成交量達門檻、價格上漲；法人與五日均量待資料源補齊"})
    return sorted(candidates, key=lambda x:(x["score"],x["volume"]), reverse=True)[:CONFIG["top_n"]]

def market_view(stocks, futures):
    ups=sum(1 for s in stocks if s["change_pct"]>0)
    downs=sum(1 for s in stocks if s["change_pct"]<0)
    total=max(1,ups+downs)
    ratio=ups/total
    foreign=futures.get("foreign_net_oi",0)
    if ratio>=0.58 and foreign>=0:
        return {"bias":"偏多作戰","reason":"上漲家數占優，期貨外資部位未形成反向壓力。","risk":"中","tag":"偏多","tone":"positive"}
    if ratio<=0.42 and foreign<=0:
        return {"bias":"偏空防守","reason":"下跌家數占優，期貨外資部位未形成支撐。","risk":"高","tag":"偏空","tone":"danger"}
    return {"bias":"區間觀察","reason":"現貨廣度與期貨籌碼未形成一致方向，降低出手頻率。","risk":"中高","tag":"中性","tone":"neutral"}

def main():
    now=datetime.now(TZ)
    sources={}
    try:
        stocks, twse_url=fetch_twse()
        sources["TWSE上市行情"]={"ok":True,"note":f"{len(stocks)}筆"}
    except Exception as e:
        stocks=[]
        sources["TWSE上市行情"]={"ok":False,"note":str(e)[:100]}
    try:
        futures, taifex_url, notes=fetch_taifex()
        sources["TAIFEX期權籌碼"]={"ok":not notes,"note":"；".join(notes) if notes else "API連線正常"}
    except Exception as e:
        futures={"foreign_net_oi":0,"trust_net_oi":0,"dealer_net_oi":0,"put_call_ratio":"—"}
        sources["TAIFEX期權籌碼"]={"ok":False,"note":str(e)[:100]}

    latest_path=DATA/"latest.json"
    previous={}
    if latest_path.exists():
        try: previous=json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception: pass

    if not stocks and previous:
        previous["generated_at"]=now.strftime("%Y-%m-%d %H:%M:%S")
        previous["sources"]=sources
        previous["risks"]=["本次官方行情抓取失敗，頁面保留上一次成功資料。","禁止將舊資料當成今日即時交易依據。"]
        payload=previous
    else:
        longs=score_stocks(stocks)
        payload={
          "version":"1.0",
          "report_date":now.strftime("%Y-%m-%d"),
          "generated_at":now.strftime("%Y-%m-%d %H:%M:%S"),
          "market":market_view(stocks,futures),
          "futures":futures,
          "long_candidates":longs,
          "reversal_watch":[],
          "risks":[
            "目前公開 API 未完整提供個股外資買賣超、融資維持率與五日均量，相關欄位不虛構。",
            "漲停／跌停反向法人策略需接入逐股法人資料後才會自動列出。",
            "盤後資料不等於隔日開盤方向，進場仍須看量價與停損。"
          ],
          "sources":sources
        }
    DATA.mkdir(exist_ok=True)
    latest_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    archive=DATA/"history"
    archive.mkdir(exist_ok=True)
    (archive/f'{payload["report_date"]}.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f'Updated {latest_path}')

if __name__=="__main__":
    main()
