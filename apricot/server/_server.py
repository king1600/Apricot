#!/usr/bin/env python3
#! python3

import os, sys
import asyncio

from ._router import ApricotRouter
from ..client import ApricotClient

class ApricotServer(object):

	def __init__(self, host="localhost", port=8080, loop=None):
		''' create Apricot Server
		@param port : port to host server on
		'''

		# event loop
		if loop == None:
			self.loop   = asyncio.get_event_loop()#uvloop.new_event_loop()
		else:
			self.loop   = loop

		# set settings
		self.host       = host
		self.port       = port
		self.running    = False
		self.canRun     = True
		self.isClosed   = False

		# server objects
		self.server     = None
		self.clients    = {}
		self.clientObj  = ApricotClient

		# create router
		self.router     = ApricotRouter(self)

	def __del__(self):
		self.stop() # stop all tasks

		# close the event loop
		try: self.loop.close()
		except: pass
		self.loop = None

	def start(self):
		''' start apricot server '''
		if self.canRun:

			# create server coroutine
			coro = asyncio.start_server(self.accept_client, 
				self.host, self.port, loop=self.loop)

			# get socket server from coroutine
			self.server = self.loop.run_until_complete(coro)

			# server is started
			print("Server stated on: {0}:{1}".format(self.host, self.port))
			self.running = True

	def wait_until_stopped(self):
		''' wait until server is stopped '''
		if not self.running or not self.canRun: return
		if self.running and self.canRun:
			try:
				self.loop.run_forever()
			except KeyboardInterrupt:
				return

	def stop(self):
		''' close apricot server '''
		if self.isClosed: return

		# wait for all connections to close
		if self.server is not None:
			self.server.close()
			self.loop.run_until_complete(
				self.server.wait_closed())
			self.server = None

		# wait for all tasks to close
		#for task in asyncio.Task.all_tasks(self.loop):
		#	task.cancel()

		# close ApricotServer
		self.running  = False
		self.canRun   = False
		self.isClosed = True
		self.loop.stop()

	#### Server Functions ####

	async def accept_client(self, reader, writer):
		''' handle requests for new clients '''

		# create a new client and task
		new_client = self.clientObj(reader, writer, self)
		new_task = asyncio.Task(new_client.start())

		# add client to server clients
		self.clients[new_task] = (new_client, reader, writer)

		# add client remove callback
		new_task.add_done_callback(self.on_client_exit)

	# remove client on exit
	def on_client_exit(self, task):
		self.clients[task][0].running = False
		del self.clients[task]