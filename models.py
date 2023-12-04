from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    otp_secret = db.Column(db.String(128), unique=True)  # Updated data type for otp_secret

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_cart_items(self):
        return Order.query.filter_by(user_id=self.id, is_placed=False).all()

    def add_to_cart(self, product_id, quantity):
        order = Order(user_id=self.id, product_id=product_id, quantity=quantity)
        db.session.add(order)
        db.session.commit()

    def remove_from_cart(self, product_id):
        order = Order.query.filter_by(user_id=self.id, product_id=product_id, is_placed=False).first()
        if order:
            db.session.delete(order)
            db.session.commit()
            
    def place_order(self):
        cart_items = self.get_cart_items()
        if not cart_items:
            return False

        for item in cart_items:
            item.is_placed = True
        db.session.commit()
        return True


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    image = db.Column(db.String(128))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'description': self.description,
            'image': self.image
        }


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref='orders')
    quantity = db.Column(db.Integer, nullable=False)
    is_placed = db.Column(db.Boolean, default=False)  # Add this line
    payment_intent_id = db.Column(db.String(255))


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    order = db.relationship('Order', backref=db.backref('cart_items', lazy=True))

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float(precision=2), nullable=False)