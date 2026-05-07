"""
After successful VMS install:
  1. Verify final state (kubectl pods, vsh status)
  2. Export certs from /var/tmp/copy_certs/ for Director upload
  3. Test HTTPS endpoint
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'

s = VmsSSH(HOST, USER, PASSWORD)

print("=== vsh status (final) ===")
s.run("vsh status 2>&1 | head -30", login=True)

print("\n=== K8s pods (all namespaces) ===")
s.run("kubectl get pods --all-namespaces -o wide 2>&1 | head -50", sudo=True)

print("\n=== K8s services (LoadBalancer) ===")
s.run("kubectl get svc --all-namespaces 2>&1 | head -30", sudo=True)

print("\n=== Cluster info ===")
s.run("kubectl get nodes -o wide 2>&1", sudo=True)

print("\n=== Certificates in /var/tmp/copy_certs/ (for Director upload) ===")
s.run("ls -la /var/tmp/copy_certs/", sudo=True)

print("\n=== Pull certs to workstation ===")
sftp = s.client.open_sftp()
local_dir = r'C:\Claude\vms_install\certs'
os.makedirs(local_dir, exist_ok=True)

for f in ['root-ca-cert.pem', 'ca-cert-bundle.pem', 'server-cert.pem']:
    remote = f'/var/tmp/copy_certs/{f}'
    local = os.path.join(local_dir, f'final_{f}')
    try:
        s.run(f"chmod 644 {remote}", sudo=True, quiet=True)
        sftp.get(remote, local)
        print(f"✓ {remote} → {local}")
    except FileNotFoundError:
        print(f"✗ {remote} not found")
    except Exception as e:
        print(f"✗ {remote}: {e}")
sftp.close()

print("\n=== HTTPS endpoint test (Elastic IP) ===")
s.run("curl -k -s -o /dev/null -w 'HTTPS Elastic IP: %{http_code} (%{time_total}s)\\n' https://192.168.30.16:443/ --max-time 10")
s.run("curl -k -s -o /dev/null -w 'HTTPS Elastic FQDN: %{http_code}\\n' https://vms-1-elastic.mylab.com/ --max-time 10")
s.run("curl -k -s -o /dev/null -w 'HTTPS API: %{http_code}\\n' https://192.168.30.16:8091/ --max-time 10")

print("\n=== Memory/CPU after install ===")
s.run("free -h && echo --- && uptime && echo --- && df -h /")

s.close()
