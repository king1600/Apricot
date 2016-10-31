#!/usr/bin/env python3
#! python3

try: import ujson as json
except: import json

from ._parser import ApricotParser

class ApricotHttpResponse(object):
	def __init__(self, httpData=b'', aUrl=None):
		self.data = httpData

		self.headers    = {}
		self.status     = None
		self.version    = None
		self.keep_alive = None
		self._body      = None
		self._text      = ''
		self._json      = None

		# set null url info
		self.url     = aUrl.url if aUrl is not None else None
		self.host    = aUrl.host if aUrl is not None else None
		self.schema  = aUrl.schema if aUrl is not None else None
		self.port    = aUrl.port if aUrl is not None else None
		self.path    = aUrl.path if aUrl is not None else None

	def feed(self):
		self.parser = ApricotParser('response')
		self.parser.feed(self.data)
		del self.data
		self.set_attributes()

	async def feed_async(self):
		self.parser = ApricotParser('response')
		await self.parser.feed_async(self.data)
		del self.data
		self.set_attributes()

	def set_attributes(self):
		self._body      = self.parser.body
		self.headers    = self.parser.headers
		self.version    = self.parser.http_ver
		self.status     = self.parser.status
		self.keep_alive = self.parser.keep_alive

		charset = 'utf-8'

		if self._body is not None:
			if 'Content-Type' in self.headers:
				c_type = self.headers['Content-Type']
				if 'charset=' in c_type:
					charset = c_type.split('charset=')[1].split(';')[0]
				if 'json' in c_type:
					try:
						self._json = json.loads(self._body.decode())
					except Exception as e:
						self._json = None
			try:
				self._text = self._body.decode(str(charset).lower())
			except:
				self._text = self._body.decode('utf-8')

	async def json(self): return self._json

	async def text(self): return self._text

	async def body(self): return self._body



class ApricotResponse(object):
	''' Apricot HTTP Response Object '''

	def __init__(self, status=200, headers={},
		content_type=None, charset=None, body=None, text=None):
		self.status       = status
		self.headers      = headers
		self.content_type = content_type
		self.charset      = charset
		self.body         = body
		self.text         = text
		self.using        = 'body'

		header_keys = [x.lower() for x in self.headers]

		if self.body is not None:
			self.headers = {}
			self.headers['Content-Length'] = len(self.body)
		if self.text is not None:
			self.headers = {}
			self.headers['Content-Length'] = len(self.text)
			self.content_type = 'text/plain'
			self.charset      = 'utf-8'
			self.using        = 'text'
		else:
			self.content_type = 'application/html'

		if self.content_type is not None:
			if 'content-type' not in header_keys:
				c_type = self.content_type
				if self.charset is not None:
					c_type += ';charset=' + self.charset
				if self.headers is not None:
					self.headers['Content-Type'] = c_type