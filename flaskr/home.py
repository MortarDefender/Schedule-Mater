import json
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for
)
from log import get_logger
import smtplib
import ssl


bp = Blueprint('home', __name__)
logger = get_logger()


@bp.route('/')
def index():
    """ main page of the site, redirect to most other sub pages """
    return render_template('home/homepage.html', title="Schedule Master")


@bp.route('/contact', methods=('GET', 'POST'))
def contact():
    """ contact page function """
    if request.method == 'POST':
        email = request.form['email']
        subject = request.form['subject']
        error = None

        if not email:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:  # changed to sending an email using the relevant information
            # logger.info("{} has contacted the developer about '{}'".format(email, subject))
            log_info = {'info': "{} has contacted the developer about '{}'".format(email, subject)}
            logger.info(json.dumps(log_info))
            print "Email: {}\r\nSubject: {}\r\nhas contacted you, please return to him shortly".format(email, subject)
            port = 587
            smtp_server = "smtp.gmail.com"
            receiver_email = "tamiristrue@gmail.com"
            password = input("Type your password and press enter:")
            message = """\
            Subject: {}

            Email: {}\r\nhas contacted you, please return to him shortly.""".format(email, subject)
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(receiver_email, password)
                server.sendmail(receiver_email, receiver_email, message)

            return redirect(url_for('home.index'))
    return render_template('home/contact.html')


@bp.route('/about', methods=('GET', 'POST'))
def about():
    """ about page function """
    return render_template('home/about.html')
