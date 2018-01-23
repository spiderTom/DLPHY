
from os import walk
import os
mypath = os.getcwd()
print(mypath)
f = []
binfiles = []
outfiles = []
result = []


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
    
    
    

for (dirpath, dirnames, filenames) in walk(mypath):
    f.extend(filenames)
    break
for item in f:
    if item.find('.bin') != -1:
        binfiles.append(item)
    if item.find('.out') != -1:
        outfiles.append(item)

#print("binfiles:", binfiles)
#print("outfiles :",outfiles)
#./HbViewer -b BTS315572_12A1_dlphy_tdd_hbfast_Dl8DspNyCpu1.bin -o Dl8DspNyCpu1.out > 12A1fast.txt
for binfile in binfiles:
    outputfile = getOutputFileName(binfile)
    #print(outputfile)

    for i in range(1, 8):
        cpuname = "Cpu" + str(i)
        print(cpuname)
        if binfile.find(cpuname) != -1:
            for outfile in outfiles:
                if outfile.find(cpuname) != -1:
                    commandString = "./HbViewer -b " + binfile + " -o " + outfile + " > " + outputfile + "\n"
                    result.append(commandString)
                else:
                    continue
        else:
            continue



fp = open("tubocommand.txt", 'w')
for item in result:
    fp.write(item)
    os.system(item)

fp.close()
            

