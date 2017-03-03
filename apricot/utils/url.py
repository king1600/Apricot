from urllib.parse import urlparse, parse_qs, urlencode

class ApricotUrl:
    def __init__(self, url):
        self.parse(url)

    def parse(self, url):
        parsed      = urlparse(url)

        self.url    = url
        self.path   = parsed.path
        self.host   = parsed.netloc
        self.port   = 443 if parsed.scheme.endswith('s') else 80
        self.port   = parsed.port if parsed.port is not None else self.port
        self.schema = parsed.scheme

        self.params = parse_qs(parsed.query)
        for key in self.params:
            self.params[key] = ';'.join(self.params[key])

    def getpath(self):
        url = urlencode(self.params)
        if url != '':
            url = '?' + url
        return self.path + url