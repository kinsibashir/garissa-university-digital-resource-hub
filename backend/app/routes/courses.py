from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Course, Department

courses_bp = Blueprint('courses', __name__)

@courses_bp.route('/', methods=['GET'])
def get_courses():
    """
    Get all courses with optional filters
    Query parameters: department_id, year, semester, search
    """
    # Get filter parameters
    department_id = request.args.get('department_id')
    year = request.args.get('year')
    semester = request.args.get('semester')
    search = request.args.get('search', '').strip()
    
    # Build query
    query = Course.query
    
    # Apply filters
    if department_id:
        query = query.filter_by(department_id=department_id)
    if year:
        query = query.filter_by(year=year)
    if semester:
        query = query.filter_by(semester=semester)
    if search:
        query = query.filter(
            (Course.code.ilike(f'%{search}%')) | 
            (Course.title.ilike(f'%{search}%'))
        )
    
    # Order by year, semester, and code
    courses = query.order_by(Course.year, Course.semester, Course.code).all()
    
    return jsonify([course.to_dict() for course in courses]), 200

@courses_bp.route('/<int:id>', methods=['GET'])
def get_course(id):
    """
    Get a specific course by ID
    """
    course = Course.query.get(id)
    
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    return jsonify(course.to_dict()), 200

@courses_bp.route('/by-code/<string:code>', methods=['GET'])
def get_course_by_code(code):
    """
    Get a specific course by code
    """
    course = Course.query.filter_by(code=code).first()
    
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    return jsonify(course.to_dict()), 200

@courses_bp.route('/', methods=['POST'])
@jwt_required()
def create_course():
    """
    Create a new course (Admin only)
    Expected JSON: {code, title, department_id, year, semester}
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
    
    # Validate required fields
    required_fields = ['code', 'title', 'department_id', 'year', 'semester']
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        return jsonify({
            'error': f'Missing required fields: {", ".join(missing_fields)}'
        }), 400
    
    # Check if course code already exists
    existing = Course.query.filter_by(code=data['code']).first()
    if existing:
        return jsonify({'error': 'Course code already exists'}), 400
    
    # Check if department exists
    department = Department.query.get(data['department_id'])
    if not department:
        return jsonify({'error': 'Department not found'}), 404
    
    # Validate year and semester
    try:
        year = int(data['year'])
        semester = int(data['semester'])
        
        if year < 1 or year > 5:
            return jsonify({'error': 'Year must be between 1 and 5'}), 400
        
        if semester < 1 or semester > 2:
            return jsonify({'error': 'Semester must be 1 or 2'}), 400
    except ValueError:
        return jsonify({'error': 'Year and semester must be integers'}), 400
    
    # Create new course
    course = Course(
        code=data['code'],
        title=data['title'],
        department_id=data['department_id'],
        year=year,
        semester=semester
    )
    
    try:
        db.session.add(course)
        db.session.commit()
        
        return jsonify({
            'message': 'Course created successfully',
            'course': course.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create course: {str(e)}'}), 500

@courses_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_course(id):
    """
    Update a course (Admin only)
    Expected JSON: any of {code, title, department_id, year, semester}
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get course
    course = Course.query.get(id)
    
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if data.get('code'):
        # Check if code is already taken by another course
        existing = Course.query.filter_by(code=data['code']).first()
        if existing and existing.id != id:
            return jsonify({'error': 'Course code already exists'}), 400
        course.code = data['code']
    
    if data.get('title'):
        course.title = data['title']
    
    if data.get('department_id'):
        department = Department.query.get(data['department_id'])
        if not department:
            return jsonify({'error': 'Department not found'}), 404
        course.department_id = data['department_id']
    
    if data.get('year'):
        try:
            year = int(data['year'])
            if year < 1 or year > 5:
                return jsonify({'error': 'Year must be between 1 and 5'}), 400
            course.year = year
        except ValueError:
            return jsonify({'error': 'Year must be an integer'}), 400
    
    if data.get('semester'):
        try:
            semester = int(data['semester'])
            if semester < 1 or semester > 2:
                return jsonify({'error': 'Semester must be 1 or 2'}), 400
            course.semester = semester
        except ValueError:
            return jsonify({'error': 'Semester must be an integer'}), 400
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Course updated successfully',
            'course': course.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update course: {str(e)}'}), 500

