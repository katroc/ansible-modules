#!/usr/bin/python

import subprocess
from ansible.module_utils.basic import AnsibleModule

def run_command(command):
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode

def main():
    module = AnsibleModule(
        argument_spec=dict(),
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(changed=True)

    cmd = ['realm', 'list']

    # Check if the system is already part of any realm
    stdout, stderr, rc = run_command(cmd)

    if rc != 0:
        module.fail_json(msg="Failed to list realms", stderr=stderr, stdout=stdout, rc=rc)
    
    if not stdout:
        # No realm to leave, exit with a success message
        module.exit_json(changed=False, msg="No realm to leave", stdout=stdout, stderr=stderr)
    
    # Leave the realm
    cmd = ['realm', 'leave']
    stdout, stderr, rc = run_command(cmd)
    
    if rc != 0:
        module.fail_json(msg="Failed to leave realm", stderr=stderr, stdout=stdout, rc=rc)
    
    module.exit_json(changed=True, msg="Successfully left the realm", stdout=stdout, stderr=stderr)

if __name__ == '__main__':
    main()
