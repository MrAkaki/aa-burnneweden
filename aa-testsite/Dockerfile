ARG AA_DOCKER_TAG=registry.gitlab.com/allianceauth/allianceauth/auth:v5.0.1
FROM ${AA_DOCKER_TAG}

USER root
RUN pip install --no-cache-dir flit_core whitenoise
USER allianceauth
