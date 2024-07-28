from flask import Flask, render_template, redirect, request, url_for, flash, session
from pymongo import MongoClient
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key should be randomly generated

client = MongoClient('mongodb://localhost:27017/')
db = client['monkeymesh_database']
user_collection = db['monkeymesh']  # Corrected the collection name

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    username = session.get('username')
    posts = db.posts.find()
    return render_template("index.html", posts=posts, username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = user_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash('You were successfully logged in.', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template("/login/index.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        image_file = request.files['image_file']
        
        if user_collection.find_one({'username': username}):
            flash('Username already exists, please choose a different one.', 'error')
        else:
            if image_file and allowed_file(image_file.filename):
                image_filename = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
                image_file.save(image_filename)
                image_url = url_for('static', filename='uploads/' + image_file.filename)
            else:
                image_url = None  # No image uploaded or invalid file type

            hashed_password = generate_password_hash(password)
            user_collection.insert_one({'username': username, 'password': hashed_password, 'profile_pic': image_url})
            flash('User registered successfully.', 'success')
            return redirect(url_for('login'))
            
    return render_template("/signup/index.html")

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    username = session.get('username')
    user = user_collection.find_one({'username': username})
    posts = db.posts.find({'username': username})
    profile_pic = user.get('profile_pic', '/static/img/man.png')  # Default picture if none set
    post_count = db.posts.count_documents({'username': username})  # Get the count of posts by user
    return render_template("/dashboard/index.html", username=username, posts=posts, profile_pic=profile_pic, post_count=post_count)


@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'username' not in session:
        flash('You must be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content']
        image_url = request.form.get('image', '')
        image_file = request.files.get('image_file')
        username = session.get('username')
        user = user_collection.find_one({'username': username})

        if image_file:
            image_filename = image_file.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)
            image_url = url_for('static', filename=f'uploads/{image_filename}')

        post = {'username': username, 'content': content, 'image': image_url, 'profile_pic': user['profile_pic']}
        db.posts.insert_one(post)
        flash('Your post has been created successfully.', 'success')
        return redirect(url_for('home'))

    return render_template("/dashboard/post.html")


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You were successfully logged out.', 'success')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
