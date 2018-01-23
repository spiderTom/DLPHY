




fp = open("messagesRp3.rtm", 'r')
fptarget = open("target.rtm", 'w')

result = []
content = fp.readlines()

for item in content:
    if item.find('iqRoutedByAIF') != -1:
        result.append(item)
        result.append("    axcType(4)                 = 0;\n")
    else:
        result.append(item)

fptarget.writelines(result)

