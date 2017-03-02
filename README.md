## Usage

### Server
```python
import json
from apricot.server import ApricotServer
from apricot.client import ApricotResponse

async def index(req):
  return ApricotResponse(status=200, text="Hello world")

async def post(req):
  data = req.headers
  if req.has_body:
    data['X-Form-Data'] = req.body
  data['X-Url-Params'] = json.dumps(req.query_dict)
  return ApricotResponse(status=200, text=json.dumps(data))

if __name__ == "__main__":
  server = ApricotServer(port=8080)
  
  server.router.add_get('/', index)
  server.router.add_post('/post', post)
  
  try:
    server.wait_until_stopped()
  except KeyboardInterrupt:
    pass
  except Exception as err:
    print("Error:", str(err))
  server.stop()
```

### Client

```python
from apricot.client import ApricotSession

...

async with ApricotSession() as sess:
  resp = await sess.get("https://google.com/humans.txt")
  print(resp.status)
  print(await resp.text())
```
