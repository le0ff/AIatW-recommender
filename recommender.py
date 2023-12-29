# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html

from flask import Flask, render_template, request
from flask_user import login_required, UserManager, current_user

from models import db, User, Movie, Rating
from read_data import check_and_read_data

# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

    # Flask-SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///movie_recommender.sqlite'  # File-based SQL database
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Avoids SQLAlchemy warning

    # Flask-User settings
    USER_APP_NAME = "Movie Recommender"  # Shown in and email templates and page footers
    USER_ENABLE_EMAIL = False  # Disable email authentication
    USER_ENABLE_USERNAME = True  # Enable username authentication
    USER_REQUIRE_RETYPE_PASSWORD = True  # Simplify register form

# Create Flask app
app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db
db.init_app(app)  # initialize database
db.create_all()  # create database if necessary
user_manager = UserManager(app, db, User)  # initialize Flask-User management


@app.cli.command('initdb')
def initdb_command():
    global db
    """Creates the database tables."""
    check_and_read_data(db)
    print('Initialized the database.')


#template filter, to apply this function to a movie in the jinja2 template
@app.template_filter('get_rating')
def get_rating(movie):
    #get first (here only one value possible) rating of Rating where movie_id and current_user are matching to the current movie
    user_rating = Rating.query.filter_by(movie_id=movie.id, user_id=current_user.id).first()
    #return user_rating or 0.0
    return user_rating.rating if user_rating else 0.0

# The Home page is accessible to anyone
@app.route('/')
def home_page():
    # render home.html template
    return render_template("home.html")


# The Members page is only accessible to authenticated users via the @login_required decorator
@app.route('/movies')
@login_required  # User must be authenticated
def movies_page():
    # String-based templates

    # first 10 movies
    movies = Movie.query.limit(10).all()

    # only Romance movies
    # movies = Movie.query.filter(Movie.genres.any(MovieGenre.genre == 'Romance')).limit(10).all()

    # only Romance AND Horror movies
    # movies = Movie.query\
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Romance')) \
    #     .filter(Movie.genres.any(MovieGenre.genre == 'Horror')) \
    #     .limit(10).all()

    return render_template("movies.html", movies=movies)


@app.route('/rate', methods=['POST'])
@login_required  # User must be authenticated
def rate():
    #get movieid, rating, and current_user
    movieid = request.form.get('movieid')
    rating = request.form.get('rating')
    userid = current_user.id

    #query to check whether there is already a rating for current user and movieid
    q = db.session.query(Rating).filter((Rating.user_id == userid) & (Rating.movie_id == movieid))
    if db.session.query(q.exists()).scalar():
        #overwrite Rating WHERE user = current_user and movie = current_movie to rating
        db.session.query(Rating).filter((Rating.user_id == userid) & (Rating.movie_id == movieid)).update({"rating": rating})
        db.session.commit()
    else:
        #create new rating
        db.session.add(Rating(user_id=userid, movie_id=movieid, rating=rating))
        db.session.commit()

    #console output for now
    print("Rate {} for {} by {}".format(rating, movieid, userid))

    return ("nothing?")
    #return render_template("rated.html", rating=rating)

# Start development web server
if __name__ == '__main__':
    app.run(port=5000, debug=True)
