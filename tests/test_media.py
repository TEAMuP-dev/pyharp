"""
Tests for loading and saving the media a model is handed, and for the paths used.
"""

import os
import re
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyharp.media import (  # noqa: E402
    add_timestamp_to_path,
    get_default_path,
    get_timestamp,
    get_tick_time_in_seconds,
    load_audio,
    load_midi,
    save_audio,
    save_midi,
    ticks_to_seconds,
)


# --------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------


def test_a_timestamp_is_ordered_and_filename_safe():
    stamp = get_timestamp()

    assert re.fullmatch(r"\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}", stamp)
    assert not set(stamp) & set("/\\:*?\"<>| ")


def test_a_timestamp_takes_a_format():
    assert re.fullmatch(r"\d{4}", get_timestamp(format="%Y"))


def test_the_default_path_carries_the_extension_asked_for(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert get_default_path(ext=".flac").endswith("output.flac")


def test_the_default_path_is_absolute_and_its_directory_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = get_default_path()

    assert os.path.isabs(path)
    assert os.path.isdir(os.path.dirname(path))


def test_the_default_path_is_fixed(tmp_path, monkeypatch):
    """
    Every job writes the same filename, so nothing accumulates. An app that needs them
    kept apart passes its own path, or asks for a timestamp.
    """
    monkeypatch.chdir(tmp_path)

    assert get_default_path() == get_default_path()


def test_a_timestamp_keeps_the_stem_and_suffix():
    stamped = add_timestamp_to_path("/tmp/a/result.wav")

    assert stamped.startswith("/tmp/a/result_") and stamped.endswith(".wav")


# --------------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------------


@pytest.fixture
def tone(tmp_path):
    """A short stereo file, written through the same path an app would use."""
    import audiotools

    samples = np.stack([np.linspace(-0.5, 0.5, 8000)] * 2)[None, :, :].astype(np.float32)
    signal = audiotools.AudioSignal(samples, sample_rate=16000)
    path = str(tmp_path / "tone.wav")
    signal.write(path)

    return path


def test_audio_round_trips_its_rate_and_channels(tone, tmp_path):
    signal = load_audio(tone)

    assert signal.sample_rate == 16000
    assert signal.num_channels == 2

    out = save_audio(signal, str(tmp_path / "out.wav"))
    reloaded = load_audio(out)

    assert reloaded.sample_rate == 16000
    assert reloaded.num_channels == 2


def test_saving_audio_returns_where_it_went(tone, tmp_path):
    target = str(tmp_path / "named.wav")

    assert save_audio(load_audio(tone), target) == target
    assert os.path.exists(target)


def test_a_lossless_container_is_honored(tone, tmp_path):
    """Preserving the input's container depends on save_audio writing what it is told."""
    out = save_audio(load_audio(tone), str(tmp_path / "out.flac"))

    assert out.endswith(".flac") and os.path.exists(out)


def test_saving_audio_can_timestamp_itself(tone, tmp_path):
    out = save_audio(load_audio(tone), str(tmp_path / "out.wav"), include_timestamp=True)

    assert os.path.basename(out) != "out.wav" and out.endswith(".wav")
    assert os.path.exists(out)


def test_saving_something_that_is_not_a_signal_is_refused(tmp_path):
    with pytest.raises(AssertionError):
        save_audio("not a signal", str(tmp_path / "out.wav"))


# --------------------------------------------------------------------------------
# MIDI
# --------------------------------------------------------------------------------


@pytest.fixture
def score():
    """The MIDI the UI tester ships, so these run against a real file."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "ui_tester", "resources", "test.mid",
    )

    if not os.path.exists(path):
        pytest.skip("the UI tester's test.mid is not present")

    return path


def test_midi_round_trips_its_notes_ticks_tempo_and_tracks(score, tmp_path):
    midi = load_midi(score)
    pitches = [note.pitch for track in midi.tracks for note in track.notes]

    out = save_midi(midi, str(tmp_path / "out.mid"))
    reloaded = load_midi(out)

    assert reloaded.ticks_per_quarter == midi.ticks_per_quarter
    assert len(reloaded.tracks) == len(midi.tracks)
    assert [n.pitch for t in reloaded.tracks for n in t.notes] == pitches
    assert round(reloaded.tempos[0].qpm) == round(midi.tempos[0].qpm)


def test_editing_a_score_in_place_keeps_everything_else(score, tmp_path):
    """What lets a MIDI model change pitches without disturbing the rest."""
    midi = load_midi(score)
    before = [note.pitch for track in midi.tracks for note in track.notes]
    ticks, track_count = midi.ticks_per_quarter, len(midi.tracks)

    for track in midi.tracks:
        for note in track.notes:
            note.pitch += 2

    reloaded = load_midi(save_midi(midi, str(tmp_path / "shifted.mid")))

    assert [n.pitch for t in reloaded.tracks for n in t.notes] == [p + 2 for p in before]
    assert reloaded.ticks_per_quarter == ticks
    assert len(reloaded.tracks) == track_count


def test_saving_midi_returns_where_it_went(score, tmp_path):
    target = str(tmp_path / "named.mid")

    assert save_midi(load_midi(score), target) == target
    assert os.path.exists(target)


def test_saving_midi_can_timestamp_itself(score, tmp_path):
    out = save_midi(load_midi(score), str(tmp_path / "out.mid"), include_timestamp=True)

    assert os.path.basename(out) != "out.mid" and out.endswith(".mid")
    assert os.path.exists(out)


# --------------------------------------------------------------------------------
# Tick to time conversion, which output labels are positioned by
# --------------------------------------------------------------------------------


def built_score(tpq, tempos):
    """A score carrying only the tempo map, which is all this conversion reads."""
    import symusic

    score = symusic.Score(tpq)

    for time_in_ticks, qpm in tempos:
        score.tempos.append(symusic.Tempo(time_in_ticks, qpm))

    return score


def test_a_tick_duration_converts_at_the_given_tempo():
    # One quarter note at 120 BPM lasts half a second
    assert ticks_to_seconds(480, 120, 480) == pytest.approx(0.5)


def test_tick_zero_is_time_zero():
    assert get_tick_time_in_seconds(0, built_score(480, [(0, 100)])) == 0.0


def test_a_single_tempo_times_the_whole_score():
    score = built_score(480, [(0, 60)])

    # One quarter note at 60 BPM lasts a second
    assert get_tick_time_in_seconds(480, score) == pytest.approx(1.0)


def test_a_tempo_change_applies_from_where_it_sits():
    score = built_score(480, [(0, 60), (480, 120)])

    # A second for the first quarter, then a half for the second
    assert get_tick_time_in_seconds(960, score) == pytest.approx(1.5)


def test_a_score_with_no_tempo_plays_at_the_default():
    """A MIDI file without a tempo event is played at 120 BPM."""
    assert get_tick_time_in_seconds(480, built_score(480, [])) == pytest.approx(0.5)


def test_the_stretch_before_the_first_tempo_plays_at_the_default():
    """
    A tempo event is not required to sit at tick zero. What comes before it is timed at
    the default, not at the rate it introduces.
    """
    score = built_score(480, [(480, 60)])

    # A half second at the default for the first quarter, then a second at 60 BPM
    assert get_tick_time_in_seconds(960, score) == pytest.approx(1.5)
