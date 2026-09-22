from game.mapdata import MapData

m = MapData()
print("Total ground tiles:", len(m.ground_set))
print("Total dirt road tiles:", len(m.dirt_road_set))
print("Total walkable tiles:", len(m.walkable_set))

dirt_count = 0
grass_count = 0

for pos in m.walkable_set:
    cost = m.get_step_cost(pos)
    if cost == 0.5:
        dirt_count += 1
    elif cost == 1.0:
        grass_count += 1

print(f"Walkable Dirt Road Tiles (Cost 0.5): {dirt_count}")
print(f"Walkable Grass Tiles (Cost 1.0): {grass_count}")
