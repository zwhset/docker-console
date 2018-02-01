from flask import Flask, render_template, jsonify
from flask_sockets import Sockets
import docker
from docker.errors import NotFound
import time
import configure 
from thread_send import threadSend


app = Flask(__name__)
sockets = Sockets(app)
docker_client = docker.APIClient(base_url=configure.DOCKER_HOST,
         version=configure.DOCKER_API_VERSION,timeout=configure.TIME_OUT)

@app.route('/containers')
def containers():
    return jsonify(docker_client.containers())


@app.route('/console/<container_id>')
def console(container_id):
    return render_template('index.html', container_id=container_id)

def create_exec(container_id):
   command = ["/bin/sh","-c",'TERM=xterm-256color; export TERM; [ -x /bin/bash ] && ([ -x /usr/bin/script ] && /usr/bin/script -q -c "/bin/bash" /dev/null || exec /bin/bash) || exec /bin/sh']
   create_exec_options = {
       "tty": True,
       "stdin": True,
   }
   exec_id = docker_client.exec_create(container_id, command, **create_exec_options)
   return exec_id

@sockets.route('/echo/<container_id>')
def echo_socket(ws, container_id):
    try:
        exec_id = create_exec(container_id)
        sock = docker_client.exec_start(exec_id, detach=False, tty=True, stream=False,
                       socket=True)
        sock.settimeout(600)
        send = threadSend(ws,sock)
        send.start()
        while not ws.closed:
            message = ws.receive()
            if message is not None:
                sock.send(message)
    except NotFound:
        ws.send("not fund container[%s]." % container_id)

if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()

