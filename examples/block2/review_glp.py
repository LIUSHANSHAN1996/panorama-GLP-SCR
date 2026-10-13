# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reproduce individual predictions, their unions and review contact sheets.
Run from repository root: python examples/block2/review_glp.py
"""
import argparse
import json
import sys
from pathlib import Path
import cv2
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from glp.core import generate_glass_mask
from run_glp import run

def main():
    base = Path(__file__).resolve().parent
    config = json.loads((base/'jobs.json').read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='outputs/block2_review')
    args = parser.parse_args()
    out = Path(args.output).resolve()
    (out/'individual').mkdir(parents=True, exist_ok=True)
    individual = {}
    for job in config['jobs']:
        im, _ = generate_glass_mask(base/job['source_mask'], **(config['defaults'] | job['geometry']))
        individual[job['job_id']] = im
        if not cv2.imwrite(str(out/'individual'/(job['job_id']+'.png')), im):
            raise OSError(job['job_id'])
    run(base/'jobs.json', out/'merged')
    stats = {}
    for target in dict.fromkeys(j['target_id'] for j in config['jobs']):
        jobs = [j for j in config['jobs'] if j['target_id'] == target]
        merged = cv2.imread(str(out/'merged'/(target+'__facade.png')))
        union = np.logical_or.reduce([np.any(individual[j['job_id']] != 255, axis=2) for j in jobs])
        assert np.array_equal(union, np.any(merged != 255, axis=2))
        for j in jobs:
            im = individual[j['job_id']]
            fg = np.any(im != 255, axis=2)
            assert np.array_equal(merged[fg], im[fg])
        stats[target] = dict(glass_pixels=int(union.sum()), individual_colors_preserved=True,
                             exact_union=True, image_size=[merged.shape[1], merged.shape[0]])
        canvas = np.full((1221,1056,3), (242,237,232), dtype=np.uint8)
        def label(text, y):
            cv2.putText(canvas,text,(16,y),cv2.FONT_HERSHEY_SIMPLEX,.45,(30,30,30),1,cv2.LINE_AA)
        label(target+' | height 1.2 m | pink: left facade; green: right facade',25)
        panels = [(j['job_id'],individual[j['job_id']]) for j in jobs] + [('UNION of all three references',merged)]
        for i,(name,im) in enumerate(panels):
            y = 45 + i*294
            label(name,y+15)
            canvas[y+22:y+278,16:1040] = cv2.resize(im,(1024,256),interpolation=cv2.INTER_NEAREST)
        if not cv2.imwrite(str(out/('review_'+target+'.png')),canvas):
            raise OSError(target)
    (out/'checks.json').write_text(json.dumps(stats,indent=2)+'\n')
    print(json.dumps(stats,indent=2))

if __name__ == '__main__':
    main()
