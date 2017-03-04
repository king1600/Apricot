from urllib.parse import urlparse
from urllib.parse import parse_qs
from urllib.parse import urlencode
from urllib.parse import quote_plus

class ApricotUrl:
    def __init__(self, url, params=None):
        self.parse(url, params)

    def parse(self, url, params):
        """ Parse the url and retrive its attributes """

        # parse the url
        parsed      = urlparse(url)

        # get basic url attributes
        self.url    = url
        self.path   = parsed.path
        self.host   = parsed.netloc
        self.port   = 443 if parsed.scheme.endswith('s') else 80
        self.port   = parsed.port if parsed.port is not None else self.port
        self.schema = parsed.scheme

        # add parameters into dictionary
        self.params = parse_qs(parsed.query)
        for key in self.params:
            self.params[key] = ';'.join(self.params[key])
        if params is not None:
            for param in params:
                self.params[param] = quote_plus(params[param])

    def getpath(self):
        """ Return url path with parameters """
        url = urlencode(self.params)
        if url != '':
            url = '?' + url
        return self.path + url