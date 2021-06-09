from flask import Flask, request, redirect, url_for, render_template, make_response, jsonify
from werkzeug.utils import secure_filename
from server import (get_user_info, can_edit_news, get_all_tags, read_post, save_post, add_post, get_comments, set_like,
                    is_liked, write_comment, login, delete_comment, del_post, registry_posts, get_all_tags)
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


@app.route('/news_old')
def news_old_route():
    return render_template('news.html')


@app.route('/edit_news_old')
def edit_news_old_route():
    return render_template('edit_news.html')


@app.route('/registration')
def registration_route():
    return render_template('register.html')

# ===========================


@app.route('/edit/<post>')
@app.route('/edit/')
@app.route('/edit')
def edit_news_route(post=None):
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
        'id': post
    }
    user_info = get_user_info(params)
    if user_info:
        if can_edit_news(params):
            params_to_render = {
                'news': read_post(params, stat=False) if post else None,
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


@app.route('/news/<post>')
def news_route(post=None):
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
        'id': post
    }
    if post:
        params_to_render = read_post(params)
        params_to_render['is_editor'] = can_edit_news(params)
        params_to_render['comments'] = get_comments(params)
        params_to_render['is_authorized'] = bool(get_user_info(params))
        params_to_render['is_liked'] = is_liked(params)
        encode_params(params_to_render)
        print(params_to_render)
        return render_template('news.html', **params_to_render)
    else:
        return render_template('news.html')


@app.route('/like', methods=['POST'])
def like_route():
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
    }
    params.update(dict(request.form))
    return set_like(params)


@app.route('/send_comment', methods=['POST'])
def send_comment_route():
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
    }
    params.update(dict(request.form))
    result = write_comment(params)
    result['comments'] = get_comments(params)
    encode_params(result)
    return result


@app.route('/login')
def login_route():
    session = request.cookies.get('session')
    params = {
        'session': session
    }
    if session is not None:
        if not get_user_info(params):
            resp = make_response(redirect(url_for('login_route')))
            resp.set_cookie('session', '', expires=0)
            return resp
        return redirect(url_for('news_route', post='60c055d0a566bd9944e161bb'))
    return render_template('auth.html')


@app.route('/login', methods=['POST'])
def do_login_route():
    params = dict(request.form)
    result = login(params)
    encode_params(result)
    if result['success']:
        resp = make_response(json.dumps(result))
        resp.set_cookie('session', str(result['session']), max_age=60 * 60 * 24 * 365 * 2)
    else:
        resp = make_response(json.dumps(result))
    return resp


@app.route('/delete_comment', methods=['POST'])
def delete_comment_route():
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
    }
    params.update(dict(request.form))
    result = delete_comment(params)
    params['id'] = params['post_id']
    result['comments'] = get_comments(params)
    encode_params(result)
    return make_response(json.dumps(result))


@app.route('/delete', methods=['POST'])
def delete_route():
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
    }
    params.update(dict(request.form))
    result = del_post(params)
    encode_params(result)
    return make_response(result)


@app.route('/news_registry', methods=['POST'])
def news_registry_route():
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
    }
    params.update(dict(request.form))
    params['limit'] = int(params['limit'])
    params['tags'] = [tag for tag in params['tags'].split(',') if tag]
    params['page'] = int(params['page'])
    print(params)
    result = registry_posts(params)
    encode_params(result)
    return make_response(result)


@app.route('/news/')
@app.route('/news')
def all_news_route():
    params = {
        'session': uuid.UUID(request.cookies.get('session')) if request.cookies.get('session') else '',
        'tags': get_all_tags({})
    }
    params['is_authorized'] = bool(get_user_info(params))
    params['is_editor'] = can_edit_news(params)
    encode_params(params)
    return render_template('all_news.html', **params)


if __name__ == '__main__':
    app.run()
