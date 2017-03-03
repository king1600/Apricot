import ssl
import certifi
import asyncio
from collections import deque

from ..utils import ApricotUrl
from ..utils import add_headers
from .protocol import ApricotProtocol

class ApricotSession:
    def __init__(self, loop=None):
        self.loop = loop if loop != None else asyncio.get_event_loop()
        self.connections = deque()
        self.isClosed    = False

        # SSL authentication
        self.ca_path = certifi.where()
        self.ca_auth = ssl.Purpose.CLIENT_AUTH
        self.SSL     = ssl.create_default_context(self.ca_auth, capath=self.ca_path)

        # Cookie handling
        self.cookies = {}

    def __del__(self):
        self.close()
        
    async def __aenter__(self):
        return self

    async def __aexit__(self, type, value, traceback):
        self.close()

    def close(self):
        if self.isClosed: return
        print("closing clients")
        while len(self.connections) > 0:
            conn = self.connection.pop()
            conn.close()
        self.isClosed = True

    def on_conn_exit(self, conn):
        if conn in self.connections:
            conn.close()
            try: self.connections.remove(conn)
            except: pass

    async def get(self, url):
        return await self.request("GET", url)

    ##### Request Processing ####

    async def request(self, method, url, *args):
        try:
            Url      = ApricotUrl(url)
            Headers  = {'Host': Url.host + ('' if Url.port != 443 else ':443')}
            Request  = ' '.join([method.upper(), Url.getpath(), "HTTP/1.1\r\n"])
            Request  = add_headers(Request, Headers)
            Protocol = lambda: ApricotProtocol(self.on_conn_exit, Request)

            ctx = self.SSL if Url.schema == 'https' else None
            conn, protocol = await self.loop.create_connection(
                Protocol, Url.host, Url.port, ssl=ctx)

            await protocol.ready.wait()

            print("Headers:", protocol.headers, "\n")
            print("Body:", protocol.data, "\n")

        except asyncio.CancelledError:
            return
        except Exception as err:
            print(err)