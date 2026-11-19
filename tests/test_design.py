import copy
import json
import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from stimulus_test.catalog import (ManifestError, audio_paths, load_manifest,
                                   static_path, validate_audio_files)
from stimulus_test.config import BASE_IDS, CHARACTERISTICS
from stimulus_test.schedule import generate_schedule


class DesignTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest()

    def test_manifest_has_40_comparisons_and_44_paths(self):
        self.assertEqual(len(self.manifest['stimuli']), 40)
        self.assertEqual(len(audio_paths(self.manifest)), 44)

    def test_balanced_adjacent_blocks_over_100_schedules(self):
        signatures = set()
        for seed in range(100):
            schedule = generate_schedule(self.manifest, random.Random(seed))
            self.assertEqual(len(schedule), 40)
            self.assertEqual(len({(t['base_id'], t['characteristic'], t['endpoint']) for t in schedule}), 40)
            first_counts = Counter()
            for index in range(0, 40, 2):
                first, second = schedule[index:index + 2]
                self.assertEqual((first['base_id'], first['characteristic']),
                                 (second['base_id'], second['characteristic']))
                self.assertEqual({first['endpoint'], second['endpoint']}, {'low', 'high'})
                self.assertEqual((first['endpoint_position'], second['endpoint_position']), (1, 2))
                self.assertEqual((first['block_index'], second['block_index']), (index // 2 + 1,) * 2)
                first_counts[first['characteristic'], first['endpoint']] += 1
            for char in CHARACTERISTICS:
                self.assertEqual(first_counts[char, 'high'], 2)
                self.assertEqual(first_counts[char, 'low'], 2)
            for index, trial in enumerate(schedule, 1):
                self.assertEqual(trial['trial_index'], index)
                self.assertEqual(trial['baseline_audio'], f'stimuli/{trial["base_id"]}/baseline.mp3')
                self.assertIn(trial['base_id'], BASE_IDS)
            signatures.add(tuple(t['stimulus_id'] for t in schedule))
        self.assertGreater(len(signatures), 90)

    def write_manifest(self, manifest, directory):
        path = Path(directory) / 'manifest.json'
        path.write_text(json.dumps(manifest))
        return path

    def test_optional_metadata_can_be_omitted(self):
        for row in self.manifest['stimuli']:
            for key in ('actual_parameter_value', 'actual_parameter_unit', 'stimulus_id'):
                row.pop(key)
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(len(load_manifest(self.write_manifest(self.manifest, directory))['stimuli']), 40)

    def test_invalid_manifests_report_errors(self):
        variants = []
        missing = copy.deepcopy(self.manifest)
        missing['stimuli'].pop()
        variants.append(missing)
        duplicate = copy.deepcopy(self.manifest)
        duplicate['stimuli'][-1] = duplicate['stimuli'][0]
        variants.append(duplicate)
        wrong_baseline = copy.deepcopy(self.manifest)
        wrong_baseline['stimuli'][0]['baseline_audio'] = 'stimuli/base_02/baseline.mp3'
        variants.append(wrong_baseline)
        for variant in variants:
            with self.subTest(), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ManifestError):
                    load_manifest(self.write_manifest(variant, directory))

    def test_invalid_or_escaping_paths(self):
        for path in ['/tmp/x.mp3', '../x.mp3', 'x.wav', '', 'x\\y.mp3']:
            with self.subTest(path=path), self.assertRaises(ManifestError):
                static_path(path)

    def test_all_missing_files_are_reported_and_never_created(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ManifestError, 'Missing 44 of 44') as error:
                validate_audio_files(self.manifest, Path(directory))
            self.assertIn('base_04/roughness_high.mp3', str(error.exception))
            self.assertEqual(list(Path(directory).iterdir()), [])
