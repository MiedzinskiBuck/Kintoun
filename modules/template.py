import boto3

def create_client(botoconfig, session):
    client = session.client('SERVICE-CHANGE-THIS', config=botoconfig)
    return client

# This is the help section. When used, it should print any help to the functionality of the module that may be necessary.
def help():
    pass

# The main function will orchestrate the functionality of the module. The idea is that it will call whatever needs calling and retur the results from the module to be parsed and stored.
# It will be called from the main program with the botoconfig, that changes the user agent, and the session, which stores the profile credentials to be used.
def main(botoconfig, session):
    # module code, calls, etc...
    # return module_results
    pass