
try: import ujson as json
except: import json
from ..server import ApricotServer
from ..client import ApricotResponse

PORT = 4444

######## HTTP Route ########
# http://localhost:4444/
#############################
async def index(request):
	data_text = json.dumps({"test": True})
	return ApricotResponse(status=200, text=data_text)

######## HTTP Route ########
# http://localhost:4444/post
#############################
async def post(request):
	dict_data = request.headers

	if request.has_body:
		dict_data['form_body'] = request.body
	dict_data['url query parameters'] = request.query_dict

	dict_data = json.dumps(dict_data)
	return ApricotResponse(status=200, text=dict_data)

### Do Server ##

def start():
	# create apricot server
	server = ApricotServer(port = PORT)

	# add routing
	server.router.add_get('/', index)
	server.router.add_post('/post', post)

	# start server and wait for finish
	server.start()
	try:
		server.wait_until_stopped()
	except KeyboardInterrupt:
		pass

	# close server
	server.stop()
