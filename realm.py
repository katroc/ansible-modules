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

def set_result(result, changed=False, msg='', stdout='', stderr='', realm=None, cmd='', rc=None):
    result.update({
        'changed': changed,
        'msg': msg,
        'stdout': stdout,
        'stderr': stderr,
        'realm': realm if realm is not None else {},
        'cmd': cmd,
        'rc': rc,
    })

def join_realm(module, result, domain, user, password, computer_ou):
    cmd = ['realm', 'join', '--user', user, domain]
    if computer_ou:
        cmd.extend(['--computer-ou', computer_ou])
    result['cmd'] = ' '.join(cmd)

    rc, stdout, stderr = module.run_command(cmd, data=password)
    stdout = filter_password_prompts(stdout)
    result['stdout'] = stdout
    result['stderr'] = stderr

    if rc != 0:
        if "Already joined to this domain" in stderr or "Already joined" in stdout:
            set_result(result, msg=f"Host is already joined to {domain}", cmd=result['cmd'], rc=0)
            module.exit_json(**sanitize_keys(result, no_log_strings=[]))
        else:
            set_result(result, msg="Failed to join realm", stderr=stderr, cmd=result['cmd'], rc=rc)
            module.fail_json(**sanitize_keys(result, no_log_strings=[]))

    rc, realm_details_str, stderr = module.run_command(['realm', 'list'])
    if rc != 0:
        set_result(result, msg="Failed to retrieve realm details after join", stderr=stderr, cmd=result['cmd'], rc=rc)
        module.fail_json(**sanitize_keys(result, no_log_strings=[]))

    realm = parse_realm_details(realm_details_str)
    set_result(result, changed=True, msg=f"Successfully joined {domain}", realm=sanitize_keys(realm, no_log_strings=[]), cmd=result['cmd'], rc=0)
    module.exit_json(**sanitize_keys(result, no_log_strings=[]))

def leave_realm(module, result, domain, password):
    cmd = ['realm', 'leave', domain]
    result['cmd'] = ' '.join(cmd)

    rc, stdout, stderr = module.run_command(cmd, data=password)
    stdout = filter_password_prompts(stdout)
    result['stdout'] = stdout
    result['stderr'] = stderr

    if rc != 0:
        if "Not joined to this domain" in stderr:
            set_result(result, msg=f"Host is not joined to {domain}", cmd=result['cmd'], rc=0)
            module.exit_json(**sanitize_keys(result, no_log_strings=[]))
        else:
            set_result(result, msg="Failed to leave realm", stderr=stderr, cmd=result['cmd'], rc=rc)
            module.fail_json(**sanitize_keys(result, no_log_strings=[]))

    set_result(result, changed=True, msg=f"Successfully left {domain}", cmd=result['cmd'], rc=0)
    module.exit_json(**sanitize_keys(result, no_log_strings=[]))

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
        module.exit_json(changed=False, msg="Check mode: no changes made")

    result = {'changed': False, 'msg': '', 'stdout': '', 'stderr': '', 'realm': {}, 'cmd': '', 'rc': 0}

    if state == 'present':
        join_realm(module, result, domain, user, password, computer_ou)
    elif state == 'absent':
        leave_realm(module, result, domain, password)

if __name__ == '__main__':
    main()
