"""
Reset CockroachDB after clock skew aftermath.
HLC has timestamps in the future (when we set time to 2026-05-07).
Now real time is 2026-05-06, DB stuck.

Strategy: stop services → wipe DB store → start vms-db → init cluster + schema → start vms-admin.
"""
import sys, time
sys.path.insert(0, '.')
from lib_ssh import VmsSSH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

print("=== Stop services ===")
s.run('systemctl stop vms-admin', sudo=True)
s.run('systemctl stop vms-db', sudo=True)

print("\n=== Find DB store location ===")
s.run('grep -E "DB_STORE|db.data" /etc/systemd/system/vms-db.service /etc/default/vms* 2>&1', sudo=True)
s.run('ls -la /var/lib/db/ /var/lib/db/data/ 2>&1', sudo=True)

print("\n=== Wipe DB store ===")
s.run('rm -rf /var/lib/db/data/*', sudo=True)
s.run('ls -la /var/lib/db/data/ 2>&1', sudo=True)

print("\n=== Time check (must be real time, not future) ===")
s.run('date -u', sudo=False)

print("\n=== Start vms-db (cockroach) ===")
s.run('systemctl start vms-db', sudo=True)
print("Wait 20s for cockroach...")
time.sleep(20)
s.run('systemctl status vms-db --no-pager 2>&1 | head -12', sudo=True)

print("\n=== Test cockroach SQL connectivity ===")
s.run('/usr/local/bin/cockroach sql --certs-dir=/opt/versa/vms/certs/db_certs/ --host=localhost:26257 --execute="SELECT version();" 2>&1', sudo=True)

print("\n=== Init cluster (single-node) ===")
s.run('/usr/local/bin/cockroach init --certs-dir=/opt/versa/vms/certs/db_certs/ --host=localhost:26257 2>&1', sudo=True)

print("\n=== Wait + show databases ===")
time.sleep(5)
s.run('/usr/local/bin/cockroach sql --certs-dir=/opt/versa/vms/certs/db_certs/ --host=localhost:26257 --execute="SHOW DATABASES;" 2>&1', sudo=True)

print("\n=== Apply DB schema (db_script.sql) ===")
s.run('ls -la /opt/versa/vms/db/db_script.sql', sudo=True)
s.run('/usr/local/bin/cockroach sql --certs-dir=/opt/versa/vms/certs/db_certs/ --host=localhost:26257 < /opt/versa/vms/db/db_script.sql 2>&1 | tail -20', sudo=True)

print("\n=== Start vms-admin ===")
s.run('systemctl start vms-admin', sudo=True)
print("Wait 45s for Spring Boot startup...")
time.sleep(45)

print("\n=== vms-admin status ===")
s.run('systemctl status vms-admin --no-pager 2>&1 | head -12', sudo=True)
print()
s.run('grep -i "started\\|running\\|error\\|fail" /var/log/versa/vms/vms-admin.log 2>&1 | tail -15', sudo=True)

print("\n=== Final vsh status ===")
s.run('vsh status 2>&1 | head -20', login=True)

s.close()
