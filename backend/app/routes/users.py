from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    """
    Get all users (Admin only)
    Query parameters: role (filter by role), search (search by username or email)
    """
    # Get current user
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get filter parameters
    role = request.args.get('role')
    search = request.args.get('search', '').strip()
    
    # Build query
    query = User.query
    
    # Apply filters
    if role:
        query = query.filter_by(role=role)
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) | 
            (User.email.ilike(f'%{search}%'))
        )
    
    # Order by creation date (newest first)
    users = query.order_by(User.created_at.desc()).all()
    
    return jsonify([user.to_dict() for user in users]), 200

@users_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_user(id):
    """
    Get a specific user by ID (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get target user
    target_user = User.query.get(id)
    
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(target_user.to_dict()), 200

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_my_profile():
    """
    Get current user's own profile
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_my_profile():
    """
    Update current user's own profile
    Expected JSON: any of {username, email}
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update username if provided
    if data.get('username'):
        # Check if username is already taken by another user
        existing = User.query.filter_by(username=data['username']).first()
        if existing and existing.id != user_id:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']
    
    # Update email if provided
    if data.get('email'):
        # Check if email is already taken by another user
        existing = User.query.filter_by(email=data['email']).first()
        if existing and existing.id != user_id:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        user.email = data['email']
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

@users_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_user(id):
    """
    Update a user (Admin only)
    Expected JSON: any of {username, email, role}
    """
    # Get current user
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get target user
    target_user = User.query.get(id)
    
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update username if provided
    if data.get('username'):
        # Check if username is already taken by another user
        existing = User.query.filter_by(username=data['username']).first()
        if existing and existing.id != id:
            return jsonify({'error': 'Username already exists'}), 400
        target_user.username = data['username']
    
    # Update email if provided
    if data.get('email'):
        # Check if email is already taken by another user
        existing = User.query.filter_by(email=data['email']).first()
        if existing and existing.id != id:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'error': 'Invalid email format'}), 400
        
        target_user.email = data['email']
    
    # Update role if provided
    if data.get('role'):
        if data['role'] not in ['student', 'admin']:
            return jsonify({'error': 'Invalid role. Must be "student" or "admin"'}), 400
        
        # Prevent removing the last admin
        if data['role'] != 'admin' and target_user.role == 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                return jsonify({'error': 'Cannot remove the last admin user'}), 400
        
        target_user.role = data['role']
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': target_user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update user: {str(e)}'}), 500

@users_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_user(id):
    """
    Delete a user (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Prevent deleting self
    if id == user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    # Get target user
    target_user = User.query.get(id)
    
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Prevent deleting the last admin
    if target_user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            return jsonify({'error': 'Cannot delete the last admin user'}), 400
    
    # Check if user has uploaded resources
    if target_user.resources_uploaded and len(target_user.resources_uploaded) > 0:
        # Option 1: Block deletion
        return jsonify({
            'error': 'Cannot delete user with uploaded resources. Please delete their resources first.'
        }), 400
        
        # Option 2: Transfer resources to another admin (commented out)
        # admin_user = User.query.filter_by(role='admin').first()
        # if admin_user:
        #     for resource in target_user.resources_uploaded:
        #         resource.uploaded_by = admin_user.id
    
    try:
        db.session.delete(target_user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500

@users_bp.route('/<int:id>/role', methods=['PUT'])
@jwt_required()
def update_user_role(id):
    """
    Update a user's role (Admin only)
    Expected JSON: {role: 'student' or 'admin'}
    """
    # Get current user
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get target user
    target_user = User.query.get(id)
    
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    if not data.get('role'):
        return jsonify({'error': 'Role is required'}), 400
    
    if data['role'] not in ['student', 'admin']:
        return jsonify({'error': 'Invalid role. Must be "student" or "admin"'}), 400
    
    # Prevent removing the last admin
    if data['role'] != 'admin' and target_user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            return jsonify({'error': 'Cannot remove the last admin user'}), 400
    
    target_user.role = data['role']
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'User role updated successfully',
            'user': target_user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update user role: {str(e)}'}), 500

@users_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_user_stats():
    """
    Get user statistics (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    total_users = User.query.count()
    total_admins = User.query.filter_by(role='admin').count()
    total_students = User.query.filter_by(role='student').count()
    
    # Users registered in the last 7 days
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = User.query.filter(User.created_at >= week_ago).count()
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    return jsonify({
        'total_users': total_users,
        'total_admins': total_admins,
        'total_students': total_students,
        'new_users_last_7_days': new_users,
        'recent_users': [user.to_dict() for user in recent_users]
    }), 200

@users_bp.route('/admins', methods=['GET'])
@jwt_required()
def get_admins():
    """
    Get all admin users (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    
    if not current_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    admins = User.query.filter_by(role='admin').order_by(User.username).all()
    
    return jsonify([admin.to_dict() for admin in admins]), 200