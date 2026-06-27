from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from app import db
from app.models import User, Resource, Course
from app.utils import allowed_file, convert_image_to_pdf
from app.config import Config

resources_bp = Blueprint('resources', __name__)

def ensure_upload_dir():
    """Ensure upload directory exists"""
    upload_path = Config.UPLOAD_FOLDER
    if not os.path.exists(upload_path):
        os.makedirs(upload_path)
    return upload_path

@resources_bp.route('/', methods=['GET'])
def get_resources():
    """
    Get all resources with optional filters
    Query parameters: course_id, resource_type, department_id, year, semester, search
    """
    # Get filter parameters
    course_id = request.args.get('course_id')
    resource_type = request.args.get('resource_type')
    department_id = request.args.get('department_id')
    year = request.args.get('year')
    semester = request.args.get('semester')
    search = request.args.get('search', '').strip()
    
    # Build query
    query = Resource.query.join(Course)
    
    # Apply filters
    if course_id:
        query = query.filter(Resource.course_id == course_id)
    if resource_type:
        query = query.filter(Resource.resource_type == resource_type)
    if department_id:
        query = query.filter(Course.department_id == department_id)
    if year:
        query = query.filter(Course.year == year)
    if semester:
        query = query.filter(Course.semester == semester)
    if search:
        query = query.filter(
            (Resource.title.ilike(f'%{search}%')) |
            (Course.code.ilike(f'%{search}%')) |
            (Course.title.ilike(f'%{search}%'))
        )
    
    # Order by upload date (newest first)
    resources = query.order_by(Resource.upload_date.desc()).all()
    
    return jsonify([res.to_dict() for res in resources]), 200

@resources_bp.route('/<int:id>', methods=['GET'])
def get_resource(id):
    """
    Get a specific resource by ID
    """
    resource = Resource.query.get(id)
    
    if not resource:
        return jsonify({'error': 'Resource not found'}), 404
    
    return jsonify(resource.to_dict()), 200

@resources_bp.route('/recent', methods=['GET'])
def get_recent_resources():
    """
    Get recently uploaded resources
    Query parameter: limit (default 10)
    """
    limit = request.args.get('limit', 10, type=int)
    
    # Validate limit
    if limit < 1 or limit > 50:
        limit = 10
    
    resources = Resource.query.order_by(
        Resource.upload_date.desc()
    ).limit(limit).all()
    
    return jsonify([res.to_dict() for res in resources]), 200

@resources_bp.route('/popular', methods=['GET'])
def get_popular_resources():
    """
    Get most downloaded resources
    Query parameter: limit (default 10)
    """
    limit = request.args.get('limit', 10, type=int)
    
    # Validate limit
    if limit < 1 or limit > 50:
        limit = 10
    
    resources = Resource.query.order_by(
        Resource.download_count.desc()
    ).limit(limit).all()
    
    return jsonify([res.to_dict() for res in resources]), 200

