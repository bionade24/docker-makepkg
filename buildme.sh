#! /bin/sh

docker build --pull --no-cache -t makepkg "$(dirname $0)"
