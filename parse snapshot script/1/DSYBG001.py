

import os
from os import walk
import urllib
import zipfile


mypath = os.getcwd()
print(mypath)
zipfiles = []
f = []

for (dirpath, dirnames, filenames) in walk(mypath):
    f.extend(filenames)
    break
for item in f:
    if item.find('.zip') != -1:
        zipfiles.append(item)

url = "http://hzlinb01.china.nsn-net.net:9093/Official_Build2/TL17A_ENB_0000_000521_000022//.config"
urllib.urlretrieve (url , "config")
fp = open("config", 'r')
result = fp.readlines()
prefix = "https://beisop60.china.nsn-net.net"
svnaddress = ""
svnversion = 0
fp.close()
        
for item in result:
    if item.find("PHY_TX_TDD") != -1:
        lindex = item.find("/")
        rindex = item.find("@")
	print(item[lindex:rindex], item[rindex:-1])
        svnversion = item[rindex+1:-1]
        svnaddress = "svn co " + prefix + item[lindex:rindex] + "/config . -r" + svnversion
        print(svnaddress)

os.system(svnaddress)
os.system("./PHYTX_BUILD_MK update")
os.system("./PHYTX_BUILD_MK build SCT")

os.system("rm tubo.txt")
os.system("find . -name Dl8*.out >> tubo.txt")
os.system("find . -name DlDspKe*TDD.out >> tubo.txt")

os.system("mkdir target")

fp = open("tubo.txt", 'r')
result = fp.readlines()
for file in result:
    command = "cp " + file[:-1] + " target"
    os.system(command)

for file in zipfiles:
    command = "mkdir snap"
    os.system(command)
    command = "unzip " + file + " -d snap"
    os.system(command)


os.system("rm tubo1.txt")
os.system("find . -name \"*phytx_tdd*.xz\" >> tubo1.txt")
os.system("find . -name \"*dlphy_tdd*.xz\" >> tubo1.txt")

fp = open("tubo1.txt", 'r')
result = fp.readlines()
for file in result:
    command = "cp " + file[:-1] + " target"
    os.system(command)


