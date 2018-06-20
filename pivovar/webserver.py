from flask import Flask, render_template

application = Flask(__name__)


class WebServer(object):
    def __init__(self):
        import threading
        self.server_thread = threading.Thread(
            target=lambda: application.run(host='0.0.0.0'))
        self.server_thread.daemon = True

    def start(self):
        self.server_thread.start()


@application.route('/')
def showMachineList():
    return render_template('list.html')
