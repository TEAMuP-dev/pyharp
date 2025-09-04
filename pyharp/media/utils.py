from datetime import datetime
from pathlib import Path


__all__ = [
    'get_timestamp',
    'get_default_path',
    'add_timestamp_to_path'
]

def get_timestamp(format=None):
    """
    Obtain the current formatted timestamp.

    Args:
        format (str): format string.

    Returns:
        timestamp (str): formatted timestamp.
    """

    if format is None:
        format = '%m-%d-%Y_%H-%M-%S'

    timestamp = datetime.now().strftime(format)

    return timestamp

def get_default_path(ext=".wav"):
    """
    Obtain a default path for PyHARP output.

    Args:
        ext (str): file extension for default path.

    Returns:
        default_path (str): absolute default path with extension.
    """

    # Create a directory for outputs under CWD
    default_dir = Path("_outputs")
    default_dir.mkdir(exist_ok=True)

    # Place new outfile file under outputs directory
    default_path = default_dir / f"output{ext}"
    default_path = default_path.absolute().__str__()

    return default_path

def add_timestamp_to_path(path_):
    """
    Append a timestamp to the given path.

    Args:
        path_ (str): path to modify.

    Returns:
        timestamped_path (str): timestamped path.
    """

    path = Path(path_)

    path_t = path.parent / f"{path.stem}_{get_timestamp()}{path.suffix}"

    timestamped_path = str(path_t)

    return timestamped_path
