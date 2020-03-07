import os
import json

from flask import (
    Flask,
    render_template,
    flash,
    url_for,
    Blueprint,
    )
from flask_bootstrap import Bootstrap


def create_app(config_filename=None):
    app = Flask(__name__)

    load_config(app, config_filename)
    install_plugins(app)
    register_blueprints(app)
    install_error_handlers(app)

    return app


def load_config(app, config_filename=None):
    if config_filename:
        candidates = [config_filename]
    else:
        candidates = map(os.path.normpath, map(os.path.abspath, [
            './config.json',
            os.path.expanduser('~/.config/conman/config.json'),
            '/etc/conman/config.json',
        ]))
    config = None
    for filename in candidates:
        if os.path.exists(filename):
            with open(filename, 'r') as fp:
                config = json.load(fp)
            break
    if config is None:
        raise RuntimeError("No config files could be loaded! (Tried {})".format(', '.join(candidates)))

    app.config.update(config)


def install_plugins(app):
    Bootstrap(app)

    # kinda related?
    os.makedirs(os.path.join(app.config['DATA_DIRECTORY'], 'images'), exist_ok=True)

    # Also this should be moved
    from markupsafe import Markup
    def bool_label(v):
        lcls = 'default'
        ltext = 'None'
        if v is not None:
            if v:
                lcls = 'success'
                ltext = 'Yes'
            else:
                lcls = 'danger'
                ltext = 'No'
        return Markup(f'<span class="label label-{lcls}">{ltext}</span>')

    def image(v, size=None, class_=''):
        if not v:
            return
        url = url_for('index.images', path=v)
        style = ''
        if size == 'xs':
            style = 'max-width: 50px; max-height: 50px;'
        return Markup(f'<img src="{url}" class="{class_}" style="{style}" />')

    def strength_label(v):
        labels = {
            'mocktail': ('default', 'Mocktail'),
            'light': ('info', 'Light'),
            'normal': ('success', 'Normal'),
            'strong': ('warning', 'Strong'),
        }
        lcls, ltext = labels.get(v, ('danger', 'UNKNOWN'))
        return Markup(f'<span class="label label-{lcls}">{ltext}</span>')

    app.jinja_env.filters['bool_label'] = bool_label
    app.jinja_env.filters['image'] = image
    app.jinja_env.filters['strength_label'] = strength_label

def register_blueprints(app):
    from .views import (
        index as index_view,
        admin as admin_view,
    )
    app.register_blueprint(index_view.app, url_prefix=None)
    app.register_blueprint(admin_view.app, url_prefix='/admin')


def install_error_handlers(app):
    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def handle_error(error):
        flash(error.description, 'danger')
        return render_template('error.jinja.html', error=error), error.code
