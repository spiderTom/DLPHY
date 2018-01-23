

import os
from os import walk
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
    command = "cp " + file[:-1] + " ."
    os.system(command)

