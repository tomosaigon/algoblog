import base64
import datetime
import http.server
import requests
import ssl

TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
APP_ID = 1745
API = 'http://localhost:4001/v2'
LISTEN = ('0.0.0.0', 4443)
USESSL = False # Error: self signed certificate

def base64_decode(encoded_str):
    decoded_bytes = base64.b64decode(encoded_str)
    return decoded_bytes
    # decoded_str = decoded_bytes.decode("utf-8")
    # return decoded_str

def get_url_json_value(url):
    header = {
        "X-Algo-API-Token": TOKEN
    }
    response = requests.get(url, headers=header)
    if response.status_code == 200:
        data = response.json()
        # print(data)
        value = data.get("value")
        # print(base64_decode(value))
        # print(len(base64_decode(value)))
        # print(str(base64_decode(value)))
        # print(int(base64_decode(value)[0]))
        return base64_decode(value)
    else:
        raise Exception("Request failed with status code: {}".format(response.status_code))



class RequestHandler(http.server.SimpleHTTPRequestHandler):
    # twtxt client HEADs before reading, before following
    def do_HEAD(self):
        return self.do_GET()

    def do_GET(self):
        if self.path != '/twtxt.txt':
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><p>This is not the page you are looking for.</p></body></html>".encode())
            return

        lastId = get_url_json_value("{}/applications/{}/box?application-id={}&name=str:idLast".format(API, APP_ID, APP_ID))
        lastId = int(lastId[0])
        # print('lastId is ', lastId)

        id = 1
        out = b''
        while id <= lastId:
            tweet = get_url_json_value("{}/applications/{}/box?application-id={}&name=str:id:{}".format(API, APP_ID, APP_ID, id))
            tstamps = get_url_json_value("{}/applications/{}/box?application-id={}&name=str:timestamps".format(API, APP_ID, APP_ID))
            tstamp = int.from_bytes(tstamps[(id-1)*8:id*8], 'big')
            now = datetime.datetime.fromtimestamp(tstamp).strftime("%Y-%m-%dT%H:%M:%S%z")
            # now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
            print("debug: tweet#{}: {}".format(id, tweet))
            s = f"{now}\t{tweet.decode('ascii')}\n"
            # self.wfile.write(s.encode()) # gather output to calc content len
            out = out + s.encode()
            id = id + 1

        self.send_response(200)
        self.send_header("content-type", "text/plain")
        last = datetime.datetime.now()
        self.send_header("last-modified", "{}, {:02d} {} {} {:02d}:{:02d}:{:02d} GMT".format(last.strftime("%a"), last.day, last.strftime("%b"), last.year, last.hour, last.minute, last.second))
        self.send_header('content-length', str(len(out)))
        self.end_headers()
        self.wfile.write(out)

# Official twtxt client: SSL Certificate Error: The feed's (https://1.2.3.4:4443/twtxt.txt) SSL certificate is untrusted. Try using HTTP, or contact the feed's owner to report this issue.
if USESSL:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem') #, 'key.pem')

    with http.server.HTTPServer(LISTEN, RequestHandler) as httpd:
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        print(f"Serving at https://{LISTEN[0]}:{LISTEN[1]}")
        httpd.serve_forever()
else:
    httpd = http.server.HTTPServer(LISTEN, RequestHandler)
    httpd.serve_forever()
