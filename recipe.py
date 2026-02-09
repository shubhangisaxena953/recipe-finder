# Recipe Finder App - Single Python Script for IDLE (Updated with Caching for Faster Loading)
# Run this script in IDLE or command line: python recipe_finder.py
# Then open http://127.0.0.1:5000 in your browser.
# Prerequisites: pip install flask requests flask-login flask-sqlalchemy requests-cache
# Get a Spoonacular API key from https://spoonacular.com/food-api and replace below.
# Updates: Added caching to speed up API calls (stores responses for 1 hour to avoid repeated slow requests).

import os
import requests
from flask import Flask, render_template_string, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests_cache  # For caching API responses

# Install caching (caches API calls for 1 hour to reduce load times)
requests_cache.install_cache('spoonacular_cache', expire_after=3600)  # 3600 seconds = 1 hour

# Replace with your Spoonacular API key
SPOONACULAR_API_KEY = '686b70b85c12444a89267fa75fac6585'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'shubhangisaxena2007#'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipe_finder.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Favorites model
class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(300))

# Shopping list model
class ShoppingList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ingredient = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database
with app.app_context():
    db.create_all()

# API functions with error handling and caching
def search_recipes_by_ingredients(ingredients):
    try:
        url = 'https://api.spoonacular.com/recipes/findByIngredients'
        params = {'ingredients': ','.join(ingredients), 'apiKey': SPOONACULAR_API_KEY, 'number': 10}
        response = requests.get(url, params=params, timeout=10)  # 10-second timeout
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []

def get_recipe_details(recipe_id):
    try:
        url = f'https://api.spoonacular.com/recipes/{recipe_id}/information'
        params = {'apiKey': SPOONACULAR_API_KEY}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return {}
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return {}

# HTML templates as strings (unchanged)
base_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Recipe Finder</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <a class="navbar-brand" href="/">Recipe Finder</a>
        <div class="navbar-nav ml-auto">
            {% if current_user.is_authenticated %}
                <a class="nav-link" href="/favorites">Favorites</a>
                <a class="nav-link" href="/shopping_list">Shopping List</a>
                <a class="nav-link" href="/logout">Logout</a>
            {% else %}
                <a class="nav-link" href="/login">Login</a>
                <a class="nav-link" href="/signup">Signup</a>
            {% endif %}
        </div>
    </nav>
    <div class="container mt-4">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-info">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

home_template = base_template.replace("{% block content %}{% endblock %}", """
<h1>Search Recipes by Ingredients</h1>
<form method="POST">
    <div class="form-group">
        <label>Ingredients (comma-separated):</label>
        <input type="text" name="ingredients" class="form-control" required>
    </div>
    <button type="submit" class="btn btn-primary">Search</button>
</form>
{% if recipes %}
    <h2>Results</h2>
    <form method="POST" action="/generate_list">
        {% for recipe in recipes %}
            <div class="card mb-3">
                <div class="card-body">
                    <h5>{{ recipe.title }}</h5>
                    <img src="{{ recipe.image }}" alt="{{ recipe.title }}" style="width:200px;">
                    <p>Used: {{ recipe.usedIngredientCount }}, Missed: {{ recipe.missedIngredientCount }}</p>
                    {% if current_user.is_authenticated %}
                        <a href="/add_favorite/{{ recipe.id }}/{{ recipe.title }}/{{ recipe.image }}" class="btn btn-success">Add to Favorites</a>
                        <input type="checkbox" name="recipe_ids" value="{{ recipe.id }}"> Select for List
                    {% endif %}
                    <a href="/recipe/{{ recipe.id }}" class="btn btn-info">View Details</a>
                </div>
            </div>
        {% endfor %}
        {% if current_user.is_authenticated %}
            <button type="submit" class="btn btn-warning">Generate Shopping List</button>
        {% endif %}
    </form>
{% endif %}
""")

recipe_template = base_template.replace("{% block content %}{% endblock %}", """
<h1>{{ recipe.title }}</h1>
<img src="{{ recipe.image }}" alt="{{ recipe.title }}" style="width:300px;">
<p>{{ recipe.summary | safe }}</p>
<h3>Instructions</h3>
<p>{{ recipe.instructions | safe }}</p>
<a href="/" class="btn btn-secondary">Back</a>
""")

