from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import Order, Product, User, OrderItem
from .forms import LoginForm, RegistrationForm, TwoFactorForm, CartForm
from . import login_manager
from .utils import generate_otp, verify_otp
from functools import wraps
import os
import stripe
from stripe.error import StripeError



stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

bp = Blueprint('views', __name__)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('views.login'))
    return render_template('register.html', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('views.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('views.login'))
        login_user(user, remember=form.remember_me.data)
        if user.otp_secret is not None:
            return redirect(url_for('views.two_factor_auth'))
        else:
            return redirect(url_for('views.enable_two_factor_auth'))
    return render_template('login.html', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('views.index'))


@bp.route('/products')
@login_required
def products():
    all_products = Product.query.all()
    return render_template('products.html', products=all_products)


@bp.route('/product/<int:product_id>')
@login_required
def product(product_id):
    product = Product.query.filter_by(id=product_id).first()
    if product is None:
        return "Product not found", 404
    return render_template('product.html', product=product.to_dict())


@bp.route('/two_factor_auth', methods=['GET', 'POST'])
@login_required
def two_factor_auth():
    form = TwoFactorForm()
    if form.validate_on_submit():
        otp = form.otp.data
        if verify_otp(current_user, otp):
            flash('OTP verified successfully')
            return redirect(url_for('views.index'))
        else:
            flash('Incorrect OTP')
    return render_template('2fa.html', form=form)


@bp.route('/enable_two_factor_auth')
@login_required
def enable_two_factor_auth():
    otp_secret = generate_otp(current_user)
    organization_name = 'My Custom OTP'  # You can replace this with anything
    qr_data = f'otpauth://totp/{organization_name}:{current_user.email}?secret={otp_secret}&issuer={organization_name}'
    qr_code_url = f'https://api.qrserver.com/v1/create-qr-code/?data={qr_data}&size=200x200'
    return render_template('enable_2fa.html', otp_secret=otp_secret, qr_code_url=qr_code_url)


@bp.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    data = request.get_json()
    amount = data.get('amount')
    if amount is None:
        return jsonify({'error': 'Amount is required'}), 400
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount),
            currency='usd',
        )
        return jsonify({
            'clientSecret': intent['client_secret'],
            'id': intent['id']
        })
    except StripeError as e:
        return jsonify(str(e)), 403



@bp.route('/checkout')
@login_required
def checkout():
    cart_items = current_user.get_cart_items()
    total_amount = calculate_total_amount(cart_items)
    stripe_total_amount = int(total_amount * 100)  # Convert to cents
    stripe_publishable_key = os.environ.get('STRIPE_PUBLISHABLE_KEY')  
    return render_template('checkout.html', stripe_total_amount=stripe_total_amount, stripe_publishable_key=stripe_publishable_key)

def calculate_total_amount(cart_items):
    return sum([item.product.price * item.quantity for item in cart_items])


@bp.route('/add-to-cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    # Get the product to be added to the cart
    product = Product.query.get_or_404(product_id)

    # Check if the product is already in the user's cart
    cart_item = Order.query.filter_by(
        user_id=current_user.id, product_id=product_id, is_placed=False).first()

    if cart_item:
        # If the product is already in the cart, update the quantity
        cart_item.quantity += 1
        db.session.commit()
        flash('Product quantity updated')
    else:
        # If the product is not in the cart, create a new cart item
        cart_item = Order(user_id=current_user.id,
                          product_id=product_id, quantity=1)
        db.session.add(cart_item)
        db.session.commit()
        flash('Product added to cart')

    return redirect(url_for('views.product', product_id=product_id))


@bp.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    form = CartForm()
    cart_items = current_user.get_cart_items()

    if request.method == 'POST':
        for item in cart_items:
            new_quantity = request.form.get(f"quantity-{item.product.id}")
            item.quantity = int(new_quantity)
        db.session.commit()
        flash('Cart updated')
        return redirect(url_for('views.cart'))

    return render_template('cart.html', form=form, cart_items=cart_items)


@bp.route('/remove-from-cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    current_user.remove_from_cart(product_id)
    flash('Item removed from cart!', 'success')
    return redirect(url_for('views.cart'))


@bp.route('/place-order', methods=['POST'])
@login_required
def place_order():
    if current_user.place_order():
        flash('Order placed successfully')
        return redirect(url_for('views.checkout'))
    else:
        flash('Error placing order')
        return redirect(url_for('views.cart'))

@bp.route('/success')
@login_required
def success():
    # Get the user's recent order
    order = Order.query.filter_by(user_id=current_user.id, is_placed=True).order_by(Order.id.desc()).first()
    if order:
        return render_template('success.html')
    else:
        return redirect(url_for('main.index'))
