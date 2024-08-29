from dataclasses import dataclass, field
from typing import List, Union, Dict

__all__ = [
    'OutputLabel',
    'AudioLabel',
    'SpectrogramLabel',
    'MidiLabel',
    'LabelList'
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

LabelUnion = Union[AudioLabel, SpectrogramLabel, MidiLabel, OutputLabel]

@dataclass
class LabelList:

    meta: Dict[str, str] = field(default_factory = dict)

    labels: List[LabelUnion] = field(default_factory = list)

    def __post_init__(self):
        self.meta = {
            "_type": self.__class__.__name__
        }

    def append(self, label):
        self.labels.append(label)

    def __iter__(self):
        return iter(self.labels)

    def __getitem__(self, item):
        return self.labels[item]

    def __len__(self):
        return len(self.labels)