import time
from io import BytesIO
from io import StringIO
from gzip import GzipFile

from .. import __version__

# import best json library
try:
    import ujson as json
except:
    try: import simplejson as json
    except: import json

# HTTP constants
BREAK   = "\r\n"
BBREAK  = BREAK.encode()
CHARSET = "utf-8"
ENDING  = BREAK + BREAK

# Default request headers (overridable)
REQUEST_HEADERS = {
    'Accept':          '*/*',
    'Connection':      'closed',
    'User-Agent':      'python-apricot/' + __version__,
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.8,pt;q=0.6,es;q=0.4,ru;q=0.2,de;q=0.2,fr;q=0.2,id;q=0.2'
}

def get_date():
    """ Returns HTTP formatted current date """
    time.strftime('%a, %d %b %Y %H:%M:%S', time.localtime())

def json_dump(data, indent=None):
    """ Dump json using best json lib available """
    return json.dumps(data, indent=indent)

def json_load(data):
    """ Load json using best json lib available """
    return json.loads(data)

def gzip_decode(data):
    """ Return data decoded by gzip """
    stream = BytesIO if isinstance(data, bytes) else StringIO
    with GzipFile(fileobj=stream(data)) as file:
        try: unzipped = file.read()
        except: unzipped = None
    return unzipped

def add_headers(resp='', keyset=None, data=None):
    """ Take request string and add headers + body """

    # create starting headers
    headers = REQUEST_HEADERS.copy()

    # override custom headers
    if keyset is not None:
        for key in keyset:
            headers[key.lower()] = keyset[key]
    
    # build the headers
    builder = StringIO(resp)
    for key in headers:
        builder.write(key.title())
        builder.write(': ')
        builder.write(headers[key])
        builder.write(BREAK)
    builder.write(BREAK)

    # finalize the data
    data = data if data is not None else b''
    request = (resp + builder.getvalue()).encode() + data
    builder.close()
    del builder
    return request
