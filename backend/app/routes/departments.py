from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Department

departments_bp = Blueprint('departments', __name__)

@departments_bp.route('/', methods=['GET'])
def get_departments():
    """
    Get all departments
    Returns list of all departments with their details
    """
    departments = Department.query.order_by(Department.name).all()
    return jsonify([dept.to_dict() for dept in departments]), 200

@departments_bp.route('/<int:id>', methods=['GET'])
def get_department(id):
    """
    Get a specific department by ID
    """
    department = Department.query.get(id)
    
    if not department:
        return jsonify({'error': 'Department not found'}), 404
    
    return jsonify(department.to_dict()), 200

@departments_bp.route('/', methods=['POST'])
@jwt_required()
def create_department():
    """
    Create a new department (Admin only)
    Expected JSON: {name}
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Department name is required'}), 400
    
    # Check if department already exists
    existing = Department.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': 'Department already exists'}), 400
    
    # Create new department
    department = Department(name=data['name'])
    
    try:
        db.session.add(department)
        db.session.commit()
        
        return jsonify({
            'message': 'Department created successfully',
            'department': department.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create department: {str(e)}'}), 500

@departments_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_department(id):
    """
    Update a department (Admin only)
    Expected JSON: {name}
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get department
    department = Department.query.get(id)
    
    if not department:
        return jsonify({'error': 'Department not found'}), 404
    
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Department name is required'}), 400
    
    # Check if name is already taken by another department
    existing = Department.query.filter_by(name=data['name']).first()
    if existing and existing.id != id:
        return jsonify({'error': 'Department name already exists'}), 400
    
    # Update department
    department.name = data['name']
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Department updated successfully',
            'department': department.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update department: {str(e)}'}), 500

@departments_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_department(id):
    """
    Delete a department (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get department
    department = Department.query.get(id)
    
    if not department:
        return jsonify({'error': 'Department not found'}), 404
    
    # Check if department has courses
    if department.courses and len(department.courses) > 0:
        return jsonify({
            'error': 'Cannot delete department with existing courses. Please delete all courses first.'
        }), 400
    
    try:
        db.session.delete(department)
        db.session.commit()
        
        return jsonify({'message': 'Department deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete department: {str(e)}'}), 500

@departments_bp.route('/<int:id>/courses', methods=['GET'])
def get_department_courses(id):
    """
    Get all courses in a specific department
    """
    department = Department.query.get(id)
    
    if not department:
        return jsonify({'error': 'Department not found'}), 404
    
    courses = department.courses
    return jsonify([course.to_dict() for course in courses]), 200

@departments_bp.route('/search', methods=['GET'])
def search_departments():
    """
    Search departments by name
    Query parameter: q (search query)
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify([]), 200
    
    departments = Department.query.filter(
        Department.name.ilike(f'%{query}%')
    ).order_by(Department.name).limit(20).all()
    
    return jsonify([dept.to_dict() for dept in departments]), 200

@departments_bp.route('/stats', methods=['GET'])
def get_department_stats():
    """
    Get statistics for all departments (number of courses and resources)
    """
    departments = Department.query.all()
    
    stats = []
    for dept in departments:
        course_count = len(dept.courses) if dept.courses else 0
        resource_count = 0
        if dept.courses:
            for course in dept.courses:
                resource_count += len(course.resources) if course.resources else 0
        
        stats.append({
            'id': dept.id,
            'name': dept.name,
            'course_count': course_count,
            'resource_count': resource_count
        })
    
    return jsonify({
        'departments': stats,
        'total_departments': len(departments)
    }), 200