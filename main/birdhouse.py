import flask, flask.views
from flask import url_for, request, session, redirect, jsonify, Response, make_response, current_app
from jinja2 import environment, FileSystemLoader
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy import Boolean
from sqlalchemy import or_
from flask.ext import admin
from flask.ext.admin.contrib import sqla
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin import Admin, BaseView, expose
from dateutil.parser import parse as parse_date
from flask import render_template, request
from flask import session, redirect
from datetime import timedelta
from datetime import datetime
from functools import wraps, update_wrapper
import threading
from threading import Timer
from multiprocessing.pool import ThreadPool
import calendar
from calendar import Calendar
from time import sleep
import requests
import datetime
from datetime import date
import time
import json
import uuid
import random
import string
import smtplib
from email.mime.text import MIMEText as text
import os
import schedule
from werkzeug.utils import secure_filename
from tasks import send_notification, send_arrival_notifications, create_pdf
import db_conn
from db_conn import db, app
from models import *
import xlrd

IPP_URL = 'https://devapi.globelabs.com.ph/smsmessaging/v1/outbound/%s/requests'
ALSONS_APP_ID = 'MEoztReRyeHzaiXxaecR65HnqE98tz9g'
ALSONS_APP_SECRET = '01c5d1f8d3bfa9966786065c5a2d829d7e84cf26fbfb4a47c91552cb7c091608'
ALSONS_PASSPHRASE = 'PF5H8S9t7u'
ALSONS_SHORTCODE = '21586853'

ALLOWED_EXTENSIONS = set(['xls', 'xlsx', 'csv'])
UPLOAD_FOLDER = 'static/records'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class IngAdmin(sqla.ModelView):
    column_display_pk = True

class SchoolAdmin(sqla.ModelView):
    column_display_pk = True
    column_include_list = ['api_key', 'name', 'url', 'address', 'city', 'email', 'tel']

class StudentAdmin(sqla.ModelView):
    column_display_pk = True
    column_searchable_list = ['first_name', 'last_name', 'middle_name', 'id_no']

admin = Admin(app, name='raven')
admin.add_view(SchoolAdmin(Client, db.session))
admin.add_view(SchoolAdmin(Package, db.session))
admin.add_view(SchoolAdmin(PackageItem, db.session))
admin.add_view(SchoolAdmin(Cargo, db.session))
admin.add_view(SchoolAdmin(CargoItem, db.session))
admin.add_view(SchoolAdmin(Notification, db.session))
admin.add_view(SchoolAdmin(AdminUser, db.session))
admin.add_view(SchoolAdmin(ArrivalBatch, db.session))
admin.add_view(SchoolAdmin(ArrivalNotification, db.session))
admin.add_view(SchoolAdmin(Report, db.session))

def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response    
    return update_wrapper(no_cache, view)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def search_inbound(**kwargs):
    query = 'Package.query.filter(Package.client_no=="'+session['client_no']+'",Package.status!="Done",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'Package.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').order_by(Package.created_at.desc())'
    return eval(query)

def search_inbound_count(**kwargs):
    query = 'Package.query.filter(Package.client_no.ilike("'+session['client_no']+'"),'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'Package.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').count()'
    return eval(query)

def search_cargo(**kwargs):
    query = 'Cargo.query.filter(Cargo.client_no=="'+session['client_no']+'",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'Cargo.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').order_by(Cargo.created_at.desc())'
    return eval(query)

def search_cargo_count(**kwargs):
    query = 'Cargo.query.filter(Cargo.client_no=="'+session['client_no']+'",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'Cargo.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').count()'
    return eval(query)

def search_history(**kwargs):
    query = 'Package.query.filter(Package.client_no=="'+session['client_no']+'",Package.status=="Done",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'Package.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').order_by(Package.created_at.desc())'
    return eval(query)

def search_history_count(**kwargs):
    query = 'Package.query.filter(Package.client_no=="'+session['client_no']+'",Package.status=="Done",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'Package.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').count()'
    return eval(query)

def search_report(**kwargs):
    query = 'Report.query.filter(Report.client_no=="'+session['client_no']+'",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'Report.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').order_by(Report.created_at.desc())'
    return eval(query)

def search_report_count(**kwargs):
    query = 'Report.query.filter(Report.client_no=="'+session['client_no']+'",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'Report.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').count()'
    return eval(query)

def search_user(**kwargs):
    query = 'AdminUser.query.filter(AdminUser.client_no=="'+session['client_no']+'",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'AdminUser.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').order_by(AdminUser.created_at.desc())'
    return eval(query)

def search_user_count(**kwargs):
    query = 'AdminUser.query.filter(AdminUser.client_no=="'+session['client_no']+'",'
    for arg_name in kwargs:
        if kwargs[arg_name]:
            query += 'AdminUser.' + arg_name + '.ilike("%'+kwargs[arg_name]+'%"),'
    query += ').count()'
    return eval(query)


@app.route('/',methods=['GET','POST'])
@nocache
def index():
    if not session:
        return redirect('/login')
    session['inbound_limit'] = 50
    session['cargo_limit'] = 50
    session['history_limit'] = 50
    session['report_limit'] = 50
    session['waybill_items'] = []
    session['cargo_items'] = []
    user = AdminUser.query.filter_by(id=session['user_id']).first()
    total_entries = Package.query.filter(Package.client_no==session['client_no'], Package.status!='Done').count()
    packages = Package.query.filter(Package.client_no==session['client_no'], Package.status!='Done').order_by(Package.created_at.desc()).slice(session['inbound_limit'] - 50, session['inbound_limit'])
    
    user = AdminUser.query.filter_by(id=session['user_id']).first()
    if user.password == user.temp_pw:
        change_pw = 'yes'
    else:
        change_pw = 'no'

    if total_entries < 50:
        return flask.render_template(
        'index.html',
        client_name=session['client_name'],
        user_name=session['user_name'],
        packages=packages,
        limit=total_entries,
        total_entries=total_entries,
        prev_btn='disabled',
        next_btn='disabled',
        change_pw=change_pw,
        user_role=user.role
    )
    return flask.render_template(
        'index.html',
        client_name=session['client_name'],
        user_name=session['user_name'],
        packages=packages,
        limit=session['inbound_limit'],
        total_entries=total_entries,
        prev_btn='disabled',
        next_btn='enabled',
        change_pw=change_pw,
        user_role=user.role
    )


@app.route('/login',methods=['GET','POST'])
@nocache
def login_page():
    if session:
        return redirect('/')
    return flask.render_template('login.html')


@app.route('/user/authenticate',methods=['GET','POST'])
def authenticate_user():
    data = flask.request.form.to_dict()
    client = Client.query.filter_by(client_no=data['client_no']).first()
    if not client or client == None:
        return jsonify(status='failed', error='Invalid client ID.')
    user = AdminUser.query.filter_by(email=data['user_email'],password=data['user_password']).first()
    if not user or user == None:
        return jsonify(status='failed', error='Invalid email or password.')
    if user.client_no != client.client_no:
        return jsonify(status='failed', error='Not authorized.')
    session['user_name'] = user.name
    session['user_id'] = user.id
    session['client_no'] = client.client_no
    session['client_name'] = client.name
    return jsonify(status='success', error=''),200


