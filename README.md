# KINTOUN
<p align="left">
    <img src="https://user-images.githubusercontent.com/41388860/164986870-09e9890c-1633-4ecc-9dda-64be2b11761e.png"/>
</p>

[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)

Tool designed to help in Cloud Security testing. This project started as a way to learn more about AWS attacks.

At the moment, KintoUn only provides support for AWS environments so this documentation will focus on the AWS aspect of the tool. Once it starts to implement other Cloud Providers, the propper changes will be done to this document.

A lot of this project is inspired by Pacu, from Rhino Security, which is one of the best offensive AWS tools that is out there. If you are looking for a full testing framework for AWS Environments, make sure to check their [Github repo](https://github.com/RhinoSecurityLabs/pacu) out.

## Description

The main goal behind this tool is to make it flexible and allow it to growth as new features and vulnerabilities are introduced into Cloud Environments while keeping its code base simple. That is the main reason that the tool follows a "modular" approach, where the desired modules are loaded dinamically and can also be used on its on for a more customized approach.

Since all modules are designed to be able to run on their own, they can be imported by other scripts with very little modification needed. To run a module, you need to basically call its "main()" function passing a botoconfig object, a session object and a session name that could be basically any string you wish. More about what each object represents on the following sections.

### Botoconfig Object

The botoconfig object is for configuring client-specific configurations that affect the behaviour of your specific client object only. The options used supersede those found in other configuration locations. On ***KintoUn***, they are used mainly to validate the "user-agent" configuration used.

When ***KintoUn*** starts executing, it checks for the "user-agent" configuration of the system using the "boto3.session.Session()._session.user_agent()" call. Then, it tries to determine if the "user-agent" configuration corresponds to either Kali Linux, Parrot or Pentoo and, if it does, it will use a "user-agent list" that is stored on "data/user_agents.txt" to randomly change this value.

Then, it will create a config object called "botocore_config", which is the result of the function "botocore.config.Config()", and return this object to the main program, that will then pass this botoconfig object to the "main()" function of the loaded modules.

### Session Object

Accordingly to the official boto3 [Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/session.html), a Session manages state about a particular configuration. You can use this session to store your AWS Credentials, default region and other configurations.

On ***KintoUn*** we use this session object to store the profile keys that you will select at the start of the program. Then, with all modules will be called with this session's context.

### Session Name

The "Session Name" is a way for ***KintoUn*** to be able to distinguish between executions and to propperly store the module's results. It uses this "session name" to create a directory on which it stores the results. The created directory will have the name of the current session, so if a session has a name of "HackerSession", all its module's results would be stored at "results/HackerSession/*".

## MODULES 

To facilitate parsing, all modules main functions receives at least a "selected_session", which will be used to store results and the actual "session", which will be used to create a boto3 client.

The tools is "module based" which means that we have a main program that dinamically loads the required modules to run.

The modules will follow a template that will allow each module to be loaded and ran by demmand.

### MAIN Function

When you select a module to run, Kinto-un will dinamically load this module and call it's "main" function, that will then orchestrate the remaining of the actions to be perform and, if applicable, return the results of the module to be parsed and then stored for further analysis.

### HOW TO CREATE A MODULE

Once a module is selected **KintoUn** will load this module in runtime and call its **main()** function, passing the current session to it. 

In order to create a module, it is just a matter of creating a **main()** function that will receive the current session and perform other actions with this session's context.

You can follow the "template.py" file to create a module.

## To Do

- Results module
- CloudFormation Enumeration
