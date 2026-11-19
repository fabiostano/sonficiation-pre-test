import copy
import json
import math
import re

from otree.api import *

from .catalog import load_manifest, manifest_digest, prepare_audio
from .config import (BREAK_EVERY, CHARACTERISTICS, ENABLE_PRACTICE,
                     MENTAL_DIMENSIONS, QUALITY_DIMENSIONS, REFERENCE_MAGNITUDE)
from .schedule import generate_schedule

doc = 'Auditory biofeedback pretest: representation, sound quality, and magnitude estimation.'


class C(BaseConstants):
    NAME_IN_URL = 'stimulus_test'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 40
    REFERENCE_MAGNITUDE = REFERENCE_MAGNITUDE


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


def validate_dimensions():
    seen = set()
    for dimension in MENTAL_DIMENSIONS:
        name = dimension.get('field', '')
        if not re.fullmatch(r'(mental_[a-z_]+|attentional_[a-z_]+)', name) or name in seen:
            raise ValueError(f'Mental dimension fields must have unique mental_/attentional_ names: {name!r}')
        for key in ('label', 'question', 'left', 'center', 'right'):
            if not isinstance(dimension.get(key), str) or not dimension[key]:
                raise ValueError(f'Mental dimension {name} requires {key}.')
        if not isinstance(dimension.get('enabled'), bool):
            raise ValueError(f'Mental dimension {name} requires enabled=True or False.')
        seen.add(name)


validate_dimensions()


class Player(BasePlayer):
    trial_index = models.IntegerField()
    block_index = models.IntegerField()
    base_id = models.StringField()
    characteristic = models.StringField()
    endpoint = models.StringField()
    endpoint_position = models.IntegerField()
    baseline_audio = models.LongStringField()
    manipulated_audio = models.LongStringField()
    baseline_playback = models.LongStringField()
    manipulated_playback = models.LongStringField()
    stimulus_id = models.StringField()
    actual_parameter_value = models.StringField()
    actual_parameter_unit = models.StringField()
    manifest_version = models.StringField()
    manifest_sha256 = models.StringField()
    dimension_config_json = models.LongStringField()

    # All configured dimensions get separate exported columns, including disabled ones.
    for dimension in MENTAL_DIMENSIONS:
        locals()[dimension['field']] = models.IntegerField(
            label=dimension['question'], choices=list(range(-3, 4)),
            widget=widgets.RadioSelectHorizontal,
        )
    if MENTAL_DIMENSIONS:
        del dimension

    annoyance = models.IntegerField(choices=list(range(1, 8)), widget=widgets.RadioSelectHorizontal)
    pleasantness = models.IntegerField(choices=list(range(1, 8)), widget=widgets.RadioSelectHorizontal)
    magnitude_estimate = models.FloatField(label='Your estimate for Sound B')
    reference_magnitude = models.IntegerField(initial=100)
    assessments_saved = models.BooleanField(initial=False)
    trial_completed = models.BooleanField(initial=False)


def magnitude_estimate_error_message(player, value):
    if not math.isfinite(value) or value <= 0:
        return 'Enter a positive, finite number. You may use decimals; 100 means no perceived difference.'


def creating_session(subsession):
    session = subsession.session
    if subsession.round_number == 1:
        manifest = load_manifest()
        aliases = prepare_audio(manifest)  # Fails clearly for the researcher if any MP3 is missing.
        session.stimulus_manifest = manifest
        session.mental_dimensions = copy.deepcopy([item for item in MENTAL_DIMENSIONS if item['enabled']])
        session.enable_practice = session.config.get('enable_practice', ENABLE_PRACTICE)
        session.break_every = session.config.get('break_every', BREAK_EVERY)
        if not isinstance(session.enable_practice, bool):
            raise ValueError('enable_practice must be True or False.')
        if (isinstance(session.break_every, bool) or not isinstance(session.break_every, int)
                or session.break_every < 0 or session.break_every % 2):
            raise ValueError('break_every must be 0 (disabled) or a positive even number, to keep pairs together.')
        digest = manifest_digest(manifest)
        for player in subsession.get_players():
            schedule = generate_schedule(manifest)
            for trial in schedule:
                trial.update(baseline_playback=aliases[trial['baseline_audio']],
                             manipulated_playback=aliases[trial['manipulated_audio']],
                             manifest_version=manifest['version'], manifest_sha256=digest,
                             dimension_config_json=json.dumps(session.mental_dimensions, ensure_ascii=False))
            player.participant.trial_schedule = schedule
            player.participant.practice_audio = schedule[0]['baseline_playback']
    for player in subsession.get_players():
        trial = player.participant.trial_schedule[subsession.round_number - 1]
        for name in ('trial_index', 'block_index', 'base_id', 'characteristic', 'endpoint',
                     'endpoint_position', 'baseline_audio', 'manipulated_audio',
                     'baseline_playback', 'manipulated_playback', 'manifest_version',
                     'manifest_sha256', 'dimension_config_json'):
            setattr(player, name, trial[name])
        for name in ('stimulus_id', 'actual_parameter_value', 'actual_parameter_unit'):
            value = trial.get(name)
            setattr(player, name, '' if value is None else str(value))


def audio_context(player):
    return dict(audio_a=player.baseline_playback, audio_b=player.manipulated_playback,
                audio_key=f'{player.participant.code}-{player.trial_index}')


class Representation(Page):
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        return [item['field'] for item in player.session.mental_dimensions] + ['annoyance', 'pleasantness']

    @staticmethod
    def vars_for_template(player):
        return dict(audio_context(player), dimensions=player.session.mental_dimensions,
                    quality_dimensions=QUALITY_DIMENSIONS, progress=(player.trial_index - 1) * 100 / C.NUM_ROUNDS)

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.assessments_saved = True


class Magnitude(Page):
    form_model = 'player'
    form_fields = ['magnitude_estimate']

    @staticmethod
    def vars_for_template(player):
        return dict(audio_context(player), characteristic_info=CHARACTERISTICS[player.characteristic],
                    progress=(player.trial_index - 1) * 100 / C.NUM_ROUNDS)

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.trial_completed = True


class Break(Page):
    @staticmethod
    def is_displayed(player):
        interval = player.session.break_every
        return bool(interval and player.round_number < C.NUM_ROUNDS and player.round_number % interval == 0)


EXPORT_FIELDS = [
    'trial_index', 'block_index', 'base_id', 'characteristic', 'endpoint', 'endpoint_position',
    'baseline_audio', 'manipulated_audio', 'baseline_playback', 'manipulated_playback',
    'stimulus_id', 'actual_parameter_value', 'actual_parameter_unit',
    'manifest_version', 'manifest_sha256', 'dimension_config_json',
    'reference_magnitude', 'magnitude_estimate',
] + [item['field'] for item in MENTAL_DIMENSIONS] + [
    'annoyance', 'pleasantness', 'assessments_saved', 'trial_completed',
]


def custom_export(players):
    yield ['session_code', 'participant_code', 'tester_id'] + EXPORT_FIELDS
    for player in players:
        yield [player.session.code, player.participant.code, player.participant.label] + [
            player.field_maybe_none(name) for name in EXPORT_FIELDS
        ]


page_sequence = [Representation, Magnitude, Break]
