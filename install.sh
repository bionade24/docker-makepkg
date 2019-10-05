#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

cp -f bin/dmakepkg.py /usr/local/bin/dmakepkg
cp -f $PWD/containerBuilder.py /usr/local/share/docker-makepkg
cp -f $PWD/run.py /usr/local/share/docker-makepkg