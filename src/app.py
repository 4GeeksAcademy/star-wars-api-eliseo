import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Favorite, People, Planet

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

# User endpoints
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

# Favorite planets
@app.route('/users/<int:user_id>/favorite/planet/<int:planet_id>', methods=['POST'])
def add_favorite_planet(user_id, planet_id):

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": f"User with id {user_id} does not exist!"})
    
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"error": f"Planet with id {planet_id} does not exist!"}), 404

    favorite = Favorite.query.filter_by(user_id=user_id, planet_id=planet_id).first()
    if favorite:
        return jsonify({"error": f"Planet {planet_id} is already in user {user_id}'s favorites!"}), 400

    favorite = Favorite(user_id=user_id, planet_id=planet_id)
    db.session.add(favorite)
    db.session.commit()
    return jsonify({"message": f"Planet {planet_id} added to user {user_id}'s favorites!"}), 201

@app.route('/users/<int:user_id>/favorite/planet/<int:planet_id>', methods=['DELETE'])
def delete_favorite_planet(user_id, planet_id):
    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": f"User with id {user_id} does not exist!"}), 404

    # Check if planet exists
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"error": f"Planet with id {planet_id} does not exist!"}), 404

    # Check if the favorite relationship exists
    favorite = Favorite.query.filter_by(user_id=user_id, planet_id=planet_id).first()
    if not favorite:
        return jsonify({"error": f"Favorite planet with id {planet_id} does not exist for user {user_id}!"}), 404

    # Delete the favorite relationship
    db.session.delete(favorite)
    db.session.commit()
    return jsonify({"message": f"Planet {planet_id} removed from user {user_id}'s favorites!"}), 200

# Favorite people
@app.route('/users/<int:user_id>/favorite/people/<int:people_id>', methods=['POST'])
def add_favorite_people(user_id, people_id):
    # Check if the user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": f"User with id {user_id} does not exist!"}), 404

    # Check if the person exists
    person = People.query.get(people_id)
    if not person:
        return jsonify({"error": f"Person with id {people_id} does not exist!"}), 404

    # Check if the person is already in the user's favorites
    existing_favorite = Favorite.query.filter_by(user_id=user_id, people_id=people_id).first()
    if existing_favorite:
        return jsonify({"error": f"Person {people_id} is already in user {user_id}'s favorites!"}), 400

    # Add the favorite
    new_favorite = Favorite(user_id=user_id, people_id=people_id)
    db.session.add(new_favorite)
    db.session.commit()
    return jsonify({"message": f"Person {people_id} added to user {user_id}'s favorites!"}), 201

@app.route('/users/<int:user_id>/favorite/people/<int:people_id>', methods=['DELETE'])
def delete_favorite_people(user_id, people_id):
    # Check if the user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": f"User with id {user_id} does not exist!"}), 404

    # Check if the person exists
    person = People.query.get(people_id)
    if not person:
        return jsonify({"error": f"Person with id {people_id} does not exist!"}), 404

    # Check if the favorite exists
    favorite = Favorite.query.filter_by(user_id=user_id, people_id=people_id).first()
    if not favorite:
        return jsonify({"error": f"Person {people_id} is not in user {user_id}'s favorites!"}), 404

    # Delete the favorite
    db.session.delete(favorite)
    db.session.commit()
    return jsonify({"message": f"Person {people_id} removed from user {user_id}'s favorites!"}), 200

# People endpoints
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
    # Check if the person exists
    person = People.query.get(people_id)
    if not person:
        return jsonify({"error": f"Person with id {people_id} does not exist!"}), 404

    # Get and validate input data
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    # Validate fields if provided
    if 'people_name' in data and not isinstance(data['people_name'], str):
        return jsonify({"error": "people_name must be a string"}), 400
    if 'age' in data and (not isinstance(data['age'], int) or data['age'] < 0):
        return jsonify({"error": "age must be a positive integer"}), 400
    if 'force_alignment' in data and not isinstance(data['force_alignment'], str):
        return jsonify({"error": "force_alignment must be a string"}), 400
    if 'height' in data and (not isinstance(data['height'], int) or data['height'] <= 0):
        return jsonify({"error": "height must be a positive integer"}), 400

    # Update fields only if they are provided in the request
    person.people_name = data.get('people_name', person.people_name)
    person.age = data.get('age', person.age)
    person.force_alignment = data.get('force_alignment', person.force_alignment)
    person.height = data.get('height', person.height)

    # Commit changes to the database
    db.session.commit()
    return jsonify({"message": f"Person {people_id} updated!"}), 200

@app.route('/people/<int:people_id>', methods=['DELETE'])
def delete_person(people_id):
    # Check if the person exists
    person = People.query.get(people_id)
    if not person:
        return jsonify({"error": f"Person with ID {people_id} does not exist!"}), 404

    # Delete the person from the database
    db.session.delete(person)
    db.session.commit()

    return jsonify({"message": f"Person with ID {people_id} deleted successfully!"}), 200


# Planet endpoints
@app.route('/planets', methods=['POST'])
def create_planet():
    data = request.get_json()
    if not data.get('planet_name') or not data.get('weather'):
        return jsonify({"error": "planet_name and weather are required!"}), 400

    new_planet = Planet(
        planet_name=data.get('planet_name'),
        population=data.get('population', 0),
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
    # Check if the planet exists
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"error": f"Planet with ID {planet_id} does not exist!"}), 404

    # Get the request body
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is missing!"}), 400

    # Validate input fields
    if 'planet_name' in data and not isinstance(data['planet_name'], str):
        return jsonify({"error": "planet_name must be a string!"}), 400
    if 'population' in data and not isinstance(data['population'], int):
        return jsonify({"error": "population must be an integer!"}), 400
    if 'weather' in data and not isinstance(data['weather'], str):
        return jsonify({"error": "weather must be a string!"}), 400

    # Update fields if provided
    planet.planet_name = data.get('planet_name', planet.planet_name)
    planet.population = data.get('population', planet.population)
    planet.weather = data.get('weather', planet.weather)

    # Commit changes to the database
    db.session.commit()

    return jsonify({"message": f"Planet with ID {planet_id} updated successfully!"}), 200


@app.route('/planets/<int:planet_id>', methods=['DELETE'])
def delete_planet(planet_id):
    # Check if the planet exists
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"error": f"Planet with ID {planet_id} does not exist!"}), 404

    # Delete the planet
    db.session.delete(planet)
    db.session.commit()

    return jsonify({"message": f"Planet with ID {planet_id} deleted successfully!"}), 200


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
