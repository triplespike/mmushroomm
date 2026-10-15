import urllib.request
import plistlib
import io
import os
import re
from PIL import Image

out_dir = '/home/spike/projects/mmushroomm-gd/assets/icons'
os.makedirs(out_dir, exist_ok=True)
headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}

def parse_rect(s):
    return [int(n) for n in re.findall(r'-?\d+', s)]

def parse_point(s):
    return [int(n) for n in re.findall(r'-?\d+', s)]

def render_sheet_icon(form, id_str, layers_config):
    plist_url = f'https://gdbrowser.com/iconkit/icons/{id_str}-uhd.plist'
    png_url = f'https://gdbrowser.com/iconkit/icons/{id_str}-uhd.png'
    
    with urllib.request.urlopen(urllib.request.Request(plist_url, headers=headers)) as r:
        pl = plistlib.loads(r.read())
    with urllib.request.urlopen(urllib.request.Request(png_url, headers=headers)) as r:
        sheet = Image.open(io.BytesIO(r.read())).convert('RGBA')
    
    frames = {}
    for name, data in pl['frames'].items():
        x, y, w, h = parse_rect(data['textureRect'])
        rotated = data.get('textureRotated', False)
        if rotated:
            crop = sheet.crop((x, y, x + h, y + w))
            crop = crop.transpose(Image.Transpose.ROTATE_90)
        else:
            crop = sheet.crop((x, y, x + w, y + h))
        
        offset = parse_point(data.get('spriteOffset', '{0,0}'))
        frames[name] = (crop, offset)
    
    cw, ch = 300, 300
    canvas = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    
    for layer_name_suffix, tint_color in layers_config:
        fname = f'{id_str}_{layer_name_suffix}'
        if fname in frames:
            crop, offset = frames[fname]
            crop = crop.copy()
            if tint_color is not None:
                tr, tg, tb = tint_color
                pix = crop.load()
                for py in range(crop.height):
                    for px in range(crop.width):
                        r, g, b, a = pix[px, py]
                        if a > 0:
                            pix[px, py] = (int(r * tr / 255), int(g * tg / 255), int(b * tb / 255), a)
            
            cx = (cw - crop.width) // 2 + offset[0]
            cy = (ch - crop.height) // 2 - offset[1]
            canvas.alpha_composite(crop, (cx, cy))
    
    bbox = canvas.getbbox()
    return canvas.crop(bbox)

# 1. Sheet-based native rendering
configs = {
    'cube': ('player_49', [('2_001.png', (255, 255, 255)), ('001.png', (255, 0, 0))]),
    'ship': ('ship_01', [('2_001.png', (255, 255, 255)), ('001.png', (255, 0, 0))]),
    'ball': ('player_ball_01', [('2_001.png', (255, 255, 255)), ('001.png', (255, 0, 0))]),
    'ufo': ('bird_11', [('3_001.png', (255, 255, 255)), ('2_001.png', (255, 255, 255)), ('001.png', (255, 0, 0))]),
    'wave': ('dart_01', [('2_001.png', (255, 255, 255)), ('001.png', (255, 0, 0))]),
}

for name, (id_str, cfg) in configs.items():
    res = render_sheet_icon(name, id_str, cfg)
    res.save(f'{out_dir}/{name}.png')
    print(f'Rendered native {name}: {res.size}')

# 2. Smooth linear continuous rendering for complex forms (swing, jetpack, robot, spider)
smooth_configs = [
    ('swing', 'swing', 17, 190.0),
    ('jetpack', 'jetpack', 8, 175.0),
    ('robot', 'robot', 10, 175.0),
    ('spider', 'spider', 2, 175.0),
]

for name, form, icon_id, scale_base in smooth_configs:
    url = f'https://gdbrowser.com/icon/icon?form={form}&icon={icon_id}'
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as r:
        im = Image.open(io.BytesIO(r.read())).convert('RGBA')
    
    pix = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if a == 0:
                continue
            if r <= 20 and g <= 20 and b <= 20:
                continue # keep smooth native black outline
            elif r >= 235 and g >= 235 and b >= 235:
                pix[x, y] = (255, 255, 255, a) # secondary white
            else:
                scale = min(1.0, r / scale_base)
                pix[x, y] = (int(255 * scale), 0, 0, a) # linear smooth GD red
    
    bbox = im.getbbox()
    res = im.crop(bbox)
    res.save(f'{out_dir}/{name}.png')
    print(f'Rendered smooth {name}: {res.size}')
