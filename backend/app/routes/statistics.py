from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Department, Course, Resource
from sqlalchemy import func, desc
from datetime import datetime, timedelta

statistics_bp = Blueprint('statistics', __name__)

@statistics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """
    Get comprehensive dashboard statistics (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Basic counts
    total_users = User.query.count()
    total_departments = Department.query.count()
    total_courses = Course.query.count()
    total_resources = Resource.query.count()
    
    # Resource type breakdown
    notes_count = Resource.query.filter_by(resource_type='Note').count()
    past_papers_count = Resource.query.filter_by(resource_type='Past Paper').count()
    revision_materials_count = Resource.query.filter_by(resource_type='Revision Material').count()
    
    # Total downloads
    total_downloads = db.session.query(func.sum(Resource.download_count)).scalar() or 0
    
    # Most downloaded resources (top 10)
    most_downloaded = Resource.query.order_by(
        Resource.download_count.desc()
    ).limit(10).all()
    
    # Recently uploaded resources (top 10)
    recent_uploads = Resource.query.order_by(
        Resource.upload_date.desc()
    ).limit(10).all()
    
    # Statistics by department
    department_stats = []
    departments = Department.query.all()
    for dept in departments:
        course_count = len(dept.courses) if dept.courses else 0
        resource_count = 0
        if dept.courses:
            for course in dept.courses:
                resource_count += len(course.resources) if course.resources else 0
        
        department_stats.append({
            'id': dept.id,
            'name': dept.name,
            'course_count': course_count,
            'resource_count': resource_count
        })
    
    # Statistics by year
    year_stats = db.session.query(
        Course.year,
        func.count(Course.id).label('course_count'),
        func.count(Resource.id).label('resource_count')
    ).outerjoin(Resource).group_by(Course.year).order_by(Course.year).all()
    
    year_stats_formatted = [
        {
            'year': item[0],
            'course_count': item[1],
            'resource_count': item[2]
        } for item in year_stats
    ]
    
    # User registration stats (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_registrations = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_days_ago).group_by(
        func.date(User.created_at)
    ).order_by(func.date(User.created_at)).all()
    
    daily_registrations_formatted = [
        {
            'date': str(item[0]),
            'count': item[1]
        } for item in daily_registrations
    ]
    
    # Resource upload stats (last 30 days)
    daily_uploads = db.session.query(
        func.date(Resource.upload_date).label('date'),
        func.count(Resource.id).label('count')
    ).filter(Resource.upload_date >= thirty_days_ago).group_by(
        func.date(Resource.upload_date)
    ).order_by(func.date(Resource.upload_date)).all()
    
    daily_uploads_formatted = [
        {
            'date': str(item[0]),
            'count': item[1]
        } for item in daily_uploads
    ]
    
    return jsonify({
        'overview': {
            'total_users': total_users,
            'total_departments': total_departments,
            'total_courses': total_courses,
            'total_resources': total_resources,
            'total_downloads': total_downloads
        },
        'resource_breakdown': {
            'notes': notes_count,
            'past_papers': past_papers_count,
            'revision_materials': revision_materials_count
        },
        'most_downloaded': [res.to_dict() for res in most_downloaded],
        'recent_uploads': [res.to_dict() for res in recent_uploads],
        'department_stats': department_stats,
        'year_stats': year_stats_formatted,
        'daily_registrations': daily_registrations_formatted,
        'daily_uploads': daily_uploads_formatted
    }), 200

@statistics_bp.route('/overview', methods=['GET'])
@jwt_required()
def get_overview_stats():
    """
    Get quick overview statistics (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    total_users = User.query.count()
    total_departments = Department.query.count()
    total_courses = Course.query.count()
    total_resources = Resource.query.count()
    total_downloads = db.session.query(func.sum(Resource.download_count)).scalar() or 0
    
    # Students registered in last 7 days
    week_ago = datetime.utcnow() - timedelta(days=7)
    new_students = User.query.filter(
        User.role == 'student',
        User.created_at >= week_ago
    ).count()
    
    # Resources uploaded in last 7 days
    new_resources = Resource.query.filter(
        Resource.upload_date >= week_ago
    ).count()
    
    # Active departments (with at least one course)
    active_departments = Department.query.join(Course).distinct().count()
    
    return jsonify({
        'total_users': total_users,
        'total_departments': total_departments,
        'active_departments': active_departments,
        'total_courses': total_courses,
        'total_resources': total_resources,
        'total_downloads': total_downloads,
        'new_students_7_days': new_students,
        'new_resources_7_days': new_resources
    }), 200

@statistics_bp.route('/resources', methods=['GET'])
@jwt_required()
def get_resource_statistics():
    """
    Get detailed resource statistics (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get filter parameters
    department_id = request.args.get('department_id')
    year = request.args.get('year')
    
    # Build query
    query = Resource.query.join(Course)
    
    if department_id:
        query = query.filter(Course.department_id == department_id)
    if year:
        query = query.filter(Course.year == year)
    
    # Execute query
    resources = query.all()
    
    # Calculate statistics
    total = len(resources)
    notes = sum(1 for r in resources if r.resource_type == 'Note')
    past_papers = sum(1 for r in resources if r.resource_type == 'Past Paper')
    revision_materials = sum(1 for r in resources if r.resource_type == 'Revision Material')
    total_downloads = sum(r.download_count for r in resources)
    
    # Average downloads per resource
    avg_downloads = total_downloads / total if total > 0 else 0
    
    # Resources with no downloads
    zero_downloads = sum(1 for r in resources if r.download_count == 0)
    
    return jsonify({
        'total_resources': total,
        'notes': notes,
        'past_papers': past_papers,
        'revision_materials': revision_materials,
        'total_downloads': total_downloads,
        'average_downloads': round(avg_downloads, 2),
        'zero_downloads': zero_downloads,
        'download_rate': round((1 - (zero_downloads / total if total > 0 else 1)) * 100, 2)
    }), 200

@statistics_bp.route('/users', methods=['GET'])
@jwt_required()
def get_user_statistics():
    """
    Get detailed user statistics (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # User counts
    total_users = User.query.count()
    total_admins = User.query.filter_by(role='admin').count()
    total_students = User.query.filter_by(role='student').count()
    
    # Users by registration month (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    monthly_registrations = db.session.query(
        func.strftime('%Y-%m', User.created_at).label('month'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= six_months_ago).group_by(
        func.strftime('%Y-%m', User.created_at)
    ).order_by(func.strftime('%Y-%m', User.created_at)).all()
    
    monthly_registrations_formatted = [
        {
            'month': item[0],
            'count': item[1]
        } for item in monthly_registrations
    ]
    
    return jsonify({
        'total_users': total_users,
        'total_admins': total_admins,
        'total_students': total_students,
        'monthly_registrations': monthly_registrations_formatted
    }), 200

@statistics_bp.route('/departments', methods=['GET'])
@jwt_required()
def get_department_statistics():
    """
    Get department statistics (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    departments = Department.query.all()
    
    stats = []
    for dept in departments:
        course_count = len(dept.courses) if dept.courses else 0
        
        resource_count = 0
        download_count = 0
        if dept.courses:
            for course in dept.courses:
                if course.resources:
                    resource_count += len(course.resources)
                    download_count += sum(r.download_count for r in course.resources)
        
        stats.append({
            'id': dept.id,
            'name': dept.name,
            'course_count': course_count,
            'resource_count': resource_count,
            'download_count': download_count,
            'avg_resources_per_course': round(resource_count / course_count if course_count > 0 else 0, 2)
        })
    
    # Sort by resource count (most resources first)
    stats.sort(key=lambda x: x['resource_count'], reverse=True)
    
    return jsonify({
        'departments': stats,
        'total_departments': len(departments)
    }), 200

@statistics_bp.route('/courses', methods=['GET'])
@jwt_required()
def get_course_statistics():
    """
    Get course statistics (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Get filter parameters
    department_id = request.args.get('department_id')
    year = request.args.get('year')
    
    # Build query
    query = Course.query
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    if year:
        query = query.filter_by(year=year)
    
    courses = query.all()
    
    stats = []
    for course in courses:
        resource_count = len(course.resources) if course.resources else 0
        download_count = sum(r.download_count for r in course.resources) if course.resources else 0
        
        stats.append({
            'id': course.id,
            'code': course.code,
            'title': course.title,
            'year': course.year,
            'semester': course.semester,
            'department_name': course.department.name if course.department else None,
            'resource_count': resource_count,
            'download_count': download_count,
            'avg_downloads_per_resource': round(download_count / resource_count if resource_count > 0 else 0, 2)
        })
    
    # Sort by resource count (most resources first)
    stats.sort(key=lambda x: x['resource_count'], reverse=True)
    
    return jsonify({
        'courses': stats,
        'total_courses': len(courses)
    }), 200

@statistics_bp.route('/trending', methods=['GET'])
def get_trending_resources():
    """
    Get trending resources (public - no auth required)
    """
    # Get trending resources from the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    trending = Resource.query.filter(
        Resource.upload_date >= thirty_days_ago
    ).order_by(
        Resource.download_count.desc()
    ).limit(10).all()
    
    return jsonify([res.to_dict() for res in trending]), 200

@statistics_bp.route('/export', methods=['GET'])
@jwt_required()
def export_statistics():
    """
    Export statistics as JSON (Admin only)
    """
    # Get current user
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is admin
    if user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    # Gather all statistics
    total_users = User.query.count()
    total_admins = User.query.filter_by(role='admin').count()
    total_students = User.query.filter_by(role='student').count()
    
    total_departments = Department.query.count()
    total_courses = Course.query.count()
    total_resources = Resource.query.count()
    total_downloads = db.session.query(func.sum(Resource.download_count)).scalar() or 0
    
    notes_count = Resource.query.filter_by(resource_type='Note').count()
    past_papers_count = Resource.query.filter_by(resource_type='Past Paper').count()
    revision_materials_count = Resource.query.filter_by(resource_type='Revision Material').count()
    
    # Top 10 downloaded resources
    top_resources = Resource.query.order_by(
        Resource.download_count.desc()
    ).limit(10).all()
    
    return jsonify({
        'export_date': datetime.utcnow().isoformat(),
        'summary': {
            'total_users': total_users,
            'total_admins': total_admins,
            'total_students': total_students,
            'total_departments': total_departments,
            'total_courses': total_courses,
            'total_resources': total_resources,
            'total_downloads': total_downloads
        },
        'resource_breakdown': {
            'notes': notes_count,
            'past_papers': past_papers_count,
            'revision_materials': revision_materials_count
        },
        'top_resources': [res.to_dict() for res in top_resources]
    }), 200