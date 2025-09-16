import sys, urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5) as r:
        data = r.read(200)
        print('HTTP', r.status)
        print(data.decode('utf-8','ignore'))
except Exception as e:
    print('ERR', e)
