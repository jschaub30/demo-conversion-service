# demo-conversion-service
Service for converting image and PDF formats into structured text

More info:
- [Project requirements](https://jeremyschaub.us/posts/post008-distributed/)


### Call the cloud service
TBD

### Run the service locally
To run the service on your local machine, you only need:
- `make`
- `docker`

Install `make`
```sh
brew install make  # OSX
sudo apt-get update && sudo apt-get install build-essential  # Ubuntu
```

Install `docker`:
- [Mac instructions](https://docs.docker.com/desktop/install/mac-install/)
- [Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/)


### Setup for local development
Install Poppler
```sh
brew install poppler # OSX
sudo apt-get update && sudo apt-get install poppler-utils  # Ubuntu
```

Create python virtual environment. Here's how using [`pyenv`](https://github.com/pyenv/pyenv).
```sh
pyenv install 3.10.14
pyenv virtualenv 3.10.14 convert
pyenv activate convert
```
