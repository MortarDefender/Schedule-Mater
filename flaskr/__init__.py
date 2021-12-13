import os
import json
from flask import Flask, render_template, send_from_directory, g
from log import get_logger

__author__ = 'Tamir'


logger = get_logger()


def create_app(test_config=None):
    """ create and configure the app """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    @app.route('/favicon.ico')
    def favicon():
        """ a favicon logo redirection """
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'lst.ico', mimetype='image/vnd.microsoft.icon')

    @app.errorhandler(404)
    def page_not_found(e):
        """ custom 404 error page """
        if g.user:
            log_info = {'warning': "{} get a 404 page".format(g.user['id']), 'error': "{}".format(e)}
            logger.warning(json.dumps(log_info))
        return render_template('error/404_error2.html'), 404

    @app.errorhandler(403)
    def page_not_found(e):
        """ custom 403 error page """
        if g.user:
            log_info = {'warning': "{} get a 403 page".format(g.user['id']), 'error': "{}".format(e)}
            logger.warning(json.dumps(log_info))
        return render_template('error/403_error.html'), 403

    from . import db
    db.init_app(app)

    from . import log
    app.cli.add_command(log.init_log_command)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import schedule
    app.register_blueprint(schedule.bp)

    from . import admin
    app.register_blueprint(admin.bp)

    from . import home
    app.register_blueprint(home.bp)
    app.add_url_rule('/', endpoint='index')

    return app
