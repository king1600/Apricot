import time
from io import BytesIO
from io import StringIO
from gzip import GzipFile

from .. import __version__
try: import simplejson as json
except: import json

BREAK   = "\r\n"
CHARSET = "utf-8"
ENDING  = BREAK + BREAK

REQUEST_HEADERS = {
    'Accept':          '*/*',
    'Connection':      'closed',
    'User-Agent':      'python-apricot/' + __version__,
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.8,pt;q=0.6,es;q=0.4,ru;q=0.2,de;q=0.2,fr;q=0.2,id;q=0.2'
}

def gzip_decode(data):
    stream = BytesIO if isinstance(data, bytes) else StringIO
    with GzipFile(fileobj=stream(data)) as file:
        try: unzipped = file.read()
        except: unzipped = None
    return unzipped

def add_headers(resp='', keyset=None, data=b''):
    headers = REQUEST_HEADERS.copy()
    headers['date'] = time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime())

    if keyset is not None:
        for key in keyset:
            headers[key.lower()] = keyset[key]
    
    builder = StringIO(resp)
    for key in headers:
        builder.write(key.title())
        builder.write(': ')
        builder.write(headers[key])
        builder.write(BREAK)
    builder.write(BREAK)

    request = (resp + builder.getvalue()).encode() + data
    builder.close()
    return request
