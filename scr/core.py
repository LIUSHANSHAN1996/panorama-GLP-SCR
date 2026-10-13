# SPDX-License-Identifier: CC-BY-NC-4.0
"""SCR classification with the paper's building-depth path geometry."""
from pathlib import Path
from collections import OrderedDict
import math
import cv2
import numpy as np
import pandas as pd
import pvlib


def wrap180(angle):
    return ((angle + 180.0) % 360.0) - 180.0


def angle_difference(a, b):
    return abs(wrap180(a - b))


def is_tree(pixel):
    return pixel is not None and pixel[1] > 150 and pixel[0] < 100 and pixel[2] < 100


def is_green_glass(pixel):
    return pixel[1] > 200 and pixel[0] < 100 and pixel[2] < 100


def is_pink_glass(pixel):
    return pixel[2] > 150 and pixel[0] > 130 and pixel[1] < 180


def window_hit(image, x, y, predicate, radius=3, minimum=3):
    count = 0
    height, width = image.shape[:2]
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            xx, yy = x + dx, y + dy
            if 0 <= xx < width and 0 <= yy < height:
                if predicate(image[yy, xx]):
                    count += 1
                    if count >= minimum:
                        return True
    return False


def glass_side_in_window(image, x, y, radius=3, minimum=3):
    """Return 'left', 'right', or None using the glass detection window."""
    height, width = image.shape[:2]
    hits = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            xx, yy = x + dx, y + dy
            if 0 <= xx < width and 0 <= yy < height:
                pixel = image[yy, xx]
                if is_green_glass(pixel):
                    hits.append((dx * dx + dy * dy, dy, dx, 'right'))
                elif is_pink_glass(pixel):
                    hits.append((dx * dx + dy * dy, dy, dx, 'left'))
    if len(hits) < minimum:
        return None
    center = image[y, x]
    if is_green_glass(center):
        return 'right'
    if is_pink_glass(center):
        return 'left'
    right_count = sum(hit[3] == 'right' for hit in hits)
    left_count = len(hits) - right_count
    if right_count != left_count:
        return 'right' if right_count > left_count else 'left'
    # Equal counts: nearest glass pixel; equal distances use row/column order.
    return min(hits)[3]


def solar_position(timestamp, settings):
    ts = pd.Timestamp(timestamp)
    if pd.isna(ts):
        raise ValueError('Timestamp is missing.')
    if ts.tzinfo is None:
        ts = ts.tz_localize(settings['timezone'])
    ts = ts.replace(second=0, microsecond=0)
    position = pvlib.solarposition.get_solarposition(
        pd.DatetimeIndex([ts]), settings['latitude'], settings['longitude']
    ).iloc[0]
    return float(position['azimuth']), float(position['apparent_elevation'])


def pixel_for(azimuth, altitude, width, height):
    return int((azimuth % 360) / 360 * width), int((90 - altitude) / 180 * height)


def direct_component(tree, building, azimuth, altitude):
    if tree is None or building is None:
        return 'NoImage'
    # Historical behavior retained; use only above-horizon times in ordinary runs.
    if altitude <= 0:
        return 'Su'
    height, width = tree.shape[:2]
    x, y = pixel_for(azimuth, altitude, width, height)
    tree_hit = window_hit(tree, x, y, is_tree)
    building_hit = window_hit(building, x, y, lambda p: bool(np.all(p < 50)))
    return 'BS' if building_hit else 'TS' if tree_hit else 'Su'


def observer_height(settings):
    """Height above the same ground datum used for building heights (meters)."""
    value = settings.get('observer_height_m', 1.2)
    if isinstance(value, bool):
        raise ValueError('observer_height_m must be a finite nonnegative number.')
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError('observer_height_m must be a finite nonnegative number.') from None
    if not math.isfinite(value) or value < 0:
        raise ValueError('observer_height_m must be a finite nonnegative number.')
    return value


def building_depth(settings):
    """Uniform blocking-building depth b in paper Eqs. (15) and (18)."""
    value = settings['building_depth_m']
    if isinstance(value, bool):
        raise ValueError('building_depth_m must be a finite nonnegative number.')
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError('building_depth_m must be a finite nonnegative number.') from None
    if not math.isfinite(value) or value < 0:
        raise ValueError('building_depth_m must be a finite nonnegative number.')
    return value


