"""Find where vsh is actually defined (it's a function, not a binary)."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASSWORD, timeout=15,
          allow_agent=False, look_for_keys=False)

def run(cmd, sudo=False):
    full = f'echo "$PASSWORD" | sudo -S -p "" {cmd}' if sudo else cmd
    full2 = f'export PASSWORD="{PASSWORD}"; {full}' if sudo else cmd
    print(f"$ {cmd}")
    _, o, e = c.exec_command(full2, timeout=30)
    rc = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace'); err = e.read().decode(errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip() and 'password for' not in err: print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")
    return out

# Login shell — should source profile.d
run("bash -lic 'type vsh' 2>&1")
run("bash -lic 'declare -f vsh' 2>&1 | head -100")
run("bash -lic 'alias vsh' 2>&1")

# List all profile.d files
run("ls /etc/profile.d/")

# Read versa-env in chunks
run("wc -l /etc/profile.d/versa-env.sh")
run("grep -n 'vsh' /etc/profile.d/versa-env.sh | head -30")
run("grep -n 'function vsh\\|^vsh\\|alias vsh' /etc/profile.d/*.sh /etc/bash* /home/admin/.bashrc /home/admin/.bash_profile /etc/skel/.bashrc 2>/dev/null | head")

# Check if there are other versa scripts
run("find /opt/versa -name 'vsh*' -type f 2>/dev/null")
run("find /usr/local -name 'vsh*' 2>/dev/null")
run("find /etc -name '*vsh*' 2>/dev/null")

# Try to grep vsh definition pattern across versa scripts
run("grep -rn 'vsh()' /etc/profile.d/ /opt/versa/scripts/ 2>/dev/null | head -10")

# Look at bashrc for admin
run("cat /home/admin/.bashrc 2>/dev/null | head -50")

# Check shadow status using a less quoting-sensitive command
run("awk -F: 'BEGIN{IGNORECASE=0} /^admin/ || /^versa/ {print $1, $3, length($2)}' /etc/shadow", sudo=True)

c.close()
