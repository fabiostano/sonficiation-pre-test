from otree.api import *

doc = 'Optional completion questionnaire and thank-you page.'


class C(BaseConstants):
    NAME_IN_URL = 'outro'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    overall_feedback = models.LongStringField(
        label='Did you notice any recurring problems with the sounds or comparisons? (optional)', blank=True,
    )
    perceptual_ambiguity = models.LongStringField(
        label='Were any sound characteristics particularly difficult to distinguish? (optional)', blank=True,
    )
    suitability = models.LongStringField(
        label='Were there any sounds you would consider unsuitable for a continuously running auditory feedback system? Why? (optional)',
        blank=True,
    )
    completed = models.BooleanField(initial=False)


class Feedback(Page):
    form_model = 'player'
    form_fields = ['overall_feedback', 'perceptual_ambiguity', 'suitability']

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.completed = True


class ThankYou(Page):
    pass


page_sequence = [Feedback, ThankYou]
