from pymongo import MongoClient, DESCENDING, ASCENDING
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


def prepare_to_save_post(params):
    """
    Выполняет проверку на совпадение заголовков, проверку пользователя, досоздает теги
    :param params:
    :return:
    """
    post = POSTS.find_one({'title': params['title']})
    if post and not (params.get('id') and post['_id'] == ObjectId(params['id'])):
        return ErrorMessages.exists_title
    user_info = USERS.find_one({'session': params['session']})
    if not user_info or (user_info['role'] != Roles.admin and user_info['role'] != Roles.editor):
        return ErrorMessages.rights_create
    created_tags = TAGS.find({'name': {'$in': params['tags']}})
    tags_to_create = set(params['tags']) - set([tag['name'] for tag in created_tags])
    if tags_to_create:
        TAGS.insert_many([{'name': tag} for tag in tags_to_create])


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
    message = prepare_to_save_post(params)
    if message:
        request['messages'] = message
        return request
    tags = TAGS.find({'name': {'$in': params['tags']}})
    post_object = {
        'title': params['title'],
        'text': params['text'],
        'author': USERS.find_one({'session': params['session']})['_id'],
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


def read_post(params):
    """
    Прочитать пост
    :param params: id
    :return:
    """
    request = {
        'success': False,
        'messages': ''
    }
    post = POSTS.find_one({'_id': ObjectId(params['id'])})
    if post:
        POSTS.update_one({'_id': ObjectId(params['id'])}, {'$set': {'views': post['views'] + 1}})
        tags = [tag['name'] for tag in TAGS.find({'_id': {'$in': post['tags']}})]
        request['success'] = True
        request.update(post)
        request['views'] += 1
        request['tags'] = tags
        return request
    else:
        request['messages'] = ErrorMessages.not_found_post
        return request


def save_post(params):
    """
    Сохранить пост после редактирования
    :param params: id, photo, title, text, session, tags
    :return: id
    """
    request = {
        'success': False,
        'messages': ''
    }
    post = POSTS.find_one({'_id': ObjectId(params['id'])})
    if post:
        message = prepare_to_save_post(params)
        if message:
            request['messages'] = message
            return request
        tags = TAGS.find({'name': {'$in': params['tags']}})
        post_to_save = {
            'title': params['title'],
            'text': params['text'],
            'tags': [tag['_id'] for tag in tags]
        }
        if params.get('photo'):
            post_to_save['photo'] = params['photo']
        POSTS.update_one({'_id': post['_id']}, {'$set': post_to_save})
        request['success'] = True
        request['id'] = post['_id']
        return request
    else:
        request['messages'] = ErrorMessages.not_found_post
        return request


def registry_posts(params):
    """
    Реестр новостей! С БОГОМ!
    :param params: limit, sort, tags, page
    :return:
    """
    if params['tags']:
        filter_tags = {'tags': {'$in': [ObjectId(tag) for tag in params['tags']]}}
    else:
        filter_tags = {}
    posts = list(POSTS.find(filter_tags).sort(params['sort']).skip((params['page'] - 1) * params['limit']).limit(params['limit']))
    for post in posts:
        post['tags'] = [tag['name'] for tag in TAGS.find({'_id': {'$in': post['tags']}})]
    return posts


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
        'id': '60be2525e3b9049d8df89b49',
        'photo': 'test.jpg',
        'title': 'Проверка заголовка!',
        'text': 'Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industrys standard dummy text ever since the 1500s, when an unknown printtook a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic.',
        'author': '60be0ff91ef3544110eefc93',
        'tags': ['Web programming', 'Java Script', 'Node JS'],
        'session': session
    }
    # print(add_post(params_to_test))
    # print(USERS.find_one({'login': 'noordan'}))
    # print(POSTS.find_one({'_id': ObjectId('60be1f90790b20914fedb1b3')}))
    # params_to_test2 = {
    #     'id': '60be1f90790b20914fedb1b3',
    #     'session': session
    # }
    # print(del_post(params_to_test2))
    # params_to_test2 = {
    #     'id': '60be2525e3b9049d8df89b49'
    # } #limit, sort, tags, page
    params_to_registry = {
        'limit': 5,
        'sort': 'views',
        'tags': ['60be1f90790b20914fedb1b0'],
        'page': 1
    }
    from pprint import pprint
    pprint(registry_posts(params_to_registry))
