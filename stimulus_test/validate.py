"""Run with: python -m stimulus_test.validate [--prepare]"""

import argparse

from .catalog import ManifestError, load_manifest, prepare_audio, validate_audio_files


def main():
    parser = argparse.ArgumentParser(description='Validate all 44 pre-rendered stimulus MP3 files.')
    parser.add_argument('--prepare', action='store_true', help='Also create condition-neutral playback copies.')
    options = parser.parse_args()
    try:
        manifest = load_manifest()
        validate_audio_files(manifest)
        if options.prepare:
            prepare_audio(manifest)
    except ManifestError as exc:
        parser.exit(1, f'Stimulus validation failed:\n{exc}\n')
    print('Validated 40 comparisons and all 44 nonempty MP3 files.'
          + (' Playback copies prepared.' if options.prepare else ''))


if __name__ == '__main__':
    main()
