from PIL import Image

def analyze(path):
    im = Image.open(path)
    # Check non-transparent pixels
    w, h = im.size
    pixels = []
    for y in range(h):
        for x in range(w):
            p = im.getpixel((x, y))
            if p[3] > 20:
                pixels.append(p[:3])
    if not pixels:
        return "completely transparent"
    r_avg = sum(p[0] for p in pixels) / len(pixels)
    g_avg = sum(p[1] for p in pixels) / len(pixels)
    b_avg = sum(p[2] for p in pixels) / len(pixels)
    return f"pixels={len(pixels)}, avg RGB=({r_avg:.1f}, {g_avg:.1f}, {b_avg:.1f})"

folder = "C:/Users/Pavilion/.gemini/antigravity/brain/38f4bb8b-a421-4acf-b988-2e6d2a7fae0d/tiles_inspect"
for name in ["obj_lid_3.png", "obj_lid_0.png", "obj_lid_1.png", "obj_lid_2.png", "grass_lid_61.png", "grass_lid_62.png", "grass_lid_63.png", "grass_lid_64.png", "grass_lid_72.png", "grass_lid_73.png", "biom_lid_22.png", "biom_lid_23.png", "biom_lid_29.png", "biom_lid_30.png", "biom_lid_36.png", "biom_lid_37.png"]:
    print(f"{name:18}: {analyze(folder + '/' + name)}")

