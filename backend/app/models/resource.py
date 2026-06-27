from app import db
from datetime import datetime

class Resource(db.Model):
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(300), nullable=False)
    resource_type = db.Column(db.String(20), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    download_count = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=True)
    
    # Constants for resource types
    NOTE = 'Note'
    PAST_PAPER = 'Past Paper'
    REVISION_MATERIAL = 'Revision Material'
    
    RESOURCE_TYPES = [NOTE, PAST_PAPER, REVISION_MATERIAL]
    
    def increment_download_count(self):
        """Increment the download count by 1"""
        self.download_count += 1
        db.session.commit()
    
    def to_dict(self):
        """Convert resource object to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'file_path': self.file_path,
            'resource_type': self.resource_type,
            'course_id': self.course_id,
            'course_code': self.course.code if self.course else None,
            'course_title': self.course.title if self.course else None,
            'department_id': self.course.department_id if self.course else None,
            'department_name': self.course.department.name if self.course and self.course.department else None,
            'year': self.course.year if self.course else None,
            'semester': self.course.semester if self.course else None,
            'uploaded_by': self.uploaded_by,
            'uploader_username': self.uploader.username if self.uploader else None,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'download_count': self.download_count,
            'description': self.description
        }
    
    def get_file_extension(self):
        """Get the file extension from the file path"""
        if self.file_path:
            return self.file_path.rsplit('.', 1)[1].lower() if '.' in self.file_path else ''
        return ''
    
    def get_file_name(self):
        """Get the file name from the file path"""
        if self.file_path:
            return self.file_path.split('/')[-1] if '/' in self.file_path else self.file_path
        return ''
    
    def __repr__(self):
        return f'<Resource {self.title}>'