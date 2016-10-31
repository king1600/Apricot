#!/usr/bin/env python3
#! python3

try: import ujson as json
except: import json

from urllib.parse import unquote
from ._parser import ApricotParser

class ApricotRequest(object):
	''' Apricot HTTP Request Object '''

	def __init__(self, data=b''):
		self.data           = data
		self.body           = None
		self.headers        = {}
		self.scheme         = 'http'
		self.method         = "GET"
		self.version        = '1.1'
		self.host           = None
		self.query_dict     = {}
		self.keep_alive     = False
		self.cookies        = {}
		self.has_body       = False
		self.content_type   = ''
		self.charset        = None
		self.content_length = None

	def build(self):
		self.parser = ApricotParser('request')
		self.parser.feed(self.data)
		del self.data

		self.set_attributes()

	async def build_async(self):
		self.build()

	async def read():
		if self.parser.body not in [b'', None]:
			if not self.parser.body.isspace():
				return self.body
		return None

	async def text():
		if self.parser.body != None:
			data = self.parser.body.decode()
			if self.charset is not None:
				charset = self.charset.lower()
			else:
				charset = 'utf-8'
			data = data.encode(charset)
			return data.decode(charset)
		return ''

	async def json(self, loads=json.loads):
		body = await self.text()
		if body is not None:
			return loads(body)
		return None


	def set_attributes(self):
		self.body    = self.parser.body
		self.headers = self.parser.headers
		self.version = self.parser.http_ver

		# get method
		try:
			self.method = self.parser.method
			if isinstance(self.method, bytes):
				self.method = self.method.decode('utf-8')
			self.method = self.method.upper()
		except: pass

		# get host
		try: self.host = self.parser.host
		except: pass

		# get query dict
		try:
			self.path       = self.parser.path
			self.query_dict = self.parser.params
		except:
			pass

		# get has body
		if self.body is not None: self.has_body = True

		# get connection keep alive
		self.keep_alive = self.parser.keep_alive

		# set variables by header values
		for head in self.headers:

			# get cookies
			if 'set-cookie' in head.lower():
				value = self.headers[head]
				try:
					info  = {}
					parts = value.split(';')
					for part in parts:
						cookieVal = '='.join(part.split('=')[1:])
						info[part.split('=')[0]] = cookieVal
					host = self.host
					if isinstance(host, bytes):
						host = host.decode('utf-8')
					self.cookies[host] = info
				except:
					pass

			# get content length
			if 'content-length' in head.lower():
				try:
					value = int(self.headers[head])
					self.content_length = value
				except:
					pass

			# get content type
			if 'content-type' in head.lower():
				try:
					value = self.headers[head]
					self.content_type = value

					if ';charset' in value.lower():
						self.charset = value.split(';charset=')[1]
				except:
					pass