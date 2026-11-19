'use strict';

(() => {
    const form = document.getElementById('form');
    let submitted = false;
    const pageError = document.querySelector('[data-page-error]');

    // Keep the actual oTree radio fields as the data source. An untouched slider
    // never checks a radio, so its visual midpoint cannot become a silent answer.
    document.querySelectorAll('[data-bipolar]').forEach(group => {
        const radios = [...group.querySelectorAll('input[type=radio]')];
        if (radios.length !== 7) return;
        const source = group.querySelector('.slider-source');
        const mount = group.querySelector('.slider-mount');
        const status = group.querySelector('.selection-status');
        const slider = document.createElement('input');
        slider.type = 'range';
        slider.min = '-3';
        slider.max = '3';
        slider.step = '1';
        slider.className = 'bipolar-slider';
        slider.setAttribute('aria-labelledby', `label-${radios[0].name}`);
        const checked = radios.find(radio => radio.checked);
        slider.value = checked ? checked.value : '0';
        const describe = () => {
            const selected = radios.find(radio => radio.checked);
            const text = selected ? `Selected: ${Number(selected.value) > 0 ? '+' : ''}${selected.value}`
                                  : 'No response selected. Choose a position; press Space to select 0.';
            status.textContent = text;
            slider.setAttribute('aria-valuetext', text);
            slider.classList.toggle('has-response', Boolean(selected));
        };
        const commit = () => {
            const selected = radios.find(radio => radio.value === slider.value);
            selected.checked = true;
            selected.dispatchEvent(new Event('change', {bubbles: true}));
            describe();
            if (pageError && [...document.querySelectorAll('[data-bipolar]')]
                .every(item => item.querySelector('input[type=radio]:checked'))) {
                pageError.hidden = true;
            }
        };
        slider.addEventListener('input', commit);
        slider.addEventListener('pointerup', commit);
        slider.addEventListener('keydown', event => {
            if (event.key === ' ' || event.key === 'Enter') {
                event.preventDefault();
                commit();
            }
        });
        radios.forEach(radio => { radio.required = false; });
        mount.append(slider);
        const ticks = document.createElement('div');
        ticks.className = 'slider-ticks';
        ticks.setAttribute('aria-hidden', 'true');
        for (let value = -3; value <= 3; value++) {
            const tick = document.createElement('span');
            tick.textContent = value > 0 ? `+${value}` : String(value);
            ticks.append(tick);
        }
        mount.append(ticks);
        source.hidden = true;
        describe();
    });

    // Native media playback only. No speed controls, autoplay, or audio processing.
    document.querySelectorAll('audio').forEach(audio => {
        audio.addEventListener('play', () => {
            document.querySelectorAll('audio').forEach(other => { if (other !== audio) other.pause(); });
        });
        const showError = () => {
            audio.dataset.failed = 'true';
            const message = audio.closest('.audio-card').querySelector('.audio-error');
            if (message) message.hidden = false;
        };
        audio.addEventListener('error', showError);
        audio.querySelectorAll('source').forEach(source => source.addEventListener('error', showError));
    });
    document.querySelectorAll('[data-audio-pair]').forEach(pair => {
        const a = pair.querySelector('[data-sound=a]');
        const b = pair.querySelector('[data-sound=b]');
        const note = pair.querySelector('[data-unlock-note]');
        const card = pair.querySelector('[data-comparison-card]');
        // Store only playback UI state; all research responses go to oTree.
        const key = `pretest-heard-a:${pair.dataset.audioKey}`;
        let unlocked = false;
        try { unlocked = sessionStorage.getItem(key) === 'yes'; } catch (_) { /* storage is optional */ }
        const update = () => {
            b.controls = unlocked;
            b.tabIndex = unlocked ? 0 : -1;
            card.classList.toggle('is-locked', !unlocked);
            note.hidden = unlocked;
        };
        a.addEventListener('ended', () => {
            unlocked = true;
            try { sessionStorage.setItem(key, 'yes'); } catch (_) { /* storage is optional */ }
            update();
        });
        b.addEventListener('play', () => { if (!unlocked) b.pause(); });
        update();
    });

    // oTree's FloatField renders a text input; retain oTree's server validation
    // while providing the numerical input requested by this experiment.
    document.querySelectorAll('.numeric-response input').forEach(input => {
        input.type = 'number';
        input.step = 'any';
        input.min = '0';
        input.inputMode = 'decimal';
        input.autocomplete = 'off';
    });

    if (form) form.addEventListener('submit', event => {
        if (submitted) { event.preventDefault(); return; }
        const unchosen = [...document.querySelectorAll('[data-bipolar]')]
            .find(group => !group.querySelector('input[type=radio]:checked'));
        if (unchosen) {
            event.preventDefault();
            if (pageError) {
                pageError.textContent = 'Please actively select a response for each mental-state question.';
                pageError.hidden = false;
            }
            unchosen.querySelector('.bipolar-slider, input[type=radio]').focus();
            return;
        }
        if (document.querySelector('audio[data-failed=true]')) {
            event.preventDefault();
            document.querySelector('.audio-error:not([hidden])').scrollIntoView({block: 'center'});
            return;
        }
        submitted = true;
        form.querySelectorAll('button[type=submit]').forEach(button => { button.disabled = true; });
    });
    window.addEventListener('pageshow', () => {
        submitted = false;
        if (form) form.querySelectorAll('button[type=submit]').forEach(button => { button.disabled = false; });
    });
})();
