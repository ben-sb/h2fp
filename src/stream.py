from states.stream_state import StreamState
from frames.frame import *
from hpack import Encoder

class Stream:
    def __init__(self, connection, stream_id):
        self.connection = connection
        self.stream_id = stream_id
        self.state = StreamState.IDLE
        self.header_encoder = Encoder()

    def process(self, frame):
        if isinstance(frame, HeadersFrame):
            self.state = StreamState.OPEN

            if 'END_HEADERS' in frame.flags:
                data = str.encode(self.connection.fingerprint)

                headers = {'content-length': len(data), 'content-type': 'text/html; charset=UTF-8', ':status': 200, 'access-control-allow-origin': '*'}
                headers_frame = HeadersFrame(self.stream_id, self.header_encoder.encode(headers), flags=['END_HEADERS'])
                self.send_headers(headers_frame)

                data_frame = DataFrame(self.stream_id, data, flags=['END_STREAM'])
                self.send_data(data_frame)
                self.close_connection()

        elif isinstance(frame, RstStreamFrame) or isinstance(frame, GoAwayFrame):
            self.close_connection()

    def send_headers(self, headers):
        self.connection.send_frame(headers)

    def send_data(self, data):
        self.connection.send_frame(data)

    def close_connection(self):
        self.state = StreamState.CLOSED
        self.connection.close()
