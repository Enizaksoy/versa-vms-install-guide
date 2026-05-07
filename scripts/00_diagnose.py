"""
VMS pre-install diagnostic — read-only.
SSH to current VMS IP and capture state. No changes made.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import paramiko

HOST = '192.168.30.59'
USER = 'admin'
PASSWORD = '<default-ova-pass>'

def run(client, cmd, sudo=False):
    if sudo:
        full = f"echo '{PASSWORD}' | sudo -S -p '' {cmd}"
    else:
        full = cmd
    stdin, stdout, stderr = client.exec_command(full, timeout=30)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    rc = stdout.channel.recv_exit_status()
    return rc, out, err

def main():
    print(f"=== Connecting to {HOST} as {USER} ===")
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cli.connect(HOST, username=USER, password=PASSWORD, timeout=15, allow_agent=False, look_for_keys=False)
    except Exception as e:
        print(f"SSH connect FAILED: {e}")
        return 1
    print("Connected.\n")

    checks = [
        ("hostname",                    "hostname",                                    False),
        ("uname -a",                    "uname -a",                                    False),
        ("os release",                  "cat /etc/os-release",                         False),
        ("ip addr",                     "ip -br addr",                                 False),
        ("ip route",                    "ip route",                                    False),
        ("/etc/network/interfaces",     "cat /etc/network/interfaces",                 True),
        ("/etc/hosts",                  "cat /etc/hosts",                              False),
        ("/etc/resolv.conf",            "cat /etc/resolv.conf",                        False),
        ("vsh status",                  "vsh status",                                  False),
        ("versa package info",          "ls /opt/versa/ 2>/dev/null",                  False),
        ("docker ps (if any)",          "docker ps 2>/dev/null | head -20",            True),
        ("disk usage",                  "df -h | head -20",                            False),
        ("memory",                      "free -h",                                     False),
        ("cpu count",                   "nproc",                                       False),
        ("uptime",                      "uptime",                                      False),
        ("vsh help (top)",              "vsh --help 2>&1 | head -40",                  False),
    ]

    for label, cmd, sudo in checks:
        print(f"--- {label} ---")
        rc, out, err = run(cli, cmd, sudo=sudo)
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print(f"[stderr] {err.rstrip()}")
        if rc != 0 and not out.strip():
            print(f"[rc={rc}]")
        print()

    cli.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())
