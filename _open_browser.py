import time, webbrowser, urllib.request

while True:
    try:
        urllib.request.urlopen("http://127.0.0.1:1616")
        webbrowser.open("http://127.0.0.1:1616")
        break
    except Exception:
        time.sleep(1)