def reflection_block_geometry(azimuth, altitude, geometry, settings, right):
    """Eqs. (14)-(19), mirrored for either facade.

    The longitudinal s axis increases along street_azimuth_deg, matching
    positive GLP walk displacement. Observer positions and building intervals
    share one origin. Ld/Lr are signed along s; heights use segment lengths.
    This is the paper's back-face-position comparison, not a full solid-ray
    intersection test along every point of the roof or other buildings.
    """
    b = building_depth(settings)
    hc = observer_height(settings)
    street = geometry['street_azimuth_deg']
    normal = (street - 90 if right else street + 90) % 360
    # Facade outward normal must face the sun; tangent rays have no finite path.
    normal_cos = math.cos(math.radians(wrap180(azimuth - normal)))
    if normal_cos <= 1e-9:
        return None
    a = geometry['distance_right_m'] if right else geometry['distance_left_m']
    W = geometry['street_width_m']
    # Signed along-street / facade-normal distance ratio on the shared axis.
    q = math.cos(math.radians(azimuth - street)) / normal_cos
    Lr = a * q                       # Eq. (19), with the appropriate side/sign
    Ld = (W + b) * q                 # Eq. (18)
    s_hit = geometry['observer_s_m'] + Ld + Lr  # Eq. (17)
    tangent = math.tan(math.radians(altitude))
    hr = math.hypot(a, Lr) * tangent           # Eq. (16)
    hd = math.hypot(W + b, Ld) * tangent       # Eq. (15)
    return dict(building_depth_m=b, distance_to_glass_m=a,
                direct_transverse_distance_m=W+b, Ld_m=Ld, Lr_m=Lr,
                s_hit_m=s_hit, hd_m=hd, hr_m=hr,
                relative_ray_height_m=hd+hr, ray_height_m=hc+hd+hr)


def reflected_component(tree, glass, azimuth, altitude, geometry, settings):
    camera_height = observer_height(settings)
    depth = building_depth(settings)
    debug = {'sun_azimuth_deg': azimuth, 'sun_altitude_deg': altitude,
             'observer_height_m': camera_height, 'building_depth_m': depth}
    if glass is None:
        return 'NoImage', debug
    if altitude <= 0:
        return 'Su', debug
    height, width = glass.shape[:2]
    view_azimuth = (2 * settings['reflection_axis_deg'] - azimuth) % 360
    x, y = pixel_for(view_azimuth, altitude, width, height)
    debug.update(reflection_x=x, reflection_y=y)
    if not (0 <= x < width and 0 <= y < height):
        return 'Su', debug
    tree_hit = is_tree(tree[y, x]) if tree is not None else False
    side = glass_side_in_window(glass, x, y)
    if side is None:
        return 'None', debug

    right = side == 'right'
    block = reflection_block_geometry(azimuth, altitude, geometry, settings, right)
    debug.update(side='right' if right else 'left', tree_hit=bool(tree_hit))
    if block is None:
        debug['geometry_reason'] = 'sun_behind_facade_or_parallel'
        return 'None', debug
    debug.update(block)
    segments = geometry['left_buildings'] if right else geometry['right_buildings']
    # Match the back-face s position to original intervals: no depth expansion.
    # At shared endpoints/overlap use the tallest candidate, not list order.
    matches = [(i, float(h)) for i, (start, end, h) in enumerate(segments)
               if start - 1e-6 <= block['s_hit_m'] <= end + 1e-6]
    if not matches:
        debug.update(segment_index=-1, segment_indices=[], effective_height_m=None,
                     geometry_reason='outside_building_table')
        return 'None', debug
    segment_index, effective_height = max(matches, key=lambda item: item[1])
    debug.update(segment_index=segment_index, segment_indices=[i for i, _ in matches],
                 effective_height_m=effective_height)
    if block['ray_height_m'] > effective_height:
        return ('BR-TS' if tree_hit else 'BR'), debug
    return 'None', debug


def merge_reflections(statuses):
    if 'BR-TS' in statuses:
        return 'BR-TS'
    if 'BR' in statuses:
        return 'BR'
    return 'None'


def final_condition(direct, reflected):
    if direct == 'Su':
        return 'Su'
    if direct == 'TS':
        return 'TS-BR' if reflected == 'BR' else 'TS'
    if direct == 'BS':
        return {'BR': 'BS-BR', 'BR-TS': 'BR-TS'}.get(reflected, 'BS')
    return direct


class MaskReader:
    def __init__(self, root, settings, legacy_missing=False):
        self.root = Path(root)
        self.size = (settings['image_width'], settings['image_height'])
        self.legacy_missing = legacy_missing
        self.cache = OrderedDict()

    def read(self, relative_path):
        path = self.root / relative_path
        if path not in self.cache:
            image = cv2.imread(str(path)) if path.is_file() else None
            if image is None and not self.legacy_missing:
                raise ValueError(f'Missing or unreadable mask: {relative_path}')
            # INTER_LINEAR matches the original cv2.resize default.
            self.cache[path] = cv2.resize(image, self.size) if image is not None else None
        self.cache.move_to_end(path)
        while len(self.cache) > 32:
            self.cache.popitem(last=False)
        return self.cache[path]
