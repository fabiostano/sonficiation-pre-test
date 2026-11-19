from otree.api import Bot, expect

from . import Feedback


class PlayerBot(Bot):
    cases = ['full', 'minimal']

    def play_round(self):
        text = 'Example internal feedback.' if self.case == 'full' else ''
        yield Feedback, dict(overall_feedback=text, perceptual_ambiguity='', suitability='')
        expect(self.player.completed, True)
        expect('Your responses have been saved.', 'in', self.html)
