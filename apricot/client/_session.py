#!/usr/bin/env python3
#! python3

import ssl
import certifi
import asyncio
from ._request import ApricotRequest
from ._protocol import ApricotProtocol
from ._response import ApricotHttpResponse
from ..utils import ApricotUrl, BREAK, REQUEST_HEADERS
from ..utils import generateID_async, json, urlencode

class ApricotSession(object):
	''' Apricot Request Session '''

	def __init__(self, loop=None):
		self.loop = loop if loop != None else asyncio.get_event_loop()
		self.connections = {} # categorize all ApricotProtocols by uuid
		self.conn_ready  = {} # hold Events to check protocol ready by uuid
		self.isClosed    = False

		self.ca_path = certifi.where()
		self.ca_auth = ssl.Purpose.CLIENT_AUTH

	def __del__(self):
		self.close()

	def close(self):
		''' close all clients '''
		if self.isClosed: return
		try:
			for uuid in self.connections:
				try:
					protocol = self.connections.pop(uuid, None)
					protocol.transport.close()
				except:
					pass
		except:
			pass
		self.isClosed = True

	### Asynchronous with statements ###

	async def __aenter__(self):
		return self

	async def __aexit__(self, type, value, traceback):
		self.close()

	### HTTP Requests ###

	async def get(self, url, params={}, headers={}, data=None, allow_redirects=True):
		return await self.do_request(
			url, "GET", params, headers, data, None, allow_redirects)

	async def post(self, url, params={}, headers={}, data=None, json=None):
		return await self.do_request(
			url, "POST", params, headers, data, json, False)

	async def head(self, url, params={}, headers={}):
		return await self.do_request(
			url, "HEAD", params, headers, None, None, False)

	### Backend Http Methods  ####

	async def buildHttpRequest(self, url, method, params, headers, data, _json):
		''' Build HTTP Request byte string from info '''
		# add url parameters
		if '?' in url:
			extra_params = '?'.join(url.split('?')[1:])
			url = url.split('?')[0]
			for part in extra_params.split('&'):
				if part != '' or not part.isspace():
					key = part.split('=')[0]
					value = '='.join(part.split('=')[1:])
					params[key] = value
		_params = "?" + urlencode(params)
		'''
		for key in params:
			value = params[key]
			key = quote(key)
			value = quote(value)
			if _params == '?': add = key + "=" + value
			else: add = '&' + key + "=" + value
			_params += add
		'''
		params = _params
		if params != '?': url += params

		# get url object
		aUrl = ApricotUrl(url)

		# build response
		fullpath = aUrl.path
		if params != '?': fullpath += params
		respData = method.upper() + ' ' + fullpath + ' HTTP/1.1' + BREAK

		# get headers
		_headers = REQUEST_HEADERS.copy()
		if aUrl.host is not None:
			port = '' if aUrl.port == 80 else str(aUrl.port)
			dns  = aUrl.host + ":" + port if port != '' else aUrl.host
			_headers["Host"] = dns
		for h in headers:
			_headers[h] = headers[h]

		# get data
		hasData = False
		DATA    = b''
		if data is not None:
			hasData = True
			if not isinstance(data, bytes): data = str(data).encode('utf-8')
			DATA = data
		if not hasData and _json is not None:
			data = json.dumps(_json)
			DATA = data.encode()

		# build byte string
		for header in _headers:
			respData += header + ": " + _headers[header] + BREAK
		respData += BREAK
		respData = respData.encode('utf-8')
		respData += DATA

		return respData, aUrl

	async def do_request(self, url, method, params, headers, data, _json, redirect):
		''' perform the basis http request '''

		# get byte data and ApricotUrl object
		respData, aUrl = await self.buildHttpRequest(
			url, method, params, headers, data, _json)

		# client info
		client_id   = await generateID_async()
		self.conn_ready[client_id] = asyncio.Event()
		client_coro = lambda: ApricotProtocol(self.loop, self, respData, client_id)

		# create connection
		if aUrl.schema == 'https':
			ctx  = ssl.create_default_context(self.ca_auth, capath=self.ca_path)
		else:
			ctx  = None
		coro = self.loop.create_connection(client_coro, aUrl.host, aUrl.port, ssl=ctx)
		task = self.loop.create_task(coro)

		# wait for protocol to be initialized
		await self.conn_ready[client_id].wait()

		# wait for data to be received
		protocol = self.connections[client_id]
		await protocol.isReady.wait()
		http_data = protocol.data

		# build http response
		response = ApricotHttpResponse(http_data, aUrl)
		await response.feed_async()

		# handle redirects
		if redirect:
			if str(response.status)[0] == '3':
				new_url = response.headers["Location"]
				headers["Referer"] = new_url
				response = await self.get(new_url, params, headers)

		# return http response
		return response