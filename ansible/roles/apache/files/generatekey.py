#!/usr/bin/python
import cgi
import cgitb
import os, subprocess
from subprocess import Popen, PIPE


print("Content-Type: text/html\n\n")

cgitb.enable()
easy_rsa_dir = "/var/www/cgi-bin/openvpn"
user_shell = "/bin/bash"


def command(cmd, out=PIPE, err=PIPE, show=False):
    proc = Popen(
        cmd,
        shell=True,
        stdout=out, stderr=err
    )
    proc.wait()
    res = proc.communicate()
    if show:
        if proc.returncode:
            print res[1] + "\n"
        print res[0] + "\n"


def file_to_string(path):
    cat = subprocess.Popen(["cat " + path],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    cat.wait()
    return cat.communicate()[0]


form = cgi.FieldStorage()
user = str(form.getvalue('user'))
if not user:
    print 'echo "Wrong username/pass pair."'
    exit(1)

os.chdir(easy_rsa_dir)
source_process = subprocess.Popen(["source ./vars && export KEY_CN=" + user + "&& ./pkitool " + user],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
source_process.wait()

secret_key_path = easy_rsa_dir + "/keys/" + user + ".key"
certificate_path = easy_rsa_dir + "/keys/" + user + ".crt"
ta_key_path = easy_rsa_dir + "/ta.key"
client_config = "client\n" \
                "dev tun\n" \
                "proto udp\n" \
                "remote 192.168.1.34 1194\n" \
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
cerificate = file_to_string(certificate_path)
ta_key = file_to_string(ta_key_path)

if len(cerificate) == 0:
    print 'echo "Keys was issued earlier. Please contact your administrator."'
    exit(1)

#create script for client
user_script = "#!" + user_shell + "\n\n"
user_script += "yum update -y\n"
user_script += "yum install epel-release -y\n"
user_script += "yum install openvpn -y\n"
user_script += "yum install easy-rsa -y\n"
#user_script += "mkdir /etc/openvpn\n"
user_script += "cp -rf /usr/share/easy-rsa/2.0/* /etc/openvpn\n"
user_script += "cd /etc/openvpn\n"
user_script += "echo \"" + cerificate + "\" > " + user + ".crt\n"
user_script += "echo \"" + secret_key + "\" > " + user + ".key\n"
user_script += 'echo "' + ta_key + '" > ta.key\n'
user_script += 'echo "' + client_config + '" > client.config\n'


print user_script

source_process = subprocess.Popen(["rm -f " + secret_key_path],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
source_process.wait()
