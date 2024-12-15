# platform

Stands up multiple microservice so they can be contacted using a single URI with `nginx` and `docker`.
Each service is stored as a git submodule, view each service for more information on that particular feature.

## Requirements

- [`docker`](https://www.docker.com/)

## How to run

1. `docker build -t platform .` # assuming you are building from this directory with the `Dockerfile`
2. `docker run -p 80:80 platform` # starts the services on port 80
