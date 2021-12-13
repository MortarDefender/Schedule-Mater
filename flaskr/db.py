import json
import click
import sqlite3
from flask import current_app, g
from flask.cli import with_appcontext
from log import get_logger


logger = get_logger()


def get_db():
    """ return the db of the site """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """ closes db """
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    """ init the db according to the schema file """
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))


@click.command('init-db')
@with_appcontext
def init_db_command():
    """ Clear the existing data and create new tables. """
    log_info = {'command': 'DB has been INIT', 'created_id': 'Nan', 'created_username': 'Nan'}
    logger.info(json.dumps(log_info))
    if g.user:
        log_info = {'warning': "{} has requested a db init".format(g.user['id']), 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))

    init_db()
    click.echo('Initialized  the database')


def init_app(app):
    """ init app - close the db and init db """
    log_info = {'info': "INIT APP"}
    logger.info(json.dumps(log_info))
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
