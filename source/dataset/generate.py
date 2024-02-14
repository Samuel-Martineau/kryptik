import bpy
import random
import contextlib
from math import hypot, radians, atan2
import os
import sys
import csv
from uuid import uuid4 as uuid
import shutil
from numpy import interp
from tqdm import trange
import bpy
from bpy_extras.object_utils import world_to_camera_view
from config import field_length, field_width, interocular_distance, focal_length, f_stop, focus_distance, sensor_width, resolution_x, resolution_y

image_count, split = sys.argv[1:]
image_count = int(image_count)

bpy.app.binary_path = os.environ.get('BLENDER_PATH', shutil.which('blender'))
bpy.ops.wm.open_mainfile(filepath="./scene.blend")

scene = bpy.context.scene
scene.render.image_settings.file_format = 'JPEG'
scene.render.resolution_x = resolution_x
scene.render.resolution_y = resolution_y
scene.render.use_multiview = True
scene.render.views_format = 'STEREO_3D'
scene.render.views["left"].file_suffix = "_left"
scene.render.views["right"].file_suffix = "_right"

target = bpy.data.objects["Cible"]
target_location = bpy.data.objects["CibleEmplacement"]
target_location.location = (0, -field_length / 2, 0)

camera = scene.camera
camera.data.stereo.interocular_distance = interocular_distance
camera.data.lens = focal_length
camera.data.dof.aperture_fstop = f_stop
camera.data.dof.focus_distance = focus_distance
camera.data.sensor_fit = 'AUTO'
camera.data.sensor_width = sensor_width


thrower = bpy.data.objects["Lanceur"]
thrower_min_distance = field_length / 2
thrower_max_distance = hypot(field_width / 2, field_length)
thrower_min_angle = -radians(90)  # half of a 180° fov
thrower_max_angle = radians(90)  # half of a 180° fov
thrower_location_x_range = (-field_width / 2, field_width / 2)
thrower_location_y_range = (0, field_length / 2)
thrower_location_z_range = (1, 1.5)

human_obstacles = [value for key, value in bpy.data.objects.items()
                   if key.startswith("Humain")]
chair_obstacles = [value for key, value in bpy.data.objects.items()
                   if key.startswith("Chaise")]
table_obstacles = [value for key, value in bpy.data.objects.items()
                   if key.startswith("Table")]
ball_obstacles = [value for key, value in bpy.data.objects.items()
                  if key.startswith("Ballon")]
robot_obstacles = [value for key, value in bpy.data.objects.items()
                   if key.startswith("Robot")]
ground_obstacles = human_obstacles + \
    chair_obstacles + table_obstacles + robot_obstacles
sky_obstacles = ball_obstacles
obstacles = ground_obstacles + sky_obstacles
obstacles_location_x_range = (-field_width / 2, field_width / 2)
obstacles_location_y_range = (-field_length / 2, field_length / 2)
sky_obstacles_location_z_range = (0, 3)


def is_target_visible():
    x, y, z = world_to_camera_view(
        scene, camera, target.location + target_location.location)
    return 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and camera.data.clip_start <= z <= camera.data.clip_end


@contextlib.contextmanager
def nostdout():
    old = os.dup(sys.stdout.fileno())
    sys.stdout.flush()
    os.close(sys.stdout.fileno())
    fd = os.open(os.devnull, os.O_WRONLY)
    yield
    os.close(fd)
    os.dup(old)
    os.close(old)


with open(f'./tmp/dataset/{split}/metadata.csv', 'a') as f:
    writer = csv.writer(f)
    for _ in trange(image_count, dynamic_ncols=True):
        thrower.location = (
            random.uniform(*thrower_location_x_range),
            random.uniform(*thrower_location_y_range),
            random.uniform(*thrower_location_z_range)
        )
        thrower.rotation_euler = (
            0,
            0,
            random.uniform(-radians(40), radians(40))
        )

        for obstacle in obstacles:
            obstacle.location = (
                random.uniform(*obstacles_location_x_range),
                random.uniform(*obstacles_location_y_range),
                0
            )
            obstacle.rotation_euler = (
                0,
                0,
                random.uniform(-radians(180), radians(180))
            )

        for obstacle in sky_obstacles:
            obstacle.location.z = random.uniform(
                *sky_obstacles_location_z_range
            )

        bpy.context.view_layer.update()

        file_name = f"{uuid()}.jpg"

        writer.writerow([
            file_name,
            interp(
                hypot(target_location.location.x - thrower.location.x,
                      target_location.location.y - thrower.location.y),
                [thrower_min_distance, thrower_max_distance],
                [0, 1]
            ),
            interp(
                -atan2(target_location.location.y - thrower.location.y,
                       target_location.location.x - thrower.location.x) - radians(90),
                [thrower_min_angle, thrower_max_angle],
                [0, 1]
            ),
            is_target_visible(),
            *thrower.location,
            thrower.rotation_euler.z,
            *(target.location + target_location.location)
        ])

        with nostdout():
            scene.render.filepath = f'./tmp/dataset/{split}/{file_name}'
            bpy.ops.render.render(write_still=True)
