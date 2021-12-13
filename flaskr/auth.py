import json
import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from db import get_db
from log import get_logger

bp = Blueprint('auth', __name__, url_prefix='/auth')
logger = get_logger()


@bp.route('/register', methods=('GET', 'POST'))
def register():
    """ register page function create the initial page and handle the register request """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        rpt_password = request.form['rpt-password']
        rank = 2          # su = 0 || admin = 1 || user = 2
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.execute('SELECT id FROM user WHERE username = ?', (username,)).fetchone() is not None:
            error = 'User {} is already registered.'.format(username)
        elif password != rpt_password:
            error = "The Passwords doesn't match"

        if error is None:
            message = {'command': 'INSERT INTO user', 'created_id': 'Nan', 'created_username': 'Nan',
                       'variable': 'username: {} || password: {} || rank: {}'.format(
                           username, generate_password_hash(password), rank)}
            logger.info(json.dumps(message))
            db.execute(
                'INSERT INTO user (username, password, rank) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), rank))
            db.commit()
            return redirect(url_for('auth.login'))

        flash(error)

    # return render_template('auth/register.html', title="Register")
    return render_template('auth/login.html', title="Register")


@bp.route('/login', methods=('GET', 'POST'))
def login():
    """ login page function, create the initial page and handle the login request """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        # print "{} - {} - {}".format(user['username'], user['id'], user['rank'])
        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            message = {'command': 'Login', 'created_id': user['id'],  'created_username': user['username']}
            logger.info(json.dumps(message))
            return redirect(url_for('index'))

        print "error: {}".format(error)
        flash(error)

    return render_template('auth/login.html', title="Log In")


@bp.before_app_request
def load_logged_in_user():
    """ load the already logged in user into the site """
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()


@bp.route('/logout')
def logout():
    """ logout function """
    message = {'command': 'Logout', 'created_id': g.user['id'],  'created_username': g.user['username']}
    logger.info(json.dumps(message))
    session.clear()
    return redirect(url_for('index'))


def login_required(view):
    """ checks if the user is logged in otherwise redirects to the login function """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
