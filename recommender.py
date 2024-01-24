# Contains parts from: https://flask-user.readthedocs.io/en/latest/quickstart_app.html
from flask import Flask, render_template, request, redirect, url_for, session
from flask_user import login_required, UserManager, current_user
import numpy as np
import random

from models import db, User, Movie, Rating, MovieGenre
from read_data import check_and_read_data
from Util import cosineSim, k_highest_argmax




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

#number of entries per page
per_page = 14
# List of genres
all_genres = ['Action', 'Adventure', 'Animation', 'Children', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir', 'Horror', 'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'Western']

#initialization of database
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


#The Members page is only accessible to authenticated users via the @login_required decorator
@app.route('/movies')
@login_required  # User must be authenticated
def movies_page():
    #set page to 1, (start page)
    page = request.args.get('page', 1, type=int)

    #set up data object for pagination, consisting of all Movies
    data = Movie.query.paginate(page=page, per_page=per_page)
    return render_template("overview.html",  data=data, genres=all_genres, title="All Movies")


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
    # print("Rate {} for {} by {}".format(rating, movieid, userid))
    #return string to not replace something
    return ("nothing?")


#route for random movies
@app.route('/random', methods=['POST'])
@login_required
def randomMovie():
    #get movieIDs for all movies rated by the user
    user_movies = Rating.query \
                    .with_entities(Rating.movie_id) \
                    .filter( (Rating.user_id == current_user.id) & (Rating.rating > 0.0)) \
                    .all()
    
    # relevant movieIDs to set
    user_movieIDs = set([movie_id for (movie_id,) in user_movies])

    #all movieIDs
    all_movies = Movie.query \
                .with_entities(Movie.id).all()
    
    #all movieIds to set
    all_movieIDs = set([movie_id for (movie_id,) in all_movies])

    #subtract user_movieIDs from all_movieIDs
    possible_movies = all_movieIDs - user_movieIDs

    #get 14 random movieIDs (for display reasons)
    rnd_possible_movieIDs = [random.choice(list(possible_movies)) for _ in range(14)]

    #get random movies (Movie objects)
    rnd_possible_movies = Movie.query \
                        .filter(Movie.id.in_(rnd_possible_movieIDs)).all()

    #render movies.html with random movies
    return render_template("movies.html", data=rnd_possible_movies, title='Random')


#recommendation route
@app.route('/recommend', methods=['POST'])
@login_required
def recommendation():
    #all movies rated by current user
    relevant_movies = Rating.query \
                    .with_entities(Rating.movie_id) \
                    .filter( (Rating.user_id == current_user.id) & (Rating.rating > 0.0) ) \
                    .all()
    # relevant movieIDs to list
    movieIDs = [movie_id for (movie_id,) in relevant_movies]

    #get all UserIDs
    users = User.query \
            .with_entities(User.id) \
            .filter(User.id != current_user.id).all()
    # userIDs to list
    userIDs = [user_id for (user_id,) in users]

    #create rating-vector of currentUser
    currentUser_vector = []
    for movie in movieIDs:
        #query to check whether there is already a rating for current user and movieid
        q = db.session.query(Rating).filter((Rating.user_id == current_user.id) & (Rating.movie_id == movie))
        if db.session.query(q.exists()).scalar():
            #append rating of 0th element of query (in our case one & only element)
            currentUser_vector.append(q[0].rating)
        #if no rating in db, we append 0
        else:
            currentUser_vector.append(0)
    
    currentUser_vector = np.array(currentUser_vector)

    userVectors = []
    cosineSimilarities = []

    count = 0

    #iterate over all userIDs
    for user in userIDs:
        userRatings = []
        count += 1
        for movie in movieIDs:
            #query to check whether there is already a rating for current user and movieid
            q = db.session.query(Rating).filter((Rating.user_id == user) & (Rating.movie_id == movie))
            if db.session.query(q.exists()).scalar():
                #append rating of 0th element of query (in our case one & only element)
                userRatings.append(q[0].rating)
            #if no rating in db, we append 0
            else:
                userRatings.append(0)
        
        userRatings = np.array(userRatings)
        cosineSimilarities.append(cosineSim(userRatings, currentUser_vector))

        userVectors.append(userRatings)
        
        if count % 100 == 0:
            print(f"{count} userVectors created")
    
    # k indices, we add + 1 (element-wise) to convert from array indexing to userIDs
    k = 4
    matches = k_highest_argmax(k, cosineSimilarities) + 1

    recommended_movieIDs = []
    #iterate over our userIDs with highest matches
    for userID in matches:
        # initalize values for current User
        selected_movies = []
        ratingValue = 5.0
        sampleSize = 3

        # loop until either the observed ratings are too low (here 4.0)
        while ((len(selected_movies) < sampleSize) & (ratingValue >= 4.0)):

            # query for userID (selected match) and current ratingValue
            best_movies = Rating.query \
                    .with_entities(Rating.movie_id) \
                    .filter((Rating.user_id == int(userID)) & (Rating.rating == ratingValue)).all()
            
            best_movieIDs = [movie_id for (movie_id,) in best_movies]
            
            #set of movies that have not been rated by our current_user in comparison to our current match
            unseen_movieIDs = set(best_movieIDs) - set(movieIDs)

            #
            if len(unseen_movieIDs) >= (sampleSize - len(selected_movies)):
                selected_movies.extend(random.sample(unseen_movieIDs, sampleSize - len(selected_movies)))
            else:
                selected_movies.extend(list(unseen_movieIDs))
                ratingValue -= 0.5
        
        movieIDs.extend(selected_movies)
        recommended_movieIDs.extend(selected_movies)

        recommended_movies = Movie.query \
                            .filter(Movie.id.in_(recommended_movieIDs)).all()

    return render_template("movies.html", data=recommended_movies, title='Recommendation')


