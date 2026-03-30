
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

## Web Control Plane (Flask)
Kintoun now includes a web control plane so multiple operators can:
- Manage AWS credentials (stored encrypted at rest)
- Launch modules from a shared UI
- Provide interactive module inputs
- Track run status and review logs/results

### Run locally
```bash
pip install -r requirements.txt
python run_web.py
```

Then open:
```text
http://127.0.0.1:5000
```

### Default login
- Username: `admin`
- Password: `admin123!`

You should override these in production:
```bash
export KINTOUN_ADMIN_USER=operator_admin
export KINTOUN_ADMIN_PASS='strong-password-here'
export KINTOUN_WEB_SECRET='strong-random-secret'
export KINTOUN_CRED_KEY='separate-credential-encryption-secret'
export KINTOUN_WEB_DB='/opt/kintoun/kintoun_web.db'
```

### Notes
- The web runner executes existing module `main(botoconfig, session)` functions.
- Modules that call `input()` require values to be supplied in the UI (`one value per line`).
- Runs are asynchronous and store stdout/stderr/result payloads for audit and review.

