#!/bin/bash

daemon -rU --name weditor --stdout $PWD/stdout.log --stderr $PWD/stderr.log -- python -m weditor -q
