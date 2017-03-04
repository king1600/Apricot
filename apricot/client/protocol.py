import json
import asyncio
import itertools
from io import BytesIO
from ..utils import BBREAK
from collections import deque
from .response import ApricotHttpResponse

class ApricotProtocol(asyncio.Protocol):
    def __init__(self, on_exit, data=None):
        # initial data, exit callback and socket obj
        self.on_exit   = on_exit
        self.init_data = data
        self.client    = None

        # data being collected
        self.headers    = deque()
        self.body       = deque()

        # data collection conditions
        self.gotHeaders = False
        self.isChunked  = False
        self.length     = None

        # socket events
        self.closed    = asyncio.Event()
        self.ready     = asyncio.Event()

    def close(self):
        """ Closes the client socket and emits the close event """
        if self.client is not None:
            self.client.close()
        if not self.closed.is_set():
            self.closed.set()

    def connection_made(self, client):
        """
        Called when the client object is connected.

        client (socket) : the client socket object
        """
        self.client = client
        if self.init_data:
            self.client.write(self.init_data)

    def connection_lost(self, exc):
        """ Runs callback function when connection is lost """
        self.on_exit(self)

    def eof_received(self):
        """
        When data is finished being collected:
            - create response
            - emit ready event
            - close connection
        """
        self.response = ApricotHttpResponse(self.headers, self.body)
        self.ready.set()
        self.close()

    def complete_headers(self):
        """ Complete header collection and start data collection. """
        self.gotHeaders = True
        headers = itertools.islice(self.headers, 1, len(self.headers))
        for header in headers:
            try:
                key, value = header.split(b': ')
                if b'transfer-encoding' in key.lower():
                    if b'chunked' in value.lower():
                        self.isChunked = True
                elif b'content-length' in key.lower():
                    self.length = int(value)
                    self.isChunked = False
            except:
                pass

    def body_at_end(self, part):
        """
        Collect body data and determine if end of Stream.

        part (bytes)  : the receiving bytes to check for validation
        return (bool) : True if EOS, False otherwise
        """
        if self.isChunked:
            try:
                size = int(part, 16)
                if size < 1: return True
                return False
            except:
                pass
        self.body.append(part)
        if self.length is not None:
            if len(b''.join(self.body)) >= self.length:
                return True
        return False

    def data_received(self, data):
        """ Handle data being received """
        for part in data.split(BBREAK):
            if part.isspace() or part == b'':
                if not self.gotHeaders:
                    self.complete_headers()
                else:
                    self.eof_received()
            else:
                if not self.gotHeaders:
                    self.headers.append(part)
                else:
                    if self.body_at_end(part):
                        return self.eof_received()
            
            