#!/bin/bash

daemon -rU --name weditor --chdir=$PWD --stdout $PWD/stdout.log --stderr $PWD/stderr.log -- python -m weditor -q
