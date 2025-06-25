# Test on w3lib 2.3.1
from w3lib.url import canonicalize_url


url = "http://localhost:8000/sbn/"

print(canonicalize_url(url,keep_fragments=keep_fragments))
print(canonicalize_url("http://localhost:8000/sbn"))
print(canonicalize_url("http://localhost:8000/"))
print(canonicalize_url("http://localhost:8000"))