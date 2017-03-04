from ..utils import json_load
from ..utils import gzip_decode

class ApricotHttpResponse:
    def __init__(self, headers, body):
        self.__parse(headers, body)

    @property
    def body(self):
        """ Raw byte data of the body """
        return self.__data

    @property
    def text(self):
        """ Body encoded text using UTF-8 """
        if isinstance(self.__data, bytes):
            return self.__data.decode(self.text_enc, 'ignore')
        elif isinstance(self.__data, str):
            return self.__data
        else:
            return str(self.__data)

    @property
    def json(self):
        """ Convert json body to python dict """
        content_type = self.content_type
        if content_type is not None:
            if 'json' in content_type.lower():
                try:
                    parts = [json_load(x) for x in self.text.split('\n') if x]
                    if len(parts) < 1: return parts[0]
                    return parts
                except:
                    pass
        return None

    @property
    def content_type(self):
        """ The content type (MIME) """
        for header in self.headers:
            if 'content-type' == header.lower().strip():
                return self.headers[header]
        return None

    @property
    def length(self):
        """ Size of the raw body """
        return len(self.__data)

    @property
    def charset(self):
        """ The text charset to encode by """
        encoding = self.encoding
        for part in encoding.split(';'):
            if 'charset' in part.lower():
                self.text_enc = '='.join(part.split('=')[1:])

    @property
    def encoding(self):
        """ Content-Encoding header or None """
        for header in self.headers:
            if 'content-encoding' == header.lower().strip():
                return self.headers[header]
        return None

    def __parse(self, headers, body):
        """ Take the protocol gathered data and parse parts """

        # get request properties
        request      = headers[0].split(b' ')
        self.version = request[0].decode()
        self.status  = int(request[1].decode())
        self.reason  = b' '.join(request[2:]).decode()

        # get headers
        self.headers = {}
        for i in range(1, len(headers)):
            key, value = headers[i].split(b': ')
            self.headers[key.decode()] = value.decode()

        # get data
        self.__data   = b''.join(body)
        self.text_enc = 'utf-8'
        for header in self.headers:
            if header.lower() == 'content-encoding':
                if 'gzip' in self.headers[header].lower():
                    self.__data = gzip_decode(self.__data)