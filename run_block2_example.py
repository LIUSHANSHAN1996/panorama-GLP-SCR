# SPDX-License-Identifier: CC-BY-NC-4.0
"""Run the real Block 2 GLP-to-SCR example from repository inputs."""
import argparse
import json
from pathlib import Path
from run_glp import run as run_glp
from run_scr import run as run_scr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='outputs/block2')
    args = parser.parse_args()
    base = Path(__file__).resolve().parent / 'examples/block2'
    out = Path(args.output).resolve()
    run_glp(base/'jobs.json', out/'glass')
    config = json.loads((base/'scr_config.json').read_text())
    for point_id, point in config['points'].items():
        for key in ['tree_mask', 'building_mask']:
            point[key] = str((base/point[key]).resolve())
        point['reflections']['facade']['glass_mask'] = str(out/'glass'/(point_id+'__facade.png'))
    config_path = out/'scr_config_used.json'
    config_path.write_text(json.dumps(config, indent=2)+'\n')
    run_scr(config_path, base/'samples.csv', out/'scr')


if __name__ == '__main__':
    main()
