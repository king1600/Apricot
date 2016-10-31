#!/usr/bin/env python3
#! python3

from httptools import parse_url
from httptools import HttpRequestParser
from httptools import HttpResponseParser

class AbstractParser(object):
	''' httptools python struct parsing '''

	def __init__(self):
		self.headers     = {}
		self.body        = b''

	def on_header(self, name, value):
		self.headers[name.decode()] = value.decode()

	def on_body(self, data):
		self.body += data

	def on_message_complete(self):
		if self.body == b'': self.body = None

	def on_message_begin(self): pass

	def on_headers_complete(self): pass

	def on_chunk_header(self): pass

	def on_chunk_complete(self): pass


class ApricotParser(object):
	''' Apricot Http Parser '''

	def __init__(self, parseType="request"):
		# create abstract parser
		self.parser = AbstractParser()

		# determine httptools parser
		if parseType.lower() == "request":
			self.parsed = HttpRequestParser(self.parser)
		else:
			self.parsed = HttpResponseParser(self.parser)

		# set null url info
		self.url     = None
		self.host    = None
		self.schema  = None
		self.port    = None
		self.path    = None
		self.params  = {} 

	async def feed_async(self, data=b''):
		self.feed(data)

	def feed(self, data=b''):
		''' feed data to parser '''
		self.raw_data = data
		self.parsed.feed_data(memoryview(data))
		self.set_attributes() # set apricot attributes

	def set_attributes(self):
		''' set ApricotParser attributes '''

		# check parser type
		if isinstance(self.parsed, HttpRequestParser):
			self.method = self.parsed.get_method().decode()
		else:
			self.status = self.parsed.get_status_code()

		# set basic attr's
		try:
			self.headers    = self.parser.headers
			self.body       = self.parser.body
			self.http_ver   = self.parsed.get_http_version()
			self.keep_alive = self.parsed.should_keep_alive()
		except Exception as e:
			print("error in parser: " + str(e))

		if self.keep_alive == None: self.keep_alive = False

		# parse url and get info
		self.get_url_info()

	def get_url_info(self):
		''' Parse url info '''
		if 'Host' in self.headers:
			try:
				# make url
				self.url = b'http://'
				self.url += self.headers['Host'].encode()

				# add path if request
				if isinstance(self.parsed, HttpRequestParser):
					path = self.raw_data.split(b'\r\n')[0].split()[1]
					self.url += path
					self.path = path

				# parse url and get basic info
				URL = parse_url(self.url)
				self.schema = URL.schema.decode()
				self.host   = URL.host.decode()
				self.port   = URL.port

				# get url query parameters if any
				if URL.query is not None:
					for param in URL.query.split(b'&'):
						parts = param.split(b'=')
						key   = parts[0].decode()
						value = b'='.join(parts[1:]).decode()
						self.params[key] = value

				# decode url from bytes to string
				self.url = self.url.decode()
			except:
				pass


