from flask import Flask, render_template

app = Flask(__name__)


def return_tag_html(number):
    return f'<li class="list-group-item about" id="li{number}"><span><input type="text" class="form-control-plaintext tag" id="tag{number}"></span></li>'


@app.route('/')
def index_route():
    return render_template('index.html')


@app.route('/news')
def news_route():
    return render_template('news.html')


@app.route('/all_news')
def all_news_route():
    return render_template('all_news.html')


@app.route('/edit_news')
def edit_news_route():
    return render_template('edit_news.html')


@app.route('/login')
def login_route():
    return render_template('auth.html')


@app.route('/registration')
def registration_route():
    return render_template('register.html')


if __name__ == '__main__':
    app.run()
