import json
import requests
from datetime import datetime, timezone

OUT = "data/data.json"
records = []

# ---------- EUROSTAT ----------
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"

EUROSTAT_SERIES = [
    {
        "dataset": "sts_inpr_m",
        "indicatore": "Produzione industriale",
        "unita": "indice 2021=100",
        "params": {"nace_r2": "C", "s_adj": "SCA", "unit": "I21"},
        "paesi": ["IT", "DE", "FR", "ES"],
        "settore": "C - Manifattura",
    },
]

def fetch_eurostat(cfg, geo):
    params = dict(cfg["params"], geo=geo, format="JSON", lang="EN",
                  sinceTimePeriod="2015-01")
    r = requests.get(EUROSTAT + cfg["dataset"], params=params, timeout=60)
    r.raise_for_status()
    js = r.json()
    tempi = js["dimension"]["time"]["category"]["index"]  # {"2015-01": 0, ...}
    valori = js.get("value", {})
    out = []
    for periodo, pos in tempi.items():
        v = valori.get(str(pos))
        if v is not None:
            out.append({
                "fonte": "Eurostat",
                "indicatore": cfg["indicatore"],
                "settore": cfg["settore"],
                "paese": geo,
                "data": periodo,
                "valore": v,
                "unita": cfg["unita"],
            })
    return out

for cfg in EUROSTAT_SERIES:
    for geo in cfg["paesi"]:
        try:
            records += fetch_eurostat(cfg, geo)
        except Exception as e:
            print(f"ERRORE Eurostat {cfg['dataset']} {geo}: {e}")

# ---------- WORLD BANK ----------
WB_SERIES = [
    {"codice": "NV.IND.MANF.ZS", "indicatore": "Valore aggiunto manifattura (% PIL)",
     "unita": "% PIL"},
]
WB_PAESI = {"IT": "IT", "DE": "DE", "FR": "FR", "ES": "ES"}

for s in WB_SERIES:
    for geo in WB_PAESI:
        try:
            url = f"https://api.worldbank.org/v2/country/{geo}/indicator/{s['codice']}"
            r = requests.get(url, params={"format": "json", "per_page": 100,
                                          "date": "2000:2030"}, timeout=60)
            r.raise_for_status()
            for row in (r.json()[1] or []):
                if row["value"] is not None:
                    records.append({
                        "fonte": "World Bank",
                        "indicatore": s["indicatore"],
                        "settore": "Manifattura",
                        "paese": geo,
                        "data": row["date"],
                        "valore": row["value"],
                        "unita": s["unita"],
                    })
        except Exception as e:
            print(f"ERRORE World Bank {s['codice']} {geo}: {e}")

# ---------- SALVATAGGIO ----------
if not records:
    raise SystemExit("Nessun dato scaricato: non sovrascrivo data.json")

records.sort(key=lambda x: (x["indicatore"], x["paese"], x["data"]))
payload = {
    "aggiornato": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "dati": records,
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
print(f"Salvati {len(records)} record")
