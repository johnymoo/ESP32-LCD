import json
from pathlib import Path

SRC = Path(__file__).parent / "downloaded" / "PCB1.epru"
OUT = Path(__file__).parent / "PCB1-complete.epru"

NETS = {
    "C1.1": "FAN12", "C1.2": "GND", "C2.1": "FAN12", "C2.2": "GND",
    "D1.1": "FAN12", "D1.2": "VIN12_PROT",
    "F1.1": "VIN12_RAW", "F1.2": "VIN12_PROT",
    "J1.1": "VIN12_RAW", "J1.2": "GND",
    "J2.1": "GND", "J2.2": "FAN12", "J2.3": "TACH1_FAN", "J2.4": "PWM_BUS",
    "J3.1": "GND", "J3.2": "FAN12", "J3.3": "TACH2_FAN", "J3.4": "PWM_BUS",
    "JDISP1.2": "GND", "JDISP1.6": "ESP_PWM", "JDISP1.7": "ESP_TACH1", "JDISP1.9": "ESP_TACH2",
    "JDISP2.2": "GND", "JDISP2.3": "GND", "JDISP2.4": "3V3",
    "Q1.1": "PWM_GATE", "Q1.2": "GND", "Q1.3": "PWM_BUS",
    "R1.1": "ESP_PWM", "R1.2": "PWM_GATE", "R2.1": "PWM_GATE", "R2.2": "GND",
    "R3.1": "TACH1_FAN", "R3.2": "ESP_TACH1", "R4.1": "ESP_TACH1", "R4.2": "3V3",
    "R5.1": "TACH2_FAN", "R5.2": "ESP_TACH2", "R6.1": "ESP_TACH2", "R6.2": "3V3",
}

rows = []
for line in SRC.read_text().splitlines():
    if "||" not in line:
        rows.append(line)
        continue
    hs, ds = line.split("||", 1)
    try:
        h, d = json.loads(hs), json.loads(ds.rstrip("| \n"))
    except Exception:
        rows.append(line)
        continue
    if h.get("type") == "PAD_NET":
        aid = json.loads(h["id"])
        ref = None
        # Build ref lookup lazily from component attributes below.
        rows.append((h, d))
    else:
        rows.append((h, d))

refs = {}
for item in rows:
    if isinstance(item, tuple):
        h, d = item
        if h.get("type") == "ATTR" and d.get("key") == "Designator":
            refs[d["parentId"]] = d["value"]

out = []
for item in rows:
    if not isinstance(item, tuple):
        out.append(item)
        continue
    h, d = item
    if h.get("type") == "PAD_NET":
        aid = json.loads(h["id"])
        ref = refs.get(aid[1])
        key = f"{ref}.{aid[2]}" if ref else None
        if key in NETS or (ref and ref.startswith("JDISP")):
            d = dict(d)
            d["padNet"] = NETS.get(key, "")
    out.append((h, d))

existing = set()
for item in out:
    if isinstance(item, tuple) and item[0].get("type") == "NET":
        existing.add(json.loads(item[0]["id"])[1])

needed = sorted(set(NETS.values()) - existing)
insert_at = next((i for i, item in enumerate(out)
                  if isinstance(item, tuple) and item[0].get("type") == "RULE_SELECTOR"), len(out))
for n, name in enumerate(needed):
    out.insert(insert_at + n, ({"type": "NET", "ticket": 7200 + n,
                                "id": json.dumps(["NET", name], separators=(",", ":"))},
                               {"netType": None, "specialColor": None, "retLine": True,
                                "differentialName": None, "isPositiveNet": False,
                                "equalLengthGroupName": None}))

def encode(item):
    if isinstance(item, str):
        return item
    h, d = item
    return json.dumps(h, separators=(",", ":"), ensure_ascii=False) + "||" + \
        json.dumps(d, separators=(",", ":"), ensure_ascii=False) + "|"

OUT.write_text("\n".join(encode(x) for x in out) + "\n")
print(f"wrote {OUT} with {len(NETS)} assigned pads and {len(needed)} new named nets")
