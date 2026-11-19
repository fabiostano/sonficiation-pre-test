"""Optional Playwright UI check with real oTree HTML and mocked audio paths.

Requires Playwright plus a desktop Chromium executable. Never supplies audio bytes.
Run: python tests/check_browser.py --executable '/path/to/chrome'
"""

import argparse
import os
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--executable', required=True)
    options = parser.parse_args()
    from playwright.sync_api import sync_playwright

    os.environ['OTREE_IN_MEMORY'] = '1'
    os.environ.pop('OTREE_EPHEMERAL', None)
    original_directory = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='auditory-pretest-browser-') as folder:
        workspace = Path(folder)
        for name in ['settings.py', 'intro', 'stimulus_test', 'outro', '_templates', '_static']:
            (workspace / name).symlink_to(ROOT / name)
        os.chdir(workspace)
        try:
            from otree.main import setup
            setup()
            from otree.session import create_session
            from otree.common2 import static_files_app
            from otree.asgi import app
            from starlette.testclient import TestClient
            from test_flow import neutral_aliases

            with patch('stimulus_test.prepare_audio', side_effect=neutral_aliases), \
                    patch.object(static_files_app, 'assert_file_exists'), \
                    sync_playwright() as playwright:
                session = create_session('stimulus_pretest', num_participants=1,
                                         modified_session_config_fields={'enable_practice': False})
                code = session.get_participants()[0].code
                client = TestClient(app)

                class Bridge(BaseHTTPRequestHandler):
                    def respond(self):
                        length = int(self.headers.get('content-length', '0'))
                        data = dict(parse_qsl(self.rfile.read(length).decode())) if length else None
                        response = client.request(self.command, self.path, data=data, allow_redirects=False)
                        self.send_response(response.status_code)
                        for key, value in response.headers.items():
                            if key.lower() not in ['content-length', 'content-encoding', 'transfer-encoding']:
                                self.send_header(key, value)
                        self.send_header('Content-Length', str(len(response.content)))
                        self.end_headers()
                        self.wfile.write(response.content)

                    do_GET = respond
                    do_POST = respond

                    def log_message(self, *args):
                        pass

                server = HTTPServer(('127.0.0.1', 0), Bridge)
                Thread(target=server.serve_forever, daemon=True).start()
                browser = playwright.chromium.launch(executable_path=options.executable, headless=True)
                context = browser.new_context(viewport={'width': 1200, 'height': 1000})
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/InitializeParticipant/{code}')
                page.locator('input[name=audio_setup][value=headphones]').check()
                page.get_by_role('button', name='Continue to instructions').click()
                page.get_by_role('button', name='Continue', exact=True).click()
                page.wait_for_url('**/Representation/**')
                sliders = page.locator('.bipolar-slider')
                assert sliders.count() == 3
                assert page.locator('input[type=radio]:checked').count() == 0
                assert page.locator('.bipolar-slider.has-response').count() == 0
                assert page.locator('[data-sound=b]').evaluate('(el) => el.controls') is False
                assert page.locator('audio[autoplay]').count() == 0
                assert 'roughness' not in page.content().lower()

                # Test the A-before-B gate without pretending to play or decode audio.
                page.locator('[data-sound=a]').dispatch_event('ended')
                assert page.locator('[data-sound=b]').evaluate('(el) => el.controls') is True
                for field in ['annoyance', 'pleasantness']:
                    page.locator(f'input[name={field}][value="4"]').check(force=True)
                page.get_by_role('button', name='Save ratings and continue').click()
                assert page.locator('[data-page-error]').is_visible()
                sliders.nth(0).focus()
                page.keyboard.press('Space')
                assert page.locator('input[name=mental_activation]:checked').input_value() == '0'
                sliders.nth(1).focus()
                page.keyboard.press('ArrowLeft')
                assert page.locator('input[name=mental_workload]:checked').input_value() == '-1'
                sliders.nth(2).focus()
                page.keyboard.press('ArrowRight')
                assert page.locator('input[name=attentional_focus]:checked').input_value() == '1'
                assert page.locator('[data-page-error]').is_hidden()
                widths = page.locator('.quality-question').first.locator('.form-check-label').evaluate_all(
                    '(els) => els.map(el => el.getBoundingClientRect().width)')
                assert len(widths) == 7 and max(widths) - min(widths) < 1
                page.screenshot(path='/tmp/auditory-pretest-desktop.png', full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path='/tmp/auditory-pretest-mobile.png', full_page=True)
                page.get_by_role('button', name='Save ratings and continue').click()
                page.wait_for_url('**/Magnitude/**')
                magnitude = page.locator('input[name=magnitude_estimate]')
                assert magnitude.input_value() == ''
                assert magnitude.get_attribute('type') == 'number'
                assert magnitude.get_attribute('step') == 'any'
                assert page.locator('[data-sound=b]').evaluate('(el) => el.controls') is True
                magnitude.fill('0')
                page.get_by_role('button', name='Save comparison and continue').click()
                assert 'Enter a positive, finite number' in page.content()
                page.locator('input[name=magnitude_estimate]').fill('123.456789')
                page.get_by_role('button', name='Save comparison and continue').click()
                page.wait_for_url('**/Representation/**')
                assert page.locator('input[type=radio]:checked').count() == 0
                # Each new comparison requires its own reference playback.
                assert page.locator('[data-sound=b]').evaluate('(el) => el.controls') is False
                assert not errors, errors
                print('Chromium UI passed: untouched controls, keyboard selection, A/B gate, responsive scales, '
                      'staged submission, numeric validation, and next-comparison reset.')
                print('Audio was not supplied, played, or decoded. Screenshots: /tmp/auditory-pretest-{desktop,mobile}.png')
                browser.close()
                server.shutdown()
                server.server_close()
        finally:
            os.chdir(original_directory)


if __name__ == '__main__':
    main()
