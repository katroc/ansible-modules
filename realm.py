#!/usr/bin/python3

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = '''
---
module: realm
short_description: Runs the realm command to join or leave an Active Directory domain
description:
    - Runs the realm command to join or leave an Active Directory domain.
attributes:
    check_mode:
        support: full
    diff_mode:
        support: none
options:
    domain:
        type: str
        description:
            - The domain to join or leave.
        required: true
    user:
        type: str
        description:
            - The user to use for joining the domain.
        required: false
    password:
        type: str
        description:
            - The password to use for the domain account.
        required: false
        no_log: true
    state:
        type: str
        description:
            - The state of the value for the key.
            - Can be present or absent.
        required: true
        choices: [ present, absent ]
requirements:
    - sssd 
    - realmd 
    - oddjob 
    - oddjob-mkhomedir 
    - adcli 
    - samba-common 
    - samba-common-tools 
    - krb5-workstation 
    - openldap-clients
author:
    - nil nil.nul@nil.com>
'''

EXAMPLES = '''
- name: Join Domain
  realm:
    domain: example.com
    user: example_user
    password: example_password
    state: present
    
- name: Leave Domain
  realm:
    domain: example.com
    state: absent
'''

import re
from ansible.module_utils.basic import AnsibleModule, sanitize_keys

def filter_password_prompts(output):
    filtered_output = re.sub(r'^Password for .+: $', '', output, flags=re.MULTILINE)
    # Strip leading/trailing whitespace and remove empty lines
    return '\n'.join([line for line in filtered_output.splitlines() if line.strip()])

def parse_realm_details(realm_details_str):
    realm_details_dict = {}
    for line in realm_details_str.splitlines():
        parts = line.split(': ')
        if len(parts) == 2:
            key, value = parts
            key, value = key.strip(), value.strip()
            if value:
                if key in realm_details_dict:
                    if isinstance(realm_details_dict[key], list):
                        realm_details_dict[key].append(value)
                    else:
                        realm_details_dict[key] = [realm_details_dict[key], value]
                else:
                    realm_details_dict[key] = value
    return realm_details_dict

def main():
    module = AnsibleModule(
        argument_spec=dict(
            domain=dict(type='str', required=True),
            user=dict(type='str', required=False),
            password=dict(type='str', required=False, no_log=True),
            computer_ou=dict(type='str', required=False),
            state=dict(type='str', choices=['present', 'absent'], default='present')
        ),
        supports_check_mode=True
    )

    domain = module.params['domain']
    user = module.params['user']
    password = module.params['password']
    computer_ou = module.params.get('computer_ou')
    state = module.params['state']

    if module.check_mode:
        module.exit_json(changed=True)

    result = {'changed': False, 'msg': '', 'stdout': '', 'stderr': '', 'realm': {}, 'cmd': ''}

    if state == 'present':
        cmd = ['realm', 'join', '--user', user, domain]
        if computer_ou:
            cmd.extend(['--computer-ou', computer_ou])
        result['cmd'] = ' '.join(cmd)

        rc, stdout, stderr = module.run_command(cmd, data=password)
        stdout = filter_password_prompts(stdout)
        result['stdout'] = stdout

        if rc != 0:
            if "Already joined to this domain" in stderr:
                result['msg'] = f"Host is already joined to {domain}"
                module.exit_json(**sanitize_keys(result, no_log_strings=[]))
            else:
                result['msg'] = "Failed to join realm"
                result['stderr'] = stderr
                result['rc'] = rc
                module.fail_json(**sanitize_keys(result, no_log_strings=[]))

        rc, realm_details_str, stderr = module.run_command(['realm', 'list'])
        if rc != 0:
            result['msg'] = "Failed to retrieve realm details after join"
            result['realm'] = realm_details_str
            result['stderr'] = stderr
            result['rc'] = rc
            module.fail_json(**sanitize_keys(result, no_log_strings=[]))

        realm = parse_realm_details(realm_details_str)
        result['changed'] = True
        result['msg'] = f"Successfully joined {domain}"
        result['realm'] = sanitize_keys(realm, no_log_strings=[])
        module.exit_json(**sanitize_keys(result, no_log_strings=[]))

    elif state == 'absent':
        cmd = ['realm', 'leave', domain]
        result['cmd'] = ' '.join(cmd)

        rc, stdout, stderr = module.run_command(cmd, data=password)
        stdout = filter_password_prompts(stdout)
        result['stdout'] = stdout

        if rc != 0:
            if "Not joined to this domain" in stderr:
                result['msg'] = f"Host is not joined to {domain}"
                module.exit_json(**sanitize_keys(result, no_log_strings=[]))
            else:
                result['msg'] = "Failed to leave realm"
                result['stderr'] = stderr
                result['rc'] = rc
                module.fail_json(**sanitize_keys(result, no_log_strings=[]))

        result['changed'] = True
        result['msg'] = f"Successfully left {domain}"
        module.exit_json(**sanitize_keys(result, no_log_strings=[]))

if __name__ == '__main__':
    main()
