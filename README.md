# AWSERIALKILLER

[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)

Tool to help in AWS testing. This project started as a way to learn more about AWS attacks and, after a while, it became a tool that helped me allong with some aws testing, so I've decided to make it a modular tool.

The main idea behind this tool is to make it flexible and allow it to growth as new features and vulnerabilities are introduced into the AWS environment while keeping its code base simple.

## To Do

- Implement some way to store data.
- Start implementing privesc modules.

## MODULES 

The tools is "module based" which means that we have a main program that dinamically loads the required modules to run.

The modules will follow a template that will allow each module to be loaded and ran by demmand.

### HOW TO CREATE A MODULE

Once a module is selected **AWSerialKiller** will load this module in runtime and call its **main()** function, passing the current session to it. 

In order to create a module, it is just a matter of creating a **main()** function that will receive the current session and perform other actions with this session's context.
