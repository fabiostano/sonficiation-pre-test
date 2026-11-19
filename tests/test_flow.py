import copy
import csv
import hashlib
import io
import logging
import unittest
from unittest.mock import patch

from otree.bots.runner import run_all_bots_for_session_config
from otree.common2 import static_files_app
from otree.database import db
from otree.session import create_session
from starlette.testclient import TestClient

from intro import Player as IntroPlayer
from stimulus_test import (Break, C, Player, Representation, custom_export)
from stimulus_test.catalog import load_manifest


def neutral_aliases(manifest):
    return {row[key]: f'stimuli/prepared/{hashlib.sha256(row[key].encode()).hexdigest()}.mp3'
            for row in manifest['stimuli'] for key in ('baseline_audio', 'manipulated_audio')}


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.audio = patch('stimulus_test.prepare_audio', side_effect=neutral_aliases)
        self.audio.start()
        self.static = patch.object(static_files_app, 'assert_file_exists')
        self.static.start()
        self.addCleanup(self.audio.stop)
        self.addCleanup(self.static.stop)
        from otree.asgi import app
        self.client = TestClient(app)

    def post(self, url, data):
        response = self.client.post(url, data=data, allow_redirects=True)
        db.expire_all()
        return response

    def create(self, **config):
        return create_session('stimulus_pretest', num_participants=1,
                              modified_session_config_fields=config)

    def start_comparisons(self, session):
        participant = session.get_participants()[0]
        code = participant.code
        response = self.client.get(f'/InitializeParticipant/{code}')
        response = self.post(response.url, data={'tester_id': '', 'audio_setup': 'headphones'})
        response = self.post(response.url, data={})
        if session.enable_practice:
            response = self.post(response.url, data={'practice_magnitude': 100})
        self.assertIn('/Representation/', str(response.url))
        return code, response

    def test_full_bots_two_participants_two_cases(self):
        logging.getLogger('otree.bots').setLevel(logging.WARNING)
        run_all_bots_for_session_config('stimulus_pretest', 2, None)

    def test_reload_validation_partial_data_and_duplicate_submission(self):
        session = self.create(enable_practice=False)
        session_id = session.id
        code, response = self.start_comparisons(session)
        original = copy.deepcopy(Player.objects_get(session_id=session_id, round_number=1).participant.trial_schedule)
        url = str(response.url)
        html = response.text
        self.assertNotIn(' checked', html)
        self.assertNotIn('magnitude_estimate', html)
        for term in ['roughness', 'brightness', 'noisiness', 'pulse_frequency', 'pitch', '_high', '_low', 'debug-var-value']:
            self.assertNotIn(term, html.lower())
        for _ in range(3):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(Player.objects_get(session_id=session_id, round_number=1).participant.trial_schedule, original)

        partial = {'mental_activation': -3, 'mental_workload': 0, 'attentional_focus': 3, 'annoyance': 2}
        invalid = self.post(url, data=partial)
        self.assertIn('/Representation/', str(invalid.url))
        self.assertIn('checked', invalid.text)
        complete = dict(partial, pleasantness=7)
        response = self.post(url, data=complete)
        magnitude_url = str(response.url)
        self.assertIn('/Magnitude/', magnitude_url)
        player = Player.objects_get(session_id=session_id, round_number=1)
        self.assertTrue(player.assessments_saved)
        self.assertFalse(player.trial_completed)
        self.assertEqual(player.mental_activation, -3)
        self.assertEqual(player.pleasantness, 7)
        self.assertIsNone(player.field_maybe_none('magnitude_estimate'))
        self.assertIn('Your first-impression ratings have been saved.', response.text)
        self.assertNotIn('name="mental_activation"', response.text)
        self.assertIn('value=""', response.text)

        # A browser refresh/back or duplicate first-stage POST cannot overwrite saved ratings.
        duplicate = self.post(url, data=dict(complete, mental_activation=3))
        self.assertIn('/Magnitude/', str(duplicate.url))
        self.assertEqual(Player.objects_get(session_id=session_id, round_number=1).mental_activation, -3)
        response = self.post(magnitude_url, data={'magnitude_estimate': '123.456789'})
        self.assertIn('/Representation/', str(response.url))
        self.assertEqual(Player.objects_get(session_id=session_id, round_number=1).magnitude_estimate, 123.456789)
        again = self.post(magnitude_url, data={'magnitude_estimate': 999})
        self.assertEqual(str(again.url), str(response.url))
        self.assertEqual(Player.objects_get(session_id=session_id, round_number=1).magnitude_estimate, 123.456789)

        players = list(Player.objects_filter(session_id=session_id).order_by('round_number'))
        rows = list(custom_export(players))
        self.assertEqual(len(rows), 41)
        first = dict(zip(rows[0], rows[1]))
        second = dict(zip(rows[0], rows[2]))
        self.assertTrue(first['trial_completed'])
        self.assertFalse(second['trial_completed'])
        self.assertEqual(first['participant_code'], code)
        self.assertIsNone(second['magnitude_estimate'])

    def test_disabled_dimension_and_feature_switches(self):
        from stimulus_test.config import MENTAL_DIMENSIONS
        dimensions = copy.deepcopy(MENTAL_DIMENSIONS)
        dimensions[1]['enabled'] = False
        with patch('stimulus_test.MENTAL_DIMENSIONS', dimensions):
            session = self.create(enable_practice=False, break_every=0)
        code, response = self.start_comparisons(session)
        self.assertNotIn('name="mental_workload"', response.text)
        self.assertIn('name="mental_activation"', response.text)
        player = Player.objects_get(session_id=session.id, round_number=1)
        self.assertNotIn('mental_workload', Representation.get_form_fields(player))
        self.assertFalse(Break.is_displayed(player.in_round(10)))

    def test_breaks_only_after_complete_pairs(self):
        session = self.create()
        players = list(Player.objects_filter(session_id=session.id).order_by('round_number'))
        self.assertEqual([p.round_number for p in players if Break.is_displayed(p)], [10, 20, 30])
        for p in players:
            self.assertEqual(p.trial_index, p.round_number)
            self.assertEqual(p.endpoint_position, 1 if p.round_number % 2 else 2)

    def test_missing_audio_blocks_real_session_creation(self):
        self.audio.stop()
        from stimulus_test.catalog import ManifestError
        with patch('stimulus_test.catalog.validate_audio_files', side_effect=ManifestError('Missing 44 of 44 required MP3 files')):
            with self.assertRaisesRegex(Exception, 'Missing 44 of 44'):
                self.create()

    def test_standard_and_custom_exports(self):
        from otree.export import export_app
        session = self.create()
        session_id = session.id
        players = list(Player.objects_filter(session_id=session_id).order_by('round_number'))
        rows = list(custom_export(players))
        self.assertEqual(len(rows), 41)
        for row in rows[1:]:
            values = dict(zip(rows[0], row))
            self.assertEqual(values['reference_magnitude'], 100)
            self.assertIsNone(values['magnitude_estimate'])
            self.assertFalse(values['trial_completed'])
        for app, expected in [('intro', 'audio_setup'), ('stimulus_test', 'mental_activation'),
                              ('outro', 'perceptual_ambiguity')]:
            output = io.StringIO()
            export_app(app, output)
            output.seek(0)
            reader = csv.DictReader(output)
            self.assertIn('player.' + expected, reader.fieldnames)
            self.assertTrue(list(reader))
