from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
import datetime
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, EditProfileForm, AddMovieForm
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import requests


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)
ckeditor = CKEditor(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

movie_endpoint = 'https://api.themoviedb.org/3/search/movie'
movie_img_endpoint = "https://image.tmdb.org/t/p/w500"
API_KEY = "cfea93bb49c2265e9f6a16e2cebbbf3e"

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# CONFIGURE TABLE
class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = db.relationship("User", back_populates="posts")
    comments = db.relationship("Comments", back_populates="parent_post")
    likes = db.Column(db.Integer)

    def __repr__(self):
        return f'<Post "{self.title}">'


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = db.relationship("BlogPost", back_populates="author")
    comments = db.relationship("Comments", back_populates="comment_author")
    movies = db.relationship("Movies", back_populates="movie_user")
    friends = db.relationship("Friends", back_populates="requested_user")
    about = db.Column(db.Text, nullable=True)
    profile_image = db.Column(db.String(100))
    requests = db.relationship("FriendRequests", back_populates="user_request")
    liked_posts = db.relationship("PostLikes", back_populates="user")

    def __repr__(self):
        return f"<User {self.name}>"


class Comments(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = db.relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)
    parent_post = db.relationship("BlogPost", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))

    def __repr__(self):
        return f"<Comment {self.id}>"


class Movies(db.Model):
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    movie_user = db.relationship("User", back_populates="movies")
    movie_img_url = db.Column(db.String(1000))
    movie_overview = db.Column(db.String(1000))
    movie_title = db.Column(db.String(100), nullable=False)
    movie_date = db.Column(db.String(250), nullable=False)
    movie_rating = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<Movie {self.movie_title}>"


class Friends(db.Model):
    __tablename__ = "friends"

    id = db.Column(db.Integer, primary_key=True)
    requested_id = db.Column(db.Integer,  db.ForeignKey("users.id"), nullable=False)
    addressed_id = db.Column(db.Integer, nullable=False)
    requested_name = db.Column(db.String(1000))
    addressed_name = db.Column(db.String(1000))
    relationship_date = db.Column(db.String(250), nullable=False)
    requested_user = db.relationship("User", back_populates="friends")

    def __repr__(self):
        return f"<Relationship {self.requested_name}, {self.addressed_name}>"


class FriendRequests(db.Model):
    __tablename__ = "requests"

    id = db.Column(db.Integer, primary_key=True)
    requested_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    addressed_id = db.Column(db.Integer, nullable=False)
    user_request = db.relationship("User", back_populates="requests")


class PostLikes(db.Model):
    __tablename__ = "post_likes"

    id = db.Column(db.Integer, primary_key=True)
    liked_post = db.Column(db.Integer, nullable=False)
    user = db.relationship("User",  back_populates="liked_posts")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


db.create_all()


