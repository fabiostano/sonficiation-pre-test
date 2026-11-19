"""Pure block randomization: every characteristic has two high-first bases."""

import random

from .config import BASE_IDS, CHARACTERISTICS


def generate_schedule(manifest, rng=None):
    rng = rng or random.SystemRandom()
    lookup = {(row['base_id'], row['characteristic'], row['endpoint']): row
              for row in manifest['stimuli']}
    blocks = []
    for characteristic in CHARACTERISTICS:
        high_first_bases = set(rng.sample(list(BASE_IDS), 2))
        for base_id in BASE_IDS:
            endpoints = ('high', 'low') if base_id in high_first_bases else ('low', 'high')
            blocks.append([lookup[base_id, characteristic, endpoint].copy() for endpoint in endpoints])
    rng.shuffle(blocks)
    schedule = []
    for block_index, block in enumerate(blocks, 1):
        for endpoint_position, trial in enumerate(block, 1):
            schedule.append(dict(trial, trial_index=len(schedule) + 1,
                                 block_index=block_index, endpoint_position=endpoint_position))
    return schedule
