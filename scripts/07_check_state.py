"""Verify password change took effect and check if 'default password' warning is gone."""
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
    full = f"echo '{PASSWORD}' | sudo -S -p '' bash -c \"{cmd}\"" if sudo else cmd
    print(f"$ {cmd}")
    _, o, e = c.exec_command(full, timeout=30)
    rc = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip() and 'password for' not in err: print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")
    return out + err

# vsh status — does default-password warning still appear?
status_out = run("vsh status 2>&1 | head -60")
default_warning = 'default/expired passwords' in status_out
print(f"\n[default password warning still present? {default_warning}]\n")

# Also check passwd state for both users
run("getent passwd admin versa", sudo=False)
run("chage -l admin", sudo=True)
run("chage -l versa", sudo=True)

# Show /etc/shadow ages (to detect default vs custom)
run("awk -F: '$1 ~ /admin|versa/ {print $1, $3}' /etc/shadow", sudo=True)

c.close()
