#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import subprocess

def run_command(module, command):
    """Run a shell command and return the output, error, and exit code."""
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        return result.stdout, result.stderr, result.returncode
    except subprocess.CalledProcessError as e:
        module.fail_json(msg="Command failed", stderr=e.stderr, stdout=e.stdout, rc=e.returncode)

def parse_realm_details(realm_details_str):
    """Parse realm details string and return as a dictionary."""
    lines = realm_details_str.split('\n')
    realm_details_dict = {}
    for line in lines:
        parts = line.split(': ')
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()
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
        argument_spec=dict(),
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(changed=False)

    cmd = ['realm', 'list']
    
    stdout, stderr, rc = run_command(module, cmd)
    if rc != 0:
        module.fail_json(msg="Failed to list realms", stderr=stderr, stdout=stdout, rc=rc)
    
    if not stdout.strip():
        module.exit_json(changed=False, msg="No realms to list", realms=[])
    
    realm = parse_realm_details(stdout)
    
    module.exit_json(changed=False, msg="Realm list retrieved successfully", realm=realm)

if __name__ == '__main__':
    main()
