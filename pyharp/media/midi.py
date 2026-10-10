from .utils import *

import symusic


__all__ = [
    'load_midi',
    'save_midi',
    'ticks_to_seconds',
    'get_tick_time_in_seconds'
]

# The tempo a MIDI file plays at until a tempo event says otherwise
DEFAULT_QPM = 120.0

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

    # The stretch before the first tempo event plays at the default, as does a file
    # carrying no tempo at all. A tempo event at tick zero supersedes this entry, since
    # the stretch it covers is then empty.
    segments = [(0, DEFAULT_QPM)]
    segments += [
        (tempo.time, tempo.qpm) for tempo in sorted(midi.tempos, key=lambda t: t.time)
    ]

    time = 0.0

    for index, (start, qpm) in enumerate(segments):
        if start >= tick:
            break

        # Up to the next tempo event, or to the requested tick where none follows
        end = segments[index + 1][0] if index + 1 < len(segments) else tick

        time += ticks_to_seconds(min(end, tick) - start, qpm, midi.ticks_per_quarter)

    return time
