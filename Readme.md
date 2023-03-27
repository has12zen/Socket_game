```
brew install mkcert
mkcert -install
mkcert -cert-file ./certs/server.crt -key-file ./certs/server.key localhost 127.0.0.1
openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj "/CN=localhost/C=US/L=San Fransisco" -keyout server.key -out server.crt

```

```
export DJANGO_SETTINGS_MODULE=ChatApp.settings
```