import app as application
import pytest


def test_home_page_renders_local_development_defaults(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Every Commit. Every Release." in response.data
    assert b"0.1.0-local" in response.data
    assert b"Unavailable" in response.data


def test_health_returns_healthy_json(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_version_api_has_truthful_local_defaults(client, monkeypatch):
    for variable in (
        "APP_VERSION",
        "BUILD_NUMBER",
        "GIT_COMMIT",
        "REPOSITORY_URL",
    ):
        monkeypatch.delenv(variable, raising=False)

    response = client.get("/api/version")

    assert response.status_code == 200
    assert response.get_json() == {
        "version": "0.1.0-local",
        "build_number": "local-development",
        "commit_sha": "unknown",
        "repository_url": "Not configured (local development)",
        "deployment_status": "Unavailable",
        "metadata": {
            "defaults_used": [
                "APP_VERSION",
                "BUILD_NUMBER",
                "GIT_COMMIT",
                "REPOSITORY_URL",
            ],
            "is_local_development": True,
            "deployment_status_note": (
                "Deployment status is not reported by the application."
            ),
        },
    }


def test_version_api_uses_environment_metadata(client, monkeypatch):
    configured = {
        "APP_VERSION": "2.1.0",
        "BUILD_NUMBER": "42",
        "GIT_COMMIT": "abc123",
        "REPOSITORY_URL": "https://github.com/example/deployscope",
    }
    for variable, value in configured.items():
        monkeypatch.setenv(variable, value)

    payload = client.get("/api/version").get_json()

    assert payload["version"] == "2.1.0"
    assert payload["build_number"] == "42"
    assert payload["commit_sha"] == "abc123"
    assert payload["repository_url"] == configured["REPOSITORY_URL"]
    assert payload["deployment_status"] == "Unavailable"
    assert payload["metadata"]["defaults_used"] == []
    assert payload["metadata"]["is_local_development"] is False


def test_empty_environment_values_use_local_defaults(client, monkeypatch):
    for variable in (
        "APP_VERSION",
        "BUILD_NUMBER",
        "GIT_COMMIT",
        "REPOSITORY_URL",
    ):
        monkeypatch.setenv(variable, "")

    payload = client.get("/api/version").get_json()

    assert payload["version"] == "0.1.0-local"
    assert payload["build_number"] == "local-development"
    assert payload["commit_sha"] == "unknown"
    assert payload["repository_url"] == "Not configured (local development)"
    assert len(payload["metadata"]["defaults_used"]) == 4


@pytest.fixture
def client(monkeypatch):
    for variable in (
        "APP_VERSION",
        "BUILD_NUMBER",
        "GIT_COMMIT",
        "REPOSITORY_URL",
    ):
        monkeypatch.delenv(variable, raising=False)
    application.app.config.update(TESTING=True)
    with application.app.test_client() as test_client:
        yield test_client
