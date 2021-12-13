import os
import json
import datetime
from flask import jsonify
from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, send_from_directory
)
from werkzeug.security import generate_password_hash
from werkzeug.exceptions import abort
from auth import login_required
from db import get_db
from log import get_logger, extract_logs, create_log_file_dir
from table import create_table, web_table, create_excel_table

bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = get_logger()

# TODO: create a schedule using algorithm and upload to the site


@bp.route('/')
@login_required
def index():
    """ admin page """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin index page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    return render_template('admin/index.html')


def create_time_shift(shift):
    """ :return a time shift table
        :var shift the amount of hours in a single shift """
    shifts = range(0, 24 + shift, shift)
    return ["{}:00 - {}:00".format(x, y) for x, y in zip(shifts, shifts[1:])]


def get_current_date():
    """ return the current date in the format Y-M-D """
    today = datetime.date.today()
    return "{}-{}-{}".format(today.year, today.month, today.day if len(str(today.day)) > 1 else "0{}".format(today.day))


def create_time_table(start_day="Sun", date=None, days_amount=7):
    """ :return a day and dates table
        :var start_day the starting day of the table
        :var date the starting date of the table
        :var days_amount the amount of days in the table """
    days = {"Sun": "Sunday", "Mon": "Monday", "Tue": "Tuesday", "Wed": "Wednesday",
            "Thu": "Thursday", "Fri": "Friday", "Sat": "Saturday"}
    if date is None:
        first_date = datetime.date.today()
        index = 1
        while datetime.date.ctime(first_date)[0:3] != start_day:
            first_date = first_date + datetime.timedelta(days=index)
    else:
        first_date = datetime.datetime.strptime(date[2:] + " 00:00:00", '%y-%m-%d %H:%M:%S')

    time = [first_date + datetime.timedelta(days=i) for i in range(0, days_amount, 1)]
    return ["{}\r\n{}.{}.{}".format(days[datetime.date.ctime(day)[0:3]], day.day, day.month, day.year) for day in time]


def split_at(arr, index=7):
    result = []
    line = []
    for i, item in enumerate(arr):
        line.append(item)
        if (i + 1) % index == 0:
            result.append(line)
            line = []
    return result


