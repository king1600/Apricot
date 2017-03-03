import json
import asyncio
from io import BytesIO
from collections import deque
from ..utils import gzip_decode

class ApricotProtocol(asyncio.Protocol):
    def __init__(self, on_exit, data=None):
        self.on_exit   = on_exit
        self.init_data = data
        self.client    = None

        self.headers    = deque()
        self.data       = deque()

        self.gotHeaders = False
        self.isChunked  = False
        self.length     = None

        self.closed    = asyncio.Event()
        self.ready     = asyncio.Event()

    async def wait_closed(self):
        await self.closed.wait()

    def close(self):
        if self.client is not None:
            self.client.close()
        if not self.closed.is_set():
            self.closed.set()

    def connection_made(self, client):
        self.client = client
        if self.init_data:
            self.client.write(self.init_data)

    def connection_lost(self, exc):
        self.on_exit(self)

    def eof_received(self):
        self.headers = b''.join(self.headers).split(b'\r\n')
        self.data    = b''.join(self.data)
        for key in self.headers:
            if b'content-encoding' in key.lower():
                if b'gzip' in b' '.join(key.split(b' ')[1:]).lower():
                    self.data = gzip_decode(self.data)
                    break

        self.ready.set()
        self.close()

    def data_received(self, data):
        parts = data.split(b'\r\n\r\n') #
        for part in parts:
            #print("Part:", part, "\n")
            if not self.gotHeaders:
                self.headers.append(part)
                for key in part.split(b'\r\n'):
                    if b'content-length' in key.lower():
                        try: self.length = int(key.split(b' ')[-1])
                        except: self.length = None
            else:
                part = part.split(b'\r\n')
                for p in part:
                    try: int(p, 16)
                    except: self.data.append(p)
            if len(parts) > 1:
                if not self.gotHeaders:
                    self.gotHeaders = True
                else:
                    if parts[-1] == b'':
                        return self.eof_received()
            if self.length is not None:
                if len(b''.join(self.data)) >= self.length:
                    return self.eof_received()
            
            