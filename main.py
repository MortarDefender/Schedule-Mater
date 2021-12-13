import time
import click
import requests
import sqlite3
from flask import current_app, g
from flask.cli import with_appcontext
from flask import Flask
from flask import request
from flask import render_template

__author__ = 'Tamir'

app = Flask(__name__)
app.config['SECRET_KEY'] = "6484284f4f1e617dd6e0d83d2c32a6a4b593f5ad10637792"


@app.route("/", methods=['GET', 'POST'])
@app.route("/home", methods=['GET', 'POST'])
def app_main():
    """ the home screen of the web page """
    return render_template('main.html')


@app.errorhandler(404)
def page_not_found(e):
    """ custom 404 error page """
    return render_template('404_error.html'), 404


@app.errorhandler(403)
def forbidden_page(e):
    """ custom 403 error page """
    return render_template('403_error.html'), 403


@app.errorhandler(500)
def system_error_page(e):
    """ custom 500 error page """
    return render_template('500_error.html'), 500


@app.errorhandler(400)
def system_error_page(e):
    """ custom 500 error page """
    return render_template('400_error.html'), 400
