import pygame, os
from PIL import Image, ImageDraw, ImageFont

pygame.init()

# 1. Annotate Grass.png
grass_img = Image.open("Game-AI/assets/sprout/Grass.png")
gw, gh = grass_img.size
cols = gw // 16
rows = gh // 16

annotated_grass = Image.new("RGBA", (gw * 3, gh * 3), (255, 255, 255, 255))
draw = ImageDraw.Draw(annotated_grass)

for r in range(rows):
    for c in range(cols):
        lid = r * cols + c
        gid = lid + 1 # firstgid=1
        tile = grass_img.crop((c * 16, r * 16, (c + 1) * 16, (r + 1) * 16))
        tile_scaled = tile.resize((48, 48), Image.Resampling.NEAREST)
        annotated_grass.paste(tile_scaled, (c * 48, r * 48), tile_scaled if tile_scaled.mode == "RGBA" else None)
        draw.rectangle([c * 48, r * 48, (c + 1) * 48 - 1, (r + 1) * 48 - 1], outline=(180, 180, 180, 120))
        draw.text((c * 48 + 2, r * 48 + 2), f"L{lid}\nG{gid}", fill=(0, 0, 0))

annotated_grass.save("C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/grass_annotated.png")
print("Saved grass_annotated.png")

# 2. Annotate Objects.png
obj_path = "Game-AI/assets/Shining Fields_free_v1.1/Shining Fields_free_v1.1/Sprites/Objects/Objects.png"
if os.path.exists(obj_path):
    obj_img = Image.open(obj_path)
    ow, oh = obj_img.size
    ocols = 6 # from Objects.tsx columns=6
    orows = 5 # tilecount=30
    annotated_obj = Image.new("RGBA", (ocols * 48, orows * 48), (255, 255, 255, 255))
    odraw = ImageDraw.Draw(annotated_obj)
    for r in range(orows):
        for c in range(ocols):
            lid = r * ocols + c
            gid = lid + 825
            if c * 16 < ow and r * 16 < oh:
                tile = obj_img.crop((c * 16, r * 16, min(ow, (c + 1) * 16), min(oh, (r + 1) * 16)))
                tile_scaled = tile.resize((48, 48), Image.Resampling.NEAREST)
                annotated_obj.paste(tile_scaled, (c * 48, r * 48), tile_scaled if tile_scaled.mode == "RGBA" else None)
            odraw.rectangle([c * 48, r * 48, (c + 1) * 48 - 1, (r + 1) * 48 - 1], outline=(180, 180, 180, 120))
            odraw.text((c * 48 + 2, r * 48 + 2), f"L{lid}\nG{gid}", fill=(200, 0, 0))
    annotated_obj.save("C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/objects_annotated.png")
    print("Saved objects_annotated.png")

