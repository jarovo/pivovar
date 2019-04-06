from pivovar import config
from flask import Flask, render_template, send_from_directory
from urllib.parse import urljoin


class DefaultConfig(object):
    PORT = 5000
    WASH_URL = 'http://localhost:5001/'
    INSTANCE_CONFIG_FILE = 'webserver.cfg'


app = Flask(__name__)
config.configure_app(app)


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


@app.route('/')
def wash():
    wash_url = app.config['WASH_URL']
    return render_template(
        'wash.html',
        real_temps_url=urljoin(wash_url, '/real_temps'),
        wash_machine_url=urljoin(wash_url, '/wash_machine')
    )


def main():
    app.run(port=app.config['PORT'], debug=True)


if __name__ == '__main__':
    main()
