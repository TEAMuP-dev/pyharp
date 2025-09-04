from .utils import *

import symusic


__all__ = [
    'load_midi',
    'save_midi',
    'ticks_to_seconds',
    'get_tick_time_in_seconds'
]

def load_midi(input_midi_path):
    """
    Loads MIDI at a specified path using symusic (https://yikai-liao.github.io/symusic/).

    Args:
        input_midi_path (str): the MIDI filepath to load.

    Returns:
        midi (symusic.Score): wrapped midi data.
    """

    midi = symusic.Score.from_file(input_midi_path)

    return midi

def save_midi(midi, output_midi_path=None, include_timestamp=False) -> str:
    """
    Saves MIDI to a specified path using symusic (https://yikai-liao.github.io/symusic/).

    Args:
        midi (symusic.Score): wrapped midi data.
        output_midi_path (str): the filepath to use to save the MIDI.
        include_timestamp (bool): whether to include a timestamp in the filename.

    Returns:
        output_midi_path (str): the filepath of the saved MIDI.
    """

    assert isinstance(midi, symusic.Score), \
        "Default loading only supports instances of symusic.Score."

    if output_midi_path is None:
        output_midi_path = get_default_path(ext=".mid")

    if include_timestamp:
        output_midi_path = add_timestamp_to_path(output_midi_path)

    midi.dump_midi(output_midi_path)

    return output_midi_path

def ticks_to_seconds(ticks, tempo, ticks_per_quarter):
    """
    Compute the absolute time corresponding to a tick duration.

    Args:
        ticks (int): duration in ticks.
        tempo (float): tempo in beats per minute.
        ticks_per_quarter (int): number of ticks for one quarter beat.

    Returns:
        seconds (float): duration in seconds.
    """

    # Seconds per beat times number of quarter beats
    seconds = (60 / tempo) * (ticks / ticks_per_quarter)

    return seconds

def get_tick_time_in_seconds(tick, midi):
    """
    Determine the absolute time corresponding to a given tick.

    Args:
        tick (int): tick to convert to seconds.
        midi (symusic.Score): wrapped midi data.

    Returns:
        time (float): absolute time in seconds.
    """

    time, ticks_elapsed = 0.0, 0

    for i in range(len(midi.tempos)):
        tick_duration = tick - ticks_elapsed

        if tick_duration <= 0:
            break

        if i != len(midi.tempos) - 1:
            tick_duration = min(tick_duration, midi.tempos[i + 1].time - ticks_elapsed)

        ticks_elapsed += tick_duration

        time += ticks_to_seconds(tick_duration, midi.tempos[i].qpm, midi.ticks_per_quarter)

    return time
