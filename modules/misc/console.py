import boto3

def create_console_link(session, profile):
    print("[+] Getting login information for: {}".format(profile))
    try:
        console_function = console.Console()
        console_link = console_function.get_console_link(session, profile)
        print("[+] Console Link: {}".format(console_link))
    except Exception as e:
        print(e)
