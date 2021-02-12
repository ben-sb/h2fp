from hpack import Decoder
import struct
from enum import Enum


class Frame:
    type = None
    allowed_flags = []

    def __init__(self, stream_id, flags=()):
        self.stream_id = stream_id
        self.flags = []

        for flag in flags:
            self.flags.append(flag)

    def parse_flags(self, flags):
        for allowed_flag in self.allowed_flags:
            if flags & allowed_flag.bit:
                self.flags.append(allowed_flag.name)

    def parse_payload(self, payload):
        raise NotImplementedError()

    def serialize(self):
        flags = 0
        for allowed_flag in self.allowed_flags:
            if allowed_flag.name in self.flags:
                flags |= allowed_flag.bit

        payload = self.serialize_payload()

        header = struct.pack('>HBBBL',
            (len(payload) >> 8) & 0xFFFF,
            len(payload) & 0xFF,
            self.type,
            flags,
            self.stream_id & 0x7FFFFFFF
        )

        return header + payload

    def serialize_payload(self):
        return b''

    def __repr__(self):
        return str({'type': self.__class__.__name__, 'flags':self.flags, 'stream_id':self.stream_id})

    @staticmethod
    def parse(raw):
        try:
            header = raw[:9]
            payload_length = struct.unpack('!I', b'\x00' + header[:3])[0]
            type = header[3]
            flags = header[4]
            stream_id = struct.unpack('!I', header[5:9])[0]

            frame = FRAME_TYPES[type](stream_id)
            frame.parse_flags(flags)

            return (frame, payload_length)
        except:
            return None


class Flag:
    def __init__(self, name, bit):
        self.name = name
        self.bit = bit

class DataFrame(Frame):
    type = 0x0
    allowed_flags = [
        Flag('END_STREAM', 0x1),
        Flag('PADDED', 0x8)
    ]

    def __init__(self, stream_id, data='', **kwargs):
        super().__init__(stream_id, **kwargs)
        self.data = data

    def parse_payload(self, payload):
        pos = 0

        if 'PADDED' in self.flags:
            self.pad_length = payload[pos]
            pos += 1
        else:
            self.pad_length = 0

        self.data = payload[pos:len(payload) - self.pad_length]

    def serialize_payload(self):
        padding_data = b''
        padding = b'\0' * 0

        return b''.join([padding_data, self.data, padding])

class HeadersFrame(Frame):
    type = 0x1
    allowed_flags = [
        Flag('END_STREAM', 0x1),
        Flag('END_HEADERS', 0x4),
        Flag('PADDED', 0x8),
        Flag('PRIORITY', 0x20)
    ]
    header_decoder = Decoder()

    def __init__(self, stream_id, data=b'', **kwargs):
        super().__init__(stream_id, **kwargs)
        self.data = data

    def parse_payload(self, payload):
        pos = 0

        if 'PADDED' in self.flags:
            self.pad_length = payload[pos]
            pos += 1
        else:
            self.pad_length = 0

        if 'PRIORITY' in self.flags:
            self.stream_dependency = struct.unpack('!L', payload[pos:pos+4])[0]
            self.exclusive = (self.stream_dependency >> 31) & 1
            self.stream_dependency &= 0x7FFFFFFF
            pos += 4

            self.weight = payload[pos] + 1
            pos += 1

        self.header_block = payload[pos: len(payload) - self.pad_length]
        self.headers = self.header_decoder.decode(self.header_block)

    def serialize_payload(self):
        padding_data = b''
        padding = b'\0' * 0

        if 'PRIORITY' in self.flags:
            priority_data = b''
        else:
            priority_data = b''

        return b''.join([padding_data, priority_data, self.data, padding])

class PriorityFrame(Frame):
    type = 0x2
    allowed_flags = []

    def parse_payload(self, payload):
        self.stream_dependency = struct.unpack('!I', payload[0:4])[0]
        self.exclusive = self.stream_dependency >> 31
        self.weight = payload[4] + 1

class RstStreamFrame(Frame):
    type = 0x3
    allowed_flags = []

    def parse_payload(self, payload):
        self.error_code = struct.unpack('!I', payload[0:4])[0]

class Settings(Enum):
    HEADER_TABLE_SIZE =         0x01
    ENABLE_PUSH =               0x02
    MAX_CONCURRENT_STREAMS =    0x03
    INITIAL_WINDOW_SIZE =       0x04
    MAX_FRAME_SIZE =            0x05
    MAX_HEADER_LIST_SIZE =      0x06

class SettingsFrame(Frame):
    type = 0x4
    allowed_flags = [
        Flag('ACK', 0x1)
    ]

    def __init__(self, stream_id, settings=[], **kwargs):
        super().__init__(stream_id, kwargs)
        self.settings = settings

    def parse_payload(self, payload):
        self.settings = []
        pos = 0

        while pos < len(payload):
            id = struct.unpack('!H', payload[pos:pos+2])[0]
            pos += 2
            value = struct.unpack('!I', payload[pos:pos+4])[0]
            pos += 4

            self.settings.append([Settings(id), value])

    def serialize_payload(self):
        return b''.join([struct.pack('!HL', setting & 0xFF, value) for setting, value in self.settings])

class PushPromiseFrame(Frame):
    type = 0x5
    allowed_flags = [
        Flag('END_HEADERS', 0x4),
        Flag('PADDED', 0x8)
    ]
    header_decoder = Decoder()

    def parse_payload(self, payload):
        pos = 0

        if 'PADDED' in self.flags:
            self.pad_length = payload[pos]
            pos += 1
        else:
            self.pad_length = 0

        self.promised_stream_id = struct.unpack('!I', payload[pos:pos+4])[0]
        pos += 4
        self.header_block = payload[pos: len(payload) - self.pad_length]
        self.headers = self.header_decoder.decode(self.header_block)

class PingFrame(Frame):
    type = 0x6
    allowed_flags = [
        Flag('ACK', 0x1)
    ]

    def parse_payload(self, payload):
        self.opaque_data = payload[0:8]

class GoAwayFrame(Frame):
    type = 0x7
    allowed_flags = []

    def parse_payload(self, payload):
        self.last_stream_id = struct.unpack('!I', payload[0:4])[0]
        self.error_code = struct.unpack('!I', payload[4:8])[0]
        self.additional_data = payload[8:len(payload)]


class WindowUpdateFrame(Frame):
    type = 0x8
    allowed_flags = []

    def parse_payload(self, payload):
        self.increment = struct.unpack('!I', payload[0:4])[0]

class ContinuationFrame(Frame):
    type = 0x9
    allowed_flags = [
        Flag('END_HEADERS', 0x4)
    ]
    header_decoder = Decoder()

    def parse_payload(self, payload):
        self.header_block = payload[0:len(payload)]
        self.headers = self.header_decoder.decode(self.header_block)


FRAME_TYPES = [
    DataFrame,
    HeadersFrame,
    PriorityFrame,
    RstStreamFrame,
    SettingsFrame,
    PushPromiseFrame,
    PingFrame,
    GoAwayFrame,
    WindowUpdateFrame,
    ContinuationFrame
]

