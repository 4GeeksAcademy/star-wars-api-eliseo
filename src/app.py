"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Favorite, People, Planet
#from models import Person

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    return generate_sitemap(app)

@app.route('/user', methods=['GET'])
def handle_hello():

    response_body = {
        "msg": "Hello, this is your GET /user response "
    }

    return jsonify(response_body), 200

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{"id": u.id, "email": u.email} for u in users])

@app.route('/users/<int:user_id>/favorites', methods=['GET'])
def get_user_favorites(user_id):

    favorites = Favorite.query.filter_by(user_id=user_id).all()
    return jsonify({
        "planets": [f.planet_id for f in favorites if f.planet_id],
        "people": [f.people_id for f in favorites if f.people_id]
    })

@app.route('/users/<int:user_id>/favorite/planet/<int:planet_id>', methods=['POST'])
def add_favorite_planet(user_id, planet_id):

    favorite = Favorite(user_id=user_id, planet_id=planet_id)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({"message": f"Planet {planet_id} added to user {user_id}'s favorites!"}), 201

@app.route('/users/<int:user_id>/favorite/people/<int:people_id>', methods=['POST'])
def add_favorite_people(user_id, people_id):
    
    favorite = Favorite(user_id=user_id, people_id=people_id)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({"message": f"Person {people_id} added to user {user_id}'s favorites!"}), 201

@app.route('/users/<int:user_id>/favorite/planet/<int:planet_id>', methods=['DELETE'])
def delete_favorite_planet(user_id, planet_id):
    
    favorite = Favorite.query.filter_by(user_id=user_id, planet_id=planet_id).first_or_404()
    db.session.delete(favorite)
    db.session.commit()
    return jsonify({"message": f"Planet {planet_id} removed from user {user_id}'s favorites!"})

@app.route('/users/<int:user_id>/favorite/people/<int:people_id>', methods=['DELETE'])
def delete_favorite_people(user_id, people_id):
   
    favorite = Favorite.query.filter_by(user_id=user_id, people_id=people_id).first_or_404()
    db.session.delete(favorite)
    db.session.commit()
    return jsonify({"message": f"Person {people_id} removed from user {user_id}'s favorites!"})

# Extra points end-points #
# People

@app.route('/people', methods=['POST'])
def create_person():
   
    data = request.get_json()
    new_person = People(
        people_name=data.get('people_name'),
        age=data.get('age'),
        force_alignment=data.get('force_alignment'),
        height=data.get('height')
    )
    db.session.add(new_person)
    db.session.commit()
    return jsonify({
        "message": "Person created!",
        "person_id": new_person.id
    }), 201

@app.route('/people/<int:people_id>', methods=['PUT'])
def update_person(people_id):
    
    person = People.query.get_or_404(people_id)
    data = request.get_json()
    
    # Update fields only if they are provided in the request
    person.people_name = data.get('people_name', person.people_name)
    person.age = data.get('age', person.age)
    person.force_alignment = data.get('force_alignment', person.force_alignment)
    person.height = data.get('height', person.height)
    
    db.session.commit()
    return jsonify({
        "message": f"Person {people_id} updated!"
    })

@app.route('/people/<int:people_id>', methods=['DELETE'])
def delete_person(people_id):
   
    person = People.query.get_or_404(people_id)
    db.session.delete(person)
    db.session.commit()
    return jsonify({
        "message": f"Person {people_id} deleted!"
    })

#Planets

@app.route('/planets', methods=['POST'])
def create_planet():
    data = request.get_json()

    # Check for required fields
    if not data.get('planet_name') or not data.get('weather'):
        return jsonify({"error": "planet_name and weather are required!"}), 400

    new_planet = Planet(
        planet_name=data.get('planet_name'),
        population=data.get('population', 0),  # Default to 0 if not provided
        weather=data.get('weather')
    )
    db.session.add(new_planet)
    db.session.commit()
    return jsonify({
        "message": "Planet created!",
        "planet_id": new_planet.id
    }), 201

@app.route('/planets/<int:planet_id>', methods=['PUT'])
def update_planet(planet_id):
    planet = Planet.query.get_or_404(planet_id)
    data = request.get_json()
    
    # Update only fields provided in the request
    planet.planet_name = data.get('planet_name', planet.planet_name)
    planet.population = data.get('population', planet.population)
    planet.weather = data.get('weather', planet.weather)
    
    db.session.commit()
    return jsonify({
        "message": f"Planet {planet_id} updated!"
    })

@app.route('/planets/<int:planet_id>', methods=['DELETE'])
def delete_planet(planet_id):
    """Delete a planet."""
    planet = Planet.query.get_or_404(planet_id)
    db.session.delete(planet)
    db.session.commit()
    return jsonify({
        "message": f"Planet {planet_id} deleted!"
    })


# this only runs if `$ python src/app.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
