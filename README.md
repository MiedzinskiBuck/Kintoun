<p align="center">
    <img src=https://github.com/MiedzinskiBuck/Kintoun/assets/41388860/79376afe-2eb3-4264-a0ea-9b5e7da85842>
</p>

#

[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)

Tool designed to help in Cloud Security testing. This project started as a way to learn more about AWS attacks.

At the moment, KintoUn only provides support for AWS environments so this documentation will focus on the AWS aspect of the tool. Once it starts to implement other Cloud Providers, the propper changes will be done to this document.

A lot of this project is inspired by Pacu, from Rhino Security, which is one of the best offensive AWS tools that is out there. If you are looking for a full testing framework for AWS Environments, make sure to check their [Github repo](https://github.com/RhinoSecurityLabs/pacu) out.

Please refer to the [Wiki](https://github.com/MiedzinskiBuck/Kintoun/wiki) for more information about the Tool's features.

## Running With Docker
KintoUn is an interactive script, so if you want to use docker to run it, follow those steps:

```
docker built -t kintoun [myrepo]
docker run -i miedzinski/kintoun [ARGUMENTS]
```

## TODO
Improve docker experience and overal improvements

