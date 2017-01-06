# all the imports
import os
import sys
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

# Extra command line arguments for init
import optparse


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def flaskrun(app, default_host="127.0.0.1",
             default_port="5000", argv=sys.argv):
    """
    Takes a flask.Flask instance and runs it. Parses 
    command-line flags to configure the app.
    """

    # Set up the command-line options
    parser = optparse.OptionParser()
    parser.add_option("-H", "--host",
                      help="Hostname of the Flask app " +
                           "[default %s]" % default_host,
                      default=default_host)
    parser.add_option("-P", "--port",
                      help="Port for the Flask app " +
                           "[default %s]" % default_port,
                      default=default_port)
    parser.add_option("-i", "--init",
                      help="Initialise a new database while starting the app",
                      dest="init_db", default=1)

    # Two options useful for debugging purposes, but
    # a bit dangerous so not exposed in the help message.
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug",
                      help=optparse.SUPPRESS_HELP)
    parser.add_option("-p", "--profile",
                      action="store_true", dest="profile",
                      help=optparse.SUPPRESS_HELP)

    options, _ = parser.parse_args(argv)

    # If the user selects the profiling option, then we need
    # to do a little extra setup
    if options.init_db:
        init_db()

    if options.profile:
        from werkzeug.contrib.profiler import ProfilerMiddleware

        app.config['PROFILE'] = True
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app,
                                          restrictions=[30])
        options.debug = True

    app.run(
        debug=options.debug,
        host=options.host,
        port=int(options.port)
    )


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
    cur = g.db.execute('select * from entries order by votes desc')
    rows = cur.fetchall()
    is_serv = request.remote_addr
    print request.remote_addr
    return render_template('index.html', songs=rows, iss=is_serv)


@app.route("/vote", methods=["POST"])
def vote():
    _id = request.form.get('id')
    sid = request.form.get('sid')
    print _id, sid
    try:
        g.db.execute('insert into votes (sid, ip) values(?, ?)',
                     (_id, request.remote_addr))
        g.db.commit()
    except Exception as e:
        print str(e)
        return 'You\'ve already voted.', 400
    if sid == '+':
        query = "update entries set votes = votes + 1 where id = {0}"
    else:
        query = "update entries set votes = votes - 1 where id = {0}"
    g.db.execute(query.format(_id))
    g.db.commit()
    cur = g.db.execute("select votes from entries where id = {0}".format(_id))
    rows = cur.fetchall()
    return str(rows[0][0])


@app.route("/get_songs")
def get_songs():
    cur = g.db.execute('select * from entries order by votes desc')
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
        artists = ""
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
            g.db.execute("""insert into entries (mid, title, album, artist, \
                         filename, length) values (?, ?, ?, ?, ?, ?)""",
                         entity)
            g.db.commit()
            flash('New entry was successfully posted')
            return redirect(url_for("queue"))
    return render_template("upload.html")


@app.route("/change_song")
def change_song():
    g.db.execute("""delete from entries where id in (select id\
                 from entries order by votes desc limit 1)""")
    g.db.commit()
    return redirect(url_for("queue"))


if __name__ == "__main__":
    flaskrun(app=app)
    # app.run(debug=True)
