#!/usr/bin/env python3
#! python3

import asyncio
from ..client import ApricotRequest
from ..client import ApricotResponse

class ApricotInvalidHttpMethod(Exception): pass

class ApricotRouter(object):
	''' Apricot Router to route http requests '''

	def __init__(self, server):
		self.server = server
		self.routes = {
			"GET":[],
			"POST":[],
			"HEAD":[]
		}

	##### Routing #####

	def add_get(self, path='/', callback=None):
		self.add_route('GET', path, callback)

	def add_post(self, path='/', callback=None):
		self.add_route('POST', path, callback)

	def add_head(self, path='/', callback=None):
		self.add_route('HEAD', path, callback)

	def add_route(self, method, path='/', callback=None):
		''' add a coroutine object to callback of route '''
		if str(method).upper() not in self.routes:
			raise ApricotInvalidHttpMethod("Method is not valid!")

		# add/override route
		entry = [path, callback]
		self.routes[str(method).upper()].append(entry)

	##### Request Processing ####

	async def default_404(self, request):
		''' do default 404 not found messages '''
		return ApricotResponse(status=404)

	async def default_200(self, request):
		''' do default 200 ok message for post '''
		return ApricotResponse(status=200)

	async def perform_task(self, func, client, request):
		''' perform an async task '''
		response = await func(request)
		client.response = response

	##### Main Request processsing #####

	async def process_request(self, client, request):
		''' route request to coroutine path '''

		# setup vars for evaluation
		path   = request.path
		if isinstance(path, bytes): path = path.decode('utf-8')
		method = request.method
		found  = False
		coro   = None

		try:
			# look for path not path + query-string
			if '?' in path: path = path.split('?')[0]

			# find coroutine to run
			if method.upper() in self.routes:
				routes = self.routes[method.upper()]
				for route in routes:
					if route[0] == path:
						found = True
						coro  = route[1]
						break
		except:
			pass

		# set default coro if coro wasn't found
		if not found:
			coro = self.default_404

		# done callback
		def on_finish(self, *args):
			client.event.set() # set client for response object

		# run task and add callback
		task_coro = lambda: self.perform_task(coro, client, request) 
		new_task  = asyncio.Task(task_coro())
		new_task.add_done_callback(on_finish)

