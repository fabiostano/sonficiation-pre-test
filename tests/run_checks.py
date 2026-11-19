"""Isolated server/form tests without synthesizing or substituting audio.

Only MP3 preparation and template file-existence checks are mocked. No media
bytes are created. These tests cannot establish playback or acoustic validity.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    original_directory = Path.cwd()
    os.environ['OTREE_IN_MEMORY'] = '1'
    os.environ.pop('OTREE_EPHEMERAL', None)
    with tempfile.TemporaryDirectory(prefix='auditory-pretest-checks-') as temporary:
        workspace = Path(temporary)
        for name in ['settings.py', 'intro', 'stimulus_test', 'outro', '_templates', '_static']:
            (workspace / name).symlink_to(ROOT / name)
        os.chdir(workspace)
        try:
            from otree.main import setup
            setup()
            suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_*.py')
            result = unittest.TextTestRunner(verbosity=2).run(suite)
        finally:
            os.chdir(original_directory)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
