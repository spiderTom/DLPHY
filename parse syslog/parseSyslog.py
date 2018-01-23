
from os import walk
import os
mypath = os.getcwd()

f = []
logfiles = []
outfiles = []
result = []
error = []


for (dirpath, dirnames, filenames) in walk(mypath):
    f.extend(filenames)
    break
for item in f:
    if item.find('.LOG') != -1:
        logfiles.append(item)
print("logfiles is:", logfiles)

for logfile in logfiles:
    print("logfilename is:", logfile)
    fp1 = open(logfile, 'r')

    for line in fp1.readlines():
        if line.find("/phy tx") != -1 or line.find("/PHY TX") != -1:
            result.append(line)
        elif line.find("/dlphy/") != -1 or line.find("/DLPHY/") != -1:
            result.append(line)
        else:
            pass
        if line.find("err/phy tx") != -1 or line.find("ERR/PHY TX") != -1\
            or line.find("final=1.0") != -1:
            error.append(line)
    fp1.close()
    

if len(error) != 0:
    print("!!!!error size is:", len(error))

fp = open("tubo.LOG", 'w+')
for item in result:
    fp.write(item)
fp.close()
            
fperror = open("ERROR.LOG", 'w+')
for item in error:
    fperror.write(item)
fperror.close()
