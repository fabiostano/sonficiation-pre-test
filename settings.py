from os import environ


SESSION_CONFIGS = [
    dict(
        name='stimulus_pretest',
        display_name='Auditory stimulus pre-test',
        num_demo_participants=1,
        app_sequence=['intro', 'stimulus_test', 'outro'],
        enable_practice=True,
        break_every=10,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.00,
    participation_fee=0.00,
    doc='Internal pre-testing of stimuli.',
)

PARTICIPANT_FIELDS = ['trial_schedule', 'practice_audio']
SESSION_FIELDS = ['stimulus_manifest', 'mental_dimensions', 'enable_practice', 'break_every']

LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = False

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')
SECRET_KEY = environ.get(
    'OTREE_SECRET_KEY', 'stimulus-pretest-local-development-only',
)

DEMO_PAGE_INTRO_HTML = 'Auditory stimulus evaluation: 40 sound comparisons and final feedback.'
INSTALLED_APPS = ['otree']

