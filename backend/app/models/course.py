from app import db
from datetime import datetime

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resources = db.relationship('Resource', backref='course', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert course object to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'title': self.title,
            'department_id': self.department_id,
            'department_name': self.department.name if self.department else None,
            'year': self.year,
            'semester': self.semester,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resource_count': len(self.resources) if self.resources else 0
        }
    
    def get_full_name(self):
        """Get full course name with code and title"""
        return f"{self.code} - {self.title}"
    
    def __repr__(self):
        return f'<Course {self.code}>'