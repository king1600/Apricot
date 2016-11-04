#!/usr/bin/env python3
#! python3

import random
import asyncio

from ..utils import createResponse, BREAK
from ._request import ApricotRequest

class ApricotClient(object):
	''' Apricot async server client '''

	def __init__(self, reader, writer, server):
		self.reader   = reader
		self.writer   = writer
		self.server   = server
		self.running  = True
		self.event    = asyncio.Event()
		self.response = None

		self.hasHeaders = False
		self.headerData = b''
		self.bodyData   = b''
		self.badData    = [False, None, b'']

	async def start(self):
		''' event loop to process data '''
		while self.running:

			# read http headers
			data = await self.readline()
			if data in self.badData:
				self.running = False
				break

			while data not in self.badData:

				# exit on no data
				if not data or self.reader.at_eof():
					self.running = False
					break

				# break on http line break
				if data == BREAK.encode('utf-8'):
					self.hasHeaders = True
					break

				# append to header data if not break yet
				if not self.hasHeaders:
					self.headerData += data

				# read data
				data = await self.readline()
				if data in self.badData:
					self.running = False
					break

			# if not running, exit
			if not self.running: break

			# if headers are ready, its time to attempt to get body
			# 1) process it through the router and generate response
			# 2) send response to socket
			# 3) if ok, get and save body
			if self.hasHeaders:
				
				# build request object
				request = ApricotRequest(self.headerData)
				await request.build_async()

				# get post data
				if request.content_length is not None:
					# get data
					to_read = int(request.content_length)
					data    = await self.read(to_read)

					# decode by charset
					if request.charset is not None:
						if request.charset != '' and not request.charset.isspace():
							charset = str(request.charset)
						else: charset = 'utf-8'
					else: charset = 'utf-8'

					# set data
					try:
						request.body  = data
						request.text  = data.decode(charset)
						self.bodyData = data
					except:
						pass

				# attempt to route
				self.on_request(request)
				await self.server.router.process_request(self, request)

				# wait for coro to finish
				await self.event.wait()

				# set to 404 if a response object wasn't set
				if self.response == None:
					self.response = await self.server.router.default_404(request)

				# create HTTP response
				respContent = createResponse(self.response)
				if not isinstance(respContent, bytes):
					respContent = respContent.encode('utf-8')

				# write http response and close connection
				await self.write(respContent)
				self.running = False
				break

		# drain out thr write buffer
		await self.drain()

		# EOF
		self.on_eof()
		if self.writer.can_write_eof():
			self.writer.write_eof()
		self.reader.feed_eof()

		# Exit
		self.on_exit()
		self.writer.close()


	##### Overwritable Callback functions #####

	def on_exit(self):
		''' This function is called when client is exitting '''
		pass

	def on_read(self, data):
		''' This function is called when byte data is read '''
		pass

	def on_readline(self, data):
		''' This function is called specifically when readline is called '''
		pass

	def on_write(self, data):
		''' This function is called when writing data to trasport '''
		pass

	def on_request(self, request):
		''' This function is called when HTTP Request is formed '''
		pass

	def on_eof(self):
		''' This function is called right before EOF is written '''
		pass

	##### IO Functions #####

	async def read(self, n=-1):
		''' read from reader '''
		data = await self.reader.read(n)
		self.on_read(data)
		return data

	async def readline(self):
		''' read line from reader '''
		data = await self.reader.readline()
		self.on_read(data)
		self.on_readline(data)
		return data


	async def write(self, data, eof=False):
		''' write data to client '''
		if eof: data += "\n"
		if not isinstance(data, bytes):
			data = data.encode('utf-8')
		self.on_write(data)

		self.writer.write(data)

	async def drain(self):
		await self.writer.drain()