@courses_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_course(id):
    """
    Delete a course (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get course
    course = Course.query.get(id)
    
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Check if course has resources
    if course.resources and len(course.resources) > 0:
        return jsonify({
            'error': 'Cannot delete course with existing resources. Please delete all resources first.'
        }), 400
    
    try:
        db.session.delete(course)
        db.session.commit()
        
        return jsonify({'message': 'Course deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete course: {str(e)}'}), 500

@courses_bp.route('/<int:id>/resources', methods=['GET'])
def get_course_resources(id):
    """
    Get all resources for a specific course
    """
    course = Course.query.get(id)
    
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    resources = course.resources
    return jsonify([resource.to_dict() for resource in resources]), 200

@courses_bp.route('/search', methods=['GET'])
def search_courses():
    """
    Search courses by code or title
    Query parameter: q (search query)
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify([]), 200
    
    courses = Course.query.filter(
        (Course.code.ilike(f'%{query}%')) | 
        (Course.title.ilike(f'%{query}%'))
    ).order_by(Course.code).limit(20).all()
    
    return jsonify([course.to_dict() for course in courses]), 200

@courses_bp.route('/filters', methods=['GET'])
def get_course_filters():
    """
    Get available filter options for courses
    Returns distinct years, semesters, and departments
    """
    years = db.session.query(Course.year).distinct().order_by(Course.year).all()
    years = [year[0] for year in years if year[0] is not None]
    
    semesters = db.session.query(Course.semester).distinct().order_by(Course.semester).all()
    semesters = [sem[0] for sem in semesters if sem[0] is not None]
    
    departments = Department.query.order_by(Department.name).all()
    
    return jsonify({
        'years': years,
        'semesters': semesters,
        'departments': [dept.to_dict() for dept in departments]
    }), 200

@courses_bp.route('/bulk', methods=['POST'])
@jwt_required()
def bulk_create_courses():
    """
    Create multiple courses at once (Admin only)
    Expected JSON: {courses: [{code, title, department_id, year, semester}, ...]}
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
    
    if not data.get('courses'):
        return jsonify({'error': 'Courses data is required'}), 400
    
    courses_data = data['courses']
    created_courses = []
    errors = []
    
    for idx, course_data in enumerate(courses_data):
        try:
            # Validate required fields
            required_fields = ['code', 'title', 'department_id', 'year', 'semester']
            missing_fields = [field for field in required_fields if not course_data.get(field)]
            
            if missing_fields:
                errors.append({
                    'index': idx,
                    'error': f'Missing fields: {", ".join(missing_fields)}'
                })
                continue
            
            # Check if course exists
            if Course.query.filter_by(code=course_data['code']).first():
                errors.append({
                    'index': idx,
                    'error': f'Course code {course_data["code"]} already exists'
                })
                continue
            
            # Check if department exists
            department = Department.query.get(course_data['department_id'])
            if not department:
                errors.append({
                    'index': idx,
                    'error': f'Department {course_data["department_id"]} not found'
                })
                continue
            
            # Create course
            course = Course(
                code=course_data['code'],
                title=course_data['title'],
                department_id=course_data['department_id'],
                year=course_data['year'],
                semester=course_data['semester']
            )
            
            db.session.add(course)
            created_courses.append(course.to_dict())
            
        except Exception as e:
            errors.append({
                'index': idx,
                'error': str(e)
            })
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_courses)} courses created successfully',
            'created': created_courses,
            'errors': errors,
            'total_attempted': len(courses_data),
            'successful': len(created_courses)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create courses: {str(e)}'}), 500