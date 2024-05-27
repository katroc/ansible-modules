#!/usr/bin/python
from ansible.module_utils.basic import AnsibleModule
import requests
from requests_ntlm import HttpNtlmAuth
import re
import warnings

def get_ndes_otp(url, username, password, domain, ca_cert=None):
    try:
        response = requests.get(url, auth=HttpNtlmAuth(f"{domain}\\{username}", password), verify=(ca_cert if url.startswith('https') else False))
        response.raise_for_status()
    except requests.RequestException as e:
        return None, f"Error: {e}"

    if response.status_code == 200:
        html_content = response.content.decode('utf-16-le')
        otp_matches = re.findall(r'[A-F0-9]{16}', html_content)  # Assuming OTP length is fixed to 16 characters
        if otp_matches:
            return otp_matches[0], None
        else:
            return None, "No OTP found in HTTP Response. Check your Permissions."
    else:
        return None, f"Got HTTP Response {response.status_code}."

def main():
    module = AnsibleModule(
        argument_spec=dict(
            url=dict(type='str', required=True),
            username=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            domain=dict(type='str', required=True),
            ca_cert=dict(type='str', default=None)
        )
    )

    url = module.params['url']
    username = module.params['username']
    password = module.params['password']
    domain = module.params['domain']
    ca_cert = module.params['ca_cert']

    otp, error = get_ndes_otp(url, username, password, domain, ca_cert)
    if error:
        module.fail_json(msg=error)
    else:
        module.exit_json(changed=False, otp=otp)

if __name__ == '__main__':
    main()
