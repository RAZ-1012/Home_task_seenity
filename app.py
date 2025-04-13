from flask import Flask, request
from api.endpoints import register_routes


def create_app():
    """
    Factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    register_routes(app)

    # Add global cache headers
    @app.after_request
    def add_cache_headers(response):
        if request.method == "GET":
            response.headers["Cache-Control"] = "public, max-age=3600"
        else:
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5005)
