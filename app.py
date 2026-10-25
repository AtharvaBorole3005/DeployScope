import os

from flask import Flask, jsonify, render_template

app = Flask(__name__)


def get_version_metadata():
    """Return configured build metadata without inferring deployment success."""
    defaults = {
        "APP_VERSION": "0.1.0-local",
        "BUILD_NUMBER": "local-development",
        "GIT_COMMIT": "unknown",
        "REPOSITORY_URL": "Not configured (local development)",
    }
    values = {key: os.environ.get(key) or default for key, default in defaults.items()}
    defaults_used = [
        key for key, default in defaults.items() if not os.environ.get(key)
    ]

    return {
        "version": values["APP_VERSION"],
        "build_number": values["BUILD_NUMBER"],
        "commit_sha": values["GIT_COMMIT"],
        "repository_url": values["REPOSITORY_URL"],
        "deployment_status": "Unavailable",
        "metadata": {
            "defaults_used": defaults_used,
            "is_local_development": bool(defaults_used),
            "deployment_status_note": (
                "Deployment status is not reported by the application."
            ),
        },
    }


@app.get("/")
def index():
    return render_template("index.html", version=get_version_metadata())


@app.get("/health")
def health():
    return jsonify(status="healthy"), 200


@app.get("/api/version")
def version():
    return jsonify(get_version_metadata()), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
