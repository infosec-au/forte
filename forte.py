# all the imports
from __future__ import with_statement
from sqlite3 import dbapi2 as sqlite3
from flask_mail import Mail, Message
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
import string, random

# configuration
DATABASE = 'forte.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'


# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
mail = Mail(app)

def connect_db():
  return sqlite3.connect(app.config['DATABASE'])

def init_db():
  with closing(connect_db()) as db:
    with app.open_resource('schema.sql') as f:
      db.cursor().executescript(f.read())
    db.commit()

@app.before_request
def before_request():
  """Make sure we are connected to the database each request."""
  g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
  """Closes the database again at the end of the request."""
  if hasattr(g, 'db'):
    g.db.close()


@app.route('/')
def index():
  return render_template('index.html')

@app.route('/playlists/new', methods=['GET', 'POST'])
def new_playlist():
  error = None
  if request.method ==  'POST':
    playlist_hash = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(8))
    g.db.execute('insert into playlists (name, description, hash) values (?, ?, ?)',
                 [request.form['name'], request.form['description'], playlist_hash])
    g.db.commit()
    if request.form['email']:
      emails = request.form['email'].split()
      #Add validation for emails
      msg = Message("Forte playlist",
                    sender="noreply@forte.csesoc.unsw.edu.au",
                    recipients=emails)
      # Check for hostname rather than doing this
      # Add a nicer message
      msg.body = "http://localhost:5000/" + playlist_hash
      mail.send(msg)

    flash('New playlist was created')
    return redirect('/playlists/' + playlist_hash)
  return render_template('playlists_new.html')

@app.route('/playlists/<playlist_hash>', methods=['GET', 'POST'])
def view_playlist(playlist_hash):
  error = None
  playlist_id = g.db.execute('select id from playlists where hash=?', [playlist_hash]).fetchall()[0][0]
  if request.method == "POST":
    g.db.execute('insert into songs (name, artist, youtube, votes, playlist) values (?, ?, ?, ?, ?)',
                 [request.form['name'], request.form['artist'], request.form['youtube'], 0, playlist_id])
    g.db.commit()
    flash('New song was added')
    return redirect('/playlists/' + playlist_hash)
  else:
    playlist_obj = g.db.execute('select id, name, description, hash from playlists where id=?', [str(playlist_id)])
    playlist = [dict(name=row[1], description=row[2], hash=row[3]) for row in playlist_obj.fetchall()][0]
    song_obj = g.db.execute('select id, name, artist, youtube, votes from songs where playlist=? order by votes desc',[playlist_id])
    songs = [dict(id=row[0], name=row[1], artist=row[2], youtube=row[3], votes=row[4]) for row in song_obj.fetchall()]
    return render_template('playlists_view.html', playlist=playlist, songs=songs)

@app.route('/playlists/<playlist_hash>/<int:song_id>/up', methods=["POST"])
def upvote_song(playlist_hash, song_id):
  error = None
  g.db.execute('update songs set votes=votes+1 where id=?', [song_id])
  g.db.commit()
  return redirect('/playlists/' + playlist_hash)

@app.route('/playlists/<playlist_hash>/<int:song_id>/down', methods=["POST"])
def downvote_song(playlist_hash, song_id):
  error = None
  g.db.execute('update songs set votes=votes-1 where id=?', [song_id])
  g.db.commit()
  return redirect('/playlists/' + playlist_hash)


if __name__ == '__main__':
    app.debug = True
    app.run()
