#!/usr/bin/python
import cgitb
from os import chdir, environ
from subprocess import Popen, PIPE
import sqlite3
import re


def file_to_string(path):
    cat = Popen(["cat " + path],
                stdout=PIPE, stderr=PIPE, shell=True)
    cat.wait()
    return cat.communicate()[0]

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
easy_rsa_dir = "/etc/openvpn"
user_shell = "/bin/bash"

# curl test
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
ca_crt_path = easy_rsa_dir + "/keys/ca.crt"
ta_key_path = easy_rsa_dir + "/ta.key"

secret_key = file_to_string(secret_key_path)
certificate = file_to_string(certificate_path)
ta_key = file_to_string(ta_key_path)
ca_cert = file_to_string(ca_crt_path)

if len(certificate) == 0:
    print 'echo "Keys was issued earlier. Please contact your administrator."'
    exit(1)

client_config = "client\n" \ 
                "tls-client\n" \  #режим "клиент-сервер"
                "dev tun\n" \     #создание маршрутизируемого IP-туннеля
                "proto udp\n" \   #выбор протокола 
                "port 1194\n" \   #порт для работы OpenVPN
                "remote " + environ["SERVER_ADDR"] + "\n" \ #реальный IP-адрес сервера
                "remote-cert-tls server\n" \ #защита от подмены сервера третьим лицом
                "cd /etc/openvpn\n" \
                "pull\n" \        #разрешение на прием конфигурации клиента с сервера
                "tls-auth /etc/openvpn/ta.key 1\n" \ #ключ HMAC
                "cipher DES-EDE3-CBC\n" \    #выбор шифра (не имеет значения в рамках работы)
                "user nobody\n" \            #запуск демона OpenVPN из-под 
                "group nobody\n" \           #непривилегирированного пользователя
                "ca /etc/openvpn/ca.crt\n" \ #сертифика УЦ
                "cert /etc/openvpn/" + user + ".crt\n" \ #откртый ключ клиента
                "key  /etc/openvpn/" + user + ".key\n" \ #закрытый ключ клиента
                "keepalive 10 120\n" \       #настройка проверки активности сессии 
                "comp-lzo\n" \               #параметры сжатия трафика
                "log-append openvpn.log\n" \ #путь к логам
                "verb 3"                     #уровень подробности логов
# client script
user_script = "#!" + user_shell + "\n\n"
user_script += "yum update -y\n"
user_script += "yum install epel-release -y\n"
user_script += "yum install openvpn -y\n"
user_script += "yum install easy-rsa -y\n"
user_script += "cp -rf /usr/share/easy-rsa/2.0/* /etc/openvpn\n"
user_script += "cd /etc/openvpn\n"
user_script += "echo \"" + certificate + "\" > " + user + ".crt\n"
user_script += "echo \"" + secret_key + "\" > " + user + ".key\n"
user_script += "echo \"" + secret_key + "\" > " + user + ".key\n"
user_script += "chmod 0600 " + user + ".key\n"
user_script += 'echo "' + ta_key + '" > ta.key\n'
user_script += 'echo "' + client_config + '" > client.conf\n'
user_script += 'echo "' + ca_cert + '" > ca.crt\n'
user_script += "systemctl start openvpn@client\n"
user_script += "systemctl enable openvpn@client\n"

print user_script

source_process = Popen(["rm -f " + secret_key_path],        #удалить закрытый
                       stdout=PIPE, stderr=PIPE, shell=True)#ключ клиента
source_process.wait()
