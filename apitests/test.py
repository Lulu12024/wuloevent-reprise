import requests
from django.utils.encoding import force_str

with requests.get('http://localhost:1337/v1/transactions/nsA46zinTbFy5tD/stream-status/', stream=True) as r:
    x = [force_str(line) for line in r.iter_lines() if len(line) > 5]
    print(list(x))