"""Manifest validation and byte-for-byte, condition-neutral playback copies."""

import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath

from .config import BASE_IDS, CHARACTERISTICS, ENDPOINTS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path(__file__).with_name('manifest.json')
STATIC_ROOT = PROJECT_ROOT / '_static'


class ManifestError(ValueError):
    pass


def static_path(relative, static_root=STATIC_ROOT):
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ManifestError('Audio paths must be nonempty POSIX paths relative to _static/.')
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or path.suffix.lower() != '.mp3':
        raise ManifestError(f'Invalid MP3 path relative to _static/: {relative!r}')
    root = Path(static_root).resolve()
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ManifestError(f'Audio path escapes _static/: {relative!r}')
    return resolved


def load_manifest(path=MANIFEST_PATH):
    """Validate the complete 4 × 5 × 2 design; optional metadata can be omitted."""
    try:
        manifest = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise ManifestError(f'Cannot read stimulus manifest {path}: {exc}') from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get('stimuli'), list):
        raise ManifestError('Manifest must contain a stimuli list.')
    if not isinstance(manifest.get('version'), str) or not manifest['version'].strip():
        raise ManifestError('Manifest requires a nonempty version string.')
    expected = {(base, char, endpoint) for base in BASE_IDS
                for char in CHARACTERISTICS for endpoint in ENDPOINTS}
    seen, baselines, manipulated_paths, stimulus_ids = set(), {}, set(), set()
    for index, row in enumerate(manifest['stimuli'], 1):
        if not isinstance(row, dict):
            raise ManifestError(f'Stimulus {index} must be an object.')
        required = ('base_id', 'characteristic', 'endpoint', 'baseline_audio', 'manipulated_audio')
        if any(not isinstance(row.get(key), str) or not row[key] for key in required):
            raise ManifestError(f'Stimulus {index} requires {", ".join(required)}.')
        combination = (row['base_id'], row['characteristic'], row['endpoint'])
        if combination not in expected or combination in seen:
            raise ManifestError(f'Unexpected or duplicate combination: {combination}')
        seen.add(combination)
        for key in ('baseline_audio', 'manipulated_audio'):
            static_path(row[key])
        if baselines.setdefault(row['base_id'], row['baseline_audio']) != row['baseline_audio']:
            raise ManifestError(f'All comparisons for {row["base_id"]} must use the same baseline.')
        if row['manipulated_audio'] in manipulated_paths:
            raise ManifestError(f'Manipulated MP3 paths must be unique: {row["manipulated_audio"]}')
        manipulated_paths.add(row['manipulated_audio'])
        stimulus_id = row.get('stimulus_id')
        if stimulus_id is not None:
            if not isinstance(stimulus_id, str) or not stimulus_id or stimulus_id in stimulus_ids:
                raise ManifestError('Optional stimulus_id values must be nonempty, unique strings.')
            stimulus_ids.add(stimulus_id)
        for key in ('actual_parameter_value', 'actual_parameter_unit'):
            value = row.get(key)
            if value is not None and (isinstance(value, (list, dict, bool)) or
                                      (isinstance(value, float) and not math.isfinite(value))):
                raise ManifestError(f'{key} must be a scalar value or null.')
    if seen != expected:
        raise ManifestError(f'Expected exactly 40 comparisons. Missing combinations: {sorted(expected - seen)}')
    if len(set(baselines.values())) != 4 or set(baselines.values()) & manipulated_paths:
        raise ManifestError('The design requires 4 distinct baseline paths and 40 distinct comparison paths.')
    return manifest


def audio_paths(manifest):
    return sorted({row[key] for row in manifest['stimuli']
                   for key in ('baseline_audio', 'manipulated_audio')})


def validate_audio_files(manifest, static_root=STATIC_ROOT):
    missing = [path for path in audio_paths(manifest) if not static_path(path, static_root).is_file()]
    empty = [path for path in audio_paths(manifest)
             if static_path(path, static_root).is_file() and static_path(path, static_root).stat().st_size == 0]
    errors = []
    if missing:
        errors.append(f'Missing {len(missing)} of 44 required MP3 files:\n' +
                      '\n'.join(f'  _static/{path}' for path in missing))
    if empty:
        errors.append('Empty MP3 files:\n' + '\n'.join(f'  _static/{path}' for path in empty))
    if errors:
        raise ManifestError('\n'.join(errors) + '\nSupply the pre-rendered MP3s; no audio is generated or substituted.')


def manifest_digest(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def prepare_audio(manifest, static_root=STATIC_ROOT):
    """Hash and copy existing MP3 bytes; never synthesize or process audio.

    Opaque content-addressed URLs prevent condition labels in the player and
    preserve earlier session audio when a source file is later replaced.
    """
    validate_audio_files(manifest, static_root)
    directory = Path(static_root) / 'stimuli' / 'prepared'
    directory.mkdir(parents=True, exist_ok=True)
    aliases = {}
    for relative in audio_paths(manifest):
        source = static_path(relative, static_root)
        with source.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        target = directory / f'{digest}.mp3'
        if not target.exists():
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as temporary:
                temporary_name = temporary.name
                with source.open('rb') as stream:
                    shutil.copyfileobj(stream, temporary)
            os.replace(temporary_name, target)
        aliases[relative] = f'stimuli/prepared/{digest}.mp3'
    return aliases
