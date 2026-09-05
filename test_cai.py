import requests

url = 'http://localhost:8000/api/cai/alerts/HSCL'
try:
    res = requests.get(url, headers={'Authorization': 'Bearer test'})
    print(res.text)
except Exception as e:
    print(e)
