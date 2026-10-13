# SPDX-License-Identifier: CC-BY-NC-4.0
"""Run direct, reflected and final SCR classification using explicit input keys."""
import argparse
import csv
import json
from pathlib import Path
from scr.core import (MaskReader, solar_position, direct_component,
                      reflected_component, merge_reflections, final_condition, observer_height, building_depth)


def run(config_path, input_path, output_dir, legacy_missing=False):
    config_path, input_path, output_dir = map(Path, (config_path, input_path, output_dir))
    config = json.loads(config_path.read_text(encoding='utf-8'))
    settings = config['settings']
    camera_height = observer_height(settings)
    depth = building_depth(settings)
    groups = config['reflection_groups']
    if not groups or len(groups) != len(set(groups)):
        raise ValueError('reflection_groups must contain unique group names.')
    with input_path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not {'sample_id', 'point_id', 'timestamp'} <= set(reader.fieldnames or []):
            raise ValueError('CSV requires sample_id, point_id, timestamp columns.')
        records = list(reader)
    if not records:
        raise ValueError('Input contains no samples.')
    ids = [r['sample_id'] for r in records]
    if any(not i.strip() for i in ids) or len(ids) != len(set(ids)):
        raise ValueError('sample_id must be nonempty and unique.')
    masks = MaskReader(config_path.parent, settings, legacy_missing)
    results, debug = [], []
    for record in records:
        point_id = record['point_id']
        if point_id not in config['points']:
            raise ValueError(f'Unknown point_id: {point_id}')
        point = config['points'][point_id]
        tree, building = masks.read(point['tree_mask']), masks.read(point['building_mask'])
        azimuth, altitude = solar_position(record['timestamp'], settings)
        if altitude <= 0 and not legacy_missing:
            raise ValueError(f"{record['sample_id']}: SCR requires the sun above the horizon.")
        direct = direct_component(tree, building, azimuth, altitude)
        statuses = []
        row = {k: record[k] for k in ('sample_id', 'point_id', 'timestamp')}
        row['observer_height_m'] = camera_height
        row['building_depth_m'] = depth
        row['direct_status'] = direct
        for group in groups:
            g = point['reflections'][group]
            glass = masks.read(g['glass_mask'])
            status, details = reflected_component(tree, glass, azimuth, altitude, g['geometry'], settings)
            statuses.append(status)
            row[f'reflection_{group}'] = status
            debug.append(dict(sample_id=record['sample_id'], group=group, status=status, **details))
        reflected = merge_reflections(statuses)
        row.update(reflected_status=reflected, final_status=final_condition(direct, reflected))
        row['input_status'] = 'incomplete' if tree is None or building is None or 'NoImage' in statuses else 'ok'
        results.append(row)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / 'predictions.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    (output_dir / 'reflection_debug.json').write_text(json.dumps(debug, indent=2), encoding='utf-8')
    print(f'Wrote {len(results)} predictions to {output_dir / "predictions.csv"}')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='examples/block2/scr_config.json')
    parser.add_argument('--input', default='examples/block2/samples.csv')
    parser.add_argument('--output', default='outputs/scr')
    parser.add_argument('--legacy-missing', action='store_true',
                        help='Reproduce historical missing-mask handling; marks incomplete inputs.')
    args = parser.parse_args()
    try:
        run(args.config, args.input, args.output, args.legacy_missing)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f'SCR input error: {error}\n')
