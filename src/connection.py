from states.connection_state import ConnectionState
from stream import Stream
from frames.frame import *
from threading import Thread
import socket
import base64
import sys

H2_PREFACE = b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'
PREFACE_SIZE = 24
BUFFER_SIZE = 2048

class Connection(Thread):
    def __init__(self, sock):
        super().__init__()
        self.sock = sock
        self.streams = {}

        # data for fingerprint
        self.settings = []
        self.window_update = '00'
        self.priority = []
        self.pseudo_headers = []
        self.fingerprint = ""

    def run(self):
        self.state = ConnectionState.IDLE
        self.receive_preface()

        while self.state != ConnectionState.CLOSED:
            frame = self.recv_frame()
            if frame != None:
                self.process(frame)

    def receive_preface(self):
        try:
            client_preface = self.sock.recv(PREFACE_SIZE)
            self.state = ConnectionState.OPEN if client_preface == H2_PREFACE else ConnectionState.CLOSED
        except:
            self.close()

    def recv_frame(self):
        try:
            header = self.sock.recv(9)
            frame, payload_length = Frame.parse(header)

            payload = self.sock.recv(payload_length)
            frame.parse_payload(payload)

            return frame
        except:
            self.close()
            return None

    def create_stream(self, stream_id):
        s = Stream(self, stream_id)
        self.streams[stream_id] = s
        return s

    def process(self, frame):

        if not self.fingerprint:
            if isinstance(frame, SettingsFrame):
                self.settings = ['{}:{}'.format(s[0].value, s[1]) for s in frame.settings]

                if 'ACK' not in frame.flags:
                    settings = SettingsFrame(0, [])
                    self.send_frame(settings)

            elif isinstance(frame, WindowUpdateFrame):
                self.window_update = str(frame.increment)
                # should adjust window size accordingly

            elif isinstance(frame, PriorityFrame):
                self.priority.append('{}:{}:{}:{}'.format(frame.stream_id, frame.exclusive, frame.stream_dependency, frame.weight))
                # should record priorities

            elif isinstance(frame, HeadersFrame):
                for header in frame.headers:
                    if header[0].startswith(':'):
                        self.pseudo_headers.append(header[0][1])

                self.build_fingerprint()

        elif isinstance(frame, RstStreamFrame) or isinstance(frame, GoAwayFrame):
            self.close()

        # pass frame to appropriate stream
        if frame.stream_id != 0:
            stream = self.streams[frame.stream_id] if frame.stream_id in self.streams else self.create_stream(frame.stream_id)
            stream.process(frame)

    def send_frame(self, frame):
        self.sock.send(frame.serialize())

    def build_fingerprint(self):
        fp_data = []
        fp_data.append(','.join(self.settings))
        fp_data.append(self.window_update)
        fp_data.append(','.join(self.priority if len(self.priority) > 0 else ['0']))
        fp_data.append(','.join(self.pseudo_headers))

        self.fingerprint = self.encode('|'.join([str(d) for d in fp_data]))

    def encode(self, fp):
        return ('01'*10) + 'b3' + base64.b64encode(fp.encode('utf-8')).decode('utf-8')

    def close(self):
        self.state = ConnectionState.CLOSED
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        sys.exit()