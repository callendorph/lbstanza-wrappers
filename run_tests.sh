#!/bin/bash

which stanza
if [ $? -ne 0 ] ; then
  echo "No Stanza Found on PATH"
  exit 1
fi

set -e
python -m unittest discover .