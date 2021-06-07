from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import uuid

DATABASE = MongoClient('localhost', 27017)['coursework']
COMMENTS = DATABASE['comments']
POSTS = DATABASE['posts']
USERS = DATABASE['users']
TAGS = DATABASE['tags']


class Roles:
    admin = 'admin'
    editor = 'editor'
    user = 'user'


class ErrorMessages:
    registered_login = 'This login is already registered!'
    not_exists_login = 'This login does not exist!'
    wrong_password = 'Wrong password!'
    exists_title = 'There is already such a title!'
    rights_create = 'Insufficient rights to create news!'
    not_found_post = 'Post not found!'
    rights_delete = 'Insufficient rights to delete news!'


def register(params):
    """
    Регистрация
    :param params: login, password, name, surname, email, role, session
    :return: session
    """
    request = {
        'success': False,
        'message': ''
    }
    if USERS.find_one({'login': params['login']}):
        request['message'] = ErrorMessages.registered_login
        return request
    params['role'] = Roles.user
    params['password'] = generate_password_hash(params['password'])
    params['session'] = uuid.uuid4()
    USERS.insert_one(params)
    request['success'] = True
    request['session'] = params['session']
    return request


def login(params):
    """
    Авторизация
    :param params: login, password
    :return: session
    """
    request = {
        'success': False,
        'messages': ''
    }
    user = USERS.find_one({'login': params['login']})
    if not user:
        request['messages'] = ErrorMessages.not_exists_login
        return request
    if check_password_hash(user['password'], params['password']):
        new_session = uuid.uuid4()
        USERS.update_one(user, {'$set': {'session': new_session}})
        request['session'] = new_session
        request['success'] = True
        return request
    else:
        request['messages'] = ErrorMessages.wrong_password
        return request


def add_post(params):
    """
    Создать новостной пост
    :param params: photo, title, text, session, tags
    :return: _id
    """
    request = {
        'success': False,
        'messages': ''
    }
    if POSTS.find_one({'title': params['title']}):
        request['messages'] = ErrorMessages.exists_title
        return request
    user_info = USERS.find_one({'session': params['session']})
    if not user_info or (user_info['role'] != Roles.admin and user_info['role'] != Roles.editor):
        request['messages'] = ErrorMessages.rights_create
        return request
    created_tags = TAGS.find({'name': {'$in': params['tags']}})
    tags_to_create = set(params['tags']) - set([tag['name'] for tag in created_tags])
    if tags_to_create:
        TAGS.insert_many([{'name': tag} for tag in tags_to_create])
    tags = TAGS.find({'name': {'$in': params['tags']}})
    post_object = {
        'title': params['title'],
        'text': params['text'],
        'author': user_info['_id'],
        'tags': [tag['_id'] for tag in tags],
        'views': 0,
        'likes': 0,
        'photo': params['photo'],
        'date': datetime.now()
    }
    inserted_id = POSTS.insert_one(post_object).inserted_id
    request['success'] = True
    request['id'] = inserted_id
    return request


def del_post(params):
    """
    Удалить пост
    :param params: id, session
    :return:
    """
    request = {
        'success': False,
        'messages': ''
    }
    if not POSTS.find_one({'_id': ObjectId(params['id'])}):
        request['messages'] = ErrorMessages.not_found_post
        return request
    user_info = USERS.find_one({'session': params['session']})
    if not user_info or (user_info['role'] != Roles.admin and user_info['role'] != Roles.editor):
        request['messages'] = ErrorMessages.rights_delete
        return request
    POSTS.delete_one({'_id': ObjectId(params['id'])})
    request['success'] = True
    return request


if __name__ == '__main__':
    session = uuid.UUID('5e928523-9ed3-40eb-b800-fd7390bc2ea5')
    # params_to_test = {
    #     'login': 'noordan',
    #     'password': '123456',
    #     'name': 'Nikita',
    #     'surname': 'Lukyanov',
    #     'email': 'mail@mail.ru'
    # }
    # print(register(params_to_test))
    # print(login(params_to_test))
    params_to_test = {
        'photo': 'test.jpg',
        'title': 'Проверка заголовка!',
        'text': 'Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printtook a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic.',
        'author': '60be0ff91ef3544110eefc93',
        'tags': ['Web programming', 'Java Script', 'Node JS'],
        'session': session
    }
    print(add_post(params_to_test))
    # print(USERS.find_one({'login': 'noordan'}))
    # print(POSTS.find_one({'_id': ObjectId('60be1f90790b20914fedb1b3')}))
    # params_to_test2 = {
    #     'id': '60be1f90790b20914fedb1b3',
    #     'session': session
    # }
    # print(del_post(params_to_test2))
