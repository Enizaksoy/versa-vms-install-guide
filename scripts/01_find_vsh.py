"""Locate vsh binary and check Versa version."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST, USER, PASSWORD = '192.168.30.59', 'admin', '<default-ova-pass>'

def run(c, cmd, sudo=False):
    full = f"echo '{PASSWORD}' | sudo -S -p '' {cmd}" if sudo else cmd
    _, o, e = c.exec_command(full, timeout=30)
    return o.read().decode(errors='replace'), e.read().decode(errors='replace')

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASSWORD, timeout=15, allow_agent=False, look_for_keys=False)

cmds = [
    "find /opt/versa -name 'vsh' -type f 2>/dev/null",
    "find / -name 'vsh' -type f 2>/dev/null | head -5",
    "ls /opt/versa/bin/ 2>/dev/null | head -30",
    "ls /opt/versa/scripts/ 2>/dev/null | head -30",
    "cat /opt/versa/vms/version 2>/dev/null",
    "cat /opt/versa/etc/version* 2>/dev/null",
    "find /opt/versa -name 'version*' -maxdepth 3 2>/dev/null",
    "cat /etc/profile.d/*versa* 2>/dev/null",
    "echo $PATH",
    "ls -la /opt/versa/scripts/certificates/ 2>/dev/null",
    "ls -la /opt/versa/vms/ 2>/dev/null",
]
for cmd in cmds:
    print(f"$ {cmd}")
    o, e = run(c, cmd, sudo=True)
    if o.strip(): print(o.rstrip())
    if e.strip() and 'password' not in e: print(f"[err] {e.rstrip()}")
    print()

c.close()
