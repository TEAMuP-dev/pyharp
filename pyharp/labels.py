from dataclasses import dataclass


__all__ = [
    'OutputLabel',
    'AudioLabel',
    'SpectrogramLabel',
    'MidiLabel'
]


@dataclass
class OutputLabel:
    t: float
    label: str
    duration: float = 0.0
    description: str = None

    def __post_init__(self):
        self.y = None

    def set_y(self, y):
        self.y = y


@dataclass
class AudioLabel(OutputLabel):
    amplitude: float = 0.0

    def __post_init__(self):
        super().__post_init__()

        self.y = (self.amplitude + 1) / 2
        self.label_type = self.__class__.__name__


@dataclass
class SpectrogramLabel(OutputLabel):
    frequency: float = 440.0

    def __post_init__(self):
        super().__post_init__()

        # TODO - not sure what to do here yet
        self.label_type = self.__class__.__name__


@dataclass
class MidiLabel(OutputLabel):
    pitch: float = 69

    def __post_init__(self):
        super().__post_init__()

        self.y = self.pitch / 128
        self.label_type = self.__class__.__name__
