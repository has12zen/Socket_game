# Socket Spades

Socket Spades is a spades game with bidding, implemented with Django Channels.

## Installation

### Step 1: Generate certificates
If you are planning to use the certs included with repo you can skip it.
Before you can run Socket Spades, you need to set up SSL certificates. You can do this using `mkcert`, a tool that generates and manages SSL certificates. 

To install `mkcert` using Homebrew, run the following command:

```bash
brew install mkcert
```

Once `mkcert` is installed, you can create the SSL certificates for localhost and 127.0.0.1 by running:

```bash
mkcert -install
mkcert -cert-file ./certs/server.crt -key-file ./certs/server.key localhost 127.0.0.1
```

You can also generate a self-signed SSL certificate using OpenSSL by running:

```bash
openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj "/CN=localhost/C=US/L=San Fransisco" -keyout server.key -out server.crt
```
### Step 2: Install dependencies and run server
Create a virtual environment and activate it by running:

```bash
python3 -m venv venv-name
source venv-name/bin/activate
```
Next, install all required dependencies by running:

```bash
pip install -r requirements.txt
```

Run the following commands to create database tables:

```bash
export DJANGO_SETTINGS_MODULE=ChatApp.settings
python3 manage.py makemigrations chat    
python3 manage.py migrate
```

Finally, run the server using:

```bash
./run.sh
```
