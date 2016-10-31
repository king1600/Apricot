#!/usr/bin/env python3
#! python3

import httptools

class ApricotUrlException(Exception): pass

class ApricotUrl(object):
	''' Parse url info using httptools '''

	def __init__(self, url):
		self.url = url
		url = httptools.parse_url(url.encode('utf-8'))

		try:
			self.schema = url.schema
			self.host   = url.host
			self.port   = url.port
			self.path   = url.path
			self.query  = url.query

			if self.schema == None: self.schema = 'http'
			else: self.schema = self.schema.decode('utf-8')

			if self.host is not None: self.host = self.host.decode('utf-8')
			if self.path == None: self.path = '/'
			else: self.path = self.path.decode('utf-8')
			if self.query == None: self.query = ''
			else: self.query = self.query.decode('utf-8')

			if self.port == None:
				if self.schema == 'https': self.port = 443
				else: self.port = 80
			else:
				self.port = int(self.port)
		except Exception as e:
			raise ApricotUrlException("Failed to extract url info!\n:" + str(e))