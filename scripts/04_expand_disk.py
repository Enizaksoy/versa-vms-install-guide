"""
After ESXi disk expand: grow partition + resize filesystem.
Then verify disk >= 1024 GiB so VMS install passes.
"""
import sys, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST = '192.168.30.15'
USER = 'admin'
PASSWORD = '<default-ova-pass>'

def run(c, cmd, sudo=False, timeout=60):
    full = f"echo '{PASSWORD}' | sudo -S -p '' bash -c \"{cmd}\"" if sudo else cmd
    print(f"$ {cmd}")
    _, o, e = c.exec_command(full, timeout=timeout)
    rc = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip() and 'password for' not in err:
        print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")
    return rc, out, err

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASSWORD, timeout=15,
          allow_agent=False, look_for_keys=False)

print("=== Discover disk layout ===")
run(c, "lsblk", sudo=True)
run(c, "df -h /", sudo=False)
run(c, "fdisk -l 2>/dev/null | head -60", sudo=True)
run(c, "vgs && pvs && lvs", sudo=True)
run(c, "cat /proc/partitions", sudo=False)

c.close()
