from pivovar import configure_app
import requests
from flask import Flask, render_template, request
from flask_babel import Babel
from urllib.parse import urljoin


class DefaultConfig(object):
    PORT = 5000
    WASH_URL = 'http://localhost:5001/'
    INSTANCE_CONFIG_FILE = 'webserver.cfg'
    BABEL_TRANSLATION_DIRECTORIES = 'translations'


app = Flask(__name__)
configure_app(app)
babel = Babel(app)


@babel.localeselector
def get_locale():
    # Try to guess the language from the user accept
    # header the browser transmits.  We support en/cs in this
    # example.  The best match wins.
    loc = request.accept_languages.best_match(['cs', 'en'])
    return loc


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
