import math

from otree.api import *

doc = 'Listening setup, representation instructions, and optional unanalysed practice.'


class C(BaseConstants):
    NAME_IN_URL = 'intro'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    tester_id = models.StringField(label='Tester ID (optional)', blank=True)
    audio_setup = models.StringField(
        label='What are you listening with?',
        choices=[['headphones', 'Headphones / earphones'], ['speakers', 'Speakers'], ['other', 'Other']],
        widget=widgets.RadioSelect,
    )
    practice_magnitude = models.FloatField(label='Your estimate for Sound B')


def practice_magnitude_error_message(player, value):
    if not math.isfinite(value) or value <= 0:
        return 'Enter a positive number. Decimals are allowed; 100 means no perceived difference.'


class Welcome(Page):
    form_model = 'player'
    form_fields = ['tester_id', 'audio_setup']

    @staticmethod
    def vars_for_template(player):
        return dict(volume_audio=player.participant.practice_audio)

    @staticmethod
    def before_next_page(player, timeout_happened):
        if player.tester_id.strip():
            player.participant.label = player.tester_id.strip()


class Instructions(Page):
    pass


class Practice(Page):
    form_model = 'player'
    form_fields = ['practice_magnitude']

    @staticmethod
    def is_displayed(player):
        return player.session.enable_practice

    @staticmethod
    def vars_for_template(player):
        return dict(audio_a=player.participant.practice_audio, audio_b=player.participant.practice_audio,
                    audio_key=f'{player.participant.code}-practice')


page_sequence = [Welcome, Instructions, Practice]
