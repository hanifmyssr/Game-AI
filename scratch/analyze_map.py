import json

with open("data/map.json", "r", encoding="utf-8") as f:
    data = json.load(f)

ground_coords = set()
for c in data["ground"]:
    ground_coords.add((c["atlas_x"], c["atlas_y"]))

print("Ground atlas coords:", sorted(list(ground_coords)))

obs_coords = set()
for c in data["obstacles"]:
    obs_coords.add((c.get("src"), c["atlas_x"], c["atlas_y"]))

print("Obstacle sources and atlas coords:", sorted(list(obs_coords)))