favorites_template = base_template.replace("{% block content %}{% endblock %}", """
<h1>Your Favorites</h1>
{% for fav in favorites %}
    <div class="card mb-3">
        <div class="card-body">
            <h5>{{ fav.title }}</h5>
            <img src="{{ fav.image }}" alt="{{ fav.title }}" style="width:200px;">
            <a href="/remove_favorite/{{ fav.id }}" class="btn btn-danger">Remove</a>
        </div>
    </div>
{% endfor %}
""")

shopping_list_template = base_template.replace("{% block content %}{% endblock %}", """
<h1>Shopping List</h1>
<ul class="list-group">
    {% for item in items %}
        <li class="list-group-item">{{ item.quantity }} {{ item.ingredient }}</li>
    {% endfor %}
</ul>
<a href="/clear_list" class="btn btn-danger">Clear List</a>
""")

login_template = base_template.replace("{% block content %}{% endblock %}", """
<h1>Login</h1>
<form method="POST">
    <div class="form-group">
        <label>Username:</label>
        <input type="text" name="username" class="form-control" required>
    </div>
    <div class="form-group">
        <label>Password:</label>
        <input type="password" name="password" class="form-control" required>
    </div>
    <button type="submit" class="btn btn-primary">Login</button>
</form>
<a href="/signup">Don't have an account? Sign up</a>
""")

signup_template = base_template.replace("{% block content %}{% endblock %}", """
<h1>Signup</h1>
<form method="POST">
    <div class="form-group">
        <label>Username:</label>
        <input type="text" name="username" class="form-control" required>
    </div>
    <div class="form-group">
        <label>Password:</label>
        <input type="password" name="password" class="form-control" required>
    </div>
    <button type="submit" class="btn btn-primary">Signup</button>
</form>
<a href="/login">Already have an account? Login</a>
""")

# Routes (unchanged)
@app.route('/', methods=['GET', 'POST'])
def home():
    recipes = []
    if request.method == 'POST' and 'ingredients' in request.form:
        ingredients = [i.strip() for i in request.form['ingredients'].split(',')]
        recipes = search_recipes_by_ingredients(ingredients)
    return render_template_string(home_template, recipes=recipes)

@app.route('/recipe/<int:recipe_id>')
@login_required
def recipe_details(recipe_id):
    recipe = get_recipe_details(recipe_id)
    return render_template_string(recipe_template, recipe=recipe)

@app.route('/favorites')
@login_required
def favorites():
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    return render_template_string(favorites_template, favorites=favs)

@app.route('/add_favorite/<int:recipe_id>/<title>/<image>')
@login_required
def add_favorite(recipe_id, title, image):
    fav = Favorite(user_id=current_user.id, recipe_id=recipe_id, title=title, image=image)
    db.session.add(fav)
    db.session.commit()
    flash('Added to favorites!')
    return redirect(url_for('home'))

@app.route('/remove_favorite/<int:fav_id>')
@login_required
def remove_favorite(fav_id):
    fav = Favorite.query.get(fav_id)
    if fav and fav.user_id == current_user.id:
        db.session.delete(fav)
        db.session.commit()
        flash('Removed from favorites!')
    return redirect(url_for('favorites'))

@app.route('/shopping_list')
@login_required
def shopping_list():
    items = ShoppingList.query.filter_by(user_id=current_user.id).all()
    return render_template_string(shopping_list_template, items=items)

@app.route('/generate_list', methods=['POST'])
@login_required
def generate_list():
    recipe_ids = request.form.getlist('recipe_ids')
    for rid in recipe_ids:
        recipe = get_recipe_details(int(rid))
        for ingredient in recipe.get('extendedIngredients', []):
            item = ShoppingList(user_id=current_user.id, ingredient=ingredient['original'], quantity=str(ingredient.get('amount', '')))
            db.session.add(item)
    db.session.commit()
    flash('Shopping list generated!')
    return redirect(url_for('shopping_list'))

@app.route('/clear_list')
@login_required
def clear_list():
    ShoppingList.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('List cleared!')
    return redirect(url_for('shopping_list'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid credentials')
    return render_template_string(login_template)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created!')
        return redirect(url_for('login'))
    return render_template_string(signup_template)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
