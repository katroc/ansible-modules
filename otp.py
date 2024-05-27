#!/usr/bin/python
from ansible.module_utils.basic import AnsibleModule
import requests
from requests_ntlm import HttpNtlmAuth
import re

DOCUMENTATION = '''
---
module: adcs_ndes_otp
short_description: Retrieve OTP from ADCS NDES service.
description:
    - This module retrieves a one-time password (OTP) from the Network Device Enrollment Service (NDES) of an Active Directory Certificate Services (ADCS) server.
author: 
    - Your Name
options:
    url:
        description:
            - The URL of the NDES service.
        required: true
        type: str
    username:
        description:
            - The username for authentication.
        required: true
        type: str
    password:
        description:
            - The password for authentication.
        required: true
        type: str
    domain:
        description:
            - The domain of the user account.
        required: true
        type: str
    ca_cert:
        description:
            - The path to the CA certificate file for SSL verification.
        required: false
        type: str
'''

EXAMPLES = '''
- name: Retrieve OTP from ADCS NDES service
  adcs_ndes_otp:
    url: "http://ca/certsrv/mscep_admin"
    username: "username"
    password: "password"
    domain: "example.com"
  register: otp_result
'''

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
        ),
        supports_check_mode=False
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
