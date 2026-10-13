# SPDX-License-Identifier: CC-BY-NC-4.0
"""Generate same-height glass predictions; optional height changes are explicit."""
import argparse
import json
import re
from pathlib import Path
import cv2
import numpy as np
from glp.core import generate_glass_mask


def run(config_path, output_dir):
    config_path, output_dir = Path(config_path), Path(output_dir)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    jobs = config.get('jobs', [])
    if not jobs:
        raise ValueError('jobs must contain at least one projection.')
    ids = [job['job_id'] for job in jobs]
    if len(ids) != len(set(ids)):
        raise ValueError('job_id values must be unique.')
    merged, details = {}, []
    for job in jobs:
        target, group = job['target_id'], job['group']
        if any(not re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in (target,group)):
            raise ValueError('target_id and group accept only letters, digits, hyphens and underscores.')
        params = dict(config.get('defaults', {}))
        params.update(job.get('geometry', {}))
        image, counts = generate_glass_mask(config_path.parent / job['source_mask'], **params)
        key = (target, group)
        if key not in merged:
            merged[key] = image
        else:
            old = merged[key]
            if old.shape != image.shape:
                raise ValueError('Masks merged into one target/group must have the same dimensions.')
            old_fg, new_fg = np.any(old!=255,axis=2), np.any(image!=255,axis=2)
            if np.any(old_fg & new_fg & np.any(old!=image,axis=2)):
                raise ValueError('Left/right colors conflict between reference predictions; inspect sources.')
            old[new_fg] = image[new_fg]
        details.append(dict(job_id=job['job_id'], target_id=target, group=group,
                            source_mask=job['source_mask'], geometry=params, contours=counts))
    output_dir.mkdir(parents=True,exist_ok=True)
    outputs = []
    for (target,group), image in merged.items():
        name = f'{target}__{group}.png'
        if not cv2.imwrite(str(output_dir/name),image):
            raise OSError(f'Could not write {name}')
        outputs.append(dict(target_id=target,group=group,glass_mask=name))
    manifest = dict(outputs=outputs,jobs=details)
    (output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Wrote {len(outputs)} glass masks to {output_dir}')
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='examples/block2/jobs.json')
    parser.add_argument('--output',default='outputs/glp')
    args=parser.parse_args()
    try:
        run(args.config,args.output)
    except (ValueError,KeyError,OSError) as error:
        parser.exit(1,f'GLP input error: {error}\n')
