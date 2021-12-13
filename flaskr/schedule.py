import json
from flask import jsonify
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from auth import login_required
from admin import create_time_shift, create_time_table, check_date, get_settings_variables, split_at
from db import get_db
from log import get_logger

bp = Blueprint('schedule', __name__, url_prefix='/schedule')
logger = get_logger()


@bp.route('/')
@login_required
def index():
    """ show the schedule table of the current week """
    def get_sql(start_date, end_date):
        """ return a schedule table that is between the start_date and end_date """
        schedule = get_db().execute(
            'SELECT date, shift '
            'FROM schedule '
            'WHERE p.id = ? AND date BETWEEN ? AND ?', (g.usser['id'], start_date, end_date)
        ).fetchall()
        return schedule

    db = get_db()
    schedule = db.execute(
        'SELECT s.id, shift, date, created, author_id, username'
        ' FROM schedule s JOIN user u ON s.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    for i in schedule:
        print "Date: {} - {} - {}".format(i['shift'], i['date'], i['username'])

    const_variables = get_settings_variables(to_html=False)
    days_amount = const_variables["days_amount"]  # 7
    shift_time = const_variables["shift_time"]    # 4
    start_day = const_variables["start_day"]      # "Sun"
    dates = split_at(create_time_table(start_day=start_day, days_amount=days_amount))
    table = create_time_shift(shift_time)
    # sql = get_sql(dates[0], dates[-1])
    return render_template('schedule/index2.html', schedule=schedule, days=dates, table=table,
                           range=range(0, len(table), 1), range2=range(0, 7, 1), range_matrix=range(0, len(dates), 1))


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            logger.info("INSERT INTO schedule. by: {} -> {} - {} - {}".format(g.user['id'], title, body, g.user['id']))
            db = get_db()
            db.execute(
                'INSERT INTO schedule (title, body, author_id) '
                'VALUES (?, ?, ?)', (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('schedule.index'))

    return render_template('schedule/create.html')


def get_post(id, check_author=True):
    schedule = get_db().execute(
        'SELECT p.id, body, created, author_id, username '
        'FROM schedule p JOIN user u ON p.author_id = u.id '
        'WHERE p.id = ?', (id,)
    ).fetchone()

    if schedule is None:
        abort(404, "Schedule id {0} doesn't exist.".format(id))

    if check_author and schedule['author_id'] != g.user['id']:
        abort(403)

    return schedule


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    schedule = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            logger.info("UPDATE schedule SET. by: {} -> {} - {} - {}".format(g.user['id'], title, body, id))
            db = get_db()
            db.execute(
                'UPDATE schedule SET title = ?, body = ? WHERE id = ?', (title, body, id)
            )
            db.commit()
            return redirect(url_for('schedule.index'))

    return render_template('schedule/update.html', schedule=schedule)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    logger.info("'DELETE FROM  schedule. by: {} -> {}".format(g.user['id'], id))
    db = get_db()
    db.execute('DELETE FROM schedule WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('schedule.index'))


@bp.route('/create_shift', methods=('POST',))
@login_required
def create_shift():
    """ creates and deletes shifts according to the time and date """
    def check(_time, _date):
        """ check if the user has already taken the shift with the time and date """
        shift = get_db().execute(
            'SELECT s.id, date, shift, created, author_id, username '
            'FROM schedule s JOIN user u ON s.author_id = u.id '
            'WHERE shift = ? AND date = ? AND s.author_id = ?', (_time, _date, g.user['id'])
        ).fetchone()

        if shift is None:
            return None
        else:
            return 1

    if request.method == 'POST':
        time = request.form['shift']
        date = request.form['date']
        action = request.form['action']
        # print "{} -- {} -- {}".format(time, date, action)

        if action == "handle":
            if check_date(date):
                print "################ user backdate ################"
                log_info = {'info': "tried to backtrack a shift", 'created_id': g.user['id'],
                            'created_username': g.user['username'],
                            'variable': 'date: {} || shift: {} || username: {}'.format(date, time, g.user['username'])}
                logger.warning(json.dumps(log_info))
                info = {"db": "backdate"}
                return jsonify(info)
            elif check(time, date) is None:  # there is no shift with the time and date under that user
                print "added"
                log_info = {'command': 'INSERT INTO schedule', 'created_id': g.user['id'],
                            'created_username': g.user['username'],
                            'variable': 'date: {} || shift: {} || user id: {}'.format(date, time, g.user['id'])}
                logger.info(json.dumps(log_info))
                db = get_db()
                db.execute(
                    'INSERT INTO schedule (date, shift, author_id) VALUES (?, ?, ?)', (date, time, g.user['id']))
                db.commit()
            else:                          # there is a shift with the time and date
                print "removed"
                log_info = {'command': 'DELETE FROM schedule', 'created_id': g.user['id'],
                            'created_username': g.user['username'],
                            'variable': 'date: {} || shift: {} || user id: {}'.format(date, time, g.user['id'])}
                logger.info(json.dumps(log_info))
                db = get_db()
                db.execute(
                    'DELETE FROM schedule WHERE author_id = ? AND shift = ? AND date = ?',
                    (g.user['id'], time, date))
                db.commit()

        elif action == "check":
            if check(time, date) is None:
                info = {"db": "None"}
                return jsonify(info)
            else:
                info = {"db": "not None"}
                return jsonify(info)

    log_info = {"warning": "tried to access create_shift using GET", 'created_id': g.user['id'],
                'created_username': g.user['username']}
    logger.warning(json.dumps(log_info))
    info = {"db": "inside"}
    return jsonify(info)
