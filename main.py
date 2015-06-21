# all the imports
import os
import hashlib
import sqlite3
from mutagen.mp3 import MP3
from contextlib import closing
from mutagen.easyid3 import EasyID3
from werkzeug import secure_filename
from flask import Flask, request, g, redirect, url_for, \
    render_template, flash, send_from_directory

# configuration
DATABASE = 'flask.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
UPLOAD_FOLDER = "upload"
BLOCKSIZE = 5192

# Application
app = Flask(__name__)
app.config.from_object(__name__)

music_dir = ""


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


ALLOWED_EXTN = set(["mp3"])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTN


@app.before_request
def before_request():
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


@app.route("/", methods=["GET"])
def queue():
    cur = g.db.execute('select title, album, artist, filename, length from entries')
    rows = cur.fetchall()
    is_serv = request.remote_addr == '127.0.0.1'
    return render_template('index.html', songs=rows, iss=is_serv)


@app.route("/get_songs")
def get_songs():
    cur = g.db.execute('select title, album, artist, filename, length from entries')
    rows = cur.fetchall()
    return render_template('songs.html', songs=rows)


def hash_value(pathname):
    hasher = hashlib.md5()
    with open(pathname, 'rb') as f:
        buf = f.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(BLOCKSIZE)

    return hasher.hexdigest()


def meta_data(pathname):
    audio = MP3(pathname, ID3=EasyID3)
    try:
        name = audio.get('title')[0]
    except:
        name = ""
    try:
        album = audio.get('album')[0]
    except:
        album = ""
    try:
        artists = audio.get('artist')[0]
    except:
        artists = []
    try:
        length = audio.info.length
    except:
        length = 0.0
    return name, album, artists, length


@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('Project/css', path)


@app.route('/img/<path:path>')
def send_img(path):
    return send_from_directory('Project/img/', path)


@app.route('/songs/<path:path>')
def song(path):
    return send_from_directory('upload', path)


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            hash_val = hash_value(path)

            name, album, artists, length = meta_data(path)

            entity = [hash_val, name, album, artists, filename, length]

            g.db.execute("insert into entries (mid, title, album, artist, \
                         filename, length) values (?, ?, ?, ?, ?, ?)", entity)
            g.db.commit()
            flash('New entry was successfully posted')
            return redirect(url_for("queue"))
    return render_template("upload.html")


@app.route("/change_song")
def change_song():
    g.db.execute("delete from entries where id in (select id from entries limit 1)")
    g.db.commit()
    return redirect(url_for("queue"))


if __name__ == "__main__":
    app.run(host='0.0.0.0',
            debug=True)
    # app.run(debug=True)
