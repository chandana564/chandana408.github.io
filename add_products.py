from app.models import Product
from flask import Flask, url_for
from flask_sqlalchemy import SQLAlchemy
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SERVER_NAME'] = 'localhost:5000'  # or your preferred server name
db = SQLAlchemy(app)

# rest of the script


with app.app_context():
    all_products = [
        {
            'name': 'The Essentials Basket',
            'price': 10.00,
            'description': "This is a carefully curated basket that brings together all your daily essentials in one place! With fresh and delicious bread, creamy and nutritious milk, and other essential shopping items, our basket offers a one-stop solution for all your grocery needs. Whether you're looking for a quick breakfast fix or planning a cozy dinner at home, this basket is sure to make your life easier and more convenient.",
            'image': url_for('static', filename='img/image1.jpg')
        },
        {
            'name': 'The Classic Buttoned Shirt',
            'price': 20.00,
            'description': "It is the perfect addition to any wardrobe! Our buttoned shirt is not only stylish and trendy but also comfortable and versatile. Crafted with the finest materials and attention to detail, this shirt offers a perfect fit and a flattering silhouette. Whether you're dressing up for a fancy occasion or dressing down for a casual day out, our buttoned shirt will help you make a bold statement and stand out from the crowd. Don't miss out on this must-have addition to your wardrobe!",
            'image': url_for('static', filename='img/download.png')
        }
    ]
    for product_data in all_products:
        product = Product(**product_data)
        db.session.add(product)
        db.session.commit()
