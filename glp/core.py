# SPDX-License-Identifier: CC-BY-NC-4.0
"""Glass location prediction on facade planes parallel to a street axis."""
import math
from pathlib import Path
import cv2
import numpy as np


def project_pixels(pixels, width, height, *, signed_distance_m, street_azimuth_deg,
                   walk_distance_m=0.0, lateral_offset_m=0.0,
                   source_height_m=0.0, target_height_m=None):
    """Project source pixels to a target viewpoint; heights share a ground datum.

    Omitting target_height_m preserves the source height. Coordinates are west,
    south, up, with the source camera at horizontal origin.
    """
    if target_height_m is None:
        target_height_m = source_height_m
    pixels = np.asarray(pixels, dtype=float).reshape(-1, 2)
    phi = 2 * np.pi * pixels[:, 0] / width
    theta = np.pi / 2 - np.pi * pixels[:, 1] / height
    directions = np.column_stack((-np.cos(theta)*np.sin(phi),
                                  -np.cos(theta)*np.cos(phi), np.sin(theta)))
    angle = math.radians(street_azimuth_deg)
    forward = np.array([-math.sin(angle), -math.cos(angle), 0.0])
    right = np.array([-math.cos(angle), math.sin(angle), 0.0])
    denominator = directions @ right
    valid = np.abs(denominator) >= 1e-9
    distance = np.zeros(len(pixels))
    np.divide(signed_distance_m, denominator, out=distance, where=valid)
    valid &= distance > 0
    points = distance[:, None] * directions
    points[:, 2] += source_height_m
    camera = walk_distance_m * forward + lateral_offset_m * right
    camera[2] = target_height_m
    vectors = points - camera
    rho = np.hypot(vectors[:, 0], vectors[:, 1])
    valid &= np.linalg.norm(vectors, axis=1) > 1e-9
    new_phi = np.mod(np.arctan2(-vectors[:, 0], -vectors[:, 1]), 2*np.pi)
    new_theta = np.arctan2(vectors[:, 2], rho)
    result = np.column_stack((new_phi / (2*np.pi)*width,
                              (np.pi/2-new_theta) / np.pi*height))
    return result, valid


def fill_wrapped_polygon(output, pixels, color):
    """Unwrap around the horizontal seam, tile, then let OpenCV clip the polygon."""
    height, width = output.shape[:2]
    xy = np.array(pixels, dtype=float, copy=True)
    xy[:, 0] = np.unwrap(xy[:, 0] * 2*np.pi / width) * width / (2*np.pi)
    if np.ptp(xy[:, 0]) >= width:
        raise ValueError('Contour spans a complete panorama; split the source region.')
    # Every vertex is retained, including vertices needed to close across the seam.
    first = math.ceil(-float(xy[:, 0].max())/width)
    last = math.floor((width-1-float(xy[:, 0].min()))/width)
    for tile in range(first, last+1):
        shifted = xy.copy()
        shifted[:, 0] += tile*width
        polygon = np.floor(shifted).astype(np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(output, [polygon], color)


def generate_glass_mask(image_path, *, street_azimuth_deg, distance_left_m,
                        distance_right_m, walk_distance_m=0.0, lateral_offset_m=0.0,
                        source_height_m=0.0, target_height_m=None, tolerance=10):
    """Return a white-background BGR mask suitable for SCR and a contour summary."""
    values = [street_azimuth_deg, distance_left_m, distance_right_m, walk_distance_m,
              lateral_offset_m, source_height_m]
    if target_height_m is not None:
        values.append(target_height_m)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Geometry values must be finite.')
    if distance_left_m <= 0 or distance_right_m <= 0:
        raise ValueError('Source camera-to-facade distances must be positive.')
    if not -distance_left_m < lateral_offset_m < distance_right_m:
        raise ValueError('Target must remain between the two modeled facade planes.')
    if not isinstance(tolerance, int) or not 0 <= tolerance <= 100:
        raise ValueError('tolerance must be an integer between 0 and 100.')
    image = cv2.imread(str(Path(image_path)), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f'Cannot read source glass mask: {image_path}')
    if image.ndim != 3 or image.shape[2] not in (3,4):
        raise ValueError('Source must be an RGB/RGBA color mask.')
    height, width = image.shape[:2]
    if width != 2*height:
        raise ValueError('Source must be a full equirectangular panorama with width = 2*height.')
    rgb = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2RGB)
    output = np.full((height,width,3),255,dtype=np.uint8)
    summary = {}
    sides = [('left', np.array([255,105,180]), -distance_left_m),
             ('right', np.array([0,255,0]), distance_right_m)]
    for name, color, signed_distance in sides:
        mask = cv2.inRange(rgb, np.clip(color-tolerance,0,255), np.clip(color+tolerance,0,255))
        if image.shape[2] == 4:
            mask[image[:,:,3] == 0] = 0
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        count = 0
        for contour in contours:
            vertices = contour.reshape(-1,2)
            if len(vertices) < 3:
                continue
            projected, valid = project_pixels(vertices,width,height,signed_distance_m=signed_distance,
                street_azimuth_deg=street_azimuth_deg,walk_distance_m=walk_distance_m,
                lateral_offset_m=lateral_offset_m,source_height_m=source_height_m,
                target_height_m=target_height_m)
            if not valid.all():
                raise ValueError(f'{name} glass contour contains a ray that cannot intersect its facade. '
                                 'Check colors, distances and panorama orientation.')
            fill_wrapped_polygon(output,projected,tuple(int(c) for c in color[::-1]))
            count += 1
        summary[name] = count
    return output, summary
