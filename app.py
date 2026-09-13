from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from flask import Flask,request,render_template,redirect,url_for,session,flash
from werkzeug.security import generate_password_hash,check_password_hash
from functools import wraps
from datetime import datetime
from waitress import serve
load_dotenv()
MY_KEY=os.getenv("MY_KEY")
app=Flask(__name__)
app.config["SECRET_KEY"] =MY_KEY
app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///sales_inventory.db"
db=SQLAlchemy(app)
def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args,**kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))

        if session['role'] !='admin':
            flash ("admin only","error")
            return redirect(url_for('products_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@app.route('/register_page')
def register_page():
    return render_template('register_page.html')

@app.route('/login_page')
def login_page():
    return render_template('login_page.html')

@app.route('/products_page')
@login_required
def products_page():
    products=Products.query.all()
    search=request.args.get('search')
    if search:
        products=Products.query.filter(Products.name.ilike(f"%{search}%")).all()
    return render_template('products_page.html',products=products)

@app.route('/stock_page')
@login_required
def stock_page():
    products=Products.query.all()
    return render_template('stock_page.html',products=products)

@app.route('/sales_page')
@login_required
def sales_page():
    sales=Sales.query.all()
    products=Products.query.all()
    return render_template('sales_page.html',products=products,sales=sales)

@app.route('/users_page')
@admin_required
def users_page():
    users=Users.query.all()
    return render_template(
        'users_page.html',
        users=users
    )

@app.route('/product_edit_page/<int:id>')
@admin_required
def product_edit_page(id):
    product=Products.query.get(id)
    if product is None:
        flash ("product not found","error")
        return redirect(url_for('products_page'))

    return render_template(
        'product_edit_page.html',
        product=product
    )

@app.route('/product_add_page')
@admin_required
def product_add_page():
    return render_template('product_add_page.html')

@app.route('/adjust_stock_page/<int:id>')
@admin_required
def adjust_stock_page(id):
    product=Products.query.get(id)
    if product is None:
        flash ("product not found","error")
        return redirect(url_for('stock_page'))
    return render_template(
        'adjust_stock_page.html',
        product=product
    )

class RevokedToken(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    jti=db.Column(db.String(200),unique=True,nullable=False)
class Users(db.Model):
    user_id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(80),nullable=False)
    email=db.Column(db.String(80),unique=True ,nullable=False)
    password=db.Column(db.String(200),nullable=False)
    role=db.Column(db.String(80),nullable=False)
    is_active =db.Column(db.Boolean,default=True)
class Products(db.Model):
    product_id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(80),nullable=False)
    price=db.Column(db.Integer,nullable=False)
    stock=db.Column(db.Integer,nullable=False)
class Sales(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    product_id=db.Column(db.Integer,db.ForeignKey("products.product_id") ,nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey("users.user_id") ,nullable=False)
    total_price=db.Column(db.Integer,nullable=False)
    date=db.Column(db.DateTime,nullable=False)
    quantity=db.Column(db.Integer,nullable=False)
    product=db.relationship('Products')
    user=db.relationship('Users')

@app.context_processor
def inject_user():
    if 'user_id' in session:
        user=Users.query.get(session['user_id'])
        return {'current_user':user}
    return {'current_user':None}
@app.route('/register',methods=['POST'])
def register():
    data=request.form
    existing=Users.query.filter_by(email=data['email']).first()
    if existing:
      flash ("email already exists")
      return redirect(url_for('register_page'))
    user=Users(
        name=data['name'],
        email=data['email'],
        password=generate_password_hash(data['password']),
        role="user"
    )
    db.session.add(user)
    db.session.commit()
    flash ("registered successfully","success")
    return redirect(url_for('register_page'))


@app.route('/login',methods=['POST'])
def login():
    email=request.form['email']
    password=request.form['password']
    user=Users.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password,password):
        flash ("wrong email or password")
        return redirect(url_for('login_page'))
    if not user.is_active:
        flash ("this user is deactivated","error")
        return redirect(url_for('login_page'))
    session['user_id'] = user.user_id
    session['role'] = user.role
    return redirect(url_for('products_page'))

@app.route('/logout',methods=['POST'])
@login_required
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/deactivate_user/<int:id>')
@admin_required
def deactivate_user(id):
    user=Users.query.get(id)
    if not user:
        flash ("user not found","error")
        return redirect(url_for('users_page'))
    user.is_active=False
    db.session.commit()
    flash (f"user {user.name} is deactivated")
    return redirect(url_for('users_page'))

@app.route('/reactivate_user/<int:id>')
@admin_required
def reactivate_user(id):
    user=Users.query.get(id)
    if not user:
        flash ("user not found","error")
        return redirect(url_for('users_page'))
    user.is_active=True
    db.session.commit()
    flash (f"user {user.name} is reactivated","success")
    return redirect(url_for('users_page'))

@app.route('/products',methods=['GET'])
def show_products():
    products=Products.query.all()
    result=[]
    for product in products:
        result.append({
            "id":product.product_id,
            "name":product.name,
            "price":product.price,
            "stock":product.stock
        })
    return {
        "products":result
    }

@app.route('/product_add',methods=['POST'])
@admin_required
def add_products():
    data=request.form
    if data['quantity']<=0:
        flash ("wrong value","error")
        return redirect(url_for('product_add_page'))
    if data['price']<=0:
        flash ("wrong value","error")
        return redirect(url_for('product_add_page'))
    try:
        int(data['price']) and int(data['stock'])
    except ValueError:
        flash ("wrong values")
        return redirect(url_for('product_add_page'))
    product=Products(
    name=data['name'],
    price=data['price'],
    stock=data['stock']
    )
    db.session.add(product)
    db.session.commit()
    flash ("product added successfully","success")
    return redirect(url_for('products_page'))

@app.route('/product_edit/<int:id>',methods=['POST'])
@admin_required
def edit_product(id):
    data=request.form
    if data['quantity']<=0:
        flash ("wrong value","error")
        return redirect(url_for('product_edit_page'))
    if data['price']<=0:
        flash ("wrong value","error")
        return redirect(url_for('product_edit_page'))
    try:
        int(data['price']) and int(data['stock'])
    except ValueError:
        flash ("wrong values")
        return redirect(url_for('product_edit_page'))
    product=Products.query.get(id)
    if product is None:
        flash ("product not found","error")
        return redirect(url_for('products_page'))
    product.name=data['name']
    product.price=data['price']
    product.stock=data['stock']
    db.session.commit()
    flash ("product updated successfully","success")
    return redirect(url_for('products_page'))

@app.route('/product_delete/<int:id>',methods=['POST'])
@admin_required
def delete_product(id):
    product=Products.query.get(id)
    if product is None:
        flash ("product not found","error")
        return redirect(url_for('products_page'))
    db.session.delete(product)
    db.session.commit()
    flash ("product deleted successfully","success")
    return redirect(url_for('products_page'))

@app.route('/adjust_stock/<int:id>',methods=['POST'])
@admin_required
def adjust_stock(id):
    data=request.form
    try:
        int(data['quantity'])
    except ValueError:
        flash ("wrong value","error")
        return redirect(url_for('adjust_stock_page'))
    if data['quantity']<=0:
        flash ("wrong value","error")
        return redirect(url_for('adjust_stock_page'))
    product=Products.query.get(id)
    if product is None:
        flash ("product not found","error")
        return redirect(url_for('stock_page'))
    if data['action'] == 'add':
        product.stock+=int(data['quantity'])
    elif product.stock< int(data['quantity']):
        flash("can't remove that quantity (The quantity is insufficient.)","error")
        redirect(url_for('adjust_stock_page'))
    else:
        product.stock-=int(data['quantity'])
    db.session.commit()
    flash ("stock adjusted successfully","success")
    return redirect(url_for('stock_page'))

@app.route('/sale',methods=['POST'])
@login_required
def make_sale():
    data=request.form
    if data['quantity']<=0:
        flash ("wrong value","error")
        return redirect(url_for('sales_page'))
    try:
        int(data['quantity'])
    except ValueError:
        flash ("wrong value","error")
        return redirect(url_for('sales_page'))
    product=Products.query.filter_by(product_id=data['product_id']).first()
    if product is None:
        flash ("product not found","error")
        return redirect(url_for('sales_page'))
    quantity=int(data['quantity'])
    if quantity <1:
        flash ("invalide quantity","error")
        return redirect(url_for('sales_page'))
    elif product.stock < quantity:
        flash ("no enough stock","error")
        return redirect(url_for('sales_page'))
    user=Users.query.get(session['user_id'])
    total_price=product.price*quantity
    product.stock-=quantity

    sale=Sales(
        product_id=product.product_id,
        user_id=user.user_id,
        total_price=total_price,
        date=datetime.now(),
        quantity=quantity
    )
    db.session.add(sale)
    db.session.commit()
    flash ("sale committed successfully","success")
    return redirect(url_for('sales_page'))

@app.route('/low_stock',methods=['GET'])
def low_stock_products():
    products=Products.query.filter(Products.stock<=5).all()
    result=[]
    for product in products:
        result.append({
            "id":product.product_id,
            "name":product.name,
            "price":product.price,
            "stock":product.stock
        })

    return {
        "low stock products":result
    },200

@app.route('/dashboard_page',methods=['GET'])
@admin_required
def show_dashboard():
    products_count=Products.query.count()
    sales_count=Sales.query.count()
    total_revenue=0
    sales=Sales.query.all()
    products=Products.query.all()
    for sale in sales:
        total_revenue += sale.total_price
    low_quantity_products=Products.query.filter(Products.stock<=5).all()
    low_quantity_products_number=Products.query.filter(Products.stock<=5).count()
    best_selling_products=[]
    for product in products:
        sales_for_each = Sales.query.filter_by(product_id=product.product_id).all()
        quantity=0
        for sale in sales_for_each:
            quantity+=sale.quantity
        if quantity >= 50:
            best_selling_products.append({
                "id":product.product_id,
                "name":product.name,
                "quantity":quantity
            })
    return render_template(
        'dashboard_page.html',
        products_count=products_count,
        sales_count=sales_count,
        total_revenue=total_revenue,
        best_selling_products=best_selling_products,
        low_quantity_products_number=low_quantity_products_number,
        low_quantity_products=low_quantity_products
    )

if __name__=='__main__':
    serve(app ,host='0.0.0.0',port=9000 )