import socket
import requests

# Force IPv4
orig_getaddrinfo = socket.getaddrinfo

def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = ipv4_only

r = requests.get("https://data-api.polymarket.com/trades?limit=1", timeout=10)
print(r.status_code)
print(r.text)
