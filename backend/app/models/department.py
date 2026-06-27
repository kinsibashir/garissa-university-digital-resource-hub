from app import db
from datetime import datetime

class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    courses = db.relationship('Course', backref='department', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert department object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'course_count': len(self.courses) if self.courses else 0
        }
    
    def __repr__(self):
        return f'<Department {self.name}>'