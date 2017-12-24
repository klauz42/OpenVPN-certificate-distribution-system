#!/usr/bin/python
import cgitb
from os import chdir, environ
from subprocess import Popen, PIPE
import sqlite3
import re

print("Content-Type: text/html\n\n")

# bruteforce protection
remote_addr = environ["REMOTE_ADDR"]
db = '/var/www/cgi-bin/connections.sqlite'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("INSERT INTO conns (ip, timestamp) VALUES (\"" + remote_addr + "\", strftime('%s','now'))")
c.execute("SELECT count(ip) FROM conns WHERE ip=\"" + remote_addr + "\" AND timestamp>strftime('%s','now')-1000")
try:
    counts = c.fetchall()[0][0]
    assert counts < 10
except AssertionError:
    print "<h1>403 Forbidden Error</h1>"
    exit(0)
finally:
    conn.commit()
    c.close()
    conn.close()

cgitb.enable()
easy_rsa_dir = "/var/www/cgi-bin/openvpn"
user_shell = "/bin/bash"


def file_to_string(path):
    cat = Popen(["cat " + path],
                stdout=PIPE, stderr=PIPE, shell=True)
    cat.wait()
    return cat.communicate()[0]


# curl tese
http_user_agent = environ["HTTP_USER_AGENT"]
if not re.search(r"curl", http_user_agent):
    print '<h1>Please, use command: <font face="Courier New"> curl ' + environ["SERVER_ADDR"] +\
          '/cgi-bin/keygenerate.py | sudo sh</font></h1>'
    exit(1)

user = str(environ["REMOTE_USER"])
chdir(easy_rsa_dir)
source_process = Popen(["source ./vars && export KEY_CN=" + user + "&& ./pkitool " + user],
                       stdout=PIPE, stderr=PIPE, shell=True)
source_process.wait()

secret_key_path = easy_rsa_dir + "/keys/" + user + ".key"
certificate_path = easy_rsa_dir + "/keys/" + user + ".crt"
ta_key_path = easy_rsa_dir + "/ta.key"

client_config = "client\n" \
                "dev tun\n" \
                "proto udp\n" \
                "remote " + environ["SERVER_ADDR"] + " 1194\n" \
                "resolv-retry infinite\n" \
                "nobind\n" \
                "persist-key\n" \
                "persist-tun\n" \
                "ca /etc/openvpn/ca.crt\n" \
                "cert /etc/openvpn/" + user + ".crt\n" \
                "key  /etc/openvpn/" + user + ".key\n" \
                "comp-lzo\n" \
                "verb 3"

secret_key = file_to_string(secret_key_path)
certificate = file_to_string(certificate_path)
ta_key = file_to_string(ta_key_path)

if len(certificate) == 0:
    print 'echo "Keys was issued earlier. Please contact your administrator."'
    exit(1)

# client script
user_script = "#!" + user_shell + "\n\n"
user_script += "yum update -y\n"
user_script += "yum install epel-release -y\n"
user_script += "yum install openvpn -y\n"
user_script += "yum install easy-rsa -y\n"
user_script += "mkdir /etc/openvpn\n"
user_script += "cp -rf /usr/share/easy-rsa/2.0/* /etc/openvpn\n"
user_script += "cd /etc/openvpn\n"
user_script += "echo \"" + certificate + "\" > " + user + ".crt\n"
user_script += "echo \"" + secret_key + "\" > " + user + ".key\n"
user_script += 'echo "' + ta_key + '" > ta.key\n'
user_script += 'echo "' + client_config + '" > client.config\n'

print user_script

source_process = Popen(["rm -f " + secret_key_path],
                       stdout=PIPE, stderr=PIPE, shell=True)
source_process.wait()