def is_admin(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return func(*args, **kwargs)
        else:
            return redirect(url_for('get_all_posts'))
    return decorator


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.order_by(BlogPost.id.desc()).all()
    return render_template("index.html", all_posts=posts)


@app.route("/post/<int:index>", methods=['GET', 'POST'])
def show_post(index):
    form = CommentForm()
    post = BlogPost.query.get(index)
    is_liked = False

    if current_user.is_authenticated:
        if len(PostLikes.query.filter_by(liked_post=index, user_id=current_user.id).all()) > 0:
            is_liked = True

    if form.validate_on_submit():
        comment = form.text.data
        author_id = current_user.id
        new_comment = Comments(text=comment,
                               author_id=author_id,
                               post_id=index)
        db.session.add(new_comment)
        db.session.commit()
    comments = Comments.query.filter_by(post_id=index).all()
    return render_template("post.html", post=post, form=form, comments=comments, liked=is_liked)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route('/new-post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        title = form.title.data
        subtitle = form.subtitle.data
        author_id = current_user.id
        img_url = form.img_url.data
        content = form.content.data
        day = datetime.datetime.now().day
        month = datetime.datetime.now().strftime("%B")
        year = datetime.datetime.now().year
        date = f"{month} {day}, {year}"
        post = BlogPost(title=title,
                        subtitle=subtitle,
                        img_url=img_url,
                        body=content,
                        date=date,
                        author_id=author_id,
                        likes=0)
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('get_all_posts'))

    return render_template("make-post.html", form=form)


@app.route("/post/like/<int:post_id>", methods=['GET', 'POST'])
@login_required
def likePost(post_id):
    post = BlogPost.query.get(post_id)
    post.likes += 1

    like = PostLikes(liked_post=post_id,
                     user_id=current_user.id)
    db.session.add(like)
    db.session.commit()

    return redirect(url_for('show_post', index=post_id))


@app.route("/post/unlike/<int:post_id>", methods=['GET', 'POST'])
@login_required
def unlikePost(post_id):
    post = BlogPost.query.get(post_id)
    post.likes -= 1

    like = PostLikes.query.filter_by(liked_post=post_id,
                                     user_id=current_user.id).first()
    db.session.delete(like)
    db.session.commit()

    return redirect(url_for('show_post', index=post_id))


@app.route('/edit-post/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    form = CreatePostForm(title=post.title,
                          subtitle=post.subtitle,
                          img_url=post.img_url,
                          author=post.author,
                          content=post.body)

    if form.validate_on_submit():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.img_url = form.img_url.data
        post.body = form.content.data

        db.session.commit()
        return redirect(url_for('show_post', index=post_id))

    return render_template("make-post.html", form=form, post_id=post_id)


@app.route("/delete/<post_id>")
@login_required
def delete(post_id):
    post = BlogPost.query.get(post_id)
    comments = Comments.query.filter_by(post_id=post_id).all()
    for comment in comments:
        db.session.delete(comment)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password=form.password.data,
                                                 method="pbkdf2:sha256",
                                                 salt_length=8)
        new_user = User(name=form.name.data,
                        email=form.email.data,
                        password=hashed_password,
                        about='',
                        profile_image='user-icon.jpg')
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("Password incorrect, please try again.")
        except AttributeError:
            flash("That email does not exist, please try again.")

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/profile')
@login_required
def profile():

    friends_num = len(current_user.friends) + len(Friends.query.filter_by(addressed_id=current_user.id).all())

    return render_template('profile.html', user=current_user, profile=True, friends_num=friends_num)


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(email=current_user.email,
                           name=current_user.name,
                           about=current_user.about)
    if request.method == 'POST':
        if form.image.data:
            file = secure_filename(form.image.data.filename)
            form.image.data.save('static/img/' + file)
            current_user.profile_image = file

        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.about = form.about.data
        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', form=form)


@app.route('/delete-image')
@login_required
def delete_image():
    current_user.profile_image = 'user-icon.jpg'
    db.session.commit()

    return redirect(url_for('edit_profile'))


@app.route('/search/<type>', methods=['GET'])
def search(type):
    key_word = request.args.get("search")

    if type == 'posts':
        search_results = BlogPost.query.filter(BlogPost.title.like("%" + key_word + "%")).all()
    elif type == 'profiles':
        search_results = User.query.filter(User.name.like("%" + key_word + "%")).all()
    else:
        search_results = []

    return render_template('index.html', key_word=key_word, search_results=search_results, search=True, type=type)


@app.route('/admin')
@is_admin
def admin_dashboard():
    all_posts = BlogPost.query.all()
    all_comments = Comments.query.all()
    all_user = User.query.all()
    return render_template('admin/index.html', users=all_user, posts=all_posts, comments=all_comments)


@app.route('/admin/posts')
@is_admin
def admin_posts():
    all_posts = BlogPost.query.all()
    return render_template('admin/posts.html', posts=all_posts)


@app.route('/admin/users')
@is_admin
@login_required
def admin_users():
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)


@app.route('/admin/comments')
@is_admin
@login_required
def admin_comments():
    all_comments = Comments.query.all()
    return render_template('admin/comments.html', comments=all_comments)


@app.route('/profile/find_movie', methods=['GET', 'POST'])
@login_required
def find_movie():
    form = AddMovieForm()
    if form.validate_on_submit():
        title = form.movie_title.data
        parameters = {
            "api_key": API_KEY,
            'query': title
        }
        response = requests.get(movie_endpoint, params=parameters)
        if response.status_code == 200:
            return render_template('select.html', movies=response.json()['results'], search=title)

    return render_template('add_movie.html', form=form)


@app.route("/profile/add_movie/<search>/<int:movie_index>")
@login_required
def add_movie(movie_index, search):
    index = movie_index-1
    parameters = {
        "api_key": API_KEY,
        'query': search
    }
    response = requests.get(movie_endpoint, params=parameters)

    new_movie = Movies(user_id=current_user.id,
                       movie_img_url=f"{movie_img_endpoint}{response.json()['results'][index]['poster_path']}",
                       movie_overview=response.json()['results'][index]['overview'],
                       movie_title=response.json()['results'][index]['title'],
                       movie_date=response.json()['results'][index]['release_date'],
                       movie_rating=response.json()['results'][index]['vote_average'])
    db.session.add(new_movie)
    db.session.commit()
    return redirect(url_for('profile'))


