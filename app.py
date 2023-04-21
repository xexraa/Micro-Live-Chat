import random
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import join_room, leave_room, send, SocketIO
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
socketio = SocketIO(app)

ROOMS = {}

# --------------- ROOM CREATOR --------------- #
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
            
        if code not in ROOMS:
            break
        
    return code


# --------------- ROUTES --------------- #
@app.route("/", methods=["GET", "POST"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")       
        code = request.form.get("code")
        selection = request.form.get("selection")
        join = request.form.get("join", False)
        create = request.form.get("create", False)      
        
        if not name:
            flash('Please enter your name.')
            return render_template("home.html", code=code, name=name)
        
        if join != False:
            if not code:
                flash("Please give a room code.")
                return render_template("home.html", code=code, name=name)
            elif code not in ROOMS:
                flash("Room dose not exist.")
                return render_template("home.html", code=code, name=name)
            else:           
                session["room"] = code
            
        if create != False:
            if selection != None and selection != "room_random":
                ROOMS[selection] = {"members": 0, "messages": []}
                session["room"] = selection
            else:
                room = generate_unique_code(4)
                ROOMS[room] = {"members": 0, "messages": []}
                session["room"] = room
       
        session["name"] = name 
        return redirect(url_for("room"))
  
    return render_template("home.html")


@app.route("/room")
def room():
    room = session.get("room")
    name = session.get("name")
    
    # ----- lock to enter via /room ----- #
    if room is None or session.get("name") is None or room not in ROOMS:
        return redirect(url_for("home"))
    
    if len(room) == 4:
        return render_template("room_random.html", code=room, messages=ROOMS[room]["messages"])
    else:    
        return render_template(f"{room}.html", code=room, name=name, messages=ROOMS[room]["messages"])


# --------------- EVENTS --------------- #
@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in ROOMS:
        return
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    ROOMS[room]["messages"].append(content)


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in ROOMS:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has join the room"}, to=room)
    ROOMS[room]["members"] += 1

    
@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    
    if room in ROOMS:
        ROOMS[room]["members"] -= 1
        if ROOMS[room]["members"] <= 0:
            del ROOMS[room]
            
    send({"name": name, "message": "has left the room"}, to=room)



if __name__ == '__main__':
    socketio.run(app, debug=True)
