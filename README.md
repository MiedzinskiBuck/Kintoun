<p align="left">
    <img src="https://user-images.githubusercontent.com/41388860/164986870-09e9890c-1633-4ecc-9dda-64be2b11761e.png"/>
</p>

#

[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)

Tool designed to help in Cloud Security testing. This project started as a way to learn more about AWS attacks.

At the moment, KintoUn only provides support for AWS environments so this documentation will focus on the AWS aspect of the tool. Once it starts to implement other Cloud Providers, the propper changes will be done to this document.

A lot of this project is inspired by Pacu, from Rhino Security, which is one of the best offensive AWS tools that is out there. If you are looking for a full testing framework for AWS Environments, make sure to check their [Github repo](https://github.com/RhinoSecurityLabs/pacu) out.

## Installation

KintoUn is a python3 tool so, to use it you will need to have "Python3" installed on your machine and install the required packages.

```
sudo apt-get install python3
git clone https://github.com/MiedzinskiBuck/Kintoun.git
cd Kintoun
pip3 install -r requirements.txt
```

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

To facilitate parsing, all modules main functions receives a "selected_session" parameter, which is the "Session Name" and will be used to store all module's results, the actual "session" object, and a botoconfig object. The botoconfig and session objects can be passed to the "create_client" function to create a client to perform the API Calls.

To create a client, if you started your module using the provided template, all you need to do is to instantiate a "Client()" object passing the botoconfig objetc, the session object, the service name and, optionally, the region to make the calls. Then, with the client configuration set, you can call the "create_aws_client()" function to receive the actual client object.

***Example:***
```
client = create_client.Client(botoconfig, session, 'iam')
iam_client = client.create_aws_client()
```
Now you can use the "iam_client" object to perform API Calls related to the "iam" service.

This tool is "module based" which means that we have a main program that dinamically loads the required modules to run, so you can customize it with your own modules or even use those modules in another program.

The modules will follow a template that will ease developing of new modules and allow for some standardization.

### MAIN Function

When you select a module to run, Kinto-un will dinamically load this module and call it's "main" function, that will then orchestrate the remaining of the actions to be perform and, if applicable, return the results of the module to be parsed and then stored for further analysis.

### HELP Function

Allong with the "main()" function, ***KintoUn's*** modules also provide a "help" section that should explain what each module can do. When developing new modules, please do create this code section to help users understand what the created module can do and what are the consequences of running that module, if any.

## To Do

- Results module
    - Currently the results are stored on disk and can only be readed manually or on screen when its module is ran. I want to create a functionality that allows you to fetch a module's results from within the program.
- Enumeration Modules
    - Finish to create enumeration modules. Although this is an ongoing task, I believe that we need to cover at least the main services that AWS has to offer before releasing a version of the Tool.
- Cloud Providers Support
    - KintoUn's main goal is to become a Cloud Testing tool and, to do so, it must provide support for other Cloud Providers than AWS. Currently, it only supports AWS Testing.
