#!/usr/bin/env python3
#! python3

import os
import io
import gzip
import time
import binascii
from ._url import ApricotUrl
from .. import __version__
from urllib.parse import unquote, quote_plus as quote
from urllib.parse import urlencode, parse_qs, urlparse
try: import ujson as json
except: import json

def generateID():
	return binascii.hexlify(os.urandom(4))

async def generateID_async():
	return generateID()


CHARSET   = "UTF-8"
BREAK     = "\r\n"
_BREAK    = BREAK.encode()
END_BREAK = _BREAK + _BREAK
CHUNKED   = b"Transfer-Encoding: chunked"
CHUNK_END = b'0' + _BREAK + _BREAK
CLEN      = "Content-Length"
_CLEN     = CLEN.encode()

CODES   = {
	"100": "Continue",
	"101": "Switching Protocols",
	"200": "OK",
	"201": "Created",
	"202": "Accepted",
	"203": "Non Authoritative Information",
	"204": "No Content",
	"205": "Reset Content",
	"206": "Partial Content",
	"300": "Multiple Choice",
	"301": "Moved Permanently",
	"302": "Found",
	"303": "See Other",
	"304": "Not Modified",
	"305": "Use Proxy",
	"307": "Temporary Redirect",
	"400": "Bad Request",
	"401": "Unauthorized",
	"402": "Payment Required",
	"403": "Forbidden",
	"404": "Not Found",
	"405": "Method Not Allowed",
	"406": "Not Acceptable",
	"407": "Proxy Authentication Required",
	"408": "Request Timeout",
	"409": "Conflict",
	"410": "Gone",
	"411": "Length Required",
	"412": "Precondition Failed",
	"413": "Request Entity Too Large",
	"414": "Request Uri Too Long",
	"415": "Unsupported Media Type",
	"416": "Requested Range Not Safisfiable",
	"417": "Expectation Failed",
	"500": "Interal Server Error",
	"501": "Not Implemented",
	"502": "Bad Gateway",
	"503": "Service Unavailable",
	"504": "Gateway Timeout",
	"505": "Http Version Not Supported"
}

RESPONSE_HEADERS = {
	"Server"       : "Apricot-HTTP-Server/" + __version__,
	"Connection"   : "close"
}

REQUEST_HEADERS = {
	'Connection': 'keep-alive',
	'Accept'    : '*/*',
	'User-Agent': 'python-apricot/' + __version__,
	"Accept-Encoding": "gzip, deflate, sdch",
	"Accept-Language": "en-US,en;q=0.8,pt;q=0.6,es;q=0.4,ru;q=0.2,de;q=0.2,fr;q=0.2,id;q=0.2"
}

def gzipDecode(data):
	''' decode gzip stream '''
	if isinstance(data, bytes):
		_stream = io.BytesIO
	else:
		_stream = io.StringIO
	with gzip.GzipFile(fileobj=_stream(data)) as f:
		try:
			unzipped = f.read()
		except:
			unzipped = None
	return unzipped

def createParams(params):
	if params != {} or params is not None:
		p = "?"
		for key in params:
			value = params[key]
			if not value.startswith('http'):
				value = quote(value)
			if p == '?': p += key + "=" + value
			else: p += "&" + key + "=" + value
		return p
	else:
		return ''

def createHeaders(resp=b'', headers=None):
	# set default headers
	_headers = RESPONSE_HEADERS.copy()
	_headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())

	# get headers
	if headers is not None:
		for key in headers:
			_headers[key] = headers[key]

	# build string
	for head in _headers:
		resp += (head + ": " + str(_headers[head]) + BREAK).encode()
	resp += BREAK.encode()

	return resp

def makeResponse(code=200):
	# get code and reason
	if str(code) not in CODES:
		code = 404
	reason = CODES[str(code)]
	return ('HTTP/1.1 ' + str(code) + ' ' + reason + BREAK).encode()

def createResponse(response):
	''' Create an HTTP Response byte string from ApricotResponse '''
	resp = makeResponse(response.status)
	resp = createHeaders(resp, response.headers)
	if isinstance(resp, str): resp = resp.encode()

	# add response data
	if response.using != 'body':
		resp += response.text.encode()
	else:
		if response.body is not None:
			if response.headers is not None:
				if 'Content-Length' in response.headers:
					body = response.body
					body = body if isinstance(body, bytes) else body.encode()
					resp += body

	# encode to correct charset
	resp = resp.decode()
	if response.charset is not None:
		resp = resp.encode(response.charset)
	else:
		resp = resp.encode()

	return resp