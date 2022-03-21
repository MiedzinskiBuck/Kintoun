# KINTOUN

[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)

Tool to help in AWS testing. This project started as a way to learn more about AWS attacks.

The main goal of this project is to learn more about AWS and attack paths. Eventually, it will become a tool to help automates tasks and expand to other platforms such as AZURE and Google Cloud Platform.

The main idea behind this tool is to make it flexible and allow it to growth as new features and vulnerabilities are introduced into the AWS environment while keeping its code base simple, but also beeing able to run its modules on their own with few modifications.

A lot of this project is inspired by Pacu, from Rhino Security, which is one of the best offensive AWS tools that is out there. If you are looking for a full testing framework, make sure to check their [Github repo](https://github.com/RhinoSecurityLabs/pacu) out.

## To Do

- Results module
- Lambda Enumeration
- CloudFormation Enumeration
- RDS Enumeration
- Privilege escalation Modules (WIP)

## MODULES 

To facilitate parsing, all modules main functions receives at least a "selected_session", which will be used to store results and the actual "session", which will be used to create a boto3 client.

The tools is "module based" which means that we have a main program that dinamically loads the required modules to run.

The modules will follow a template that will allow each module to be loaded and ran by demmand.

### MAIN Function

When you select a module to run, Kinto-un will dinamically load this module and call it's "main" function, that will then orchestrate the remaining of the actions to be perform and, if applicable, return the results of the module to be parsed and then stored for further analysis.

### HOW TO CREATE A MODULE

Once a module is selected **AWSerialKiller** will load this module in runtime and call its **main()** function, passing the current session to it. 

In order to create a module, it is just a matter of creating a **main()** function that will receive the current session and perform other actions with this session's context.
