"""Verify vsh status with full path + check if versa user still has default."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST = '192.168.30.15'
USER = 'admin'
PASSWORD = '<vms-admin-pass>'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASSWORD, timeout=15,
          allow_agent=False, look_for_keys=False)

def run(cmd, sudo=False):
    full = f"echo '{PASSWORD}' | sudo -S -p '' bash -c '{cmd}'" if sudo else cmd
    print(f"$ {cmd}")
    _, o, e = c.exec_command(full, timeout=30)
    rc = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip() and 'password for' not in err: print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")
    return out + err

# Try vsh with full path AND login shell
run("bash -lc '/opt/versa/bin/vsh status' 2>&1 | head -60")

# Check shadow line for versa user
run("awk -F: '/^versa:/ || /^admin:/ {print $1, length($2)}' /etc/shadow", sudo=True)

# Check if versa user can login with <default-ova-pass> (means default still)
import paramiko
print("\n=== Trying versa user with default password ===")
c2 = paramiko.SSHClient()
c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    c2.connect(HOST, username='versa', password='<default-ova-pass>', timeout=10,
               allow_agent=False, look_for_keys=False)
    print("[versa user STILL has default password '<default-ova-pass>']")
    c2.close()
    print("=> Need to change versa user password")
except paramiko.AuthenticationException:
    print("[versa user '<default-ova-pass>' rejected — password already changed or login disabled]")

c.close()
