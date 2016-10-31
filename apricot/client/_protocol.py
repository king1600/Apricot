#!/usr/bin/env python3
#! python3

import asyncio
from ..utils import generateID, _BREAK, CHUNKED, CHUNK_END

class ApricotProtocol(asyncio.Protocol):
	''' UvLoop async TCP Protocol Server '''

	def __init__(self, loop, session=None, httpData=b'', _id=None):
		# get loop and session
		self.loop = loop if loop != None else asyncio.get_event_loop()
		self.hasSession = True if session is not None else False
		if self.hasSession: self.session = session
		self.uuid = generateID() if _id == None else _id

		# create read info
		self.httpData    = httpData
		self.data        = b''
		self.headerEnd   = False

		# events for on_finish
		self.isReady    = asyncio.Event()
		self.isClosed   = asyncio.Event()

		# register Protocol to client
		if self.hasSession:
			self.session.connections[self.uuid] = self
			self.session.conn_ready[self.uuid].set()


	def connection_made(self, transport):
		# get client info
		self.transport   = transport
		self.socket      = self.transport.get_extra_info('socket')
		self.server_addr = self.transport.get_extra_info('peername')

		# write http data
		self.transport.write(self.httpData)

	def data_received(self, data):
		# get the headers
		if not self.headerEnd:
			self.data += data
			self.headerEnd = True

		# chunking data after transfer encoding
		else:
			if CHUNKED in self.data:
				self.data += data
				# exit on End Of Chunk Header
				if data.endswith(CHUNK_END):
					self.isReady.set()
			else:
				# Exit if not chunked stream
				self.isReady.set()

		# if not chunkable, exit
		if CHUNKED not in self.data:
			self.isReady.set()
		else:
			if CHUNKED in self.data and self.data.endswith(CHUNK_END):
				self.isReady.set()

		# If ready to exit, close connection
		if self.isReady.is_set():
			self.transport.close()

	def connection_lost(self, exc):
		self.isClosed.set()

	def eof_received(self):
		self.isReady.set()
		try: self.transport.close()
		except: pass