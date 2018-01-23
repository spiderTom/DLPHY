

import os
from os import walk
import urllib
import zipfile


def unZipSnapshot():
    currentPath = os.getcwd()
    zipfiles = []

    for (dirpath, dirnames, filenames) in walk(currentPath):
        for item in filenames:
            if item.find('.zip') != -1 and item.find("Snapshot") != -1:
                zipfiles.append(item)
    for file in zipfiles:
        if os.path.exists(snap):
            command = "rm snap -rf"
            os.system(command)
        command = "mkdir snap"
        os.system(command)
        command = "unzip " + file + " -d snap"
        os.system(command)

    if os.path.exists(xzfiles.txt):
        os.system("rm xzfiles.txt")
    os.system("find . -name \"*phytx_tdd*.xz\" >> xzfiles.txt")
    os.system("find . -name \"*dlphy_tdd*.xz\" >> xzfiles.txt")

    fp = open("xzfiles.txt", 'r')
    result = fp.readlines()
    for file in result:
        command = "cp " + file[:-1] + " target"
        os.system(command)
    fp.close()
    for xzfile in result:
        command = "cp " + file[:-1] + " target"
        os.system(command)
    os.system("find . -name \"*phytx_tdd*.xz\" >> xzfiles.txt")

    
def buildMapOutFile():
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

    if os.path.exists(build.txt):
        os.system("rm build.txt")
    os.system("find . -name Dl8*.out >> build.txt")
    os.system("find . -name DlDspKe*TDD.out >> build.txt")

    if os.path.exists(target):
        os.system("rm target -rf")
    os.system("mkdir target")

    fp = open("build.txt", 'r')
    result = fp.readlines()
    for file in result:
        command = "cp " + file[:-1] + " target"
        os.system(command)