@app.route('/profile/movie-info/<title>')
def movie_info(title):
    movies = Movies.query.filter_by(movie_title=title).all()
    return render_template('movie_info.html', movies=movies)


@app.route('/profile/delete-movie/<int:movie_id>/<title>')
@login_required
def delete_movie(movie_id, title):
    movie = Movies.query.get(movie_id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for('movie_info', title=title))


@app.route('/user/<int:user_id>')
def users_profile(user_id):
    is_friend = False
    is_request = False

    user = User.query.get(user_id)

    friends_num = len(user.friends) + len(Friends.query.filter_by(addressed_id=user.id).all())

    if current_user.is_authenticated:
        if user_id == current_user.id:
            return redirect(url_for('profile'))

        friend_request = FriendRequests.query.filter_by(addressed_id=user_id,
                                                        requested_id=current_user.id).first()

        if user.id in [user.addressed_id for user in Friends.query.filter_by(addressed_id=user.id, requested_id=current_user.id).all()]\
                or user.id in [user.requested_id for user in Friends.query.filter_by(requested_id=user.id, addressed_id=current_user.id).all()]\
                and user_id != current_user.id:
            is_friend = True
        else:
            is_friend = False

        if friend_request:
            is_request = True
        else:
            is_request = False

    print(user.id in [user.addressed_id for user in Friends.query.filter_by(addressed_id=user.id).all()])
    print(user.id in [user.requested_id for user in Friends.query.filter_by(requested_id=user.id).all()])

    return render_template('profile.html',
                           user=user,
                           is_friend=is_friend,
                           is_request=is_request,
                           friends_num=friends_num)


@app.route("/add_friend/<int:user_id>")
@login_required
def add_friend(user_id):
    new_request = FriendRequests(addressed_id=user_id,
                                 requested_id=current_user.id)
    db.session.add(new_request)
    db.session.commit()
    return redirect(url_for('users_profile', user_id=user_id))


@app.route('/profile/friend_requests')
@login_required
def friend_requests():

    all_requests = FriendRequests.query.filter_by(addressed_id=current_user.id)
    request_count = 0
    for _ in all_requests:
        request_count += 1

    print(request_count)

    return render_template('requests.html', requests=all_requests, request_count=request_count)


@app.route('/profile/friend_request/<int:requested_id>/<requested_name>/accept/<int:request_id>')
def accept_friend(requested_id, requested_name, request_id):
    new_friend = Friends(requested_id=requested_id,
                         addressed_id=current_user.id,
                         requested_name=requested_name,
                         addressed_name=current_user.name,
                         relationship_date=datetime.date.today())
    db.session.add(new_friend)
    friend_request = FriendRequests.query.get(request_id)
    db.session.delete(friend_request)
    db.session.commit()
    return redirect(url_for('friend_requests'))


@app.route('/profile/friend_request/decline_request/<int:request_id>')
def decline_friend(request_id):
    friend_request = FriendRequests.query.get(request_id)
    db.session.delete(friend_request)
    db.session.commit()


@app.route('/user/delete_friend/<int:friend_id>')
def delete_friend(friend_id):
    addressed_friend = Friends.query.filter_by(addressed_id=friend_id, requested_id=current_user.id).first()
    requested_friend = Friends.query.filter_by(addressed_id=current_user.id, requested_id=friend_id).first()

    if addressed_friend:
        db.session.delete(addressed_friend)
    elif requested_friend:
        db.session.delete(requested_friend)

    db.session.commit()

    return redirect(url_for('users_profile', user_id=friend_id))


@app.route("/user/<int:user_id>/view_friends")
def view_all_friends(user_id):
    user = User.query.get(user_id)
    addressed_friends = []
    requested_friends = []

    for friend in Friends.query.filter_by(addressed_id=user_id).all():
        addressed_friends += [User.query.get(friend.requested_id)]

    for friend in Friends.query.filter_by(requested_id=user_id).all():
        requested_friends += [User.query.get(friend.addressed_id)]

    all_friends = requested_friends + addressed_friends

    return render_template('all_friends.html', friends=all_friends, user=user)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
