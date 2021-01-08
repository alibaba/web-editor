# coding: utf-8
#
import os
import pkg_resources

version_file = os.path.realpath(os.path.dirname(os.path.realpath("{}".format(__file__))) + "../../../version")

if os.path.isfile(version_file):
    __version__ = open(version_file, "r").read()
else:
    __version__ = "unknown"
