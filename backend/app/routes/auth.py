from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import db
from app.models import User
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new student user
    Expected JSON: {username, email, password}
    """
    data = request.get_json()
    
    # Validate required fields
    if not data.get('username'):
        return jsonify({'error': 'Username is required'}), 400
    if not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    if not data.get('password'):
        return jsonify({'error': 'Password is required'}), 400
    
    # Check if username already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, data['email']):
        return jsonify({'error': 'Invalid email format'}), 400
    
    # Validate password length
    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    # Create new user (default role is 'student')
    user = User(
        username=data['username'],
        email=data['email'],
        role='student'
    )
    user.set_password(data['password'])
    
    try:
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login for both students and admins
    Expected JSON: {email, password}
    """
    data = request.get_json()
    
    if not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    if not data.get('password'):
        return jsonify({'error': 'Password is required'}), 400
    
    # Find user by email
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Create access token with user identity and role
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role}
    )
    
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/admin-login', methods=['POST'])
def admin_login():
    """
    Admin-only login
    Expected JSON: {email, password}
    """
    data = request.get_json()
    
    if not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    if not data.get('password'):
        return jsonify({'error': 'Password is required'}), 400
    
    # Find user by email
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Unauthorized. Admin access required'}), 403
    
    # Create access token
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'role': user.role}
    )
    
    return jsonify({
        'message': 'Admin login successful',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user information
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout endpoint (client-side token removal)
    Server just returns success response
    """
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password
    Expected JSON: {current_password, new_password}
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if not data.get('current_password'):
        return jsonify({'error': 'Current password is required'}), 400
    if not data.get('new_password'):
        return jsonify({'error': 'New password is required'}), 400
    
    # Verify current password
    if not user.check_password(data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Validate new password
    if len(data['new_password']) < 6:
        return jsonify({'error': 'New password must be at least 6 characters long'}), 400
    
    # Update password
    user.set_password(data['new_password'])
    
    try:
        db.session.commit()
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Password change failed: {str(e)}'}), 500

@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    """
    Check if email is already registered
    Expected JSON: {email}
    """
    data = request.get_json()
    
    if not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    return jsonify({
        'exists': user is not None,
        'message': 'Email already registered' if user else 'Email available'
    }), 200

@auth_bp.route('/check-username', methods=['POST'])
def check_username():
    """
    Check if username is already taken
    Expected JSON: {username}
    """
    data = request.get_json()
    
    if not data.get('username'):
        return jsonify({'error': 'Username is required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    return jsonify({
        'exists': user is not None,
        'message': 'Username already taken' if user else 'Username available'
    }), 200