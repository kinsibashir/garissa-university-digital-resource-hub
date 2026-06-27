
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object("app.config.Config")

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": "http://localhost:3000"
            }
        }
    )

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.departments import departments_bp
    from app.routes.courses import courses_bp
    from app.routes.resources import resources_bp
    from app.routes.users import users_bp
    from app.routes.statistics import statistics_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(departments_bp, url_prefix="/api/departments")
    app.register_blueprint(courses_bp, url_prefix="/api/courses")
    app.register_blueprint(resources_bp, url_prefix="/api/resources")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(statistics_bp, url_prefix="/api/statistics")

    # Home route
    @app.route("/")
    def home():
        return {
            "message": "Welcome to Garissa University Digital Resource Hub API",
            "status": "Backend is running successfully"
        }, 200

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


