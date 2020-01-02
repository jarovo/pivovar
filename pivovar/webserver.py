from pivovar import configure_app
import requests
from flask import Flask, render_template, request
from urllib.parse import urljoin


class DefaultConfig(object):
    PORT = 5000
    WASH_URL = 'http://localhost:5001/'
    INSTANCE_CONFIG_FILE = 'webserver.cfg'


app = Flask(__name__)
configure_app(app)


@app.route('/')
def wash():
    wash_url = app.config['WASH_URL']

    wm = requests.get(urljoin(wash_url, '/wash_machine')).json()
    return render_template(
        'wash.html',
        temp_log_url=urljoin(wash_url, '/temp_log'),
        wash_machine_url=urljoin(wash_url, '/wash_machine'),
        wash_machine=wm,
    )


def main():
    app.run(port=app.config['PORT'], debug=True)


if __name__ == '__main__':
    main()
