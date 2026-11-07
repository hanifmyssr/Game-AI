import json

with open("Game-AI/assets/map_new.tmj", "r", encoding="utf-8") as f:
    tmj = json.load(f)

tilesets = sorted(tmj.get("tilesets", []), key=lambda x: x["firstgid"])
for ts in tilesets:
    if "chest" in ts.get("source", "").lower():
        print("Chest tileset:", ts)

for l in tmj.get("layers", []):
    if l.get("type") == "tilelayer":
        w = l["width"]
        for i, gid in enumerate(l.get("data", [])):
            clean = gid & 0x1FFFFFFF
            if 692 <= clean <= 695:
                gx = i % w
                gy = i // w
                print(f"Chest tile GID {clean} found at ({gx}, {gy}) in {l['name']}")

