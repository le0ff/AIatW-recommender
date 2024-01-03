import csv
from sqlalchemy.exc import IntegrityError
from models import Movie, MovieGenre, Link, Tag, Rating, User

def check_and_read_data(db):
    # check if we have movies in the database
    # read data if database is empty
    if Movie.query.count() == 0:
        # read movies from csv
        with open('data/movies.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        id = row[0]
                        title = row[1]
                        movie = Movie(id=id, title=title, ratingCount=0)
                        db.session.add(movie)
                        genres = row[2].split('|')  # genres is a list of genres
                        for genre in genres:  # add each genre to the movie_genre table
                            movie_genre = MovieGenre(movie_id=id, genre=genre)
                            db.session.add(movie_genre)
                        db.session.commit()  # save data to database
                    except IntegrityError:
                        print("Ignoring duplicate movie: " + title)
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " movies read")
    
    #check if we have links in the database
    #read data if database is empty
    if Link.query.count() == 0:
        # read links from csv
        with open('data/links.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        movieID = row[0]
                        imdb = row[1]
                        tmdb = row[2]
                        links = Link(movie_id=movieID, imdb=imdb, tmdb=tmdb)
                        # add links and save to database
                        db.session.add(links)
                        db.session.commit()
                    except IntegrityError:
                        print(f"Error: {movieID}, imdb: {imdb}, tmdb: {tmdb}")
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " links read")
    
    #check if we have tags in the database
    #read data if database is empty
    if Tag.query.count() == 0:
        #read tags from csv
        with open('data/tags.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        userID = row[0]
                        movieID = row[1]
                        tag = row[2]
                        tags = Tag(user_id = userID, movie_id = movieID, tag = tag)
                        #add tags and save to database
                        db.session.add(tags)
                        db.session.commit()
                    except IntegrityError:
                        print(f"Error: user: {userID}, movie: {movieID}, tag: {tag}")
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " tags read")
    
    #check if we have ratings in the database
    #read data if database is empty
    
    #set for userIDs
    userIDs = set()
    if Rating.query.count() == 0:
        #read ratings from csv
        with open('data/ratings.csv', newline='', encoding='utf8') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            count = 0
            for row in reader:
                if count > 0:
                    try:
                        userID = row[0]
                        userIDs.add(userID)
                        movieID = row[1]
                        rating = row[2]
                        ratings = Rating(user_id = userID, movie_id = movieID, rating = rating)
                        #add ratings and save to database
                        db.session.add(ratings)
                        db.session.commit()
                    except IntegrityError:
                        print(f"Error: user: {userID}, movie: {movieID}, rating: {rating}")
                        db.session.rollback()
                        pass
                count += 1
                if count % 100 == 0:
                    print(count, " ratings read")
    
    #check if we have users in the database
    #read data if database is empty
    if User.query.count() == 0:
        count = 0
        for userID in userIDs:
            try:
                #maybe different username and encoded password already?
                users = User(id=userID, username='user'+str(userID), password='Passw0rd!')
                db.session.add(users)
                db.session.commit()
            except IntegrityError:
                print(f"Error: user: {userID}")
                db.session.rollback()
                pass
            count += 1
            if count % 100 == 0:
                print(count, " users read")
    

    #initialize the amount of ratings that exists for the movies
    movies = Movie.query.all()
    count = 0

    #iterate over all movies
    for movie in movies:
        count += 1
        #all ratings for current movie
        current_ratings = Rating.query\
                        .filter(Rating.movie_id == movie.id).all()
        
        ratingCount = len(current_ratings)
        
        #change ratingCount of current movie to amount of rating
        db.session.query(Movie).filter(Movie.id == movie.id).update({"ratingCount": ratingCount})
        db.session.commit()

        if count % 100 == 0:
            print(count, " rating counts read")