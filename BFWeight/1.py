

fp = open("1.txt", 'r')
weightStringA = []
weightStringB = []

resultA = []
resultB = []
content = fp.readlines()

def handleEachWeight(inputList):
    standard = 32767
    for input in inputList:
        input = input[2:]
        rel = input[:4]
        img = input[4:]
        #print(input, rel, img)
        relnum = int(rel, 16)
        imgnum = int(img, 16)
        if relnum > standard:
            relnum = relnum - 65535
            relnum = relnum / (standard + 1)
        else:
            relnum = relnum / standard
        if imgnum > standard:
            imgnum = imgnum - 65535
            imgnum = imgnum / (standard + 1)
        else:
            imgnum = imgnum / standard

        resultA.append(relnum)
        resultB.append(imgnum)

for item in content:
    begin = item.find('(')
    end = item.find(')')
    if begin != -1:
        item = item[begin + 1:end]
        print(item)
        temp = item.split(',')
        print(temp)
        if len(temp) == 2:
            a = temp[0]
            b = temp[1]
            weightStringA.append(a)
            weightStringB.append(b)
        if len(temp) == 1:
            a = temp[0]
            weightStringA.append(a)
print("the weightStringA size is %d"%len(weightStringA))
handleEachWeight(weightStringA)
finalResult = []
print ("asdfasdfasdfasdf")
for i in range(len(resultA)):
    print(i, resultA[i], resultB[i])
    zeroNum = 0
    while abs(resultA[i]) < 0.2:
        resultA[i] *= 10
        zeroNum += 1
    if zeroNum != 0:
        eachRecord = str(resultA[i]) + 'E-0' + str(zeroNum)
    else:
        eachRecord = str(resultA[i])
    #eachRecord.replace('0.', '.')

    zeroNum = 0
    while abs(resultB[i]) < 0.2:
        resultB[i] *= 10
        zeroNum += 1

    eachRecord += '+('
    if zeroNum != 0:
        eachRecord += str(resultB[i]) + 'E-0' + str(zeroNum)
    else:
        eachRecord += str(resultB[i])
    eachRecord += ')*1j'
    eachRecord = eachRecord.replace('0.', '.')
    finalResult.append(eachRecord)
    print("eachrecord is ",eachRecord)
print("the final result length is ", len(finalResult))
for item in finalResult:
    print(item)
print (" ".join(finalResult))


