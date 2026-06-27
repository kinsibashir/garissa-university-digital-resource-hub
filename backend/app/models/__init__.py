"""
Models package for Garissa University Digital Resource Hub
"""
from app.models.user import User
from app.models.department import Department
from app.models.course import Course
from app.models.resource import Resource

__all__ = ['User', 'Department', 'Course', 'Resource']