@resources_bp.route('/', methods=['POST'])
@jwt_required()
def upload_resource():
    """
    Upload a resource (Admin only)
    Form data: file, title, resource_type, course_id, description (optional)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file type
    if not allowed_file(file.filename):
        return jsonify({
            'error': 'File type not allowed. Please upload PDF, JPG, or PNG'
        }), 400
    
    # Get form data
    title = request.form.get('title')
    resource_type = request.form.get('resource_type')
    course_id = request.form.get('course_id')
    description = request.form.get('description', '')
    
    # Validate required fields
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    if not resource_type:
        return jsonify({'error': 'Resource type is required'}), 400
    if not course_id:
        return jsonify({'error': 'Course ID is required'}), 400
    
    # Validate resource type
    if resource_type not in Resource.RESOURCE_TYPES:
        return jsonify({
            'error': f'Invalid resource type. Must be one of: {", ".join(Resource.RESOURCE_TYPES)}'
        }), 400
    
    # Validate course exists
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404
    
    # Save file
    upload_dir = ensure_upload_dir()
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_filename = secure_filename(file.filename)
    filename = f"{timestamp}_{original_filename}"
    file_path = os.path.join(upload_dir, filename)
    
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
    
    # Convert image to PDF if needed
    file_ext = filename.rsplit('.', 1)[1].lower()
    if file_ext in ['jpg', 'jpeg', 'png']:
        pdf_path = convert_image_to_pdf(file_path, file_path)
        if pdf_path:
            # Remove original image file
            try:
                os.remove(file_path)
            except:
                pass
            file_path = pdf_path
    
    # Create resource record
    resource = Resource(
        title=title,
        file_path=file_path,
        resource_type=resource_type,
        course_id=course_id,
        uploaded_by=user_id,
        description=description
    )
    
    try:
        db.session.add(resource)
        db.session.commit()
        
        return jsonify({
            'message': 'Resource uploaded successfully',
            'resource': resource.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        # Delete file if database operation fails
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        return jsonify({'error': f'Failed to upload resource: {str(e)}'}), 500

@resources_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_resource(id):
    """
    Update a resource (Admin only)
    Expected JSON: any of {title, resource_type, course_id, description}
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get resource
    resource = Resource.query.get(id)
    
    if not resource:
        return jsonify({'error': 'Resource not found'}), 404
    
    data = request.get_json()
    
    # Update fields if provided
    if data.get('title'):
        resource.title = data['title']
    
    if data.get('resource_type'):
        if data['resource_type'] not in Resource.RESOURCE_TYPES:
            return jsonify({
                'error': f'Invalid resource type. Must be one of: {", ".join(Resource.RESOURCE_TYPES)}'
            }), 400
        resource.resource_type = data['resource_type']
    
    if data.get('course_id'):
        course = Course.query.get(data['course_id'])
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        resource.course_id = data['course_id']
    
    if data.get('description') is not None:
        resource.description = data['description']
    
    try:
        db.session.commit()
        
        return jsonify({
            'message': 'Resource updated successfully',
            'resource': resource.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update resource: {str(e)}'}), 500

@resources_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_resource(id):
    """
    Delete a resource (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get resource
    resource = Resource.query.get(id)
    
    if not resource:
        return jsonify({'error': 'Resource not found'}), 404
    
    # Delete file from filesystem
    if os.path.exists(resource.file_path):
        try:
            os.remove(resource.file_path)
        except Exception as e:
            print(f"Warning: Could not delete file {resource.file_path}: {str(e)}")
    
    try:
        db.session.delete(resource)
        db.session.commit()
        
        return jsonify({'message': 'Resource deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete resource: {str(e)}'}), 500

@resources_bp.route('/<int:id>/download', methods=['GET'])
@jwt_required()
def download_resource(id):
    """
    Download a resource and increment download count
    """
    # Get resource
    resource = Resource.query.get(id)
    
    if not resource:
        return jsonify({'error': 'Resource not found'}), 404
    
    # Check if file exists
    if not os.path.exists(resource.file_path):
        return jsonify({'error': 'File not found on server'}), 404
    
    # Increment download count
    resource.download_count += 1
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Warning: Could not update download count: {str(e)}")
    
    try:
        return send_file(
            resource.file_path,
            as_attachment=True,
            download_name=os.path.basename(resource.file_path),
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({'error': f'Failed to download file: {str(e)}'}), 500

@resources_bp.route('/<int:id>/view', methods=['GET'])
def view_resource(id):
    """
    View a resource in browser (without incrementing download count)
    """
    # Get resource
    resource = Resource.query.get(id)
    
    if not resource:
        return jsonify({'error': 'Resource not found'}), 404
    
    # Check if file exists
    if not os.path.exists(resource.file_path):
        return jsonify({'error': 'File not found on server'}), 404
    
    try:
        # Determine mimetype based on file extension
        file_ext = resource.get_file_extension()
        mimetype = None
        
        if file_ext == 'pdf':
            mimetype = 'application/pdf'
        elif file_ext in ['jpg', 'jpeg']:
            mimetype = 'image/jpeg'
        elif file_ext == 'png':
            mimetype = 'image/png'
        
        return send_file(
            resource.file_path,
            mimetype=mimetype,
            as_attachment=False
        )
    except Exception as e:
        return jsonify({'error': f'Failed to view file: {str(e)}'}), 500

@resources_bp.route('/types', methods=['GET'])
def get_resource_types():
    """
    Get available resource types
    """
    return jsonify(Resource.RESOURCE_TYPES), 200

@resources_bp.route('/stats', methods=['GET'])
def get_resource_stats():
    """
    Get resource statistics
    """
    total_resources = Resource.query.count()
    notes_count = Resource.query.filter_by(resource_type='Note').count()
    past_papers_count = Resource.query.filter_by(resource_type='Past Paper').count()
    revision_materials_count = Resource.query.filter_by(resource_type='Revision Material').count()
    
    # Total downloads
    total_downloads = db.session.query(db.func.sum(Resource.download_count)).scalar() or 0
    
    # Resources by course
    resources_by_course = db.session.query(
        Course.code,
        Course.title,
        db.func.count(Resource.id).label('count')
    ).join(Resource).group_by(Course.id).order_by(db.func.count(Resource.id).desc()).limit(10).all()
    
    return jsonify({
        'total_resources': total_resources,
        'notes_count': notes_count,
        'past_papers_count': past_papers_count,
        'revision_materials_count': revision_materials_count,
        'total_downloads': total_downloads,
        'resources_by_course': [
            {
                'code': item[0],
                'title': item[1],
                'count': item[2]
            } for item in resources_by_course
        ]
    }), 200

@resources_bp.route('/<int:id>/metadata', methods=['GET'])
def get_resource_metadata(id):
    """
    Get metadata for a resource (file size, etc.)
    """
    resource = Resource.query.get(id)
    
    if not resource:
        return jsonify({'error': 'Resource not found'}), 404
    
    # Check if file exists
    if not os.path.exists(resource.file_path):
        return jsonify({'error': 'File not found on server'}), 404
    
    file_size = os.path.getsize(resource.file_path)
    
    # Format file size
    for unit in ['B', 'KB', 'MB', 'GB']:
        if file_size < 1024.0:
            file_size_formatted = f"{file_size:.1f} {unit}"
            break
        file_size /= 1024.0
    
    return jsonify({
        'id': resource.id,
        'title': resource.title,
        'file_size': file_size_formatted,
        'file_size_bytes': os.path.getsize(resource.file_path),
        'file_extension': resource.get_file_extension(),
        'file_name': resource.get_file_name(),
        'upload_date': resource.upload_date.isoformat() if resource.upload_date else None,
        'download_count': resource.download_count
    }), 200