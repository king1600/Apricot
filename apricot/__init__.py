import asyncio

# uv loop implementation
try:
	import uvloop
	asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
	loop = uvloop.new_event_loop()
	asyncio.set_event_loop(loop)
except:
	pass

__version__ = "1.3.5"
__author__  = "Protto"