from enum import Enum

class StreamState(Enum):
    IDLE =                  0
    RESERVED_LOCAL =        1
    RESERVED_REMOTE =       2
    OPEN =                  3
    HALF_CLOSED_LOCAL =     4
    HALF_CLOSED_REMOTE =    5
    CLOSED =                6
