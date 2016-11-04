#!/usr/bin/env python3
#! python3

import asyncio
from ..utils import generateID, _BREAK, END_BREAK, CHUNKED, CHUNK_END, _CLEN

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
		self.bodyData    = b''
		self.headerData  = b''
		self.headerEnd   = False
		self.onlyHeader  = False
		self.length      = None
		self.chunk_len   = 0

		# events for on_finish
		self.isReady    = asyncio.Event()
		self.isClosed   = asyncio.Event()

		# register Protocol to client
		if self.hasSession:
			self.session.connections[self.uuid] = self
			self.session.conn_ready[self.uuid].set()


	def connection_made(self, transport):
		""" On connection made """
		
		# get client info
		self.transport   = transport
		self.socket      = self.transport.get_extra_info('socket')
		self.server_addr = self.transport.get_extra_info('peername')

		# write http data
		self.transport.write(self.httpData)

	def data_received(self, data):
		""" Receive and process data """
		chunked = False

		# get the headers
		if not self.headerEnd:
			# set header data
			self.data += data
			self.headerData = data
			self.headerEnd  = True

			# get content length
			if _CLEN in self.headerData:
				for header in self.headerData.split(_BREAK):
					try:
						key   = header.split(b': ')[0]
						value = b': '.join(header.split(b': ')[1:])
						if str(key).lower() == str(_CLEN).lower():
							self.length = int(value)
					except:
						pass
			if self.length is not None: chunked = True

			# break on header end
			if CHUNKED not in self.headerData:
				if self.length == None or self.length == 0:
					if self.headerData.endswith(_BREAK):
						chunked = False
						self.isReady.set()

			# if header only, break
			if self.httpData.startswith(b'HEAD'):
				chunked = False
				self.isReady.set()

			# if redirect, break
			resp_code = int(self.headerData.split(_BREAK)[0].split()[1])
			if str(resp_code)[0] == '3':
				chunked = False
				self.isReady.set()

			# if data already provided, break
			if self.length is not None and self.length > 0:
				self.bodyData = END_BREAK.join(self.headerData.split(END_BREAK)[1:])
				if len(self.bodyData) == self.length:
					chunked = False
					self.isReady.set()

		# chunking data after transfer encoding
		else:
			if CHUNKED in self.data:
				# chunk data
				self.data += data
				self.bodyData += data
				self.chunk_len += len(data)
				chunked = True

				# exit on End Of Chunk Header
				if data.endswith(CHUNK_END):
					self.isReady.set()
			else:
				# still chunk data if content length was reached
				if self.length is not None and self.chunk_len < self.length:
					# chunk data
					if data != self.headerData:
						self.bodyData += data
						self.data += data
						self.chunk_len += len(data)
						chunked = True
				else:
					# Exit if not chunked stream
					self.isReady.set()

		# break if content length was reached
		if chunked:
			if self.length is not None:
				if self.chunk_len >= self.length:
					self.isReady.set()

		# if not chunkable, exit
		if CHUNKED not in self.data and not chunked:
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