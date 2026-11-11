
from flask import Flask, jsonify
from flask_cors import CORS

from backend.routes.upload_routes import upload_bp
from backend.routes.ticket_routes import ticket_bp


def create_app():
    """Create and configure the Tyzo Flask application."""

    app = Flask(__name__)

    # Allow the React frontend to communicate with Flask.
    CORS(app)

    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

    # Register API routes.
    app.register_blueprint(upload_bp, url_prefix="/api")
    app.register_blueprint(ticket_bp, url_prefix="/api")

    @app.route("/", methods=["GET"])
    def home():
        return jsonify({
            "application": "Tyzo",
            "message": "Tyzo API is running",
            "version": "1.0.0"
        })

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "healthy",
            "application": "Tyzo",
            "backend": "Flask",
            "message": "Backend is ready"
        })

    return app


app = create_app()


if __name__ == "__main__":
    print("\n================================")
    print("       TYZO API SERVER")
    print("================================")
    print("Starting Flask backend...")
    print("URL: http://127.0.0.1:5000")
    print("Health: http://127.0.0.1:5000/api/health")
    print("================================\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
