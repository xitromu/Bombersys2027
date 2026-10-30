"""Хромовый логотип BOMBERSYS в духе заставок 80-х: Blender без окна, буква O — настоящая бомба с фитилём.

  blender -b -P promo/render_logo.py -- --out promo/work/logo [--frames 1,60,120] [--samples 64]

Кадры 1..LAST — логотип прилетает из глубины и встаёт на место на кадре ARRIVE, дальше покачивается, а по хрому
бежит блик. Фон прозрачный: неоновую сетку и звёзды подкладывает make_video.py.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

FONT = r"C:\Windows\Fonts\ariblk.ttf"
WIDTH, HEIGHT = 1280, 720
ARRIVE, LAST = 90, 150   # 3 с полёта и 2 с покачивания при 30 кадрах в секунду


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"out": "work/logo", "frames": "", "samples": "48"}
    key = None
    for a in argv:
        if a.startswith("--"):
            key = a[2:]
        elif key:
            opts[key] = a
            key = None
    return opts


OPTS = args()
OUT = os.path.abspath(OPTS["out"])
os.makedirs(OUT, exist_ok=True)

for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = int(OPTS["samples"])
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
prefs = bpy.context.preferences.addons["cycles"].preferences
for backend in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = backend
        prefs.get_devices()
        if any(d.type == backend for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == backend
            scene.cycles.device = "GPU"
            print("DEVICE", backend, flush=True)
            break
    except TypeError:
        continue
scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"


def ramp(nodes, links, source, stops):
    node = nodes.new("ShaderNodeValToRGB")
    cr = node.color_ramp
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[0])
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = (*stops[0][1], 1)
    for position, color in stops[1:]:
        cr.elements.new(position).color = (*color, 1)
    links.new(source, node.inputs["Fac"])
    return node


def rgb(hex_color):
    v = [int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c ** 2.2 for c in v)


# Хромовое небо: сверху голубое, у горизонта белое, под горизонтом тёмное и снизу рыжее. Блик — яркая полоса,
# которая проезжает по миру и отражается в фасках букв.
world = bpy.data.worlds.new("chrome")
world.use_nodes = True
scene.world = world
nt = world.node_tree
coord = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(coord.outputs["Generated"], sep.inputs[0])
remap = nt.nodes.new("ShaderNodeMapRange")
remap.inputs["From Min"].default_value = -1
remap.inputs["From Max"].default_value = 1
nt.links.new(sep.outputs["Z"], remap.inputs["Value"])
sky = ramp(nt.nodes, nt.links, remap.outputs["Result"], [
    (0.00, rgb("ff7a1a")), (0.30, rgb("ffd27a")), (0.47, rgb("3a1208")), (0.51, rgb("0a0420")),
    (0.54, rgb("ffffff")), (0.68, rgb("7fd4ff")), (1.00, rgb("1a2a9a"))])
sweep_map = nt.nodes.new("ShaderNodeMapping")
nt.links.new(coord.outputs["Generated"], sweep_map.inputs["Vector"])
sweep_sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(sweep_map.outputs["Vector"], sweep_sep.inputs[0])
sweep_abs = nt.nodes.new("ShaderNodeMath")
sweep_abs.operation = "ABSOLUTE"
nt.links.new(sweep_sep.outputs["X"], sweep_abs.inputs[0])
sweep_range = nt.nodes.new("ShaderNodeMapRange")
sweep_range.interpolation_type = "SMOOTHSTEP"
sweep_range.inputs["From Min"].default_value = 0.015
sweep_range.inputs["From Max"].default_value = 0.09
nt.links.new(sweep_abs.outputs[0], sweep_range.inputs["Value"])
mix = nt.nodes.new("ShaderNodeMix")
mix.data_type = "RGBA"
nt.links.new(sweep_range.outputs["Result"], mix.inputs[0])
mix.inputs[6].default_value = (7, 7, 7, 1)
nt.links.new(sky.outputs["Color"], mix.inputs[7])
bg = nt.nodes["Background"]
nt.links.new(mix.outputs[2], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.15
sweep = sweep_map


def chrome_face():
    """Лицо букв: плоскость отразила бы один цвет, поэтому полосы хрома идут по высоте буквы, как на старых логотипах."""
    mat = bpy.data.materials.new("face")
    mat.use_nodes = True
    n, l = mat.node_tree.nodes, mat.node_tree.links
    bsdf = n["Principled BSDF"]
    tex = n.new("ShaderNodeTexCoord")
    sp = n.new("ShaderNodeSeparateXYZ")
    l.new(tex.outputs["Object"], sp.inputs[0])
    rg = n.new("ShaderNodeMapRange")
    rg.inputs["From Min"].default_value = -0.02
    rg.inputs["From Max"].default_value = 0.76
    l.new(sp.outputs["Y"], rg.inputs["Value"])
    bands = ramp(n, l, rg.outputs["Result"], [
        (0.00, rgb("fff3c0")), (0.14, rgb("ff9a2e")), (0.40, rgb("6e1a08")), (0.47, rgb("140412")),
        (0.50, rgb("ffffff")), (0.70, rgb("8fe0ff")), (1.00, rgb("2a4adf"))])
    l.new(bands.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = 0.85
    bsdf.inputs["Roughness"].default_value = 0.22
    bsdf.inputs["Emission Strength"].default_value = 0.55
    l.new(bands.outputs["Color"], bsdf.inputs["Emission Color"])
    return mat


def chrome_edge():
    mat = bpy.data.materials.new("edge")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.95, 0.97, 1.0, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.08
    return mat


def side_paint():
    mat = bpy.data.materials.new("side")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb("ff1a8c"), 1)
    bsdf.inputs["Metallic"].default_value = 0.4
    bsdf.inputs["Roughness"].default_value = 0.3
    bsdf.inputs["Emission Color"].default_value = (*rgb("ff1a8c"), 1)
    bsdf.inputs["Emission Strength"].default_value = 0.5
    return mat


FACE, EDGE, SIDE = chrome_face(), chrome_edge(), side_paint()
font = bpy.data.fonts.load(FONT)


def word(text):
    curve = bpy.data.curves.new(text, "FONT")
    curve.body = text
    curve.font = font
    curve.shear = 0.22
    curve.extrude = 0.14
    curve.bevel_depth = 0.022
    curve.bevel_resolution = 3
    curve.materials.append(FACE)
    curve.materials.append(EDGE)
    curve.materials.append(SIDE)
    ob = bpy.data.objects.new(text, curve)
    scene.collection.objects.link(ob)
    return ob


logo = bpy.data.objects.new("logo", None)
scene.collection.objects.link(logo)

# Сначала строка целиком: так известны настоящие места букв. Затем «O» заменяется бомбой той же высоты.
left = word("B")
right = word("MBERSYS")
bpy.context.view_layer.update()
BALL = 0.40              # радиус бомбы: чуть выше прописной буквы
GAP = 0.05
left_width = left.dimensions.x
ball_x = left_width + GAP + BALL
right.location.x = ball_x + BALL + GAP
bpy.context.view_layer.update()
total = right.location.x + right.dimensions.x
shift = -total / 2
for ob in (left, right):
    ob.parent = logo
    ob.location.x += shift
    ob.location.y -= 0.36
    ob.rotation_euler = (0, 0, 0)
ball_x += shift

metal = bpy.data.materials.new("bomb")
metal.use_nodes = True
b = metal.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.02, 0.02, 0.03, 1)
b.inputs["Metallic"].default_value = 1.0
b.inputs["Roughness"].default_value = 0.16

bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=BALL, location=(ball_x, 0.0, 0.07))
ball = bpy.context.object
bpy.ops.object.shade_smooth()
ball.data.materials.append(metal)
ball.parent = logo

bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.13, depth=0.13,
                                    location=(ball_x + 0.15, 0.0, 0.07 + BALL * 0.93),
                                    rotation=(0, math.radians(22), 0))
cap = bpy.context.object
bpy.ops.object.shade_smooth()
cap.data.materials.append(chrome_edge())
cap.parent = logo

fuse_curve = bpy.data.curves.new("fuse", "CURVE")
fuse_curve.dimensions = "3D"
fuse_curve.bevel_depth = 0.028
fuse_curve.bevel_resolution = 3
spline = fuse_curve.splines.new("BEZIER")
points = [(ball_x + 0.18, 0.0, 0.07 + BALL + 0.03), (ball_x + 0.30, 0.0, 0.07 + BALL + 0.25),
          (ball_x + 0.58, 0.0, 0.07 + BALL + 0.27)]
spline.bezier_points.add(len(points) - 1)
for p, co in zip(spline.bezier_points, points):
    p.co = co
    p.handle_left_type = p.handle_right_type = "AUTO"
rope = bpy.data.materials.new("rope")
rope.use_nodes = True
rope.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.6, 0.45, 0.2, 1)
fuse_curve.materials.append(rope)
fuse = bpy.data.objects.new("fuse", fuse_curve)
scene.collection.objects.link(fuse)
fuse.parent = logo
SPARK_AT = Vector(points[-1])

spark = bpy.data.materials.new("spark")
spark.use_nodes = True
s = spark.node_tree.nodes["Principled BSDF"]
s.inputs["Emission Color"].default_value = (1, 0.75, 0.25, 1)
s.inputs["Emission Strength"].default_value = 30
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.045, location=SPARK_AT)
spark_ob = bpy.context.object
spark_ob.data.materials.append(spark)
spark_ob.parent = logo

cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 50
cam = bpy.data.objects.new("cam", cam_data)
cam.location = (0, -9.0, 0.2)
cam.rotation_euler = (math.radians(90), 0, 0)
scene.collection.objects.link(cam)
scene.camera = cam
key = bpy.data.lights.new("key", "AREA")
key.energy = 500
key.size = 8
key_ob = bpy.data.objects.new("key", key)
key_ob.location = (-2, -5, 5)
key_ob.rotation_euler = (math.radians(55), 0, math.radians(-15))
scene.collection.objects.link(key_ob)

# Отступы и размер: слово должно занять почти весь кадр по ширине.
FIT = 1.0
logo.scale = (FIT, FIT, FIT)
# Буквы лежат в плоскости XY; поднимаем их лицом к камере.
for ob in (left, right):
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.location.z = ob.location.y + 0.36 - 0.29
    ob.location.y = 0.0


def ease_out(t):
    return 1 - (1 - t) ** 3


def pose(frame):
    if frame <= ARRIVE:
        t = (frame - 1) / (ARRIVE - 1)
        k = ease_out(t) ** 1.4
        depth = 70.0 * (1 - k)
        logo.location = (0, depth, 0.2 + 2.5 * (1 - k))
        logo.rotation_euler = (math.radians(38 * (1 - k)), 0, math.radians(-540 * (1 - k)))
    else:
        t = (frame - ARRIVE) / 30
        logo.location = (0, 0, 0.2 + 0.03 * math.sin(t * 2.2))
        logo.rotation_euler = (math.radians(2.5 * math.sin(t * 1.7)), 0, math.radians(5 * math.sin(t * 1.1)))
    sweep.inputs["Location"].default_value[0] = -1.3 + ((frame * 0.035) % 2.6)
    wobble = 1 + 0.45 * math.sin(frame * 2.1) * math.sin(frame * 0.73)
    spark_ob.scale = (wobble, wobble, wobble)


frames = [int(f) for f in OPTS["frames"].split(",")] if OPTS["frames"] else list(range(1, LAST + 1))
for done, frame in enumerate(frames, 1):
    pose(frame)
    scene.render.filepath = os.path.join(OUT, f"logo_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
    print(f"PROGRESS {done}/{len(frames)}  frame {frame}", flush=True)
print("DONE", len(frames), flush=True)
