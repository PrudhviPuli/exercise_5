import logging
import string
import traceback
import random
import sqlite3
from datetime import datetime
from flask import *
from functools import wraps

app = Flask(__name__)

# These should make it so your Flask app always returns the latest version of
# your HTML, CSS, and JS files. We would remove them from a production deploy,
# but don't change them here.
app.debug = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache"
    return response



def get_db():
    db = getattr(g, '_database', None)

    if db is None:
        db = g._database = sqlite3.connect('db/watchparty.sqlite3')
        db.row_factory = sqlite3.Row
        setattr(g, '_database', db)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    db = get_db()
    cursor = db.execute(query, args)
    print("query_db")
    print(cursor)
    rows = cursor.fetchall()
    print(rows)
    db.commit()
    cursor.close()
    if rows:
        if one: 
            return rows[0]
        return rows
    return None

def new_user():
    name = "Unnamed User #" + ''.join(random.choices(string.digits, k=6))
    password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    cookie = ''.join(random.choices(string.ascii_lowercase + string.digits, k=40))
    api_key = ''.join(random.choices(string.ascii_lowercase + string.digits, k=40))
    u = query_db('insert into users (name, password, cookie, api_key) ' + 
        'values (?, ?, ?, ?) returning id, name, password, cookie, api_key',
        (name, password, cookie, api_key),
        one=True)
    return u

def get_user_from_cookie(request):
    user_id, password = request.cookies.get('user_id'), request.cookies.get('user_password')
    return query_db('select * from users where id = ? and password = ?', (user_id, password), one=True) if user_id and password else None

def render_with_error_handling(template, **kwargs):
    try:
        return render_template(template, **kwargs)
    except Exception as e:
        return render_template('error.html', error=str(e), traceback=traceback.format_exc()), 500


# ------------------------------ NORMAL PAGE ROUTES ----------------------------------

@app.route('/')
def index():
    print("index") # For debugging
    user = get_user_from_cookie(request)

    if user:
        rooms = query_db('select * from rooms')
        return render_with_error_handling('index.html', user=user, rooms=rooms)
    
    return render_with_error_handling('index.html', user=None, rooms=None)

@app.route('/rooms/new', methods=['GET', 'POST'])
def create_room():
    print("create room") # For debugging
    user = get_user_from_cookie(request)
    if user is None: return {}, 403

    if (request.method == 'POST'):
        name = "Unnamed Room " + ''.join(random.choices(string.digits, k=6))
        room = query_db('insert into rooms (name) values (?) returning id', [name], one=True)            
        return redirect(f'/rooms/{room["id"]}') # Look this up
    else:
        return app.send_static_file('create_room.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    user = get_user_from_cookie(request)
    if user:
        return redirect('/profile')
    if request.method == 'POST':
        u = new_user()
        resp = redirect('/profile')
        resp.set_cookie('user_id', str(u['id']))
        resp.set_cookie('user_password', u['password'])
        return resp
    return redirect('/login')


@app.route('/profile')
def profile():
    print("profile")
    user = get_user_from_cookie(request)
    if user:
        return render_with_error_handling('profile.html', user=user)
    
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('username') 
        password = request.form.get('password')
        user = query_db('select * from users where name = ? and password = ?', [name, password], one=True)
        if user:
            response = redirect('/')
            response.set_cookie('user_id', str(user['id']), httponly=True)
            response.set_cookie('user_password', user['password'], httponly=True)
            return response
        else:
            return render_with_error_handling('login.html', failed=True)
    return render_with_error_handling('login.html')


@app.route('/logout')
def logout():
    resp = redirect('/')
    resp.set_cookie('user_id', '')
    resp.set_cookie('user_password', '')
    return resp

def get_max_msg_id():
    result = query_db('select max(id) as max_id from messages', one=True)
    return result['max_id'] if result else 0


@app.route('/rooms/<int:room_id>')
def room(room_id):
    user = get_user_from_cookie(request)
    if user is None: return redirect('/')

    room = query_db('select * from rooms where id = ?', [room_id], one=True)
    return render_with_error_handling('room.html',
            room=room, user=user)

# -------------------------------- API ROUTES ----------------------------------

def authenticateUser(request):
    api_key = request.headers.get('Api-Key')
    if not api_key:
        return None
    
    user = query_db('SELECT * FROM users WHERE api_key = ?', [api_key], one=True)
    return user

# POST to change the user's name
@app.route('/api/username/change', methods = ["POST"])
def change_username():
    authenticated_user = authenticateUser(request)
    if not authenticated_user:
        return jsonify({"message":  "Unauthorized Access: Invalid API Key"}), 401
    oldUsername = request.json.get("username")
    if oldUsername:
        query_db("UPDATE users SET name = ? WHERE id = ?", [oldUsername, authenticated_user["id"]])
        response = make_response(redirect('/profile'))
        response.set_cookie('user_id', oldUsername)
        return {}
    return jsonify({"error": "Username Required"}), 400


@app.route('/api/password/change', methods=['POST'])
def change_password():
    user = authenticateUser(request)
    if not user:
        return {'message': 'Invalid API Key'}, 401
    new_password = request.json.get('password')
    if new_password:
        query_db('update users set password = ? where id = ?', (new_password, user['id']))
        resp = make_response({'pass':'Password set successfully!'})
        resp.set_cookie('user_password', new_password)
        return resp
    return {'message': 'Missing new password'}, 400


# POST to change the name of a room
@app.route("/api/room/name/change", methods=['POST'])
def change_room_name():
    authenticated_user = authenticateUser(request)
    if not authenticated_user:
        return jsonify({"messsage": "Unauthorized Access: Invalid API key"}), 401
    oldroomID = request.json.get("room_id")
    newroomName = request.json.get("name")
    if oldroomID and newroomName:
        query_db("UPDATE rooms SET name = ? where id = ?", [newroomName, oldroomID])
        return jsonify({"message": "Room name updated succesfully"}), 200
    return jsonify({"error": "Room ID and new room name are required"}), 400

# GET to get all the messages in a room
@app.route('/api/room/messages', methods=['GET'])
def get_chat_messages():
    output = {}
    user = authenticateUser(request)
    if user:
        if request.method == 'GET':
            room_id = request.args['room_id']
            messages = query_db('select msg.id, u.name, msg.body from messages msg, users u '
                        'where msg.room_id = ? and msg.user_id = u.id order by msg.id', [room_id], one=False)
            if not messages:
                return output
            for msg in messages:
                output[msg[0]] = {'id': msg[0], 'name': msg[1], 'body': msg[2]}
        return output, 200
    else:
        return render_template('error.html', args={"trace: ": 'Invalid User Credentials'}), 401
    return {'Status': 'Something went wrong!!'}, 403

# POST to post a new message to a room
@app.route("/api/message/post", methods = ["POST"])
def  post_message():
    authenticated_user = authenticateUser(request)
    if not authenticated_user:
        return jsonify({"message": "Unauthorized Access: Invalid API key"}), 401
    roomId = request.json.get("room_id")
    messageContent = request.json.get("body")
    if roomId and messageContent:
        query_db("INSERT INTO messages (room_id, user_id, body) VALUES (?, ?,?)", [roomId, authenticated_user["id"], messageContent])
        return jsonify({"message": "Message sent Succesfully"}), 200
    return jsonify({"error": "Room ID and message content required"}), 400

if  __name__ == '__main__':
    app.run(debug = True)

