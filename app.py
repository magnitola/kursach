from flask import Flask, request, redirect, url_for, render_template, make_response, jsonify
from werkzeug.utils import secure_filename
from server import get_user_info, can_edit_news, get_all_tags, read_post, save_post, add_post
from bson.objectid import ObjectId
import datetime
import json
import uuid
import os


UPLOAD_FOLDER = './static/loaded'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # if the obj is uuid, we simply return the value of uuid
            return obj.hex
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


def encode_params(params):
    for key, value in params.items():
        params[key] = json.dumps(value, cls=MyEncoder)
        params[key] = json.loads(params[key])


@app.route('/')
def index_route():
    return render_template('index.html')


@app.route('/news')
def news_route():
    return render_template('news.html')


@app.route('/all_news')
def all_news_route():
    return render_template('all_news.html')


@app.route('/edit_news_old')
def edit_news_old_route():
    return render_template('edit_news.html')


@app.route('/login')
def login_route():
    return render_template('auth.html')


@app.route('/registration')
def registration_route():
    return render_template('register.html')

# ===========================


@app.route('/edit_news/<post>')
@app.route('/edit_news/')
@app.route('/edit_news')
def edit_news_route(post=None):
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
        'id': post
    }
    user_info = get_user_info(params)
    if user_info:
        if can_edit_news(params):
            params_to_render = {
                'news': read_post(params) if post else None,
                'all_tags': [tag['name'] for tag in get_all_tags(params)],
                'is_editor': can_edit_news(params)
            }
            encode_params(params_to_render)
            return render_template('edit_news.html', **params_to_render)
        else:
            resp = make_response(redirect(url_for('all_news_route')))
            return resp
    else:
        resp = make_response(redirect(url_for('login_route')))
        resp.set_cookie('session', '', expires=0)
        return resp


@app.route('/save_news', methods=['POST'])
def save_news_route():
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
    }
    params.update(dict(request.form))
    params['tags'] = params['tags'].split(',')
    params['id'] = None if params['id'] == 'null' else params['id']
    params['photo'] = None if params['photo'] == 'null' or params['photo'] == 'undefined' else params['photo']
    print(params)
    # id, photo, title, text, session, tags
    if params['id']:
        result = save_post(params)
    else:
        result = add_post(params)
    encode_params(result)
    return make_response(result)


@app.route('/save_file', methods=['POST'])
def save_file_route():
    if request.files.getlist('file'):
        file = request.files.getlist('file')[0]
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        params = {
            'success': True,
            'filename': filename
        }
        print(params)
    else:
        params = {
            'success': True,
            'filename': None
        }
    return make_response(params)


if __name__ == '__main__':
    app.run()
