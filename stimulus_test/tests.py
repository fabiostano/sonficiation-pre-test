from otree.api import Bot, SubmissionMustFail, expect

from . import Break, C, Magnitude, Representation, custom_export


class PlayerBot(Bot):
    cases = ['full', 'minimal']

    def play_round(self):
        trial = self.participant.trial_schedule[self.round_number - 1]
        expect(self.player.base_id, trial['base_id'])
        expect(self.player.endpoint, trial['endpoint'])
        expect(self.player.trial_index, self.round_number)
        expect(self.player.trial_completed, False)
        # Conditions must not leak through labels, media URLs, or debug tables.
        expect('debug-var-value', 'not in', self.html)
        expect(self.player.manipulated_audio, 'not in', self.html)
        expect('magnitude_estimate', 'not in', self.html)
        for term in ('roughness', 'brightness', 'noisiness', 'pulse_frequency', 'pitch', '_low', '_high'):
            expect(term, 'not in', self.html.lower())
        ratings = {dimension['field']: (self.round_number % 7) - 3
                   for dimension in self.session.mental_dimensions}
        ratings.update(annoyance=(self.round_number % 7) + 1, pleasantness=7 - (self.round_number % 7))
        if self.round_number == 1:
            yield SubmissionMustFail(Representation, {})
            yield SubmissionMustFail(Representation, dict(ratings, annoyance=0, pleasantness=8))
            if self.session.mental_dimensions:
                name = self.session.mental_dimensions[0]['field']
                yield SubmissionMustFail(Representation, dict(ratings, **{name: 4}))
        yield Representation, ratings
        expect(self.player.assessments_saved, True)
        expect(self.player.trial_completed, False)
        if self.round_number == 1:
            for value in [0, -1, 'nan', 'inf', '', 'not a number']:
                yield SubmissionMustFail(Magnitude, dict(magnitude_estimate=value))
        # Deliberately disregard endpoint direction; contrary perceptions are valid data.
        estimate = [100, 0.125, 250000.75, 99.5][(self.round_number - 1) % 4]
        yield Magnitude, dict(magnitude_estimate=estimate)
        expect(self.player.magnitude_estimate, estimate)
        expect(self.player.trial_completed, True)
        for name, value in ratings.items():
            expect(getattr(self.player, name), value)
        if self.session.break_every and self.round_number % self.session.break_every == 0 and self.round_number < C.NUM_ROUNDS:
            yield Break
        if self.round_number == C.NUM_ROUNDS:
            rows = list(custom_export(self.player.in_all_rounds()))
            expect(len(rows), 41)
            expect(len({(p.base_id, p.characteristic, p.endpoint) for p in self.player.in_all_rounds()}), 40)
            expect(all(p.trial_completed for p in self.player.in_all_rounds()), True)