@app.route('/user/add',methods=['GET','POST'])
def add_user():
    data = flask.request.form.to_dict()

    new_user = AdminUser(
        client_no=session['client_no'],
        email=data['email'],
        password=data['temp_pw'],
        temp_pw=data['temp_pw'],
        name=data['name'].title(),
        role=data['role'],
        added_by_id=session['user_id'],
        added_by_name=session['user_name'],
        join_date=datetime.datetime.now().strftime('%B %d, %Y'),
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    db.session.add(new_user)
    db.session.commit()
    prev_btn = 'enabled'
    total_entries = AdminUser.query.filter_by(client_no=session['client_no']).count()
    users = AdminUser.query.filter_by(client_no=session['client_no']).order_by(AdminUser.name).slice(session['user_limit'] - 50, session['user_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['user_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str(session['user_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str((session['user_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'users.html',
        users=users,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/user/edit',methods=['GET','POST'])
def edit_user():
    data = flask.request.form.to_dict()

    user = AdminUser.query.filter_by(id=session['open_user_id']).first()
    user.name = data['name'].title()
    user.email = data['email']
    user.role = data['role']

    db.session.commit()

    total_entries = AdminUser.query.filter_by(client_no=session['client_no']).count()
    users = AdminUser.query.filter_by(client_no=session['client_no']).order_by(AdminUser.name).slice(session['user_limit'] - 50, session['user_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['user_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str(session['user_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str((session['user_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'users.html',
        users=users,
        user_id=session['user_id'],
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/user/password/reset',methods=['GET','POST'])
def reset_user_password():
    password = flask.request.form.get('password')
    user = AdminUser.query.filter_by(id=session['open_user_id']).first()
    user.password = password
    user.temp_pw = password
    db.session.commit()
    return jsonify(status='success', message=''),201


@app.route('/user/delete',methods=['GET','POST'])
def delete_user():
    user = AdminUser.query.filter_by(id=session['open_user_id']).first()
    db.session.delete(user)
    db.session.commit()

    total_entries = AdminUser.query.filter_by(client_no=session['client_no']).count()
    users = AdminUser.query.filter_by(client_no=session['client_no']).order_by(AdminUser.name).slice(session['user_limit'] - 50, session['user_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['user_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str(session['user_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str((session['user_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'users.html',
        users=users,
        user_id=session['user_id'],
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/user/password/save',methods=['GET','POST'])
def save_password():
    password = flask.request.form.get('password')
    user = AdminUser.query.filter_by(id=session['user_id']).first()
    if user.password == password:
        return jsonify(status='failed', message='The password you entered is the same as your temporary password, please enter a different one.')
    user.password = password
    db.session.commit()
    return jsonify(status='success', message='')


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/login')


@app.route('/inbound',methods=['GET','POST'])
def all_inbound():
    slice_from = flask.request.args.get('slice_from')
    prev_btn = 'enabled'
    if slice_from == 'reset':
        session['inbound_limit'] = 50
        prev_btn = 'disabled'
    total_entries = Package.query.filter(Package.client_no==session['client_no'], Package.status!='Done').count()
    packages = Package.query.filter(Package.client_no==session['client_no'], Package.status!='Done').order_by(Package.created_at.desc()).slice(session['inbound_limit'] - 50, session['inbound_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['inbound_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['inbound_limit'] - 49),str(session['inbound_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['inbound_limit'] - 49),str((session['inbound_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'inbound.html',
        packages=packages,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/inbound/next',methods=['GET','POST'])
def next_inbound():
    session['inbound_limit'] += 50
    total_entries = Package.query.filter_by(client_no=session['client_no']).count()
    inbound = Package.query.filter_by(client_no=session['client_no']).order_by(Package.created_at.desc()).slice(session['inbound_limit'] - 50, session['inbound_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['inbound_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['inbound_limit'] - 49),str(session['inbound_limit']))
            prev_btn = 'enabled'
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['inbound_limit'] - 49),str((session['inbound_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'inbound_result.html',
            inbound=inbound)
        )


@app.route('/inbound/prev',methods=['GET','POST'])
def prev_inbound():
    session['inbound_limit'] -= 50
    total_entries = Package.query.filter_by(client_no=session['client_no']).count()
    inbound = Package.query.filter_by(client_no=session['client_no']).order_by(Package.created_at.desc()).slice(session['inbound_limit'] - 50, session['inbound_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        showing = '%s - %s' % (str(session['inbound_limit'] - 49),str(session['inbound_limit']))
        if session['inbound_limit'] <= 50:
            prev_btn = 'disabled'
            next_btn='enabled'
        else:
            prev_btn = 'enabled'
            next_btn='enabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'inbound_result.html',
            inbound=inbound)
        )


@app.route('/cargos',methods=['GET','POST'])
def all_cargo():
    slice_from = flask.request.args.get('slice_from')
    prev_btn = 'enabled'
    if slice_from == 'reset':
        session['cargo_limit'] = 50
        prev_btn = 'disabled'
    total_entries = Cargo.query.filter_by(client_no=session['client_no']).count()
    cargo = Cargo.query.filter_by(client_no=session['client_no']).order_by(Cargo.created_at.desc()).slice(session['cargo_limit'] - 50, session['cargo_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['cargo_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['cargo_limit'] - 49),str(session['cargo_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['cargo_limit'] - 49),str((session['cargo_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'cargo.html',
        cargo=cargo,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/history',methods=['GET','POST'])
def all_history():
    slice_from = flask.request.args.get('slice_from')
    prev_btn = 'enabled'
    if slice_from == 'reset':
        session['history_limit'] = 50
        prev_btn = 'disabled'

    total_entries = Package.query.filter(Package.client_no==session['client_no'], Package.status=='Done').count()
    history = Package.query.filter(Package.client_no==session['client_no'], Package.status=='Done').order_by(Package.payment_date.desc()).slice(session['history_limit'] - 50, session['history_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['history_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['history_limit'] - 49),str(session['history_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['history_limit'] - 49),str((session['history_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'history.html',
        history=history,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/reports',methods=['GET','POST'])
def all_reports():
    slice_from = flask.request.args.get('slice_from')
    prev_btn = 'enabled'
    if slice_from == 'reset':
        session['history_limit'] = 50
        prev_btn = 'disabled'

    total_entries = Report.query.filter_by(client_no=session['client_no']).count()
    reports = Report.query.filter_by(client_no=session['client_no']).order_by(Report.created_at.desc()).slice(session['report_limit'] - 50, session['report_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['report_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['report_limit'] - 49),str(session['report_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['report_limit'] - 49),str((session['report_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'reports.html',
        reports=reports,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/blast',methods=['GET','POST'])
def get_blast():
    batch_id = flask.request.args.get('batch_id')
    batch = Batch.query.filter_by(id=batch_id).first()
    success = OutboundMessage.query.filter_by(batch_id=batch_id, status='success').all()
    failed = OutboundMessage.query.filter_by(batch_id=batch_id, status='failed').all()
    return flask.render_template('blast_info.html',batch=batch,success=success,failed=failed)


@app.route('/blasts/next',methods=['GET','POST'])
def next_blasts():
    session['cargo_limit'] += 50
    total_entries = Batch.query.filter_by(client_no=session['client_no']).count()
    blasts = Batch.query.filter_by(client_no=session['client_no']).order_by(Batch.created_at.desc()).slice(session['cargo_limit'] - 50, session['cargo_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['cargo_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['cargo_limit'] - 49),str(session['cargo_limit']))
            prev_btn = 'enabled'
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['cargo_limit'] - 49),str((session['cargo_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'blasts_result.html',
            blasts=blasts)
        )


@app.route('/blasts/prev',methods=['GET','POST'])
def prev_blasts():
    session['cargo_limit'] -= 50
    total_entries = Batch.query.filter_by(client_no=session['client_no']).count()
    blasts = Batch.query.filter_by(client_no=session['client_no']).order_by(Batch.created_at.desc()).slice(session['cargo_limit'] - 50, session['cargo_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        showing = '%s - %s' % (str(session['cargo_limit'] - 49),str(session['cargo_limit']))
        if session['cargo_limit'] <= 50:
            prev_btn = 'disabled'
            next_btn='enabled'
        else:
            prev_btn = 'enabled'
            next_btn='enabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'blasts_result.html',
            blasts=blasts)
        )


@app.route('/reminders',methods=['GET','POST'])
def payment_reminders():
    slice_from = flask.request.args.get('slice_from')
    prev_btn = 'enabled'
    if slice_from == 'reset':
        session['reminder_limit'] = 50
        prev_btn = 'disabled'
    total_entries = ReminderBatch.query.filter_by(client_no=session['client_no']).count()
    reminders = ReminderBatch.query.filter_by(client_no=session['client_no']).order_by(ReminderBatch.created_at.desc()).slice(session['reminder_limit'] - 50, session['reminder_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['reminder_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['reminder_limit'] - 49),str(session['reminder_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['reminder_limit'] - 49),str((session['reminder_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'reminders.html',
        reminders=reminders,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/reminder',methods=['GET','POST'])
def view_reminder():
    reminder_id = flask.request.args.get('reminder_id')
    reminder = ReminderBatch.query.filter_by(id=reminder_id).first()
    file_loc = '%s/%s' % (UPLOAD_FOLDER, reminder.file_name)
    success = ReminderMessage.query.filter_by(batch_id=reminder.id,status='success')
    failed = ReminderMessage.query.filter_by(batch_id=reminder.id,status='failed')
    return flask.render_template('view_reminder.html', file_loc=file_loc, batch=reminder, success=success, failed=failed)


@app.route('/reminders/next',methods=['GET','POST'])
def next_reminders():
    session['reminder_limit'] += 50
    total_entries = ReminderBatch.query.filter_by(client_no=session['client_no']).count()
    reminders = ReminderBatch.query.filter_by(client_no=session['client_no']).order_by(ReminderBatch.created_at.desc()).slice(session['reminder_limit'] - 50, session['reminder_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['reminder_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['reminder_limit'] - 49),str(session['reminder_limit']))
            prev_btn = 'enabled'
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['reminder_limit'] - 49),str((session['reminder_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'reminders_result.html',
            reminders=reminders)
        )


@app.route('/reminders/prev',methods=['GET','POST'])
def prev_reminders():
    session['reminder_limit'] -= 50
    total_entries = ReminderBatch.query.filter_by(client_no=session['client_no']).count()
    reminders = ReminderBatch.query.filter_by(client_no=session['client_no']).order_by(ReminderBatch.created_at.desc()).slice(session['reminder_limit'] - 50, session['reminder_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        showing = '%s - %s' % (str(session['reminder_limit'] - 49),str(session['reminder_limit']))
        if session['reminder_limit'] <= 50:
            prev_btn = 'disabled'
            next_btn='enabled'
        else:
            prev_btn = 'enabled'
            next_btn='enabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'reminders_result.html',
            reminders=reminders)
        )


@app.route('/contacts',methods=['GET','POST'])
def contacts():
    slice_from = flask.request.args.get('slice_from')
    prev_btn = 'enabled'
    if slice_from == 'reset':
        session['contact_limit'] = 50
        prev_btn = 'disabled'
    total_entries = Contact.query.filter_by(client_no=session['client_no']).count()
    contacts = Contact.query.filter_by(client_no=session['client_no']).order_by(Contact.name).slice(session['contact_limit'] - 50, session['contact_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['contact_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['contact_limit'] - 49),str(session['contact_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['contact_limit'] - 49),str((session['contact_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'contacts.html',
        contacts=contacts,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/contacts/next',methods=['GET','POST'])
def next_contacts():
    session['contact_limit'] += 50
    total_entries = Contact.query.filter_by(client_no=session['client_no']).count()
    contacts = Contact.query.filter_by(client_no=session['client_no']).order_by(Contact.name).slice(session['contact_limit'] - 50, session['contact_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['contact_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['contact_limit'] - 49),str(session['contact_limit']))
            prev_btn = 'enabled'
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['contact_limit'] - 49),str((session['contact_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'contacts_result.html',
            contacts=contacts)
        )


@app.route('/contacts/prev',methods=['GET','POST'])
def prev_contacts():
    session['contact_limit'] -= 50
    total_entries = Contact.query.filter_by(client_no=session['client_no']).count()
    contacts = Contact.query.filter_by(client_no=session['client_no']).order_by(Contact.name).slice(session['contact_limit'] - 50, session['contact_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        showing = '%s - %s' % (str(session['contact_limit'] - 49),str(session['contact_limit']))
        if session['contact_limit'] <= 50:
            prev_btn = 'disabled'
            next_btn='enabled'
        else:
            prev_btn = 'enabled'
            next_btn='enabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'contacts_result.html',
            contacts=contacts)
        )


@app.route('/groups',methods=['GET','POST'])
def groups():
    slice_from = flask.request.args.get('slice_from')
    prev_btn = 'enabled'
    if slice_from == 'reset':
        session['group_limit'] = 50
        prev_btn = 'disabled'
    total_entries = Group.query.filter_by(client_no=session['client_no']).count()
    groups = Group.query.filter_by(client_no=session['client_no']).order_by(Group.name).slice(session['group_limit'] - 50, session['group_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['group_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['group_limit'] - 49),str(session['group_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['group_limit'] - 49),str((session['group_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'groups.html',
        groups=groups,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/groups/next',methods=['GET','POST'])
def next_groups():
    session['group_limit'] += 50
    total_entries = Group.query.filter_by(client_no=session['client_no']).count()
    groups = Group.query.filter_by(client_no=session['client_no']).order_by(Group.name).slice(session['group_limit'] - 50, session['group_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['group_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['group_limit'] - 49),str(session['group_limit']))
            prev_btn = 'enabled'
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['group_limit'] - 49),str((session['group_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'groups_result.html',
            groups=groups)
        )


@app.route('/groups/prev',methods=['GET','POST'])
def prev_groups():
    session['group_limit'] -= 50
    total_entries = Group.query.filter_by(client_no=session['client_no']).count()
    groups = Group.query.filter_by(client_no=session['client_no']).order_by(Group.name).slice(session['group_limit'] - 50, session['group_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        showing = '%s - %s' % (str(session['group_limit'] - 49),str(session['group_limit']))
        if session['group_limit'] <= 50:
            prev_btn = 'disabled'
            next_btn='enabled'
        else:
            prev_btn = 'enabled'
            next_btn='enabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'groups_result.html',
            groups=groups)
        )


@app.route('/users',methods=['GET','POST'])
def users():
    slice_from = flask.request.args.get('slice_from')
    prev_btn = 'enabled'
    if slice_from == 'reset':
        session['user_limit'] = 50
        prev_btn = 'disabled'
    total_entries = AdminUser.query.filter_by(client_no=session['client_no']).count()
    users = AdminUser.query.filter_by(client_no=session['client_no']).order_by(AdminUser.name).slice(session['user_limit'] - 50, session['user_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['user_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str(session['user_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str((session['user_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'users.html',
        users=users,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/users/next',methods=['GET','POST'])
def next_users():
    session['user_limit'] += 50
    total_entries = AdminUser.query.filter_by(client_no=session['client_no']).count()
    users = AdminUser.query.filter_by(client_no=session['client_no']).order_by(AdminUser.name).slice(session['user_limit'] - 50, session['user_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['user_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str(session['user_limit']))
            prev_btn = 'enabled'
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['user_limit'] - 49),str((session['user_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'users_result.html',
            users=users)
        )


@app.route('/users/prev',methods=['GET','POST'])
def prev_users():
    session['user_limit'] -= 50
    total_entries = AdminUser.query.filter_by(client_no=session['client_no']).count()
    users = AdminUser.query.filter_by(client_no=session['client_no']).order_by(AdminUser.name).slice(session['user_limit'] - 50, session['user_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        showing = '%s - %s' % (str(session['user_limit'] - 49),str(session['user_limit']))
        if session['user_limit'] <= 50:
            prev_btn = 'disabled'
            next_btn='enabled'
        else:
            prev_btn = 'enabled'
            next_btn='enabled'

    return jsonify(
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
        template=flask.render_template(
            'users_result.html',
            users=users)
        )


@app.route('/user',methods=['GET','POST'])
def user_info():
    session['open_user_id'] = flask.request.args.get('user_id')
    user = AdminUser.query.filter_by(id=session['open_user_id']).first()
    return flask.render_template('user_info.html',user=user, user_id=session['user_id'])


@app.route('/groups/save',methods=['GET','POST'])
def add_group():
    name = flask.request.form.get('name')
    exists = Group.query.filter_by(name=name).first()
    if exists or exists != None:
        return jsonify(
            status='error',
            message='Duplicate group name.'
            )
    new_group = Group(
        client_no=session['client_no'],
        name=name,
        created_by_id=session['user_id'],
        created_by_name=session['user_name'],
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )
    db.session.add(new_group)
    db.session.commit()
    prev_btn = 'enabled'
    total_entries = Group.query.filter_by(client_no=session['client_no']).count()
    groups = Group.query.filter_by(client_no=session['client_no']).order_by(Group.name).slice(session['group_limit'] - 50, session['group_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['group_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['group_limit'] - 49),str(session['group_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['group_limit'] - 49),str((session['group_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return jsonify(
        status='success',
        template=flask.render_template(
                'groups.html',
                groups=groups,
                showing=showing,
                total_entries=total_entries,
                prev_btn=prev_btn,
                next_btn=next_btn,
            ),
        group_template=flask.render_template('add_contact_groups.html',groups=groups)
        )


@app.route('/contacts/upload', methods=['GET', 'POST'])
def prepare_contacts_upload():
    file = flask.request.files['contactsFile']
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    if file and allowed_file(file.filename):
        path = '%s/%s' % (UPLOAD_FOLDER, filename)
        book = xlrd.open_workbook(path)
        sheet = book.sheet_by_index(0)
        rows = sheet.nrows;
        cols = 3
        msisdn_list = []
        for row in range(rows):
            repeated_msisdn = 0
            cell = sheet.cell(row,0)
            if cell.value in msisdn_list:
                repeated_msisdn += 1
            else:
                existing_contact = Contact.query.filter_by(msisdn='0%s'%str(cell.value)[-10:]).first()
                if existing_contact or existing_contact != None:
                    repeated_msisdn += 1
                else:
                    msisdn_list.append(cell.value)
            

        new_contact_upload = ContactBatch(
            client_no=session['client_no'],
            uploader_id=session['user_id'],
            uploader_name=session['user_name'],
            batch_size=rows - repeated_msisdn,
            date=datetime.datetime.now().strftime('%B %d, %Y'),
            time=time.strftime("%I:%M%p"),
            file_name=filename,
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
         
        db.session.add(new_contact_upload)
        db.session.commit()

        upload_contacts.delay(new_contact_upload.id,session['client_no'],session['user_id'],session['user_name'])      

        existing = Contact.query.filter_by(batch_id=str(new_contact_upload.id)).count()
        new_contact_upload.pending = new_contact_upload.batch_size - existing
        db.session.commit()

        return jsonify(
            status='success',
            pending=new_contact_upload.pending,
            batch_id=new_contact_upload.id,
            template=flask.render_template('contact_upload_status.html', batch=new_contact_upload)
            )

    return jsonify(
        status = 'failed',
        message = 'Invalid file.'
        )


@app.route('/reminder/upload', methods=['GET', 'POST'])
def upload_file():
    file = flask.request.files['file']
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if file and allowed_file(file.filename):
        path = '%s/%s' % (UPLOAD_FOLDER, filename)
        book = xlrd.open_workbook(path)
        sheet = book.sheet_by_index(0)
        rows = sheet.nrows;
        cols = 2
        new_reminder = ReminderBatch(
            client_no=session['client_no'],
            sender_id=session['user_id'],
            batch_size=rows,
            sender_name=session['user_name'],
            date=datetime.datetime.now().strftime('%B %d, %Y'),
            time=time.strftime("%I:%M%p"),
            file_name=filename,
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
        db.session.add(new_reminder)
        db.session.commit()

        for row in range(rows):
            vals = []
            for col in range(cols):
                cell = sheet.cell(row,col)
                if cell.value == '':
                    vals.append(None)
                else:
                    vals.append(cell.value)

            contact = Contact.query.filter_by(msisdn='0%s'%vals[0][-10:]).first()
            if contact or contact != None:
                new_message = ReminderMessage(
                    batch_id=new_reminder.id,
                    contact_name=contact.name,
                    msisdn=contact.msisdn,
                    content=vals[1],
                    date=new_reminder.date,
                    time=new_reminder.time,
                    )
            else:
                new_message = ReminderMessage(
                    batch_id=new_reminder.id,
                    msisdn='0%s'%vals[0][-10:],
                    content=vals[1],
                    date=new_reminder.date,
                    time=new_reminder.time,
                    )
            db.session.add(new_message)
            db.session.commit()
            new_reminder.pending = ReminderMessage.query.filter_by(batch_id=new_reminder.id,status='pending').count()
            db.session.commit()

        send_reminders.delay(new_reminder.id,new_reminder.date,new_reminder.time,session['client_no'])

        return jsonify(
            status='success',
            pending=new_reminder.pending,
            batch_id=new_reminder.id,
            template=flask.render_template('reminder_status.html', batch=new_reminder)
            )

        # prev_btn = 'enabled'
        # total_entries = ReminderBatch.query.filter_by(client_no=session['client_no']).count()
        # reminders = ReminderBatch.query.filter_by(client_no=session['client_no']).order_by(ReminderBatch.created_at.desc()).slice(session['reminder_limit'] - 50, session['reminder_limit'])
        # if total_entries < 50:
        #     showing='1 - %s' % total_entries
        #     prev_btn = 'disabled'
        #     next_btn='disabled'
        # else:
        #     diff = total_entries - (session['reminder_limit'] - 50)
        #     if diff > 50:
        #         showing = '%s - %s' % (str(session['reminder_limit'] - 49),str(session['reminder_limit']))
        #         next_btn='enabled'
        #     else:
        #         showing = '%s - %s' % (str(session['reminder_limit'] - 49),str((session['reminder_limit']-50)+diff))
        #         prev_btn = 'enabled'
        #         next_btn='disabled'

        # return jsonify(
        #     status='success',
        #     template=flask.render_template(
        #             'reminders.html',
        #             reminders=reminders,
        #             showing=showing,
        #             total_entries=total_entries,
        #             prev_btn=prev_btn,
        #             next_btn=next_btn
        #         )
        #     )

    return jsonify(
        status = 'failed',
        message = 'Invalid file.'
        )


@app.route('/progress/existing',methods=['GET','POST'])
def check_existing_progress():
    blast = Batch.query.filter(Batch.sender_id==session['user_id'],Batch.pending!=0).first()
    if blast or blast != None:
        return jsonify(
            in_progress='blast',
            pending=blast.pending,
            batch_id=blast.id,
            template=flask.render_template('blast_status.html', batch=blast)
            )
    reminder = ReminderBatch.query.filter(ReminderBatch.sender_id==session['user_id'],ReminderBatch.pending!=0).first()
    if reminder or reminder != None:
        return jsonify(
            in_progress='reminder',
            pending=reminder.pending,
            batch_id=reminder.id,
            template=flask.render_template('reminder_status.html', batch=reminder)
            )
    return jsonify(in_progress='none')


@app.route('/conversation',methods=['GET','POST'])
def open_conversation():
    conversation_id = flask.request.args.get('conversation_id')
    session['conversation_id'] = conversation_id
    conversation = Package.query.filter_by(id=conversation_id).first()
    if conversation.status == 'unread':
        conversation.status = 'read'
        db.session.commit()
    messages = PackageItem.query.filter_by(conversation_id=conversation_id).order_by(PackageItem.created_at)
    return flask.render_template(
        'conversation.html',
        conversation=conversation,
        messages=messages 
        ),200


@app.route('/conversation/reply',methods=['GET','POST'])
def send_reply():
    message_content = flask.request.form.get('content')
    conversation = Package.query.filter_by(id=session['conversation_id']).first()
    client = Client.query.filter_by(client_no=session['client_no']).first()
    message_options = {
        'app_id': client.app_id,
        'app_secret': client.app_secret,
        'message': message_content,
        'address': conversation.msisdn,
        'passphrase': client.passphrase,
    }
    try:
        r = requests.post(IPP_URL%client.shortcode,message_options)
        if r.status_code != 201:
            return jsonify(status='failed')

        reply = PackageItem(
            conversation_id=conversation.id,
            message_type='outbound',
            date=datetime.datetime.now().strftime('%B %d, %Y'),
            time=time.strftime("%I:%M%p"),
            content=message_content,
            outbound_sender_id=session['user_id'],
            outbound_sender_name=session['user_name'],
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
        db.session.add(reply)
        db.session.commit()
        conversation.latest_content = message_content
        conversation.latest_date = reply.date
        conversation.latest_time = reply.time
        conversation.created_at = reply.created_at
        db.session.commit()
        return jsonify(
            status='success',
            template=flask.render_template(
                'reply.html',
                conversation=conversation,
                message=reply 
                )
            )   
    except requests.exceptions.ConnectionError as e:
        return jsonify(status='failed')


@app.route('/contact/edit',methods=['GET','POST'])
def edit_contact():
    data = flask.request.form.to_dict()
    groups = flask.request.form.getlist('groups[]')
    contact = Contact.query.filter_by(msisdn=session['contact_msisdn']).first()

    if contact.msisdn != data['msisdn']:
        existing_conversation = Package.query.filter_by(msisdn=contact.msisdn).first()
        if existing_conversation or existing_conversation != None:
            existing_conversation.contact_name = None
            existing_conversation.display_name = existing_conversation.msisdn
            db.session.commit()

    contact.name = data['name'].title()
    contact.contact_type = data['contact_type']
    contact.msisdn = '0%s'%data['msisdn'][-10:]

    existing_contact_groups = ContactGroup.query.filter_by(contact_id=contact.id).delete()

    for item in groups:
        group = Group.query.filter_by(id=int(item)).first()
        contact_group = ContactGroup(
            contact_id = contact.id,
            group_id = int(item)
            )
        db.session.add(contact_group)

    groups_to_recount = Group.query.filter_by(client_no=session['client_no'])
    for _ in groups_to_recount:
        group_size = ContactGroup.query.filter_by(group_id=_.id).count()
        _.size = group_size

    conversation = Package.query.filter_by(msisdn=data['msisdn']).first()
    if conversation or conversation != None:
        conversation.contact_name = data['name'].title()
        conversation.display_name = data['name'].title()
    db.session.commit()

    if data['type'] == 'from_convo':
        messages = PackageItem.query.filter_by(conversation_id=conversation.id).order_by(PackageItem.created_at)
        groups = Group.query.filter_by(client_no=session['client_no']).order_by(Group.name)
        contacts = Contact.query.filter_by(client_no=session['client_no']).order_by(Contact.name)
        contact_count = Contact.query.filter_by(client_no=session['client_no']).count()
        customers_count = Contact.query.filter_by(client_no=session['client_no'], contact_type='Customer').count()
        staff_count = Contact.query.filter_by(client_no=session['client_no'], contact_type='Staff').count()
        return jsonify(
            template = flask.render_template(
                'conversation.html',
                conversation=conversation,
                messages=messages 
                ),
            groups_template = flask.render_template(
                'group_count_update.html',
                contact_count=contact_count,
                customers_count=customers_count,
                staff_count=staff_count,
                groups=groups
                )
            ),201

    if session['contact_msisdn'] != data['msisdn']:
        old_conversation = Package.query.filter_by(msisdn=session['contact_msisdn']).first()
        if old_conversation or old_conversation != None:
            old_conversation.contact_name = None
            db.session.commit()

    total_entries = Contact.query.filter_by(client_no=session['client_no']).count()
    contacts = Contact.query.filter_by(client_no=session['client_no']).order_by(Contact.name).slice(session['contact_limit'] - 50, session['contact_limit'])
    if total_entries < 50:
        showing = '1 - %s' % str(total_entries)
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['contact_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['contact_limit'] - 49),str(session['contact_limit']))
            prev_btn = 'enabled'
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['contact_limit'] - 49),str((session['contact_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    groups = Group.query.filter_by(client_no=session['client_no']).order_by(Group.name)
    contacts = Contact.query.filter_by(client_no=session['client_no']).order_by(Contact.name)
    contact_count = Contact.query.filter_by(client_no=session['client_no']).count()
    customers_count = Contact.query.filter_by(client_no=session['client_no'], contact_type='Customer').count()
    staff_count = Contact.query.filter_by(client_no=session['client_no'], contact_type='Staff').count()

    return jsonify(
        template = flask.render_template(
            'contacts.html',
            contacts=contacts,
            showing=showing,
            total_entries=total_entries,
            prev_btn=prev_btn,
            next_btn=next_btn
            ),
        groups_template = flask.render_template(
            'group_count_update.html',
            contact_count=contact_count,
            customers_count=customers_count,
            staff_count=staff_count,
            groups=groups
            )
        ),201


@app.route('/contact/save',methods=['GET','POST'])
def save_contact():
    data = flask.request.form.to_dict()
    groups = flask.request.form.getlist('groups[]')
    new_contact = Contact(
        client_no=session['client_no'],
        contact_type=data['contact_type'].title(),
        name=data['name'].title(),
        msisdn='0%s'%data['msisdn'][-10:],
        added_by=session['user_id'],
        added_by_name=session['user_name'],
        join_date=datetime.datetime.now().strftime('%B %d, %Y'),
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    db.session.add(new_contact)
    db.session.commit()

    for item in groups:
        group = Group.query.filter_by(id=int(item)).first()
        contact_group = ContactGroup(
            contact_id = new_contact.id,
            group_id = int(item)
            )
        db.session.add(contact_group)
        group_size = ContactGroup.query.filter_by(group_id=int(item)).count()
        group.size = group_size
    
    conversation = Package.query.filter_by(msisdn=new_contact.msisdn).first()
    if conversation or conversation != None:
        conversation.contact_name = new_contact.name
        conversation.display_name = new_contact.name

    db.session.commit()

    if data['type'] == 'save':
        messages = PackageItem.query.filter_by(conversation_id=conversation.id).order_by(PackageItem.created_at)
        return flask.render_template(
            'conversation.html',
            conversation=conversation,
            messages=messages 
            ),201
    prev_btn='enabled'
    total_entries = Contact.query.filter_by(client_no=session['client_no']).count()
    contacts = Contact.query.filter_by(client_no=session['client_no']).order_by(Contact.name).slice(session['contact_limit'] - 50, session['contact_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['contact_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['contact_limit'] - 49),str(session['contact_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['contact_limit'] - 49),str((session['contact_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'contacts.html',
        contacts=contacts,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/contact',methods=['GET','POST'])
def get_contact_info():
    data = flask.request.args.to_dict()
    session['contact_msisdn'] = data['msisdn']
    contact = Contact.query.filter_by(msisdn=data['msisdn']).first()
    contact_groups = [r.group_id for r in db.session.query(ContactGroup.group_id).filter_by(contact_id=contact.id).all()]
    groups = Group.query.filter_by(client_no=session['client_no']).order_by(Group.name)

    return flask.render_template(
        'contact_info.html',
        type=data['type'],
        contact=contact,
        groups=groups,
        contact_groups=contact_groups
        ),200


@app.route('/group',methods=['GET','POST'])
def get_group_info():
    group_id = flask.request.args.get('group_id')
    session['open_group_id'] = group_id
    group = Group.query.filter_by(id=group_id).first()
    members = Contact.query.join(ContactGroup, Contact.id==ContactGroup.contact_id).add_columns(Contact.id, Contact.name, Contact.contact_type, Contact.msisdn).filter(Contact.id == ContactGroup.contact_id).filter(ContactGroup.group_id == group_id).all()
    return flask.render_template('group_info.html',group=group,members=members)


@app.route('/group/edit',methods=['GET','POST'])
def edit_group_info():
    group = Group.query.filter_by(id=session['open_group_id']).first()
    group.name = flask.request.form.get('group_name')
    db.session.commit()
    return jsonify(status='success'),201


@app.route('/group/members/delete/get',methods=['GET','POST'])
def get_delete_members():
    session['member_id'] = flask.request.form.get('member_id')
    session['group_id'] = flask.request.form.get('group_id')
    return jsonify(status='success'),201


@app.route('/group/members/delete',methods=['GET','POST'])
def delete_members():
    group = Group.query.filter_by(id=session['group_id']).first()
    contact_group = ContactGroup.query.filter_by(contact_id=session['member_id'], group_id=session['group_id']).first()
    db.session.delete(contact_group)
    db.session.commit()
    group.size = ContactGroup.query.filter_by(group_id=group.id).count()
    db.session.commit()
    members = Contact.query.join(ContactGroup, Contact.id==ContactGroup.contact_id).add_columns(Contact.id, Contact.name, Contact.contact_type, Contact.msisdn).filter(Contact.id == ContactGroup.contact_id).filter(ContactGroup.group_id == session['group_id']).all()
    return flask.render_template('group_info.html',group=group,members=members)


@app.route('/recipients/add', methods=['GET', 'POST'])
def add_recipients():
    special = flask.request.form.get('special')
    group_recipients_name = []
    individual_recipients_name = []
    number_recipients = []
    for group_recipient in session['group_recipients']:
        group = Group.query.filter_by(client_no=session['client_no'],id=group_recipient).first()
        group_recipients_name.append(group.name)
    for individual_recipient in session['individual_recipients']:
        contact = Contact.query.filter_by(client_no=session['client_no'],id=individual_recipient).first()
        individual_recipients_name.append(contact.name)
    for number_recipient in session['number_recipients']:
        number_recipients.append(number_recipient)
    return flask.render_template(
        'recipients.html',
        special=special,
        individual_recipients=individual_recipients_name,
        group_recipients=group_recipients_name,
        number_recipients=number_recipients
        )


@app.route('/recipients/clear', methods=['GET', 'POST'])
def clear_recipients():
    session['group_recipients'] = []
    session['individual_recipients'] = []
    session['number_recipients'] = []
    return '',201


@app.route('/blast/send', methods=['GET', 'POST'])
def send_text_blast():
    data = flask.request.form.to_dict()
    if ('special' in data) and (data['special'] != None or data['special'] != ''):
        if session['number_recipients']:
            number_recipients = ', '.join(session['number_recipients'])
            new_batch = Batch(
                client_no=session['client_no'],
                message_type='custom',
                sender_id=session['user_id'],
                sender_name=session['user_name'],
                recipient='%s, %s' % (data['special'],number_recipients),
                date=datetime.datetime.now().strftime('%B %d, %Y'),
                time=time.strftime("%I:%M%p"),
                content=data['content'],
                created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
                )
        else :
            new_batch = Batch(
                client_no=session['client_no'],
                message_type='custom',
                sender_id=session['user_id'],
                sender_name=session['user_name'],
                recipient=data['special'],
                date=datetime.datetime.now().strftime('%B %d, %Y'),
                time=time.strftime("%I:%M%p"),
                content=data['content'],
                created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
                )
        db.session.add(new_batch)
        db.session.commit()

        if data['special'] == 'Everyone':
            contacts = Contact.query.filter_by(client_no=session['client_no']).all()
        elif data['special'] == 'All Customers':
            contacts = Contact.query.filter_by(client_no=session['client_no'],contact_type='Customer').all()
        elif data['special'] == 'All Staff':
            contacts = Contact.query.filter_by(client_no=session['client_no'],contact_type='Staff').all()

        for contact in contacts:
            new_message = OutboundMessage(
                batch_id=new_batch.id,
                date=new_batch.date,
                time=new_batch.time,
                contact_name=contact.name,
                msisdn=contact.msisdn
                )
            db.session.add(new_message)
        db.session.commit()
        if session['number_recipients']:
            for msisdn in session['number_recipients']:
                number_message = OutboundMessage(
                    batch_id=new_batch.id,
                    date=new_batch.date,
                    time=new_batch.time,
                    msisdn=msisdn
                    )
                db.session.add(number_message)
            db.session.commit()

        new_batch.batch_size = OutboundMessage.query.filter_by(batch_id=new_batch.id).count()
        new_batch.pending = OutboundMessage.query.filter_by(batch_id=new_batch.id,status='pending').count()
        db.session.commit()

        blast_sms.delay(new_batch.id,new_batch.date,new_batch.time,data['content'],session['client_no'])
        
        session['group_recipients'] = []
        session['individual_recipients'] = []
        session['group_recipients_name'] = []
        session['individual_recipients_name'] = []
        session['number_recipients'] = []

        return jsonify(
            pending=new_batch.pending,
            batch_id=new_batch.id,
            template=flask.render_template('blast_status.html', batch=new_batch)
            )

    if session['number_recipients']:
        recipient_string = ', '.join(session['group_recipients_name']+session['individual_recipients_name'])
        number_recipients = ', '.join(session['number_recipients'])
        new_batch = Batch(
            client_no=session['client_no'],
            message_type='custom',
            sender_id=session['user_id'],
            sender_name=session['user_name'],
            recipient='%s, %s' % (recipient_string,number_recipients),
            date=datetime.datetime.now().strftime('%B %d, %Y'),
            time=time.strftime("%I:%M%p"),
            content=data['content'],
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
    else:
        new_batch = Batch(
            client_no=session['client_no'],
            message_type='custom',
            sender_id=session['user_id'],
            sender_name=session['user_name'],
            recipient=', '.join(session['group_recipients_name']+session['individual_recipients_name']),
            date=datetime.datetime.now().strftime('%B %d, %Y'),
            time=time.strftime("%I:%M%p"),
            content=data['content'],
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
    db.session.add(new_batch)
    db.session.commit()

    for group_id in session['group_recipients']:
        contact_group = ContactGroup.query.filter_by(group_id=group_id).all()
        for item in contact_group:
            contact = Contact.query.filter_by(id=item.contact_id).first()
            in_list = OutboundMessage.query.filter_by(batch_id=new_batch.id,msisdn=contact.msisdn).first()
            if not in_list or in_list == None:
                new_message = OutboundMessage(
                    batch_id=new_batch.id,
                    date=new_batch.date,
                    time=new_batch.time,
                    contact_name=contact.name,
                    msisdn=contact.msisdn
                    )
                db.session.add(new_message)
        db.session.commit()

    for individual_id in session['individual_recipients']:
        contact = Contact.query.filter_by(id=individual_id).first()
        in_list = OutboundMessage.query.filter_by(batch_id=new_batch.id,msisdn=contact.msisdn).first()
        if not in_list or in_list == None:
            new_message = OutboundMessage(
                batch_id=new_batch.id,
                date=new_batch.date,
                time=new_batch.time,
                contact_name=contact.name,
                msisdn=contact.msisdn
                )
            db.session.add(new_message)
    db.session.commit()

    if session['number_recipients']:
        for msisdn in session['number_recipients']:
            number_message = OutboundMessage(
                batch_id=new_batch.id,
                date=new_batch.date,
                time=new_batch.time,
                msisdn=msisdn
                )
            db.session.add(number_message)
        db.session.commit()


    new_batch.batch_size = OutboundMessage.query.filter_by(batch_id=new_batch.id).count()
    new_batch.pending = OutboundMessage.query.filter_by(batch_id=new_batch.id,status='pending').count()
    db.session.commit()

    blast_sms.delay(new_batch.id,new_batch.date,new_batch.time,data['content'],session['client_no'])
    session['group_recipients'] = []
    session['individual_recipients'] = []
    session['group_recipients_name'] = []
    session['individual_recipients_name'] = []
    session['number_recipients'] = []
    return jsonify(
        pending=new_batch.pending,
        batch_id=new_batch.id,
        template=flask.render_template('blast_status.html', batch=new_batch)
        )

    # total_entries = Batch.query.filter_by(client_no=session['client_no']).count()
    # blasts = Batch.query.filter_by(client_no=session['client_no']).order_by(Batch.created_at.desc()).slice(session['cargo_limit'] - 50, session['cargo_limit'])
    # prev_btn = 'enabled'
    # if total_entries < 50:
    #     showing='1 - %s' % total_entries
    #     prev_btn = 'disabled'
    #     next_btn='disabled'
    # else:
    #     diff = total_entries - (session['cargo_limit'] - 50)
    #     if diff > 50:
    #         showing = '%s - %s' % (str(session['cargo_limit'] - 49),str(session['cargo_limit']))
    #         next_btn='enabled'
    #     else:
    #         showing = '%s - %s' % (str(session['cargo_limit'] - 49),str((session['cargo_limit']-50)+diff))
    #         prev_btn = 'enabled'
    #         next_btn='disabled'
    # return flask.render_template(
    #     'blasts.html',
    #     blasts=blasts,
    #     showing=showing,
    #     total_entries=total_entries,
    #     prev_btn=prev_btn,
    #     next_btn=next_btn,
    # )


@app.route('/blast/progress', methods=['GET', 'POST'])
def get_blast_progress():
    batch_id = flask.request.form.get('batch_id')
    batch = ArrivalBatch.query.filter_by(id=batch_id).first()
    return jsonify(
        pending=batch.pending,
        template=flask.render_template('blast_status.html', batch=batch)
        )


@app.route('/cargo/notifications', methods=['GET', 'POST'])
def get_cargo_notifications():
    cargo = Cargo.query.filter_by(id=session['cargo_id']).first()
    notifications = ArrivalNotification.query.filter_by(cargo_id=session['cargo_id']).all()
    return jsonify(
        template=flask.render_template(
            'cargo_notifications.html',
            notifications=notifications,
            cargo=cargo
            )
        )


@app.route('/inbound/search',methods=['GET','POST'])
def search_from_inbound():
    data = flask.request.args.to_dict()
    result = search_inbound(
        waybill_no=data['waybill_no'],
        waybill_type=data['type'],
        destination=data['destination'],
        recipient=data['recipient'],
        status=data['status'],
        total=data['amount'],
        date_received=data['received'],
        arrival_date=data['arrived']
        )
    count = search_inbound_count(
        waybill_no=data['waybill_no'],
        waybill_type=data['type'],
        destination=data['destination'],
        recipient=data['recipient'],
        status=data['status'],
        total=data['amount'],
        date_received=data['received'],
        arrival_date=data['arrived']
        )
    return jsonify(
        count = count,
        template = flask.render_template('inbound_result.html',packages=result)
        )


@app.route('/cargos/search',methods=['GET','POST'])
def search_from_cargo():
    data = flask.request.args.to_dict()
    result = search_cargo(
        cargo_no=data['cargo_number'],
        truck=data['truck'],
        origin=data['origin'],
        destination=data['destination'],
        departure_date=data['departure'],
        arrival_date=data['arrival']
        )
    count = search_cargo_count(
        cargo_no=data['cargo_number'],
        truck=data['truck'],
        origin=data['origin'],
        destination=data['destination'],
        departure_date=data['departure'],
        arrival_date=data['arrival']
        )
    return jsonify(
        count = count,
        template = flask.render_template('cargo_result.html',cargo=result)
        )


@app.route('/reports/search',methods=['GET','POST'])
def search_from_reports():
    data = flask.request.args.to_dict()
    result = search_report(
        name=data['name'],
        report_type=data['type'],
        generated_by=data['staff'],
        date=data['date']
        )
    count = search_report_count(
        name=data['name'],
        report_type=data['type'],
        generated_by=data['staff'],
        date=data['date']
        )
    return jsonify(
        count = count,
        template = flask.render_template('reports_result.html',reports=result)
        )


@app.route('/history/search',methods=['GET','POST'])
def search_from_history():
    data = flask.request.args.to_dict()
    result = search_history(
        waybill_no=data['history_no'],
        waybill_type=data['history_type'],
        recipient=data['recipient'],
        total=data['amount'],
        payment_date=data['payment_date']
        )
    count = search_history_count(
        waybill_no=data['history_no'],
        waybill_type=data['history_type'],
        recipient=data['recipient'],
        total=data['amount'],
        payment_date=data['payment_date']
        )
    return jsonify(
        count = count,
        template = flask.render_template('history_result.html',history=result)
        )


@app.route('/users/search',methods=['GET','POST'])
def search_from_users():
    data = flask.request.args.to_dict()
    result = search_user(
        name=data['name'],
        role=data['role'],
        email=data['email']
        )
    count = search_user_count(
        name=data['name'],
        role=data['role'],
        email=data['email']
        )
    return jsonify(
        count = count,
        template = flask.render_template('users_result.html',users=result)
        )


@app.route('/contacts/groups/search',methods=['GET','POST'])
def search_group_recipients():
    group_name = flask.request.form.get('group_name')
    selected_groups = flask.request.form.getlist('group_recipients[]')
    groups = Group.query.filter(Group.name.ilike('%'+group_name+'%')).order_by(Group.name)
    return flask.render_template('group_recipients_result.html',groups=groups,selected_groups=selected_groups)


@app.route('/contacts/indiv/search',methods=['GET','POST'])
def search_indiv_recipients():
    name = flask.request.form.get('name')
    selected_contacts = flask.request.form.getlist('individual_recipients[]')
    contacts = Contact.query.filter(Contact.name.ilike('%'+name+'%')).order_by(Contact.name)
    return flask.render_template('indiv_recipients_result.html',contacts=contacts, selected_contacts=selected_contacts)


@app.route('/inbound/delete',methods=['GET','POST'])
def delete_inbound():
    conversation_ids = flask.request.form.getlist('selected_inbound[]')
    for conversation_id in conversation_ids:
        conversation = Package.query.filter_by(client_no=session['client_no'],id=conversation_id).first()
        db.session.delete(conversation)
        db.session.commit()
    return jsonify(status='success'),201


@app.route('/blasts/delete',methods=['GET','POST'])
def delete_blasts():
    blast_ids = flask.request.form.getlist('selected_blasts[]')
    for blast_id in blast_ids:
        blast = Batch.query.filter_by(client_no=session['client_no'],id=blast_id).first()
        db.session.delete(blast)
        db.session.commit()
    return jsonify(status='success'),201


@app.route('/reminders/delete',methods=['GET','POST'])
def delete_reminders():
    reminder_ids = flask.request.form.getlist('selected_reminders[]')
    for reminder_id in reminder_ids:
        reminder_batch = ReminderBatch.query.filter_by(client_no=session['client_no'],id=reminder_id).first()
        db.session.delete(reminder_batch)
        db.session.commit()
    return jsonify(status='success'),201


@app.route('/contacts/delete',methods=['GET','POST'])
def delete_contacts():
    contact_ids = flask.request.form.getlist('selected_contacts[]')
    for contact_id in contact_ids:
        contact = Contact.query.filter_by(client_no=session['client_no'],id=contact_id).first()
        db.session.delete(contact)
        db.session.commit()
    return jsonify(status='success'),201


@app.route('/groups/delete',methods=['GET','POST'])
def delete_groups():
    group_ids = flask.request.form.getlist('selected_groups[]')
    for group_id in group_ids:
        group = Group.query.filter_by(client_no=session['client_no'],id=group_id).first()
        db.session.delete(group)
        db.session.commit()
    return jsonify(status='success'),201


@app.route('/recipients/number/add',methods=['GET','POST'])
def add_number_recipient():
    recipient = flask.request.form.get('recipient')
    session['number_recipients'].append(recipient)
    return flask.render_template('number_recipients.html',recipient=recipient)


@app.route('/recipients/group/add',methods=['GET','POST'])
def add_group_recipient():
    recipient_id = flask.request.form.get('recipient_id')
    session['group_recipients'].append(recipient_id)
    group = Group.query.filter_by(client_no=session['client_no'],id=recipient_id).first()
    session['group_recipients_name'].append(group.name)
    return jsonify(
        size = group.size,
        template = flask.render_template('group_recipients.html', group=group)
        )


@app.route('/recipients/group/remove',methods=['GET','POST'])
def remove_group_recipient():
    recipient_id = flask.request.form.get('recipient_id')
    session['group_recipients'].remove(recipient_id)
    group = Group.query.filter_by(client_no=session['client_no'],id=recipient_id).first()
    session['group_recipients_name'].remove(group.name)
    return jsonify(
        size = group.size
        )

@app.route('/recipients/individual/add',methods=['GET','POST'])
def add_individual_recipient():
    recipient_id = flask.request.form.get('recipient_id')
    session['individual_recipients'].append(recipient_id)
    recipient = Contact.query.filter_by(client_no=session['client_no'],id=recipient_id).first()
    session['individual_recipients_name'].append(recipient.name)
    return jsonify(
        template = flask.render_template('individual_recipients.html', recipient=recipient)
        )


@app.route('/recipients/individual/remove',methods=['GET','POST'])
def remove_individual_recipient():
    recipient_id = flask.request.form.get('recipient_id')
    session['individual_recipients'].remove(recipient_id)
    recipient = Contact.query.filter_by(client_no=session['client_no'],id=recipient_id).first()
    session['individual_recipients_name'].remove(recipient.name)
    return '',201


@app.route('/recipients/number/remove',methods=['GET','POST'])
def remove_number_recipient():
    msisdn = flask.request.form.get('msisdn')
    session['number_recipients'].remove(msisdn)
    return '',201


@app.route('/recipients/special/add',methods=['GET','POST'])
def add_special_recipient():
    session['group_recipients'] = []
    session['individual_recipients'] = []
    session['group_recipients_name'] = []
    session['individual_recipients_name'] = []
    return jsonify(
        size = len(session['number_recipients'])
        ),201


@app.route('/waybill/item/save',methods=['GET','POST'])
def save_waybill_item():
    data = flask.request.form.to_dict()
    waybill_id = str(uuid.uuid4().fields[-1])[:5]
    if session['waybill_items'] == []:
        session['waybill_items'] = [{
            'id':waybill_id,
            'name':data['name'].title(),
            'quantity':data['quantity'],
            'unit':data['unit'].title(),
            'price':data['price'],
            'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        }]
    else:
        session['waybill_items'].append({
                'id':waybill_id,
                'name':data['name'].title(),
                'quantity':data['quantity'],
                'unit':data['unit'].title(),
                'price':data['price'],
                'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            })
    total = sum(float(item['price']) for item in session['waybill_items'])
    return jsonify(
        template=flask.render_template(
            'waybill_item.html',
            id=waybill_id,
            name=data['name'].title(),
            quantity=data['quantity'],
            unit=data['unit'].title(),
            price=data['price']
            ),
        total=total,
        item_count=len(session['waybill_items'])
        )


@app.route('/cargo/item/add',methods=['GET','POST'])
def add_cargo_item():
    waybill_no = flask.request.form.get('waybill_no')
    waybill = Package.query.filter_by(waybill_no=waybill_no,status='Pending').first()
    if not waybill or waybill == None:
        return jsonify(
                status='failed',
                message='Waybill not found.'
                )

    if session['cargo_items'] == []:
        session['cargo_items'] = [{
            'id':waybill.id,
            'waybill_no':waybill_no,
            'waybill_type':waybill.waybill_type,
            'destination':waybill.destination,
            'recipient':waybill.recipient
        }]
    else:
        for item in session['cargo_items']:
            if item['waybill_no'] == waybill_no:
                return jsonify(
                    status='failed',
                    message='Waybill no. %s is already added in the list.' % waybill.waybill_no
                    )
        session['cargo_items'].append({
            'id':waybill.id,
            'waybill_no':waybill_no,
            'waybill_type':waybill.waybill_type,
            'destination':waybill.destination,
            'recipient':waybill.recipient
        })
    
    return jsonify(
        status='success',
        template=flask.render_template(
            'cargo_item.html',
            waybill=waybill,
            ),
        item_count=len(session['cargo_items']),
        waybill_id=waybill.id
        )


@app.route('/cargo/items',methods=['GET','POST'])
def get_cargo_items():
    return jsonify(
        template=flask.render_template('cargo_items.html',cargo_items=session['cargo_items']),
        item_count=len(session['cargo_items'])
        )


@app.route('/cargo/items/receive',methods=['GET','POST'])
def receive_cargo_items():
    data = flask.request.form.to_dict()
    cargo = Cargo.query.filter_by(id=session['cargo_id']).first()
    cargo.arrival_date = data['date']
    cargo.arrival_time = data['time']
    cargo.received_by_id = session['user_id']
    cargo.received_by = session['user_name']
    db.session.commit()

    batch = ArrivalBatch(
        client_no=session['client_no'],
        cargo_id=cargo.id,
        cargo_no=cargo.cargo_no,
        date=datetime.datetime.now().strftime('%B %d, %Y'),
        time=time.strftime("%I:%M%p"),
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    db.session.add(batch)
    db.session.commit()

    cargo_waybills = CargoItem.query.filter_by(cargo_id=cargo.id).distinct(CargoItem.waybill_no).all()

    for cargo_waybill in cargo_waybills:
        waybill = Package.query.filter_by(waybill_no=cargo_waybill.waybill_no).first()
        waybill.status = 'Arrived'
        waybill.arrival_date = cargo.arrival_date
        waybill.arrival_time = cargo.arrival_time
        waybill.received_by_id = cargo.received_by_id
        waybill.received_by = cargo.received_by

        existing = ArrivalNotification.query.filter_by(waybill_no=cargo_waybill.waybill_no).first()
        if not existing or existing == None:
            notification = ArrivalNotification(
                client_no=session['client_no'],
                batch_id=batch.id,
                cargo_id=cargo.id,
                cargo_no=cargo.cargo_no,
                waybill_no=waybill.waybill_no,
                notification_type='Arrived',
                recipient_msisdn=waybill.recipient_msisdn,
                sender_msisdn=waybill.sender_msisdn
                )
            db.session.add(notification)

    db.session.commit()
    batch_size = ArrivalNotification.query.filter_by(batch_id=batch.id).count()
    batch.batch_size = batch_size
    batch.pending = batch_size
    db.session.commit()

    send_arrival_notifications.delay(session['client_no'],batch.id)

    cargo_items = CargoItem.query.filter_by(cargo_id=session['cargo_id']).order_by(CargoItem.created_at)
    item_count = CargoItem.query.filter_by(cargo_id=session['cargo_id']).count()
    user = AdminUser.query.filter_by(id=session['user_id']).first()
    return jsonify(
        template = flask.render_template(
            'cargo_info.html',
            cargo=cargo,
            cargo_items=cargo_items,
            item_count=item_count,
            user_role=user.role),
        user_role = user.role,
        cargo_id = cargo.id,
        arrival_date = cargo.arrival_date,
        pending=batch.pending,
        batch_id=batch.id,
        overlay_template=flask.render_template('blast_status.html', batch=batch)
        )


@app.route('/cargo/item/delete',methods=['GET','POST'])
def delete_cargo_item():
    waybill_no = flask.request.form.get('waybill_no')
    for item in session['cargo_items']:
        if item['waybill_no'] == waybill_no:
            session['cargo_items'].remove(item)
    return jsonify(status='success',item_count=len(session['cargo_items']),)


@app.route('/cargo/items/save',methods=['GET','POST'])
def save_cargo_items():
    session['cargo_waybill_items'] = []
    for waybill_item in session['cargo_items']:
        waybill = Package.query.filter_by(waybill_no=waybill_item['waybill_no']).first()
        waybill_items = PackageItem.query.filter_by(waybill_id=waybill.id).all()
        item_count = PackageItem.query.filter_by(waybill_id=waybill.id).count()
        for item in waybill_items:
            session['cargo_waybill_items'].append({
                'waybill_no':item.waybill_no,
                'item':item.item,
                'quantity':item.quantity,
                'unit':item.unit,
                'recipient':waybill.recipient,
                })
    return jsonify(
        template=flask.render_template('cargo_waybill_items.html',cargo_items=session['cargo_waybill_items']),
        item_count=len(session['cargo_waybill_items'])
        )


@app.route('/waybill/save',methods=['GET','POST'])
def save_waybill():
    data = flask.request.form.to_dict()
    existing = Package.query.filter_by(waybill_no=data['waybill_number']).first()
    if existing or existing != None:
        return jsonify(
            status='failed',
            message='Waybill number %s already exists.' % data['waybill_number']
            )
    waybill = Package(
        client_no=session['client_no'],
        waybill_no=data['waybill_number'],
        waybill_type=data['waybill_type'].title(),
        origin='Manila',
        destination=data['destination'].title(),
        sender=data['shipper'].title(),
        sender_msisdn=data['shipper_msisdn'],
        recipient=data['recipient'].title(),
        recipient_address=data['recipient_address'].title(),
        recipient_msisdn=data['recipient_msisdn'],
        date_received=data['date'],
        time_received=time.strftime("%I:%M%p"),
        total=data['total'],
        tendered=data['tendered'],
        change=data['change'],
        date_created=datetime.datetime.now().strftime('%B %d, %Y'),
        time_created=time.strftime("%I:%M%p"),
        created_by_id=session['user_id'],
        created_by=session['user_name'],
        notes=data['notes'],
        payment_date=data['date'],
        payment_received_by_id=session['user_id'],
        payment_received_by=session['user_name'],
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )
    db.session.add(waybill)
    db.session.commit()

    for item in session['waybill_items']:
        waybill_item = PackageItem(
            client_no=session['client_no'],
            waybill_id=waybill.id,
            waybill_no=waybill.waybill_no,
            item=item['name'],
            quantity=item['quantity'],
            unit=item['unit'],
            price=item['price'],
            created_at=item['created_at']
            )
        db.session.add(waybill_item)
    db.session.commit()

    session['waybill_items'] = []

    total_entries = Package.query.filter_by(client_no=session['client_no']).count()
    packages = Package.query.filter(Package.client_no==session['client_no'], Package.status!='Done').order_by(Package.created_at.desc()).slice(session['inbound_limit'] - 50, session['inbound_limit'])
    
    prev_btn = 'enabled'
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn ='disabled'
    else:
        diff = total_entries - (session['inbound_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['inbound_limit'] - 49),str(session['inbound_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['inbound_limit'] - 49),str((session['inbound_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    send_notification.delay(session['client_no'],waybill.status,waybill.waybill_no,waybill.sender_msisdn)
    send_notification.delay(session['client_no'],waybill.status,waybill.waybill_no,waybill.recipient_msisdn)

    return jsonify(
        status='success',
        template=flask.render_template(
            'inbound.html',
            packages=packages,
            showing=showing,
            total_entries=total_entries,
            prev_btn=prev_btn,
            next_btn=next_btn,
            )
    )


@app.route('/cargo/save',methods=['GET','POST'])
def save_cargo():
    data = flask.request.form.to_dict()
    existing = Cargo.query.filter_by(cargo_no=data['cargo_number']).first()
    if existing or existing != None:
        return jsonify(
            status='failed',
            message='Cargo no. %s already exists.' % data['cargo_number']
            )      

    cargo = Cargo(
        client_no=session['client_no'],
        cargo_no=data['cargo_number'],
        truck=data['truck'],
        driver=data['driver'].title(),
        crew=data['crew'].title(),
        origin=data['origin'].title(),
        destination=data['destination'].title(),
        departure_date=data['departure_date'],
        departure_time=data['departure_time'],
        date_created=datetime.datetime.now().strftime('%B %d, %Y'),
        time_created=time.strftime("%I:%M%p"),
        created_by_id=session['user_id'],
        created_by=session['user_name'],
        notes=data['notes'],
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    db.session.add(cargo)
    db.session.commit()

    for item in session['cargo_waybill_items']:
        waybill = Package.query.filter_by(waybill_no=item['waybill_no']).first()
        waybill.status='En Route'
        waybill.cargo_no=cargo.cargo_no
        waybill.truck=cargo.truck
        waybill.departure_date=cargo.departure_date
        waybill.departure_time=cargo.departure_time
        db.session.commit()
        cargo_item = CargoItem(
            client_no=session['client_no'],
            cargo_id=cargo.id,
            cargo_no=cargo.cargo_no,
            waybill_no=item['waybill_no'],
            recipient=item['recipient'],
            item=item['item'],
            quantity=item['quantity'],
            unit=item['unit'],
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
        db.session.add(cargo_item)
    db.session.commit()

    total_entries = Cargo.query.filter_by(client_no=session['client_no']).count()
    cargo = Cargo.query.filter_by(client_no=session['client_no']).order_by(Cargo.created_at.desc()).slice(session['cargo_limit'] - 50, session['cargo_limit'])
    prev_btn = 'enabled'
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['cargo_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['cargo_limit'] - 49),str(session['cargo_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['cargo_limit'] - 49),str((session['cargo_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return jsonify(
        status='success',
        template = flask.render_template(
                'cargo.html',
                cargo=cargo,
                showing=showing,
                total_entries=total_entries,
                prev_btn=prev_btn,
                next_btn=next_btn,
            )
        )


@app.route('/waybill/item/remove',methods=['GET','POST'])
def remove_waybill_item():
    item_id = flask.request.form.get('item_id')
    for item in session['waybill_items']:
        if item['id'] == item_id:
            session['waybill_items'].remove(item)
    total = sum(float(item['price']) for item in session['waybill_items'])
    return jsonify(
        status='success',
        total=total,
        item_count=len(session['waybill_items'])
        ),201


@app.route('/waybill/payment/add',methods=['GET','POST'])
def add_waybill_payment():
    data = flask.request.form.to_dict()
    waybill = Package.query.filter_by(id=session['waybill_id']).first()
    waybill.tendered = data['tendered']
    waybill.change = data['change']
    waybill.payment_date = data['date']
    waybill.payment_received_by_id = session['user_id']
    waybill.payment_received_by = session['user_name']
    db.session.commit()

    waybill_items = PackageItem.query.filter_by(waybill_id=waybill.id).order_by(PackageItem.created_at)
    item_count = PackageItem.query.filter_by(waybill_id=waybill.id).count()
    user = AdminUser.query.filter_by(id=session['user_id']).first()
    return jsonify(
        template = flask.render_template(
            'waybill_info.html',
            waybill=waybill,
            item_count=item_count,
            waybill_items=waybill_items,
            user_role=user.role),
        user_role = user.role
        )


@app.route('/waybill/item/edit/remove',methods=['GET','POST'])
def remove_waybill_item_edit():
    item_id = flask.request.form.get('item_id')
    waybill = Package.query.filter_by(id=session['waybill_id']).first()
    waybill_item = PackageItem.query.filter_by(id=item_id).first()
    
    waybill.total = int(waybill.total) - int(waybill_item.price)
    
    if waybill.waybill_type == 'Cash':
        waybill.change = int(waybill.tendered) - int(waybill.total)
    else:
        waybill.change = 0

    db.session.delete(waybill_item)
    db.session.commit()

    return jsonify(
        status='success',
        total=waybill.total,
        change=waybill.change
        ),201


@app.route('/waybill',methods=['GET','POST'])
def open_waybill():
    session['waybill_id'] = flask.request.args.get('waybill_id')
    waybill = Package.query.filter_by(id=session['waybill_id']).first()
    waybill_items = PackageItem.query.filter_by(waybill_id=session['waybill_id']).order_by(PackageItem.created_at)
    item_count = PackageItem.query.filter_by(waybill_id=session['waybill_id']).count()
    user = AdminUser.query.filter_by(id=session['user_id']).first()
    return jsonify(
        template = flask.render_template(
            'waybill_info.html',
            waybill=waybill,
            item_count=item_count,
            waybill_items=waybill_items,
            user_role=user.role),
        user_role = user.role
        )


@app.route('/cargo',methods=['GET','POST'])
def open_cargo():
    session['cargo_id'] = flask.request.args.get('cargo_id')
    cargo = Cargo.query.filter_by(id=session['cargo_id']).first()
    cargo_items = CargoItem.query.filter_by(cargo_id=session['cargo_id']).order_by(CargoItem.created_at)
    item_count = CargoItem.query.filter_by(cargo_id=session['cargo_id']).count()
    user = AdminUser.query.filter_by(id=session['user_id']).first()
    return jsonify(
        template = flask.render_template(
            'cargo_info.html',
            cargo=cargo,
            cargo_items=cargo_items,
            item_count=item_count,
            user_role=user.role),
        user_role = user.role
        )


@app.route('/waybill/item/clear',methods=['GET','POST'])
def clear_waybill_items():
    session['waybill_items'] = []
    return jsonify(status='success'),201


@app.route('/cargo/item/clear',methods=['GET','POST'])
def clear_cargo_items():
    session['cargo_items'] = []
    session['cargo_waybill_items'] = []
    return jsonify(status='success'),201


@app.route('/cargo/truck',methods=['GET','POST'])
def get_cargo_number():
    start = datetime.datetime.now().strftime('%B 01, %Y')
    end = datetime.datetime.now().strftime('%B 31, %Y')
    cargo_count = Cargo.query.filter(Cargo.departure_date >= start).filter(Cargo.departure_date <= end).count()
    cargo_number = '%s-%s' % (datetime.datetime.now().strftime('%m%Y'), cargo_count+1)
    return jsonify(status='success',cargo_number=cargo_number)


@app.route('/date',methods=['GET','POST'])
def supply_date():
    return jsonify(
        date = datetime.datetime.now().strftime('%B %d, %Y')
        )

@app.route('/report/cargo/print',methods=['GET','POST'])
def print_cargo_report():
    cargo = Cargo.query.filter_by(id=session['cargo_id']).first()
    cargo_items = CargoItem.query.filter_by(cargo_id=cargo.id).all()
    report = Report(
        client_no=session['client_no'],
        name='[Packing List] %s' % cargo.cargo_no,
        report_type='Packing List',
        generated_by=session['user_name'],
        generated_by_id=session['user_id'],
        date=datetime.datetime.now().strftime('%B %d, %Y'),
        time=time.strftime("%I:%M%p"),
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )
    db.session.add(report)
    db.session.commit()

    try:
        create_pdf.delay(
            report.id,
            flask.render_template(
                'print_cargo.html',
                report=report,
                cargo=cargo,
                cargo_items=cargo_items,
                staff_name=session['user_name'],
                date=report.date,
                time=report.time
                )
            )
        return jsonify(
            status='success',
            template=flask.render_template('download_item.html',report=report),
            report_id=report.id
            )

    except requests.exceptions.ConnectionError as e:
        report.status = 'failed'
        db.session.commit()
        return jsonify(status='failed',message='Could not generate report. Please Contact support.'),201


@app.route('/report/master/print',methods=['GET','POST'])
def print_master_list():
    cargo = Cargo.query.filter_by(id=session['cargo_id']).first()
    waybills = Package.query.filter_by(cargo_no=cargo.cargo_no).all()
    report = Report(
        client_no=session['client_no'],
        name='[Master List] %s' % cargo.cargo_no,
        report_type='Master List',
        generated_by=session['user_name'],
        generated_by_id=session['user_id'],
        date=datetime.datetime.now().strftime('%B %d, %Y'),
        time=time.strftime("%I:%M%p"),
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )
    db.session.add(report)
    db.session.commit()

    try:
        create_pdf.delay(
            report.id,
            flask.render_template(
                'print_master_list.html',
                report=report,
                cargo=cargo,
                waybills=waybills,
                staff_name=session['user_name'],
                date=report.date,
                time=report.time
                )
            )
        return jsonify(
            status='success',
            template=flask.render_template('download_item.html',report=report),
            report_id=report.id
            )

    except requests.exceptions.ConnectionError as e:
        report.status = 'failed'
        db.session.commit()
        return jsonify(status='failed',message='Could not generate report. Please Contact support.'),201


@app.route('/report/save',methods=['GET','POST'])
def generate_report():
    data = flask.request.form.to_dict()

    if data['report_type'] == 'Master List':
        cargo = Cargo.query.filter_by(cargo_no=data['cargo_no']).first()
        if not cargo or cargo == None:
            return jsonify(
                status='failed',
                message='Invalid cargo number.'
                )

        report = Report(
            client_no=session['client_no'],
            report_type=data['report_type'],
            generated_by=session['user_name'],
            generated_by_id=session['user_id'],
            date=datetime.datetime.now().strftime('%B %d, %Y'),
            time=time.strftime("%I:%M%p"),
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
        db.session.add(report)
        db.session.commit()

        waybills = Package.query.filter_by(cargo_no=cargo.cargo_no).all()
        report.name = '[Master List] %s' % cargo.cargo_no
        db.session.commit()
        report_template = flask.render_template(
            'print_master_list.html',
            report=report,
            cargo=cargo,
            waybills=waybills,
            staff_name=session['user_name'],
            date=report.date,
            time=report.time
            )

    elif data['report_type'] == 'Packing List':
        cargo = Cargo.query.filter_by(cargo_no=data['cargo_no']).first()
        if not cargo or cargo == None:
            return jsonify(
                status='failed',
                message='Invalid cargo number.'
                )

        report = Report(
            client_no=session['client_no'],
            report_type=data['report_type'],
            generated_by=session['user_name'],
            generated_by_id=session['user_id'],
            date=datetime.datetime.now().strftime('%B %d, %Y'),
            time=time.strftime("%I:%M%p"),
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
        db.session.add(report)
        db.session.commit()

        cargo_items = CargoItem.query.filter_by(cargo_id=cargo.id).all()
        report.name = '[Packing List] %s' % cargo.cargo_no
        db.session.commit()
        report_template = flask.render_template(
            'print_cargo.html',
            report=report,
            cargo=cargo,
            cargo_items=cargo_items,
            staff_name=session['user_name'],
            date=report.date,
            time=report.time
            )

    elif data['report_type'] == 'Sales Report':

        report = Report(
            client_no=session['client_no'],
            report_type=data['report_type'],
            generated_by=session['user_name'],
            generated_by_id=session['user_id'],
            date=datetime.datetime.now().strftime('%B %d, %Y'),
            time=time.strftime("%I:%M%p"),
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
        db.session.add(report)
        db.session.commit()

        if data['to_date'] == None or data['to_date'] == '':
            waybills = Package.query.filter_by(payment_date=data['from_date']).all()
            report.name = '[Sales Report] %s' % data['from_date']
        else:
            waybills = Package.query.filter(Package.payment_date >= data['from_date']).filter(Package.payment_date <= data['to_date']).order_by(Package.payment_date)
            report.name = '[Sales Report] %s - %s' % (data['from_date'],data['to_date'])
        db.session.commit()
        total_sales = sum(int(waybill.total) for waybill in waybills)
        report_template = flask.render_template(
            'print_sales_report.html',
            report=report,
            waybills=waybills,
            from_date=data['from_date'],
            to_date=data['to_date'],
            total_sales=total_sales,
            staff_name=session['user_name'],
            date=report.date,
            time=report.time
            )

    try:
        create_pdf.delay(report.id, report_template)

        prev_btn = 'enabled'
        total_entries = Report.query.filter_by(client_no=session['client_no']).count()
        reports = Report.query.filter_by(client_no=session['client_no']).order_by(Report.created_at.desc()).slice(session['report_limit'] - 50, session['report_limit'])
        if total_entries < 50:
            showing='1 - %s' % total_entries
            prev_btn = 'disabled'
            next_btn='disabled'
        else:
            diff = total_entries - (session['report_limit'] - 50)
            if diff > 50:
                showing = '%s - %s' % (str(session['report_limit'] - 49),str(session['report_limit']))
                next_btn='enabled'
            else:
                showing = '%s - %s' % (str(session['report_limit'] - 49),str((session['report_limit']-50)+diff))
                prev_btn = 'enabled'
                next_btn='disabled'

        return jsonify(
            status='success',
            download_template=flask.render_template('download_item.html',report=report),
            report_id=report.id,
            content_template=flask.render_template(
                    'reports.html',
                    reports=reports,
                    showing=showing,
                    total_entries=total_entries,
                    prev_btn=prev_btn,
                    next_btn=next_btn,
                )
            )

    except requests.exceptions.ConnectionError as e:
        report.status = 'failed'
        db.session.commit()
        return jsonify(status='failed',message='Could not generate report. Please Contact support.'),201


@app.route('/waybill/pickup',methods=['GET','POST'])
def pickup_waybill():
    data = flask.request.form.to_dict()
    waybill = Package.query.filter_by(id=session['waybill_id']).first()
    waybill.status = 'Done'
    waybill.pickup_name = data['name']
    waybill.pickup_date = data['date']
    waybill.pickup_time = data['time']
    waybill.pickup_type = data['type']
    waybill.turned_over_by_id = session['user_id']
    waybill.turned_over_by = session['user_name']
    db.session.commit()

    send_notification.delay(session['client_no'],waybill.status,waybill.waybill_no,waybill.sender_msisdn)
    send_notification.delay(session['client_no'],waybill.status,waybill.waybill_no,waybill.recipient_msisdn)
    
    session['inbound_limit'] = 50
    prev_btn = 'disabled'
    total_entries = Package.query.filter(Package.client_no==session['client_no'], Package.status!='Done').count()
    packages = Package.query.filter(Package.client_no==session['client_no'], Package.status!='Done').order_by(Package.created_at.desc()).slice(session['inbound_limit'] - 50, session['inbound_limit'])
    if total_entries < 50:
        showing='1 - %s' % total_entries
        prev_btn = 'disabled'
        next_btn='disabled'
    else:
        diff = total_entries - (session['inbound_limit'] - 50)
        if diff > 50:
            showing = '%s - %s' % (str(session['inbound_limit'] - 49),str(session['inbound_limit']))
            next_btn='enabled'
        else:
            showing = '%s - %s' % (str(session['inbound_limit'] - 49),str((session['inbound_limit']-50)+diff))
            prev_btn = 'enabled'
            next_btn='disabled'

    return flask.render_template(
        'inbound.html',
        packages=packages,
        showing=showing,
        total_entries=total_entries,
        prev_btn=prev_btn,
        next_btn=next_btn,
    )


@app.route('/report/status',methods=['GET','POST'])
def get_report_status():
    report_id = flask.request.form.get('report_id')
    report = Report.query.filter_by(id=report_id).first()
    return jsonify(
        status='success',
        report_status=report.status
        )


@app.route('/db/rebuild',methods=['GET','POST'])
def rebuild_database():
    db.drop_all()
    db.create_all()

    client = Client(
        client_no='infinitrix',
        name='Infinitrix, Inc.',
        app_id='EGXMuB5eEgCMLTKxExieqkCGeGeGuBon',
        app_secret='f3e1ab30e23ea7a58105f058318785ae236378d1d9ebac58fe8b42e1e239e1c3',
        passphrase='24BUubukMQ',
        shortcode='21588479',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    user = AdminUser(
        client_no='infinitrix',
        email='jasper@pisara.tech',
        password='ratmaxi8',
        name='Jasper Barcelona',
        role='Administrator',
        join_date=datetime.datetime.now().strftime('%B %d, %Y'),
        created_at=datetime.datetime.now().strftime('%Y-%m`-%d %H:%M:%S:%f')
        )

    package = Package(
        client_no='infinitrix',
        waybill_no='1234',
        waybill_type='Charge',
        origin='Manila',
        destination='Sorsogon',
        sender='John Doe',
        sender_msisdn='09279604172',
        recipient='Jasper Barcelona',
        recipient_address='Maharlika',
        recipient_msisdn='09176214704',
        date_received=datetime.datetime.now().strftime('%B %d, %Y'),
        time_received=time.strftime("%I:%M%p"),
        total='1200',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f'),
        date_created=datetime.datetime.now().strftime('%B %d, %Y'),
        time_created=time.strftime("%I:%M%p"),
        notes='This is a sample note.',
        created_by_id=1,
        created_by='Jasper Barcelona',
        arrival_date=datetime.datetime.now().strftime('%B %d, %Y'),
        arrival_time=time.strftime("%I:%M%p"),
        departure_date=datetime.datetime.now().strftime('%B %d, %Y'),
        departure_time=time.strftime("%I:%M%p"),
        cargo_no='052018-23',
        truck='UUE-918',
        received_by_id=1,
        received_by='Jasper Barcelona',
        turned_over_by_id=1,
        turned_over_by='Jasper Barcelona',
        pickup_name='Jasper Barcelona',
        pickup_date=datetime.datetime.now().strftime('%B %d, %Y'),
        pickup_time=time.strftime("%I:%M%p")
        )

    package1 = Package(
        client_no='infinitrix',
        waybill_no='4321',
        waybill_type='Cash',
        origin='Manila',
        destination='Legazpi',
        sender='Kretz Dy',
        sender_msisdn='09279604172',
        recipient='Merto Isuzu',
        recipient_address='Maharlika',
        recipient_msisdn='09176214704',
        date_received=datetime.datetime.now().strftime('%B %d, %Y'),
        time_received=time.strftime("%I:%M%p"),
        total='1800',
        tendered='2000',
        change='200',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f'),
        date_created=datetime.datetime.now().strftime('%B %d, %Y'),
        time_created=time.strftime("%I:%M%p"),
        payment_date='May 03, 2018',
        payment_received_by_id=1,
        payment_received_by='Jasper Barcelona',
        created_by_id=1,
        created_by='Jasper Barcelona',
        arrival_date=datetime.datetime.now().strftime('%B %d, %Y'),
        arrival_time=time.strftime("%I:%M%p"),
        departure_date=datetime.datetime.now().strftime('%B %d, %Y'),
        departure_time=time.strftime("%I:%M%p"),
        cargo_no='052018-23',
        truck='UUE-918',
        received_by_id=1,
        received_by='Jasper Barcelona',
        turned_over_by_id=1,
        turned_over_by='Jasper Barcelona',
        pickup_name='Merto Isuzu',
        pickup_date=datetime.datetime.now().strftime('%B %d, %Y'),
        pickup_time=time.strftime("%I:%M%p")
        )

    package2 = Package(
        client_no='infinitrix',
        waybill_no='5678',
        waybill_type='Cash',
        origin='Manila',
        destination='Legazpi',
        sender='Lebron James',
        sender_msisdn='092796041',
        recipient='Kobe Byrant',
        recipient_address='Maharlika',
        recipient_msisdn='09176214704',
        date_received=datetime.datetime.now().strftime('%B %d, %Y'),
        time_received=time.strftime("%I:%M%p"),
        total='1200',
        tendered='2000',
        change='800',
        status='Done',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f'),
        date_created=datetime.datetime.now().strftime('%B %d, %Y'),
        time_created=time.strftime("%I:%M%p"),
        payment_date='May 03, 2018',
        payment_received_by_id=1,
        payment_received_by='Jasper Barcelona',
        created_by_id=1,
        created_by='Jasper Barcelona',
        arrival_date=datetime.datetime.now().strftime('%B %d, %Y'),
        arrival_time=time.strftime("%I:%M%p"),
        departure_date=datetime.datetime.now().strftime('%B %d, %Y'),
        departure_time=time.strftime("%I:%M%p"),
        cargo_no='052018-23',
        truck='UUE-918',
        received_by_id=1,
        received_by='Jasper Barcelona',
        turned_over_by_id=1,
        turned_over_by='Jasper Barcelona',
        pickup_type='Delivery',
        pickup_name='Kobe Bryant',
        pickup_date=datetime.datetime.now().strftime('%B %d, %Y'),
        pickup_time=time.strftime("%I:%M%p")
        )

    for i in range(50):
        package_loop = Package(
            client_no='infinitrix',
            waybill_no='5678%s'%str(i),
            waybill_type='Cash',
            origin='Manila',
            destination='Legazpi',
            sender='Lebron James',
            sender_msisdn='092796041',
            recipient='John Doe',
            recipient_address='Maharlika',
            recipient_msisdn='09176214704',
            date_received=datetime.datetime.now().strftime('%B %d, %Y'),
            time_received=time.strftime("%I:%M%p"),
            total='1200',
            tendered='2000',
            change='800',
            status='Done',
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f'),
            date_created=datetime.datetime.now().strftime('%B %d, %Y'),
            time_created=time.strftime("%I:%M%p"),
            payment_date=datetime.datetime.now().strftime('%B %d, %Y'),
            payment_received_by_id=1,
            payment_received_by='Jasper Barcelona',
            created_by_id=1,
            created_by='Jasper Barcelona',
            arrival_date=datetime.datetime.now().strftime('%B %d, %Y'),
            arrival_time=time.strftime("%I:%M%p"),
            departure_date=datetime.datetime.now().strftime('%B %d, %Y'),
            departure_time=time.strftime("%I:%M%p"),
            cargo_no='052018-23',
            truck='UUE-918',
            received_by_id=1,
            received_by='Jasper Barcelona',
            turned_over_by_id=1,
            turned_over_by='Jasper Barcelona',
            pickup_type='Delivery',
            pickup_name='Kobe Bryant',
            pickup_date=datetime.datetime.now().strftime('%B %d, %Y'),
            pickup_time=time.strftime("%I:%M%p")
            )

        db.session.add(package_loop)
        db.session.commit()

    package_item = PackageItem(
        client_no='infinitrix',
        waybill_id=1,
        waybill_no='1234',
        item='Sample Item',
        quantity=3,
        unit='Rolls',
        price='1200',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    package_item1 = PackageItem(
        client_no='infinitrix',
        waybill_id=2,
        waybill_no='4321',
        item='Sample Item 2',
        quantity=4,
        unit='Cartons',
        price='1800',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    package_item2 = PackageItem(
        client_no='infinitrix',
        waybill_id=3,
        waybill_no='5678',
        item='Another Item',
        quantity=3,
        unit='Bundles',
        price='1200',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    cargo = Cargo(
        client_no='infinitrix',
        cargo_no='052018-23',
        truck='UUE-918',
        driver='Delfin Barcelona',
        crew='Some Crew',
        origin='Manila',
        destination='Legazpi',
        departure_date=datetime.datetime.now().strftime('%B %d, %Y'),
        departure_time=time.strftime("%I:%M%p"),
        arrival_date=datetime.datetime.now().strftime('%B %d, %Y'),
        arrival_time=time.strftime("%I:%M%p"),
        date_created=datetime.datetime.now().strftime('%B %d, %Y'),
        time_created=time.strftime("%I:%M%p"),
        created_by_id=1,
        created_by='Jasper Barcelona',
        received_by_id=1,
        received_by='Jasper Barcelona',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    cargo_item = CargoItem(
        client_no='infinitrix',
        cargo_id=1,
        cargo_no='052018-23',
        waybill_no='1234',
        item='Sample Item',
        quantity=3,
        recipient='Jasper Barcelona',
        unit='Rolls',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    cargo_item1 = CargoItem(
        client_no='infinitrix',
        cargo_id=1,
        cargo_no='052018-23',
        waybill_no='4321',
        item='Sample Item 2',
        quantity=4,
        recipient='Merto Isuzu',
        unit='Cartons',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    cargo_item2 = CargoItem(
        client_no='infinitrix',
        cargo_id=1,
        cargo_no='052018-23',
        waybill_no='5678',
        item='Another Item',
        quantity=3,
        recipient='Kobe Byrant',
        unit='Bundles',
        created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        )

    for i in range(100):
        cargo_item_loop = CargoItem(
            client_no='infinitrix',
            cargo_id=1,
            cargo_no='052018-23',
            waybill_no='5678%s'%str(i),
            item='Another Item%s'%str(i),
            quantity=3,
            recipient='Kobe Byrant',
            unit='Bundles',
            created_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            )
        db.session.add(cargo_item_loop)
        db.session.commit()

    db.session.add(client)
    db.session.add(user)
    db.session.add(package)
    db.session.add(package1)
    db.session.add(package2)
    db.session.add(package_item)
    db.session.add(package_item1)
    db.session.add(package_item2)
    db.session.add(cargo)
    db.session.add(cargo_item)
    db.session.add(cargo_item1)
    db.session.add(cargo_item2)
    db.session.commit()

    return jsonify(
        status = 'success'
        ), 201

if __name__ == '__main__':
    app.run(port=5000,debug=True,host='0.0.0.0')
    # port=int(os.environ['PORT']), host='0.0.0.0'