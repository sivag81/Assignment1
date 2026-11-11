"""Exercise the running Compose stack or Kubernetes port forwards."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(url, data=None, expected=200):
    body = json.dumps(data).encode() if data is not None else None
    req = Request(url, data=body, headers={'Content-Type':'application/json'})
    try:
        with urlopen(req, timeout=15) as response:
            status, result = response.status, json.load(response)
    except HTTPError as exc:
        status, result = exc.code, json.load(exc)
    assert status == expected, (url, status, result)
    return result


book = request('http://localhost:8001/books',
               {'title':'Distributed Systems Basics','author':'Sample Author','price':'450.00'}, 201)
assert request(f"http://localhost:8001/books/{book['id']}")['price'] == '450.00'
order = request('http://localhost:8002/orders', {'book_id':book['id'],'quantity':2}, 201)
assert order['total_price'] == '900.00', order
assert request(f"http://localhost:8002/orders/{order['id']}")['id'] == order['id']
request('http://localhost:8002/orders', {'book_id':book['id'],'quantity':0}, 422)
print(json.dumps({'book':book,'order':order}, indent=2))
print('PASS: book creation, retrieval, order collaboration, total and validation')
