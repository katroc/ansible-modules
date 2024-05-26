#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
import subprocess

def run_command(module, command, input_data=None):
    """Run a shell command and return the output, error, and exit code."""
    try:
        result = subprocess.run(command, input=input_data, text=True, capture_output=True, check=True)
        stdout = result.stdout

        # Filter out the password prompt from stdout
        filtered_stdout_lines = [line for line in stdout.splitlines() if "Password for" not in line]
        filtered_stdout = "\n".join(filtered_stdout_lines)

        stderr = result.stderr

        return filtered_stdout, stderr, result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode  # Capture the exception and return its attributes


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
        argument_spec=dict(
            domain=dict(type='str', required=True),
            user=dict(type='str', required=True),
            password=dict(type='str', required=True, no_log=True),
            computer_ou=dict(type='str', required=False),
            manage_sssd=dict(type='bool', default=True)
        ),
        supports_check_mode=True
    )

    domain = module.params['domain']
    user = module.params['user']
    password = module.params['password']
    computer_ou = module.params.get('computer_ou')
    manage_sssd = module.params['manage_sssd']

    if module.check_mode:
        module.exit_json(changed=True)

    cmd = ['realm', 'join', '--user', user, domain]
    if computer_ou:
        cmd.extend(['--computer-ou', computer_ou])
    if manage_sssd:
        cmd.append('--automatic-id-mapping=no')

    stdout, stderr, rc = run_command(module, cmd, input_data=password)

    # Check if the command failed and the system is already joined
    if rc != 0:
        if "Already joined to this domain" in stderr:
            # System is already joined, print the message to stdout
            module.exit_json(changed=False, msg="System is already joined to the realm", stdout=stdout, stderr="")
        else:
            # Another error occurred, fail the task
            module.fail_json(msg="Failed to join realm", stderr=stderr, stdout=stdout, rc=rc)

    # Retrieve realm details after successful join
    realm_details_str, stderr, rc = run_command(module, ['realm', 'list'])
    if rc != 0:
        module.fail_json(msg="Failed to retrieve realm details after join", stderr=stderr, stdout=realm_details_str, rc=rc)

    realm = parse_realm_details(realm_details_str)

    module.exit_json(changed=True, msg=f"Successfully joined to {domain}", stdout=stdout, stderr=stderr, realm=realm)

if __name__ == '__main__':
    main()
