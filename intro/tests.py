from otree.api import Bot, SubmissionMustFail, expect

from . import Instructions, Practice, Welcome


class PlayerBot(Bot):
    cases = ['full', 'minimal']

    def play_round(self):
        yield Welcome, dict(tester_id='internal-tester' if self.case == 'full' else '', audio_setup='headphones')
        yield Instructions
        if self.session.enable_practice:
            yield SubmissionMustFail(Practice, dict(practice_magnitude=0))
            yield Practice, dict(practice_magnitude=100)
        expect(len(self.participant.trial_schedule), 40)
