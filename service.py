#!/usr/bin/python3 -u
# coding: utf-8

# Import libraries
import sys

# Import classes
from src.controllers.App.Service import Service

# Instantiate Service class
my_service = Service()

# If an argument is passed, execute the corresponding module agent
if len(sys.argv) > 1:
    my_service.run_agent(sys.argv[1])
    exit(0)

# Else, execute main function
my_service.main()

exit(0)
