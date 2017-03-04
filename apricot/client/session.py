import ssl
import time
import certifi
import asyncio
from datetime import datetime
from collections import deque

from ..utils import json_dump
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
        self.cookies = deque()

    def __del__(self):
        """ Close all connections on destruction of object """
        self.close()
        
    async def __aenter__(self):
        """ Async with open statement """
        return self

    async def __aexit__(self, type, value, traceback):
        """ Async with close statement (closes connections) """
        self.close()

    def close(self):
        """ Close all running connections """
        if self.isClosed: return
        while len(self.connections) > 0:
            conn = self.connections.pop()
            conn.close()
        self.isClosed = True

    def on_conn_exit(self, conn):
        """
        Connection callback called when connection is lost to:
            - attempt to close the connecion if not closed
            - remove from global class connections
            - delete object for garbage collection
        """
        if conn in self.connections:
            conn.close()
            try: self.connections.remove(conn)
            except: pass
        del conn

    def make_cookie(self, cookie):
        """ Create a cookie entry from cookie obj """
        c     = cookie['__main__']
        key   = list(c.keys())[0]
        value = c[key]
        return '{0}={1}'.format(key, value)

    def add_cookies(self, url, headers):
        """ Add session cookies to header on request """
        cookies = []
        for cookie in self.cookies:
            if 'Path' in cookie:
                if cookie['Path'] in url.path:
                    if 'Location' in cookie:
                        if cookie['Location'] == url.path:
                            cookies.append(self.make_cookie(cookie))
                    else:
                        cookies.append(self.make_cookie(cookie))
        if len(cookies) > 1:
            values = '; ',join(cookies)
            for header in headers:
                if header.lower().strip() == 'cookie':
                    headers[header] = headers[header] + ';' + values
                    return headers
            headers['Cookie'] = values
        return headers

    def save_cookies(self, url, headers):
        """ Handle cookie data received from requests """

        # remove expired cookies
        for i in range(len(self.cookies)):
            cookie = self.cookies[i]
            try:
                for key in cookie:
                    if 'max-age' in key.lower():
                        if time.time() < cookie[key]:
                            self.cookies.remove(cookie)
                            break
                    if 'expires' in key.lower():
                        if cookie[key] < datetime.now():
                            self.cookies.remove(cookie)
                            break
            except:
                pass

        # add cookies from headers
        for header in headers:
            try:
                hkey, hvalue = header.split(': ')
                if hkey.lower().strip() == 'set-cookie':
                    cookie = {'__host__': url.host}
                    for i, item in enumerate(hvalue.split(';')):
                        if item.statswith(' '): item = item[1:]
                        if '=' in item:
                            key   = item.split('=')[0]
                            value = '='.join(item.split('=')[1:])
                            if key.lower() == 'max-age':
                                value = time.time() + int(value.strip())
                            cookie[key] = value
                            if i == 0:
                                cookie['__main__'] = {key:value}
                        else:
                            cookie[item] = True
                    self.cookies.append(cookie)
            except:
                pass


    async def get(self, url, params=None, headers=None, data=None, json=None):
        """ Perform a HTTP GET Request """
        data = json_dump(json) if json is not None else data
        return await self.request("GET", url, params=params, headers=headers, data=data)

    ##### Request Processing ####

    async def request(self, method, url, *args, params=None, headers=None, data=None):
        """ Perform the basic HTTP Request """
        try:
            Url      = ApricotUrl(url, params)
            Headers  = {'Host': Url.host + ('' if Url.port != 443 else ':443')}
            if headers is not None:
                for key in headers: Headers[key] = headers[key]
            Headers  = self.add_cookies(Url, Headers)
            Request  = ' '.join([method.upper(), Url.getpath(), "HTTP/1.1\r\n"])
            Request  = add_headers(Request, Headers, data)
            Protocol = lambda: ApricotProtocol(self.on_conn_exit, Request)

            # create http connection
            print("Host: {0.host} Port: {0.port}".format(Url))
            ctx = self.SSL if Url.schema.lower().endswith('s') else None
            conn, protocol = await self.loop.create_connection(
                Protocol, Url.host, Url.port, ssl=ctx)

            # wait for connection to finish retrieving and parsing
            self.connections.append(protocol)
            await protocol.ready.wait()
            response = protocol.response

            # save cookie data
            self.save_cookies(Url, response.headers)

            # handle redirects
            if 300 <= response.status < 400:
                for key in response.headers:
                    if 'location' in key.lower():
                        redirect = response.headers[key]
                        if redirect.startswith('/'):
                            redirect = '{0.schema}://{0.host}{1}{2}'.format(
                                Url,
                                (':'+str(Url.port) if Url.port not in [443, 80] else ''),
                                redirect
                            )
                        print("\nRedirecting to {}\n".format(redirect))
                        response = await self.request(
                            method, redirect,
                            params=params, headers=headers, data=data
                        )

            # return response object
            return response

        # handle any exceptions as well as task cancelling
        except asyncio.CancelledError:
            return
        except Exception as err:
            print(err)