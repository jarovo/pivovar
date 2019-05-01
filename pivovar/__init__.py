import os


def configure_app(app):
    config_name = os.getenv('FLASK_CONFIGURATION', 'DefaultConfig')
    # object-based default configuratiok
    app.config.from_object('{}.{}'.format(app.name, config_name))
    # instance-folders configuration
    app.config.from_pyfile(app.config['INSTANCE_CONFIG_FILE'], silent=True)


class PivovarError(Exception):
    pass
