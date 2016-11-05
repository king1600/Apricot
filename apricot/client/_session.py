#!/usr/bin/env python3
#! python3

import ssl
import certifi
import asyncio
from datetime import datetime, timedelta
from ._request import ApricotRequest
from ._protocol import ApricotProtocol
from ._response import ApricotHttpResponse
from ..utils import ApricotUrl, BREAK, REQUEST_HEADERS
from ..utils import generateID_async, json, urlencode
from ..utils import createParams

class ApricotSession(object):
	''' Apricot Request Session '''

	def __init__(self, loop=None):
		self.loop = loop if loop != None else asyncio.get_event_loop()
		self.connections = {} # categorize all ApricotProtocols by uuid
		self.conn_ready  = {} # hold Events to check protocol ready by uuid
		self.isClosed    = False

		# SSL Authentication
		self.ca_path = certifi.where()
		self.ca_auth = ssl.Purpose.CLIENT_AUTH

		# cookie handling
		self.cookies = {}

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

	async def cookie_handle(self, response):
		""" Add cookies to session """
		headers = response.headers

		for head in headers:
			# set cookie
			if str(head).lower().startswith('set-cookie'):
				# extract parts
				cookie       = headers[head]
				cookie_info  = {}
				parts        = cookie.split(";")
				cookie_key   = ''
				cookie_value = None

				# assign info, key, and value
				for pos, part in enumerate(parts):
					if part.startswith(' '): part = part[1:]
					key   = part.split("=")[0]
					value = '='.join(part.split("=")[1:])
					if pos != 0:
						cookie_info[key] = value
					else:
						cookie_key   = key
						cookie_value = value

				# handle parts
				for part in cookie_info:
					cookie_h  = str(part).lower()
					new_value = None

					# convert expire date & python datetime convert
					if cookie_h == "expires":
						date   = cookie_info[part]
						date_p = date.split()
						if '-' in date_p[1]:
							date_parts = date_p[1].split('-')
							if len(date_parts[-1]) <= 2:
								pref = str(datetime.now().year)[:2]
								date_parts[-1] = pref + date_parts[-1]
							date_rest = date_p[2:]
							date_final = [date_p[0]] + date_parts + date_rest
							date = ' '.join(date_final)
						new_value = datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %Z")

					# convert max age date
					elif cookie_h == "max-age":
						seconds   = int(cookie_info[part])
						new_value = datetime.now() + timedelta(seconds=seconds)

					# no other real conversion needed
					else:
						pass

					# set converted python value if necessary
					if new_value is not None:
						cookie_info[part] = new_value

				# create cookie entry for session
				host = response.host
				if host not in self.cookies:
					self.cookies[host] = {}
				info = {}
				info['value'] = cookie_value
				for part in cookie_info:
					if part != 'value':
						info[part] = cookie_info[part]
				if 'Path' not in info: info['Path'] = "/"

				# add to session coookies
				self.cookies[host][cookie_key] = info

	async def set_cookies(self, respData):
		""" Add cookies to response data from session """

		# get info
		request = ApricotRequest((respData + BREAK).encode())
		await request.build_async()
		host = str(request.host)
		path = request.path
		path = str(path) if path is not None else "/"
		if isinstance(path, bytes): path = path.decode()
		path = path.split("?")[0]

		# add cookies
		if host in self.cookies:
			info = self.cookies[host]
			
			# remove expired cookies
			for key in info:
				data   = info[key]
				remove = False
				if 'Expires' in data:
					if data['Expires'] < datetime.now():
						remove = True
				if 'Max-Age' in data:
					if data['Max-Age'] < datetime.now():
						remove = True
				if remove:
					info.pop(key, None)

			# add cookies to response data
			cookie_str = None
			for cookie in info:
				# only add if valid path
				cookie_path = info[cookie]['Path']
				value       = info[cookie]['value']
				if path == cookie_path or cookie_path == "/":
					if cookie_str == None:
						cookie_str = "Cookie:"
					cookie_str += " " + cookie + "=" + value + ";"
			if cookie_str is not None:
				if cookie_str.endswith(';'):
					cookie_str = cookie_str[:-1]
				cookie_str += BREAK
				respData += cookie_str

		# return new response data if changes
		return respData
						

	async def buildHttpRequest(self, url, method, params, headers, data, _json):
		''' Build HTTP Request byte string from info '''
		# add url parameters
		param_str = createParams(params)
		if '?' in url:
			param_str = param_str[1:]
			if param_str == '?': param_str = ''
			url += '&'
		if param_str == '?': param_str = ''
		url += param_str

		# get url object
		aUrl = ApricotUrl(url)

		# build response
		fullpath = aUrl.path
		if '?' in url: fullpath += "?" + '?'.join(url.split('?')[1:])
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
		if DATA != b'':
			_headers['Content-Length'] = str(len(DATA))


		# build byte string
		for header in _headers:
			respData += header + ": " + _headers[header] + BREAK
		try:
			newData = await self.set_cookies(respData)
			respData = newData
		except Exception as e:
			pass
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

		# save cookies
		await self.cookie_handle(response)

		# handle redirects
		if redirect:
			if str(response.status)[0] == '3':
				new_url = response.headers["Location"]
				if new_url.startswith('/'):
					main    = url.split('://')[1].split("/")[0]
					schema  = url.split('://')[0] + "://"
					new_url = schema + main + new_url
				if 'Referer' not in headers:
					headers["Referer"] = new_url
				response = await self.get(new_url, params, headers)

		# return http response
		return response