@bp.route('/schedule', methods=('POST', 'GET'))
@login_required
def schedule(date=None):
    """ schedule table page """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin schedule page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    def get_sql(start_date, end_date):
        """ return a schedule table that is between the start_date and end_date """
        schedule = get_db().execute(
            'SELECT date, shift '
            'FROM schedule WHERE p.id = ? AND date BETWEEN ? AND ?',
            (g.usser['id'], start_date.replace("\r\n", " "), end_date.replace("\r\n", " "))).fetchall()
        return schedule

    def get_start_day(start_day):
        index = 1
        date = datetime.date.today()
        while datetime.date.ctime(date)[0:3] != start_day:
            date = date + datetime.timedelta(days=index)
        return date

    db = get_db()
    schedule = db.execute(
        'SELECT s.id, shift, date, created, author_id, username'
        ' FROM schedule s JOIN user u ON s.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    for i in schedule:
        print "Date: {} - {} - {}".format(i['shift'], i['date'], i['username'])
    users = db.execute(
        'SELECT username FROM user'
    ).fetchall()

    if date is None:
        if request.method == 'POST':
            date = request.form["date"]
            print date
            if date == "None":
                date = None
        else:
            date = None

    # {"start_day" "days_amount" "shift_time" "min_block" "max_block"}
    const_variables = get_settings_variables(to_html=False)
    days_amount = const_variables["days_amount"]  # 7
    shift_time = const_variables["shift_time"]    # 4
    start_day = const_variables["start_day"]      # "Sun"
    dates = split_at(create_time_table(start_day=start_day, date=date, days_amount=days_amount))
    table = create_time_shift(shift_time)
    # sql = get_sql(dates[0], dates[-1])

    if date is None:
        date = get_start_day(start_day)

    return render_template('admin/schedule.html', schedule=schedule, days=dates, table=table, currrent_date=date,
                           range=range(0, len(table), 1), range2=range(0, 7, 1), users=users,
                           range_matrix=range(0, len(dates), 1))


def schedule_settings():
    """ schedule page with the a few extra options """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin schedule settings page without permission",
                    'created_id': g.user['id'], 'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    if request.method == 'POST':
        date = request.form['date']

        if date == "":
            return redirect(url_for("admin.schedule"))

        db = get_db()
        schedule = db.execute(
            'SELECT s.id, shift, date, created, author_id, username'
            ' FROM schedule s JOIN user u ON s.author_id = u.id'
            ' ORDER BY created DESC'
        ).fetchall()
        for i in schedule:
            print "Date: {} - {} - {}".format(i['shift'], i['date'], i['username'])
        users = db.execute(
            'SELECT username FROM user'
        ).fetchall()
        dates = create_time_table(date=date)
        table = create_time_shift(4)

        return render_template('admin/schedule.html', schedule=schedule, days=dates, table=table,
                               range=range(0, len(table), 1), range2=range(0, 7, 1), users=users)


@bp.route('/create_table', methods=('POST', 'GET'))
@login_required
def construct_table():
    """ create a pdf table using the schedule page information """
    print "table"
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin create_table page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    if request.method == 'POST':
        date = request.form['date']
        print date
        table_number = request.form['number']
        print table_number
        html = schedule(date=date)
        create_table(web_table(html, table_number=int(table_number)))
        create_excel_table(web_table(html))
        log_info = {'info': "{} has requested a table pdf for the date {}".format(
            g.user['id'], '{}/{}/{}'.format(date.split("-")[2], date.split("-")[1], date.split("-")[0])),
            'created_id': g.user['id'], 'created_username': g.user['username']}
        logger.info(json.dumps(log_info))

        info = {"db": "inside"}
        return jsonify(info)
    else:
        log_info = {'info': "{} has requested to see the latest table pdf ".format(g.user['id']),
                    'created_id': g.user['id'], 'created_username': g.user['username']}
        logger.info(json.dumps(log_info))
    return send_from_directory(os.getcwd(), filename="table.pdf")


def check(_time, _date, _username):
    """ check if the user has already taken the shift with the time and date """
    shift = get_db().execute(
        'SELECT s.id, shift, date, created, author_id, username'
        ' FROM schedule s JOIN user u ON s.author_id = u.id'
        ' WHERE shift = ? AND date = ? AND username = ?', (_time, _date, _username)
    ).fetchone()

    if shift is None:
        return None
    else:
        return 1


def check_date(date):
    """ check if the date given is after today date """
    today = datetime.date.today()
    return datetime.datetime.strptime("{}.{}.{}".format(today.day, today.month, today.year), '%d.%m.%Y') >= \
           datetime.datetime.strptime(date.split(" ")[1], '%d.%m.%Y')


@bp.route('/schedule/add', methods=('POST',))
@login_required
def schedule_add():
    """ add a shift into the schedule table """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access schedule_add page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    if request.method == 'POST':
        shift = request.form['shift']
        date = request.form['date'].replace("\r\n", " ")
        username = request.form['username']
        user = get_user(username=username)
        print "Id: {} || Username: {} -> date: {} || shift: {}".format(user['id'], user['username'],
                                                                       date, shift)
        if check_date(date):
            # TODO: add a warning to the user and admin of the backdate
            print "################ admin backdate ################"
            log_info = {'info': "tried to backtrack a shift", 'created_id': g.user['id'],
                        'created_username': g.user['username'],
                        'variable': 'date: {} || shift: {} || username: {}'.format(date, shift, username)}
            logger.warning(json.dumps(log_info))
        elif check(shift, date, username) is None:
            log_info = {'command': "INSERT INTO schedule", 'created_id': g.user['id'],
                        'created_username': g.user['username'],
                        'variable': 'date: {} || shift: {} || user id: {}'.format(date, shift, g.user['id'])}
            logger.info(json.dumps(log_info))
            db = get_db()
            db.execute(
                'INSERT INTO schedule (date, shift, author_id) '
                'VALUES (?, ?, ?)', (date, shift, user['id'])
            )
            db.commit()

        return redirect(url_for("admin.schedule"))

    log_info = {'warning': "tried to access schedule_add using GET", 'created_id': g.user['id'],
                'created_username': g.user['username']}
    logger.warning(json.dumps(log_info))
    return abort(403, "access denied")


@bp.route('/schedule/del', methods=('POST',))
@login_required
def schedule_del():
    """ delete a shift from the schedule table """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin schedule_del index page without permission",
                    'created_id': g.user['id'], 'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    if request.method == 'POST':
        time = request.form['shift']
        date = request.form['date']
        username = request.form['username']
        user = get_user(username=username)

        print "remove: {} - {} - {}".format(time, date, username)

        if check_date(date):
            print "################ admin backdate ################"
            log_info = {'info': "tried to remove a shift before today", 'created_id': g.user['id'],
                        'created_username': g.user['username'],
                        'variable': 'date: {} || shift: {} || username: {}'.format(date, time, username)}
            logger.warning(json.dumps(log_info))
        if check(time, date, username) is not None:
            log_info = {'command': 'DELETE FROM schedule', 'created_id': g.user['id'],
                        'created_username': g.user['username'],
                        'variable': 'date: {} || shift: {} || user id: {}'.format(date, time, g.user['id'])}
            logger.info(json.dumps(log_info))
            db = get_db()
            db.execute('DELETE FROM schedule WHERE author_id = ? AND shift = ? AND date = ?', (user['id'], time, date))
            db.commit()

        return redirect(url_for("admin.schedule"))

    log_info = {'warning': "tried to access admin schedule_del using GET", 'created_id': g.user['id'],
                'created_username': g.user['username']}
    logger.warning(json.dumps(log_info))
    return abort(403, "access denied")


@bp.route('/users')
@login_required
def users():
    """ users preferences page """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin users index page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    users = get_db().execute('SELECT u.id, username, rank FROM user u').fetchall()
    return render_template('admin/users.html', users=users)


def get_user(id=None, username=None):
    """ get user information using id or username """
    if id is not None and username is None:
        user = get_db().execute(
            'SELECT u.id, password, username, rank FROM user u WHERE u.id = ?', (id,)
        ).fetchone()
    elif username is not None and id is None:
        user = get_db().execute(
            'SELECT u.id, password, username, rank FROM user u WHERE username = ?', (username,)
        ).fetchone()
    else:
        abort(404, "User id {0} doesn't exist.".format(id))
        return None
    print "User: {} || Id: {} || Rank: {}".format(user['username'], user['id'], user['rank'])
    if user is None:
        abort(404, "User id {0} doesn't exist.".format(id))

    return user


@bp.route('/<int:id>/update', methods=('POST', ))
@login_required
def update(id):
    """ update a current user """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin %d/update index page without permission" % id,
                    'created_id': g.user['id'], 'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    user = get_user(id=id)

    if user['id'] == g.user['id']:
        return redirect(url_for("admin.users"))

    if g.user['rank'] != 0 and user['rank'] == 0:
        return redirect(url_for("admin.users"))

    db = get_db()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        rpt_password = request.form['rpt_password']
        rank = request.form['rank']
        # rank = 1 if request.form['rank'] == "admin" else 2
        error = None

        if not username:
            error = 'Username is required.'
        elif not password and not rpt_password and password != rpt_password:
            error = "The Passwords doesn't match"
        else:
            u = db.execute('SELECT id FROM user WHERE username = ?', (username,)).fetchall()
            if u is not None and len(u) > 1:
                error = 'User {} is already registered.'.format(username)

        if error is not None:
            flash(error)
            print error
        else:
            db = get_db()
            if not password:
                password = user['password']
            else:
                password = generate_password_hash(password)

            if rank == "admin":
                rank = 1
            else:
                rank = 2
            log_info = {'command': 'UPDATE user', 'created_id': g.user['id'], 'created_username': g.user['username'],
                        'variable': 'user_id: {} || username: {} || password: {} || rank: {}'.format(
                            id, username, password, rank)}
            logger.info(json.dumps(log_info))
            db.execute(
                'UPDATE user SET username = ?, password = ?, rank = ? WHERE id = ?',
                (username, password, rank, id)
            )
            db.commit()
            return redirect(url_for('admin.users'))

    return render_template('admin/update.html', user=user)  # no longer in user


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    """ create a new user """
    if g.user['rank'] != 0:
        log_info = {'warning': "tried to access admin create users page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        rpt_password = request.form['rpt_password']
        rank = request.form['rank']
        # rank = 1 if request.form['rank'] == "admin" else 2
        db = get_db()
        error = None

        print "User: {} || Rank: {}".format(username, rank)

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif db.execute('SELECT id FROM user WHERE username = ?', (username,)).fetchone() is not None:
            error = 'User {} is already registered.'.format(username)
        elif password != rpt_password:
            error = "The Passwords doesn't match"
        if error is not None:
            flash(error)
        else:
            if rank == "admin":
                rank = 1
            else:
                rank = 2
            log_info = {'command': 'INSERT INTO user', 'created_id': g.user['id'],
                        'created_username': g.user['username'],
                        'variable': 'username: {} || password: {} || rank: {}'.format(
                            username, generate_password_hash(password), rank)}
            logger.info(json.dumps(log_info))
            db.execute(
                'INSERT INTO user (username, password, rank) '
                'VALUES (?, ?, ?)', (username, generate_password_hash(password), rank)
            )
            db.commit()
            print "{} has been added".format(username)
            users = db.execute('SELECT u.id, username, password, rank From user u').fetchall()
            for user in users:
                print "Id: {} User: {} || Rank: {}".format(user['id'], user['username'], user['rank'])

            return redirect(url_for('admin.users'))

    return render_template('admin/create.html')


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    """ delete a user using id """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin %d/delete page without permission" % id,
                    'created_id': g.user['id'], 'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    user = get_user(id=id)

    if g.user['rank'] != 0 and user['rank'] != 2:
        return abort(403, "forbidden action cannot remove an admin")

    log_info = {'command': 'DELETE FROM user', 'created_id': g.user['id'], 'created_username': g.user['username'],
                'variable': 'user_id: {} || username: {} || password: {} || rank: {}'.format(
                    id, user['username'], user['password'], user['rank'])}
    logger.info(json.dumps(log_info))
    db = get_db()
    db.execute('DELETE FROM user WHERE id = ?', (id,))
    db.commit()

    return redirect(url_for('admin.users'))


def get_settings_variables(min=0, max=4, to_html=True):
    """ get all the variables from the settings file
        :param min: minimum amount of shift that can be blocked by the user
        :param max: maximum amount of shift that can be blocked by the user
        :param to_html: if True than will return a list False return a dictionary"""
    if not os.path.isfile('settings.txt'):
        return ["", "7", "8", str(min), str(max)]
    with open("settings.txt", "r") as f:
        read = f.read()
    f.close()
    result = read.split("\n")
    if to_html:
        return result
    else:
        return {"start_day": result[0], "days_amount": int(result[1]), "shift_time": int(result[2]),
                "min_block": int(result[3]), "max_block": int(result[4])}


@bp.route('/settings', methods=('GET', 'POST'))
@login_required
def settings():
    """ settings page """
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin settings page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    def set_variables(start_day, days_amount, shift_time, min_block, max_block):
        """ insert the variables given to the settings file """
        log_info = {'command': 'Update Settings', 'created_id': g.user['id'], 'created_username': g.user['username'],
                    'variable': 'start_day: {} || days_amount: {} || shift_time: {} || '
                                'min_block: {} || max_block: {}'.format(start_day, days_amount, shift_time, min_block,
                                                                        max_block)}
        logger.info(json.dumps(log_info))
        with open("settings.txt", "w") as f:
            f.write("{}\n{}\n{}\n{}\n{}".format(start_day, days_amount, shift_time, min_block, max_block))
        f.close()

    minimum_shift_block = 0
    maximum_shift_block = 4

    if request.method == 'POST':
        start_day = request.form['start_day']
        days_amount = request.form['days_amount']
        shift_time = request.form['shift_time']
        min_block = request.form['min_block']
        max_block = request.form['max_block']
        set_variables(start_day, days_amount, shift_time, min_block, max_block)

    variables = get_settings_variables(minimum_shift_block, maximum_shift_block)

    return render_template('admin/settings.html', min_shift_block=minimum_shift_block,
                           max_shift_block=maximum_shift_block, variables=variables)


@bp.route('/log', methods=('POST', 'GET'))
@login_required
def log():
    """ log file page """
    if g.user['rank'] != 0:
        log_info = {'warning': "tried to access admin log_file page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")

    options = {
        "shift created": "INSERT INTO schedule",
        "shift removed": "DELETE FROM schedule",
        "user created": "INSERT INTO user",
        "user deleted": "DELETE FROM user",
        "user updated": "UPDATE user",
        "logout": "Logout",
        "login": "Login",
        "errors": "error",
        "security threats": "security"
    }

    if request.method == 'POST':
        create_log_file_dir(action="sections")
        create_log_file_dir(action="dates")

        start_date = request.form['start_date']
        end_date = request.form['end_date']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        command = request.form['command']
        username = request.form['username']
        # user_id = request.form['user_id']
        commands = {}

        if start_date != "":
            commands['start_date'] = start_date
        if end_date != "" and start_date != "" and start_date < end_date:
            commands['end_date'] = end_date
        else:
            if start_date != "":
                commands['end_date'] = start_date

        if start_time != "":
            commands['start_time'] = start_time + ":00"
        if end_time != "" and start_time != "":
            commands['end_time'] = "23:59:59" if start_time > end_time else end_time + ":00"
        else:
            if start_time != "":
                commands['end_time'] = "23:59:59"

        if command != "":
            if command in options.keys():
                commands['command'] = options[command]
            else:
                print "command '{}' isn't in options".format(command)
        if username != "":
            commands['created_username'] = username

        # if user_id != "": commands['created_id'] = user_id
    else:
        commands = {"date": get_current_date()}
    if len(commands) != 0:
        db = extract_logs(commands=json.dumps(commands))
    else:
        return redirect(url_for("admin.log"))
    log = []
    # fix headers variables  to change dynamically according to parameters
    headers = ["#", "level", "date", "time", "variables"]
    index = range(1, len(db) + 1, 1)
    users = get_db().execute(
        'SELECT u.id, username FROM user u'
    ).fetchall()

    for item in db:
        variables = ""
        for key in item.keys():
            if key not in headers and key != "type":
                variables += "{}: {}  ".format(key, item[key])

        line = [item['level'], item['date'], item['time'].split(",")[0], variables]
        log.append(line)

    return render_template("admin/log.html", head=headers, index=index, log=log, users=users, options=options.keys())


@bp.route('/menu')
@login_required
def menu():
    if g.user['rank'] == 2:
        log_info = {'warning': "tried to access admin menu page without permission", 'created_id': g.user['id'],
                    'created_username': g.user['username']}
        logger.warning(json.dumps(log_info))
        return abort(404, "page doesn't exist")
    return render_template("admin/menu.html")
