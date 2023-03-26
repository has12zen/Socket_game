daphne -e ssl:8443:privateKey=/home/endavour/Documents/GitLab/ChatAppForGeeksForGeeksArticle/ChatApp/certs/server.key:certKey=/home/endavour/Documents/GitLab/ChatAppForGeeksForGeeksArticle/ChatApp/certs/server.crt ChatApp.asgi:application -p 8000 -b 0.0.0.0
python3 manage.py runsslserver  --certificate ./certs/cert.pem  --key ./certs/key.pem

