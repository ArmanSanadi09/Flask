from flask import Flask, render_template, request, url_for, redirect, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import json, os, secrets
import openai

# -------------------------------
# 1. Load / Save Users (JSON file)
# -------------------------------
USER_FILE = "users.json"

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    # default demo user
    return {"demo": generate_password_hash("pass")}

def save_users():
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

users = load_users()

# -------------------------------
# 2. OpenAI Setup
# -------------------------------
try:
    with open("apikey.txt","r") as f:
        openai.api_key = f.read().strip()
except FileNotFoundError:
    print("WARNING: apikey.txt not found. OpenAI functionality will be broken.")
    openai.api_key = "DUMMY_KEY"

# -------------------------------
# 3. Flask Setup
# -------------------------------
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # secure random key

# -------------------------------
# 4. Routes
# -------------------------------
@app.route("/", methods=["GET", "POST"])
def home():
    if "username" in session:
        return redirect(url_for("bot"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in users and check_password_hash(users[username], password):
            session["username"] = username
            return redirect(url_for("bot"))
        else:
            return render_template("signin.html", error="Invalid username or password.")

    return render_template("signin.html")


@app.route("/signup", methods=["POST"])
def signup():
    new_username = request.form.get("new_username")
    new_password = request.form.get("new_password")

    if not new_username or not new_password:
        return render_template("signin.html", error="Username and password are required.")

    if new_username in users:
        return render_template("signin.html", error="This user already exists. Please try another name.")

    # Save new user with hashed password
    users[new_username] = generate_password_hash(new_password)
    save_users()

    session["username"] = new_username
    return redirect(url_for("bot"))


@app.route("/bot", methods=["GET"])
def bot():
    if "username" not in session:
        return redirect(url_for("home"))

    user_key = f"messages_{session['username']}"
    if user_key not in session:
        session[user_key] = [
            {"role": "system", "content": "You are a study buddy created by Arman."}
        ]

    return render_template("bot.html", messages=session[user_key])


@app.route("/send", methods=["POST"])
def send():
    if "username" not in session:
        return redirect(url_for("home"))

    user_msg = request.form.get("message")
    user_key = f"messages_{session['username']}"

    if not user_msg:
        return redirect(url_for("bot"))

    session[user_key].append({"role": "user", "content": user_msg})
    session.modified = True

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=session[user_key]
        )
        bot_reply = response['choices'][0]['message']['content'].strip()
    except Exception as e:
        bot_reply = f"Error: Failed to get response from OpenAI. {str(e)}"

    session[user_key].append({"role": "assistant", "content": bot_reply})
    session.modified = True

    return redirect(url_for("bot"))


@app.route("/clear", methods=["POST"])
def clear():
    if "username" not in session:
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    user_key = f"messages_{session['username']}"
    session.pop(user_key, None)
    return jsonify({"status": "cleared"})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# -------------------------------
# 5. Run
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)