"""Researcher-editable wording. Restart and create new sessions after changes."""

BASE_IDS = ('base_01', 'base_02', 'base_03', 'base_04')
ENDPOINTS = ('low', 'high')
REFERENCE_MAGNITUDE = 100
ENABLE_PRACTICE = True
BREAK_EVERY = 10

CHARACTERISTICS = {
    'pitch': dict(
        label='Pitch',
        question='Compared with Sound A (100), how high is the perceived pitch of Sound B?',
        lower='Lower pitch', higher='Higher pitch',
        explanation='Pitch describes how high or low a sound seems, like a high or low musical note.',
    ),
    'roughness': dict(
        label='Roughness',
        question='Compared with Sound A (100), how rough does Sound B sound?',
        lower='Smoother', higher='Rougher',
        explanation='Roughness describes a harsh, rattling, or buzzing quality, as opposed to a smooth sound.',
    ),
    'brightness': dict(
        label='Brightness',
        question='Compared with Sound A (100), how bright does Sound B sound?',
        lower='Darker / duller', higher='Brighter / sharper',
        explanation='Brightness describes whether a sound seems dark and dull or bright and sharp.',
    ),
    'noisiness': dict(
        label='Noisiness',
        question='Compared with Sound A (100), how noisy or noise-like does Sound B sound?',
        lower='More tonal / less noisy', higher='More noise-like',
        explanation='Noisiness describes how much a sound resembles a hiss or rushing noise rather than a clear tone.',
    ),
    'pulse_frequency': dict(
        label='Pulsation rate',
        question='Compared with Sound A (100), how fast is the audible pulsation in Sound B?',
        lower='Slower pulsation', higher='Faster pulsation',
        explanation='Pulsation rate describes how quickly the audible pulses or beats repeat.',
    ),
}

MENTAL_DIMENSIONS = [
    dict(
        field='mental_activation', enabled=True, label='Mental activation',
        question='Compared with Sound A, what change in mental activation does Sound B seem to communicate?',
        left='Much calmer / less activated', center='No perceived change', right='Much more activated',
    ),
    dict(
        field='mental_workload', enabled=True, label='Mental workload',
        question='Compared with Sound A, what change in mental workload does Sound B seem to communicate?',
        left='Much lower mental workload', center='No perceived change', right='Much higher mental workload',
    ),
    dict(
        field='attentional_focus', enabled=True, label='Attentional focus',
        question='Compared with Sound A, what change in attentional focus does Sound B seem to communicate?',
        left='Much less focused', center='No perceived change', right='Much more focused',
    ),
]

QUALITY_DIMENSIONS = [
    dict(field='annoyance', question='How annoying do you find Sound B to listen to?',
         left='Not at all annoying', center='Moderately annoying', right='Extremely annoying'),
    dict(field='pleasantness', question='How pleasant does Sound B sound to you?',
         left='Not at all pleasant', center='Moderately pleasant', right='Extremely pleasant'),
]
