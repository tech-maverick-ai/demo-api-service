import os
import time
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize New Relic (should be first)
try:
    import newrelic.agent
    newrelic.agent.initialize()
except ImportError:
    print("New Relic agent not installed")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///demo.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app)
db = SQLAlchemy(app)

# Redis connection (optional)
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        decode_responses=True
    )
except:
    redis_client = None

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(50), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()
    
    # Seed data if empty
    if User.query.count() == 0:
        sample_users = [
            User(name='John Doe', email='john@example.com', role='admin'),
            User(name='Jane Smith', email='jane@example.com', role='user'),
            User(name='Bob Johnson', email='bob@example.com', role='user'),
            User(name='Alice Brown', email='alice@example.com', role='manager')
        ]
        db.session.add_all(sample_users)
        
        sample_products = [
            Product(name='Laptop Pro', price=1299.99, category='Electronics', stock=45),
            Product(name='Wireless Headphones', price=199.99, category='Electronics', stock=120),
            Product(name='Coffee Maker', price=89.99, category='Appliances', stock=30),
            Product(name='Smartphone', price=799.99, category='Electronics', stock=75),
            Product(name='Desk Chair', price=299.99, category='Furniture', stock=25)
        ]
        db.session.add_all(sample_products)
        db.session.commit()

# Helper functions
def simulate_delay():
    """Simulate realistic API delay"""
    delay = random.uniform(0.1, 0.8)
    time.sleep(delay)

def simulate_error():
    """Simulate random errors for monitoring"""
    return random.random() < 0.05  # 5% error rate

@app.before_request
def before_request():
    """Log all requests"""
    print(f"{datetime.now()} - {request.method} {request.path}")

# API Routes
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'database': 'connected',
        'redis': 'connected' if redis_client else 'not available'
    })

@app.route('/api/users')
def get_users():
    """Get all users with optional filtering"""
    simulate_delay()
    
    if simulate_error():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        role = request.args.get('role')
        query = User.query
        
        if role:
            query = query.filter(User.role == role)
        
        users = query.all()
        
        # Cache result in Redis
        if redis_client:
            try:
                redis_client.setex('users_cache', 300, str(len(users)))
            except:
                pass
        
        return jsonify([{
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat()
        } for user in users])
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user"""
    simulate_delay()
    
    try:
        data = request.get_json()
        user = User(
            name=data['name'],
            email=data['email'],
            role=data.get('role', 'user')
        )
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'id': user.id,
            'message': 'User created successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/products')
def get_products():
    """Get all products with optional filtering"""
    simulate_delay()
    
    if simulate_error():
        return jsonify({'error': 'Product service unavailable'}), 503
    
    try:
        category = request.args.get('category')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        
        query = Product.query
        
        if category:
            query = query.filter(Product.category.ilike(f'%{category}%'))
        if min_price:
            query = query.filter(Product.price >= min_price)
        if max_price:
            query = query.filter(Product.price <= max_price)
        
        products = query.all()
        
        return jsonify([{
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'category': product.category,
            'stock': product.stock,
            'created_at': product.created_at.isoformat()
        } for product in products])
        
    except Exception as e:
        print(f"Error fetching products: {e}")
        return jsonify({'error': 'Failed to fetch products'}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create a new order"""
    simulate_delay()
    
    # Simulate payment processing delay
    time.sleep(random.uniform(0.5, 2.0))
    
    if simulate_error():
        return jsonify({'error': 'Payment processing failed'}), 402
    
    try:
        data = request.get_json()
        
        # Validate order data
        user = User.query.get(data['userId'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        order = Order(
            user_id=data['userId'],
            total=data['total'],
            status='confirmed'
        )
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            'id': order.id,
            'status': order.status,
            'total': order.total,
            'created_at': order.created_at.isoformat(),
            'message': 'Order placed successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/analytics')
def get_analytics():
    """Get basic analytics data"""
    simulate_delay()
    
    try:
        total_users = User.query.count()
        total_products = Product.query.count()
        total_orders = Order.query.count()
        
        # Recent orders (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_orders = Order.query.filter(Order.created_at >= week_ago).count()
        
        return jsonify({
            'total_users': total_users,
            'total_products': total_products,
            'total_orders': total_orders,
            'recent_orders': recent_orders,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/slow-endpoint')
def slow_endpoint():
    """Intentionally slow endpoint for testing"""
    # Simulate very slow database query
    time.sleep(random.uniform(2, 5))
    return jsonify({'message': 'This was a slow operation', 'duration': '2-5 seconds'})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