#processing data
@app.route('/process_search', methods=['POST'])
@login_required  # User must be authenticated
def process_search():
    userID = current_user.id
    #get searchPrompt and genres
    session[str(userID) + "searchPrompt"] = request.form.get('searchPrompt')
    session[str(userID) + "genres"] = request.form.get('genres')

    #return ("nothing?")
    return redirect(url_for('search'))


#route for /search
@app.route('/search')
@login_required
def search():
    #get userid
    userID = current_user.id
    
    #get searchPrompt and genres from session variables
    searchPrompt = session.get(str(userID) + "searchPrompt")
    genres = session.get(str(userID) + "genres")
    page = request.args.get('page', 1, type=int)

    #instantiating
    movieIDs = []
    data = None
    title = ""

    #if genres is not empty
    if genres:
        #if genre contains only one genre:
        if "," not in genres:
            #get list of all movie ids that have genre
            movieIDquery = db.session.query(MovieGenre.movie_id) \
                        .filter(MovieGenre.genre == genres).all()
        else:
            #split string into genres
            genres = genres.split(",")
            #get list of all movie ids that have one or more of the genres listed in genres
            movieIDquery = db.session.query(MovieGenre.movie_id) \
                        .filter(MovieGenre.genre.in_(genres)).all()
        #movieIDs to set
        movieIDs = set([movie_id for (movie_id,) in movieIDquery])

    #searchPrompt AND genre filter
    if searchPrompt and movieIDs:
        title = f"Results for '{searchPrompt}' and genres: {genres}"
        data = Movie.query \
                .filter(Movie.title.like(f"%{searchPrompt}%")) \
                .filter(Movie.id.in_(movieIDs)).paginate(page=page, per_page=per_page)
    
    #only genre filter
    elif movieIDs:
        title = f"Results for genres: {genres}"
        data = Movie.query \
                .filter(Movie.id.in_(movieIDs)).paginate(page=page, per_page=per_page)
    
    #only searchPrompt filter
    elif searchPrompt:
        title = f"Results for '{searchPrompt}'"
        data = Movie.query \
                .filter(Movie.title.like(f"%{searchPrompt}%")).paginate(page=page, per_page=per_page)

    #NO FILTER (all movies)
    else:
        title = f"All movies"
        data = Movie.query.paginate(page=page, per_page=per_page)

    #render overview with filtered movies
    return render_template("overview.html", data=data, genres=all_genres, title=title)


#forwarding, this method worked out best for us eventhough we do realize it might not be the cleanest in this case
@app.route('/forward_ratings', methods=['POST'])
@login_required
def forward_ratings():

    return redirect(url_for('myratings'))


#route for myRatings
@app.route('/myratings')
@login_required
def myratings():
    #get userID
    userID = current_user.id
    page = request.args.get('page', 1, type=int)

    #get all movieIDs rated by current user
    movieIDquery = db.session.query(Rating.movie_id) \
                    .filter((Rating.user_id == userID) & (Rating.rating > 0.0) ).all()
    #movieIDs to set
    movieIDs = set([movie_id for (movie_id,) in movieIDquery])

    #get all movies rated by current user
    data = Movie.query \
            .filter(Movie.id.in_(movieIDs)).paginate(page=page, per_page=per_page)

    #render overview with filtered movies
    return render_template("overview.html", data=data, genres=all_genres, title="My Ratings")