from pathlib import Path
from datetime import datetime
import audiotools


__all__ = [
    'load_audio',
    'save_audio'
]


def load_audio(input_audio_path):
    """
    Loads audio at a specified path using audiotools (Descript).

    Args:
        input_audio_path (str): the audio filepath to load.

    Returns:
        signal (audiotools.AudioSignal): wrapped audio signal.
    """

    signal = audiotools.AudioSignal(input_audio_path)

    return signal


def save_audio(signal, output_audio_path=None, include_timestamp=False) -> str:
    """
    Saves audio to a specified path using audiotools (Descript).

    Args:
        signal (audiotools.AudioSignal): wrapped audio signal.
        output_audio_path (str): the filepath to use to save the audio.
        include_timestamp (bool): whether to include a timestamp in the filename.

    Returns:
        output_audio_path (str): the filepath of the saved audio.
    """

    assert isinstance(signal, audiotools.AudioSignal), "Default loading only supports instances of audiotools.AudioSignal."
    
    timestamp = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if include_timestamp else ""

    if output_audio_path is None:
        output_dir = Path("_outputs")
        output_dir.mkdir(exist_ok=True)
        output_audio_path = output_dir / f"output{timestamp}.wav"
        output_audio_path = output_audio_path.absolute().__str__()
    else:
        # Add timestamp to the provided path
        path_obj = Path(output_audio_path)
        output_audio_path = path_obj.parent / f"{path_obj.stem}{timestamp}{path_obj.suffix}"
        output_audio_path = str(output_audio_path)

    signal.write(output_audio_path)

    return str(signal.path_to_file)