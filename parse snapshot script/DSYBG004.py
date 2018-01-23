

import os
from os import walk
import urllib
import zipfile
command = ""
currentPath = os.getcwd()


def is_number(s):
    try:
        float(s)
        #print(float(s))
        return True
    except ValueError:
        #print("asdfasdfasdfasdf")
        pass
    return False

def getOutputFileName(inputFile):
    result = ""
    temp = inputFile.split('_')
    #print(temp)
    for item in temp:
        if is_number(item) == True:
            result += item
        if item.find('fast') != -1 or item.find('slow') != -1 or item.find('data') != -1:
            result += item
    result += ".txt"
    return result


def unZipSnapshot():
    global command, currentPath
    print("===========================")
    print("enter unZipSnapshot")

    zipfiles = []
    xzfiles = []
    for (dirpath, dirnames, filenames) in walk(currentPath):
        for item in filenames:
            if item.find('.zip') != -1 and item.find("Snapshot") != -1:
                zipfiles.append(item)
    for file in zipfiles:
        if os.path.exists("snap"):
            command = "rm snap -rf"
            os.system(command)
        command = "mkdir snap"
        os.system(command)
        command = "unzip " + file + " -d snap"
        os.system(command)

    if os.path.exists("xzfiles.txt"):
        os.system("rm xzfiles.txt")
    os.system("find . -name \"*phytx_tdd*.xz\" >> xzfiles.txt")
    os.system("find . -name \"*dlphy_tdd*.xz\" >> xzfiles.txt")

    fp = open("xzfiles.txt", 'r')
    result = fp.readlines()
    if not os.path.exists("target"):
        os.system("mkdir target")
    for file in result:
        command = "cp " + file[:-1] + " target"
        os.system(command)
    fp.close()
    for xzfile in result:
        index = xzfile.rfind('/')
        xzfiles.append(xzfile[index:-1])
    for newfile in xzfiles:
        command = "xz -d ./target/" + newfile
        os.system(command)
    print("unZipSnapshot finished!!!")
    print("===========================")
    
def buildMapOutFile():
    print("===========================")
    print("enter buildMapOutFile")
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
            break

    os.system(svnaddress)
    os.system("./PHYTX_BUILD_MK update")
    os.system("./PHYTX_BUILD_MK build SCT")

    if os.path.exists("build.txt"):
        os.system("rm build.txt")
    os.system("find . -name Dl8*.out >> build.txt")
    os.system("find . -name DlDspKe*TDD.out >> build.txt")

    if not os.path.exists("target"):
        os.system("mkdir target")
    os.system("cp -R T_Tools/SC_DSP_COMMON/SS_HB/CP_HbViewer/* target/")
    fp = open("build.txt", 'r')
    result = fp.readlines()
    for file in result:
        command = "cp " + file[:-1] + " target/"
        print command
        os.system(command)
    print("buildMapOutFile finished!!!")
    print("===========================")

def hbview():
    if os.path.exists("target"):
        os.system("mkdir target")
    else:
        print("===========================")
        print("target folder is not exist!!!")
        print("===========================")
    currentPath += "/target/"
    os.chdir(currentPath)
    print(os.getcwd())
    
    
#unZipSnapshot()
#buildMapOutFile()
hbview()


