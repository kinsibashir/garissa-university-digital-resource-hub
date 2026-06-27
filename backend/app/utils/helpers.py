import os
from PIL import Image
from PyPDF2 import PdfWriter, PdfReader
import io
from werkzeug.utils import secure_filename
from app.config import Config

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def convert_image_to_pdf(image_path, output_path):
    """Convert image to PDF and save to output_path"""
    try:
        image = Image.open(image_path)
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create PDF
        pdf_path = output_path.rsplit('.', 1)[0] + '.pdf'
        image.save(pdf_path, 'PDF', quality=95)
        return pdf_path
    except Exception as e:
        print(f"Error converting image to PDF: {str(e)}")
        return None

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def create_thumbnail(image_path, thumb_path, size=(200, 200)):
    try:
        image = Image.open(image_path)
        image.thumbnail(size)
        image.save(thumb_path)
        return thumb_path
    except:
        return None

def format_file_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} TB"