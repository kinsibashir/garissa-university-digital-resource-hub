"""
Routes package for Garissa University Digital Resource Hub
"""
from app.routes.auth import auth_bp
from app.routes.departments import departments_bp
from app.routes.courses import courses_bp
from app.routes.resources import resources_bp
from app.routes.users import users_bp
from app.routes.statistics import statistics_bp

__all__ = [
    'auth_bp',
    'departments_bp',
    'courses_bp',
    'resources_bp',
    'users_bp',
    'statistics_bp'
]