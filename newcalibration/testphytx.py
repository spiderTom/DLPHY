#!usr/bin/python
#-*- encoding=UTF-8 -*-

#__author__ = {'name      :''xuman',
#              'mail      :''man.2.xu@nsn.com',
#              'department:''DL PHY',
#              'created   :''2014-5-9'
#             }
		  
import time
import getopt
import sys
import socket
import select
import re
import threading
import Queue
import logging
import logging.handlers
import os
import xml.etree.ElementTree as ET
#from xml.dom import minidom,Node
import binascii
import signal
import ConfigParser
import subprocess
import shutil
import genUmMap
import random

#config logging module
#for log show in file
logging.basicConfig(filename='TestPhyTx_py.log',filemode='w',format='-%(levelname)-5s  -%(funcName)s:%(lineno)d : %(message)s',level=logging.DEBUG)
#for log show in console
logger = logging.getLogger('example')
formatter = logging.Formatter('-%(levelname)-7s -%(funcName)-20s:%(lineno)-4d: %(message)s')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(formatter)
logger.addHandler(console)

udplog = logging.handlers.DatagramHandler('127.0.0.1', 20002)
udplog.setLevel(logging.INFO)
udplog.setFormatter(formatter)
logger.addHandler(udplog)

#--------------------global parameters---------------------
startRoot = os.getcwd()
startRoot = startRoot.replace('\\','/')
sctRoot = os.path.abspath(r'%s/../..'%startRoot)
(commonFilesDir,commonFilesListName) = ('%s/testcases_tdd/COM'%sctRoot,'commonFileList.txt')
flagToEndUdp = 1
#---------------------hardware data------------------------
boardId = 0
phyTxControlCpuId = 0
rtmCaptureCpuId = 0
rtmControlCpuId = 0
rtmCtlAllDspProcList = []
rtmControlCpid = 0
phyTxTransmitterCpuId = 0
newLogServer = 0
sourceSicad = '10110308'
antennaGroupIdIni = 0
# Pool ID is hardcoded as:
# 1. PoolID is transparent to DL PHY, 
# 2. Multi Runuing this script with different Pool ID can cuase Cell Setup Failue
poolId= 0
#----------------------------------------------------------

#-----------------socket parameters------------------------
McuSocket = 0
(McuAddr,McuPort) = ('192.168.255.1',15001)
#----------------------------------------------------------

#---------------------udp log parameters-------------------
udpServer = '%s/../UDPServer/UDPServer.exe'%startRoot
(logServerAddr,logServerPort) = ('192.168.255.126',51000)
udpServerClose = '%s/../UDPServer/closeUDPServer.bat'%startRoot
udpLogDir = '%s/testcases_tdd/0_LOGS'%sctRoot
udpLog = ''
gCheckUdpLog = 0
#----------------------------------------------------------

#---------------options of testphytx.py--------------------
retryCount = 0                            #-t/--retry
Deployment = 2                            #-D/--deployment
dspNo = []                                #-n/--dspno        
reloadCommonFiles = 0                     #-M
CaseListName = ''                         #-l/--caselist
checkMD5 = 0                              #-m/--MD5
udpAction = 0                             #-u/--udp
powerBreakPort = 0                        #-P/--port
timeCompareFormat = ''                    #-o
freqCompareFormat = ''                    #-o
boardType = 'nyquist'                     #-T/--type
checkLog = 0                              #-c
syncSendPdsch = 0                         #-s
multiRTM = 0                              #-R
calibrationCase = 0                       #-t/--retry
#----------------------------------------------------------

#---------------case list for save case--------------------
TestCases = []                            #for test
retryTestCases = []                       #for retry
sessionCases = []                         #for reboot
caseNeedToCheckLog = []                   #save cases which need to check log
#----------------------------------------------------------

#----------------number of physical antenna----------------
numOfTxAntennasInLocalCell = 0
#----------------------------------------------------------

#-----------------file name and suffix---------------------
(rtmScriptName,rtmScriptSuffix) = ('script','rtm')
(calFileName,calFileSuffix) = ('Calcoefdata','bin')
(weightFileName,weightFileSuffix) = ('Weightdata','bin')
tmpFileStr = '.tmp'
#----------------------------------------------------------

#------------antenna&reference file name------------------- 
antennaFilesNameSISO2Port = [
    'Antenna0_1_', 'Antenna0_2_', 'Antenna0_3_', 'Antenna0_4_',
    'Antenna0_5_', 'Antenna0_6_', 'Antenna1_1_', 'Antenna1_2_',
    'Antenna1_3_', 'Antenna1_4_', 'Antenna1_5_', 'Antenna1_6_']
antennaFilesNameMIMO2Port = [
    'Antenna0_1_', 'Antenna1_1_', 'Antenna0_2_', 'Antenna1_2_',
    'Antenna0_3_', 'Antenna1_3_', 'Antenna0_4_', 'Antenna1_4_',
    'Antenna0_5_', 'Antenna1_5_', 'Antenna0_6_', 'Antenna1_6_']
antennaFilesName4Port = ['Antenna0_', 'Antenna1_', 'Antenna2_', 'Antenna3_']
antennaFilesName3DMIMO16Port = [
    'Antenna0_1_', 'Antenna1_1_', 'Antenna0_2_', 'Antenna1_2_',
    'Antenna0_3_', 'Antenna1_3_', 'Antenna0_4_', 'Antenna1_4_',
    'Antenna0_5_', 'Antenna1_5_', 'Antenna0_6_', 'Antenna1_6_',
    'Antenna0_7_', 'Antenna1_7_', 'Antenna0_8_', 'Antenna1_8_',]
antennaFilesName16Port = [
    'Antenna0_', 'Antenna1_', 'Antenna2_', 'Antenna3_',
    'Antenna4_', 'Antenna5_', 'Antenna6_', 'Antenna7_',
    'Antenna8_', 'Antenna9_', 'Antenna10_', 'Antenna11_',
    'Antenna12_', 'Antenna13_', 'Antenna14_', 'Antenna15_']

hbFileNameList = ['histbufslow_core1', 'histbuffast_core1', 'histbufslow_core4', 'histbuffast_core4', 'histbufrtm']
#----------------------------------------------------------

#------------queue for multi-threading---------------------
queueMain = Queue.Queue()                   
queueProlog = Queue.Queue()                 
queuePeroration = Queue.Queue()             
queueCompare = Queue.Queue()            
queueReboot = Queue.Queue()         
queueResult = Queue.Queue(24)                 
#----------------------------------------------------------

#------------message name,used by multi-threading---------
(PROLOG_INIT_REQ,PROLOG_INIT_RESP) = ('PROLOG_INIT_REQ','PROLOG_INIT_RESP')
(LOAD_COMMON_FILE_REQ,LOAD_COMMON_FILE_RESP) = ('LOAD_COMMON_FILE_REQ','LOAD_COMMON_FILE_RESP')
(TEST_REQ,TEST_ACK,TEST_RESP) = ('TEST_REQ','TEST_ACK','TEST_RESP')
(REBOOT_REQ,REBOOT_RESP) = ('REBOOT_REQ','REBOOT_RESP')
(COMPARE_REQ,COMPARE_RESP) = ('COMPARE_REQ','COMPARE_RESP')
(EXIT_REQ,) = ('EXIT_REQ',)
#----------------------------------------------------------

#------------variable&queue lock---------------------------
lockQueueMain = threading.RLock()
lockQueueProlog = threading.RLock()
lockQueuePeroration = threading.RLock()
lockQueueCompare = threading.RLock()
lockQueueReboot = threading.RLock()
lockHandle = threading.RLock()
lockResult = threading.RLock()
condHandle = threading.Condition(lockHandle)
#----------------------------------------------------------

#------------prepare for multi-dsp test(enable now)--------
prologHandleCount = 1
respCount = 0
sanwichConf = False 
leftRtmOfSanwich = 0     
#----------------------------------------------------------

#------------ports and dsps which could be used------------
prologFreeHandle = []
#----------------------------------------------------------

#------------working ports and dsps------------------------
prologWorkingHandle = []
#----------------------------------------------------------

#------------variables for reboot dsp----------------------
rebootDir = startRoot
rebootApp = '%s/rebootBoard.exe'%rebootDir
#----------------------------------------------------------

#------------variables used for iq compare cmd-------------
limitRelEvmSq = 0.0013
limitAbsEvmSq = 210
timeCompareScript = '%s/tools/checkResults/iqcomparetime.py'%sctRoot
freqCompareScript = '%s/tools/checkResults/iqcomparefreq.py'%sctRoot
#----------------------------------------------------------

#------------report format---------------------------------
CiLogNameFormat = 'TestPhyTx_CI_'
CiXmlLogName = 'TestPhyTx_CI_'
(passFormat,failFormat) = ('<TR><TD>%s</TD><TD>%s</TD><TD> <FONT color=#007700><B> passed </B></FONT></TD><TD>%s</TD></TR>\n',\
'<TR><TD>%s</TD><TD>%s</TD><TD> <FONT color=#ff0000><B> failed </B></FONT></TD><TD>%s</TD></TR>\n')
#----------------------------------------------------------


#------------global array index---------------------------------
#handle index 
PORT_INDEX = 0
DSP_ID_INDEX = 1
RTM_CTL_NODE_ID_INDEX = 2
RTM_CAPTRUE_NODE_ID_INDEX = 3 
TARGET_SICAD_INDEX = 4
CASE_INFO_INDEX = 6
IS_REMOTE_INDEX = 7
REMOTE_DSP_ID_INDEX = 8 
TARGET_STAT_INDEX = 9 

#test case list index 
CASE_NAME_INDEX = 0
CASE_PATH_INDEX = 1
CASE_LOG_DIR_INDEX = 2
BAND_WIDTH_LIST_INDEX = 4
CP_LIST_BY_SUBF_INDEX = 5
NO_FFT_INDEX = 7
NO_THREAD_INDEX = 10 
ANTENNA_FILE_NAME_INDEX = 12
REFERENCE_FILE_NAME_INDEX = 13
ANTENNA_COEFS_INDEX = 14
CAL_FILE_INDEX = 15 
CHK_ANTENNA_FILE_INDEX = 17
NUM_OF_PORT_LIST_INDEX = 18
DOWN_SAMPLE_LIST_INDEX = 19 
TRANSMIT_MD5_INDEX = 20
GENERATE_MD5_INDEX = 21
MULTI_CASE_LIST_INDEX = 28
CELL_ID_INDEX = 24

#----------------------------------------------------------

def getRandomAntennaGPId():
    calltimerecordfile = os.getcwd() + '/randomAntennaGPId.txt'
    AntennaGPId = [1,2,3,4]
    calltimelist = []
    recovertime = 100000
    minindex = 0
    
    if os.path.exists(calltimerecordfile) == 0:
        fp = open(calltimerecordfile,'w')
        print>>fp,0,0,0,0,
        fp.close()

    fp = open(calltimerecordfile,'r')
    for calltime in fp.readline().split(' '):
        calltimelist.append(int(calltime))
    fp.close()

    if min(calltimelist) > recovertime:
        fp = open(calltimerecordfile,'w')
        print>>fp,1,0,0,0,
        fp.close()
        return AntennaGPId[minindex]
    
    minindex = calltimelist.index(min(calltimelist))
    calltimelist[minindex]=calltimelist[minindex]+1

    fp = open(calltimerecordfile,'w')
    print>>fp,calltimelist[0],calltimelist[1],calltimelist[2],calltimelist[3],
    fp.close()

    return AntennaGPId[minindex]

def AbnormalExit():
    global udpAction
    if udpAction:
        EndLogServer()
    Report()
    os._exit(-1)

def KillSelf(signalnum,frame):
    Report()
    os._exit(-1)

signal.signal(signal.SIGINT,KillSelf)
signal.signal(signal.SIGABRT,KillSelf)
signal.signal(signal.SIGTERM,KillSelf)
#signal.signal(signal.SIGQUIT,KillSelf)
#signal.signal(signal.SIGHUP,KillSelf)

#read config file "config.xml" to get boardId,phytxControlCpuId....
def parseIdConfigFile(config_file):
    global boardId,phyTxControlCpuId,rtmCaptureCpuId,rtmControlCpuId,rtmControlCpid,\
           phyTxTransmitterCpuId,newLogServer,rtmCtlAllDspProcList,boardType
    try:
        tree = ET.parse('./%s'%config_file)
        root = tree.getroot()
        for label in root.findall('boardType'):
            if(label.get('type') == boardType):
                boardId = label.find('boardId').text
                phyTxControlCpuId = label.find('phyTxControlCpuId').text
                rtmCaptureCpuId = label.find('rtmCaptureCpuId').text
                rtmControlCpuId = label.find('rtmControlCpuId').text
                for rtmCtlDspChild in label.findall("rtmControlDsp"):
                    rtmCtlDspProcessList = []
                    rtmCtlDspNo = rtmCtlDspChild.get('dspNo')
                    rtmCtlDspProcessList.append(rtmCtlDspNo)
                    for coreChild in rtmCtlDspChild.findall("core"):
                        rtmCtlCoreNo = coreChild.get('coreNo')
                        rtmCtlCoreProcessList = coreChild.text.split()
                        rtmCtlCoreProcessList.insert(0,rtmCtlCoreNo)
                        rtmCtlDspProcessList.append(rtmCtlCoreProcessList)
                    rtmCtlAllDspProcList.append(rtmCtlDspProcessList)
                phyTxTransmitterCpuId = label.find('phyTxTransmitterCpuId').text
                rtmControlCpid = label.find('rtmControlCpid').text
                newLogServer = label.find('newLogServer').text              
    except Exception,e:
        logger.error(e)
        exit()

#read config file to get hardware data and set the socket
def init():
    global sctRoot,McuSocket
    logger.debug('start init')
    logger.info('SCT root path set to %s'%sctRoot)
    parseIdConfigFile('config.xml')
    logger.debug('start set socket connection')
    try:
        McuSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        McuSocket.connect((McuAddr,McuPort))
    except Exception,e:
        logger.error('Can not connect to BTS')
        exit()
    logger.debug('connect BTS successful')

def usage():
    print """
USAGE

NAME
    testphytx.py - Test control tool for SCT of PHY TX. (runs only in cmd window, not in cygwin shell !!!)

SYNOPSYS
    testphytx.py  [-h]  [options]

DESCRIPTION
    - Opens TCP connection to DSP on FSPx board.
    - Transmits file messages.rtm and globalParams.rtm to RTM on DSP per tftp
    - Transmits subscripts like phyDlCellSetupReq.rtm e.t.c. to RTM per tftp
    - Transmits file script.rtm for a list of testcases to RTM per tftp
    - Sends startScript message to RTM and checks Acknowledge
    - Gets IQ data files from RTM per tftp
    - Checks Test results

OPTIONS
    -h/--help          Output usage

    -l/--caselist      testlist name with path starting from /C_Test/SC_PHY/SS_PHY_TX/testcases:
                       e.g. -l PHY_TX.lst or -l SCT.lst (list of lists, contains PHY_TX.lst ...) 
                            or: -l CE_RSS_001/tc_all.lst
                       In testlist comment lines can be done with "#"

    -o                 With this option the following happens: 
                       - iqcomparetime.py is started with -v option and result is written to iqcompareTimeResult_Antenna0_verbose.txt
                       - iqcomparefreq.py is started with --o option, that means, that IQ data of Reference file and RTM file is given out
                       into resultfile iqcompareFreqResult_Antenna0.log also if there is no difference in Data.

    -n/--dspno         e.g. -n 4    range: 3:8 on Nyquist board, range: 3:6 on FSM4 board             

    -D/--deployment    e.g. -D 2 : 8 pipe beamforming; -D 3 : Non-beamforming; -D 5 : multi-cell -D 6 : super cell.
	
    -m/--MD5           use MD5 for iqcompare
	 
    -M                 forceLoadCommonFiles :  common files (globalParams.rtm , ...) are reloaded to RTM nomatter they are already there or not.
	 
    -P/--port          enable reboot part: once case runs timeout or find FATAL error when check udp log per case.

    -t/--retry         failed cases will be retry ? times

    -A/-B/-Z           mark current environment as FSM4-Adv/FSM4-Bas/FZM

    -u/--udp           open the udp server if the args followed -u is "stAcl"

    -c                 skip IQ comparison and just check if the defined log existed

    -s                 enable RTM slave, slave RTM and master RTM will send half of the number of PDSCH synchronously

    -R                 enable dual RTM controller process in one core.

    -F                 Only deployment on odd DSP
    --antennaGroupID Specify the antenna group ID for massive MIMO

USAGE
    """
    exit()


def parameterAntennaGroupId(idArg):
    global antennaGroupIdIni
    id = int(idArg)
    if id in (1, 2, 3, 4):
        antennaGroupIdIni = id
    else:
        logger.error('Wrong parameter %s with option --antennaGroupID !'%idArg)
        usage()
    
    
def parameterD(deployment):
    global Deployment
    Deployment = int(deployment)
    logger.debug('Deployment = %s'%deployment)
    if(deployment == '1'):
        logger.info('Deployment for 4 pipe beamforming is set for Nyquist!')
    elif(deployment == '2'):
        logger.info('Deployment for 8 pipe beamforming is set for Nyquist!')
    elif(deployment == '3'):
        logger.info('Deployment for none beamforming is set for Nyquist!')
    elif(deployment == '5'):
        logger.info('Deployment for multiple cells is set for Nyquist!')
    elif(deployment == '6'):
        logger.info('Deployment for super cell is set for Nyquist!')
    elif(deployment == '7'):
        logger.info('Deployment for massive mimo is set for Kepler!')
    else:
        logger.error('Wrong parameter %s with option -D !'%deployment)
        usage()

def parameterL(caselist):
    global CaseListName
    CaseListName = caselist
    logger.debug('CaseListName is %s'%caselist)

def parameterMD5():
    global checkMD5
    checkMD5 = 1
    logger.info('SCT use MD5 to comparison!')

def parameterN(dspno):
    global prologHandleCount,sanwichConf,leftRtmOfSanwich
    if(re.match('[3-8]{1}',dspno)!= None and len(dspno) == 1):
        dspNo.append(int(dspno))
    elif(re.match('[3-8]{1}:[3-8]{1}',dspno)!= None and len(dspno) == 3):
        dspnoList = dspno.split(':')
        dspNo.append(int(dspnoList[0]))
        dspNo.append(int(dspnoList[1]))
    elif(re.match('[3-8]{1}.[3-8]{1}.[3-8]{1}',dspno) != None and len(dspno) == 5):
        dspnoList = dspno.split('.')
        dspNo.append(int(dspnoList[0]))
        dspNo.append(int(dspnoList[1]))
        dspNo.append(int(dspnoList[2]))
        prologHandleCount = 3
    elif(re.match('[3-6]{1}_[3-6]{1}_[3-6]{1}_[3-6]{1}',dspno) != None and len(dspno) == 7):
        dspnoList = dspno.split('_')
        dspNo.append(int(dspnoList[0]))
        dspNo.append(int(dspnoList[1]))
        dspNo.append(int(dspnoList[2]))
        dspNo.append(int(dspnoList[3]))
        if(dspnoList[0] < dspnoList[1]):
            if(dspnoList[2] < dspnoList[3]):
                prologHandleCount = 4
            else:
                prologHandleCount = 2
        else:
            if(dspnoList[2] < dspnoList[3]):
                prologHandleCount = 2
                sanwichConf = True
                leftRtmOfSanwich = dspNo[1]
            else:
                logger.error('Wrong parameter with option -n %s, please check'%dspno)
                usage()
    else:
        logger.error('Wrong parameter with option -n %s, please check'%dspno)
        usage()
    if not sanwichConf and len(dspNo) != len(list(set(dspNo))):
            logger.error('Repeated dsp isn''t allowed in multi-dsp and remote-dsp model')
            usage()
    logger.info('SCT runs on DSP %s'%dspNo)
    logger.debug('dspNo is %s'%dspNo)

def parameterU(udp):
    global udpAction
    if(udp == 'start' or udp == 'stAcl' or udp == 'stOnly' or udp == 'ci'):
        udpAction = udp
    else:
        logger.error('Wrong parameter with option -u %s, please check'%udp)
        usage()

def parameterO():
    global timeCompareFormat,freqCompareFormat
    timeCompareFormat = '-v'
    freqCompareFormat = '-o'

def parameterM():
    global reloadCommonFiles
    reloadCommonFiles = 1
    logger.info('common files will be reload to Rtm')

def parameterC():
    global checkLog,udpAction
    checkLog = 1
    udpAction = 'stAcl'
    logger.info('SCT test only check log this time')

#parse args got from command line
def GetOptions(argv):
    if(len(argv) == 0):
        usage()
    try:
        opts,args = getopt.getopt(argv,"hD:l:mn:t:u:PcABEZoMcsRF",["help","deployment=","caselist=","MD5","dspno=","retry=","udp=","port", "antennaGroupID="])
    except getopt.GetoptError:
        usage()
    global retryCount,powerBreakPort,syncSendPdsch,multiRTM,boardType,CiLogNameFormat,CiXmlLogName,sourceSicad,hbFileNameList,calibrationCase
    for opt,arg in opts:
        if opt in ("-h","--help"):
            usage()
        elif opt in ("-D","--deployment"):
            parameterD(arg)
        elif opt in ("-l","--caselist"):
            parameterL(arg)
        elif opt in ("-m","--MD5"):
            parameterMD5()
        elif opt in ("-n","--dspno"):
            parameterN(arg)
        elif opt in ("-t","--retry"):
            retryCount = int(arg)
        elif opt in ("-u","--udp"):
            parameterU(arg)
        elif opt in ("-P","--port"):
            powerBreakPort = 1
        elif opt in ("-c","--cal"):
            calibrationCase = 1
        elif opt == '-A':
            boardType = 'fsm4_adv'
            CiLogNameFormat = 'TestPhyTx_CI_FSM4_ADV_'
            CiXmlLogName = 'TestPhyTx_CI_FSM4_ADV_'
            hbFileNameList = ['histbufslow_core1', 'histbuffast_core1', 'histbufslow_core2', 'histbuffast_core2', 'histbufrtm']
        elif opt == '-B':
            boardType = 'fsm4_bas'
            CiLogNameFormat = 'TestPhyTx_CI_FSM4_BAS_'
            CiXmlLogName = 'TestPhyTx_CI_FSM4_BAS_'
            hbFileNameList = ['histbufslow_core1', 'histbuffast_core1', 'histbufslow_core2', 'histbuffast_core2', 'histbufrtm']
        elif opt == '-E':
            boardType = 'fsm4_Ehance'
            CiLogNameFormat = 'TestPhyTx_CI_FSM4_EHANCE_'
            CiXmlLogName = 'TestPhyTx_CI_FSM4_EHANCE_'
            hbFileNameList = ['histbufslow_core1', 'histbuffast_core1', 'histbufslow_core2', 'histbuffast_core2', 'histbufrtm']
        elif opt == '-F':
            boardType = 'nyquist_adv'
            CiLogNameFormat = 'TestPhyTx_CI_ADV_'
            CiXmlLogName = 'TestPhyTx_CI_ADV_'
        elif opt == '-Z':
            boardType = 'fzm'
            sourceSicad = '123d0308'
            CiLogNameFormat = 'TestPhyTx_CI_FZM_'
            CiXmlLogName = 'TestPhyTx_CI_FZM_'
        elif opt == '-o':
            parameterO()
        elif opt == '-M':
            parameterM()
        elif opt == '-c':
            parameterC()
        elif opt == '-s':
            syncSendPdsch = 1
        elif opt == '-R':
            multiRTM = 1
        elif opt == '--antennaGroupID':
            parameterAntennaGroupId(arg)

#get arguments such as calOn,noFFT,allDsp.... and return them
def ParseTc_all_lst(lineToBeRead):
    global syncSendPdsch,gCheckUdpLog
    calOn = noFFT = scfFreq = noThread = allDsp = caseName = antennaBitmap = slave = maxPipe = 0
    scfTime = 123
    cpListBySubf = ['','','']
    mapAllowedPhtxLogIdMin = {}
    mapAllowedPhtxLogIdMax = {}
    mapAllowedRtmLogIdMin = {}
    mapAllowedRtmLogIdMax = {}
    noLineBreak = lineToBeRead.strip('\n')
    ifCaseOrNot = re.findall('^\s*([A-Z0-9]{2}_[A-Z0-9]{3}_[A-F0-9]{3})\s+([a-fA-F0-9]{1})\s*',noLineBreak)
    if(len(ifCaseOrNot) != 0):
        caseName,antennaBitmap = ifCaseOrNot[0]
        if(len(re.findall('calOn',noLineBreak)) != 0): calOn = 'calOn'
        if(len(re.findall('noFFT',noLineBreak)) != 0): noFFT = 'noFFT'
        if(len(re.findall('scf(\d+)',noLineBreak)) != 0):
            scfTime = int(re.findall('scf(\d+)',noLineBreak)[0])
        scfFreq = 100.00 / scfTime
        if(len(re.findall('noThreads',noLineBreak)) != 0): noThread = 'noThread'
        if(len(re.findall('allDsp',noLineBreak)) != 0): allDsp = 'allDsp'
        if(len(re.findall('extCp',noLineBreak)) != 0): cpListBySubf[0] = 'extCp'     
        item = re.findall('pipe\s*(\d)\s*', noLineBreak)
        if item:
            maxPipe = int(item[0])
            
        if(noLineBreak.find('MBMS') != -1):
            cpListBySubf[0] = (noLineBreak.split('MBMS')[1]).split(' ')[0]
            tmpList = cpListBySubf[0].split('_')
            if(len(tmpList) > 1):
                cpListBySubf[0] = tmpList[0]
                cpListBySubf[1] = tmpList[1]
            if(len(tmpList) == 3):
                cpListBySubf[2] = tmpList[2]
        if(noLineBreak.find('slave') != -1 and syncSendPdsch == 1): slave = 1
        if(noLineBreak.find('allowedPhytxLogId_') != -1):
            match = re.search(r'allowedPhytxLogId_(\d+)\((\d+)-(\d+)\)(\S*)', noLineBreak)
            while (match):
                logid = match.group(1);
                if (mapAllowedPhtxLogIdMin.has_key(logid)):
                    mapAllowedPhtxLogIdMin[logid] = mapAllowedPhtxLogIdMin[logid] + match.group(2);
                else:
                    mapAllowedPhtxLogIdMin[logid] = match.group(2);
                if (mapAllowedPhtxLogIdMax.has_key(logid)):
                    mapAllowedPhtxLogIdMax[logid] = mapAllowedPhtxLogIdMax[logid] + match.group(3);
                else:
                    mapAllowedPhtxLogIdMax[logid] = match.group(3);
                match = re.search(r'_(\d+)\((\d+)-(\d+)\)(\S*)', match.group(4))
        if(noLineBreak.find('allowedRtmLogId_') != -1):
            match = re.search(r'allowedRtmLogId_(\d+)\((\d+)-(\d+)\)(\S*)', noLineBreak)
            while (match):
                logid = match.group(1);
                if (mapAllowedRtmLogIdMin.has_key(logid)):
                    mapAllowedRtmLogIdMin[logid] = mapAllowedRtmLogIdMin[logid] + match.group(2);
                else:
                    mapAllowedRtmLogIdMin[logid] = match.group(2);
                if (mapAllowedRtmLogIdMax.has_key(logid)):
                    mapAllowedRtmLogIdMax[logid] = mapAllowedRtmLogIdMax[logid] + match.group(3);
                else:
                    mapAllowedRtmLogIdMax[logid] = match.group(3);
                match = re.search(r'_(\d+)\((\d+)-(\d+)\)(\S*)', match.group(4))
    if(len(mapAllowedPhtxLogIdMin) > 0 or len(mapAllowedPhtxLogIdMax) > 0 or len(mapAllowedRtmLogIdMin) or len(mapAllowedRtmLogIdMax)):
        gCheckUdpLog = 1
    return [calOn,noFFT,scfTime,scfFreq,noThread,allDsp,caseName,antennaBitmap,cpListBySubf,slave, maxPipe, mapAllowedPhtxLogIdMin, mapAllowedPhtxLogIdMax, mapAllowedRtmLogIdMin, mapAllowedRtmLogIdMax]

#return the caseType e.g.MIM,MIX,DBF,ITF....
def ParseCaseDir(caseName):
    if(re.match('[A-Z0-9]{2}_[A-Z0-9]{3}_[A-F0-9]{3}',caseName) != None):
        caseType = caseName.split('_')[1]
        return caseType
    else:
        return -1

#judge if the caselist need be test is a single case or a list and set the udpLogDir and return case/caselist path
def ParseCasePath(CaseListName):
    global sctRoot,CiLogNameFormat,CiXmlLogName,udpLogDir,udpLog
    logger.debug('start to parse caselist,caselist is %s'%CaseListName)
    if(CaseListName.find('/tc_all.lst') != -1):
        caseName = CaseListName.split('/')[-2]
        caseType = ParseCaseDir(caseName)
        if(caseType != -1):
            if(len(CaseListName.split('/')) > 2):
                testcasePath = '%s/testcases_tdd'%sctRoot
                udpLogDir = '%s/%s/%s/LOGS'%(testcasePath,caseType,caseName)
            else:
                testcasePath = '%s/testcases_tdd/%s'%(sctRoot,caseType)
                udpLogDir = '%s/%s/LOGS'%(testcasePath,caseName)
                
                print "caselist is %s, testcasePath:%s,updalogdir else %s" %(CaseListName,testcasePath,udpLogDir)
        else:
            logger.error('Can not open this testcase %s,please check'%CaseListName)
            exit()
    elif(os.path.exists(r'%s/testcases_tdd/%s'%(sctRoot,CaseListName)) == True):
        testcasePath = '%s/testcases_tdd'%sctRoot
    else:
        logger.error('Can not open this testcase %s,please check'%CaseListName)
        exit()
    logger.debug('testcasePath is %s'%testcasePath)
    if not os.path.exists(udpLogDir):
        os.mkdir(udpLogDir)
    CiLogNameFormat += os.path.basename(CaseListName).split('.')[0] + '.log'
    CiXmlLogName += os.path.basename(CaseListName).split('.')[0] + '.xml'
    udpLog = '%s/UDP_51000_tc_all.log'%udpLogDir
    logger.debug('CiLogNameFormat is %s'%CiLogNameFormat)
    return testcasePath

#get number of physical antenna according to the name of UM_MAP_XXX file
#this number will decide the number of antenna files and refrence files
def GetNumOfTxAntennasInLocalCell(caseName, maxPipe):
    global numOfTxAntennasInLocalCell
    if(caseName == 'UM_MAP_005'): numOfTxAntennasInLocalCell = 1
    elif(caseName == 'UM_MAP_006' or caseName == 'UM_MAP_003'): numOfTxAntennasInLocalCell = 2
    elif(caseName == 'UM_MAP_007'): numOfTxAntennasInLocalCell = 8
    elif(caseName == 'UM_MAP_008' or caseName == 'UM_MAP_009' or caseName == 'UM_MAP_002'): numOfTxAntennasInLocalCell = 4
    elif(caseName == 'UM_MAP_010'): numOfTxAntennasInLocalCell = 12
    elif(caseName == 'UM_MAP_013'): numOfTxAntennasInLocalCell = 16
    elif('UM_MAP_' in caseName):
        numOfTxAntennasInLocalCell = maxPipe
    
def ReadBwPortDs(casePath, useTmpFile=False):
    global checkLog
    logger.debug('casePath: %s'%casePath)
    
    if useTmpFile:
        scriptFileName =  '%s/%s.%s%s'%(casePath,rtmScriptName,rtmScriptSuffix,tmpFileStr)
    else:
        scriptFileName = '%s/%s.%s'%(casePath,rtmScriptName,rtmScriptSuffix)
        
    try:
        scriptFile = open(scriptFileName, 'r')
    except Exception,e:
        logger.error('Can not open %s'%scriptFileName)
        return (-1,-1,-1,-1,-1,None)
    numOfTxPort = 2
    cellID = None
    logNeedToCheck = -1
    bwList = []
    portList = []
    dsList = []
    for line in scriptFile:
        findList = re.findall('\@numOfTxPortsList\s*=\s*\((.*)\)\s*;',line)
        if findList:
            for i in findList[0].split(','):
                portList.append(int(i))
        elif(len(re.findall('\$numOfTxPorts\s*=\s*(\d+)\s*;',line)) != 0):
            numOfTxPort = int(re.findall('\$numOfTxPorts\s*=\s*(\d+)\s*;',line)[0])
            portList.append(numOfTxPort)
        else:
            findList = re.findall('\@dlChBwList\s*=\s*\((.*)\)\s*;',line)
            if findList:
                for i in findList[0].split(','):
                    bwList.append(int(i)/5)
            elif(len(re.findall('\$dlChBw\s*=\s*(\d+)\s*;',line)) != 0):
                bwList.append((int(re.findall('\$dlChBw\s*=\s*(\d+)\s*;',line)[0]))/5)
            else:
                findList = re.findall('\@actDownSamplingList\s*=\s*\((.*)\)\s*;',line)
                if findList:
                    for i in findList[0].split(','):
                        dsList.append(int(i))
                elif(len(re.findall('\$actDownSampling\s*=\s*(\d+)\s*;',line)) != 0):
                    dsList.append(int(re.findall('\$actDownSampling\s*=\s*(\d+)\s*;',line)[0]))
                elif (len(re.findall('\$lnCelId\s*=\s*0x(\d+)\s*;',line)) != 0):
                    cellID = int(re.findall('\$lnCelId\s*=\s*0x(\d+)\s*;',line)[0],16)
                else:
                    if checkLog:
                        if(line.find('$checkLog = "') != -1):
                            logNeedToCheck = line.split('"')[1]
        if((len(bwList) != 0 and len(portList) != 0 and len(dsList) != 0) or line.find('PBCH parameters') != -1):
            break
    scriptFile.close()
    if not bwList:bwList.append(20)
    if not portList: portList.append(2)
    if not dsList:
            if(len(bwList) == 1): dsList.append(0)
            elif(len(bwList) == 2): dsList = [0,0]
            else: dsList = [0,0,0]
    for i in range(len(bwList)):
        if(bwList[i] == 20 and dsList[i] == 1):
            bwList[i] = 15
    logger.debug('bandwidth list is %s,port list is %s,downsample list is %s,logneedtocheck is %s'%(bwList,portList,dsList,str(logNeedToCheck)))
    return (bwList,portList,dsList,numOfTxPort,logNeedToCheck,cellID)

#read script.rtm to get the value of $numOfTxPorts and $dlChBw
#set the antenna files name and reference files name and antennaCoefs according to Deployment and number of physical antenna
def ParseScript(numOfTxAntennasInLocalCell,casePath,antennaBitmap):
    global Deployment,antennaGroupIdIni
    logger.debug('numOfTxAntenna = %s, casePath = %s'%(numOfTxAntennasInLocalCell,casePath))
    bwList,portList,dsList,numOfTxPort,logNeedToCheck,cellID = ReadBwPortDs(casePath)
    if(bwList == -1 or portList == -1 or dsList == -1 or numOfTxPort == -1):
        return (-1,-1,-1,-1,-1,-1,-1)
    antennaFilesName = []
    referenceFilesName = []
    for cellIndex in range(len(portList)):
        if(Deployment == 1 or Deployment == 2):      #2 port
            if(portList[cellIndex] == 1):            #SISO
                antennaFilesNameTmp = antennaFilesNameSISO2Port[0:4]
                referenceFilesNameTmp = antennaFilesNameSISO2Port[0:4]
            else:                                    #MIMO
                antennaFilesNameTmp = antennaFilesNameMIMO2Port[0:numOfTxAntennasInLocalCell]
                referenceFilesNameTmp = antennaFilesNameMIMO2Port[0:numOfTxAntennasInLocalCell]
        elif(Deployment == 3):                       #4 port
            antennaFilesNameTmp = antennaFilesNameMIMO2Port[0:numOfTxAntennasInLocalCell]
            referenceFilesNameTmp = antennaFilesName4Port[0:numOfTxAntennasInLocalCell]
        elif(Deployment == 5):                       #multi-cell
            antennaFilesNameTmp = antennaFilesNameMIMO2Port[0:portList[cellIndex]]
            referenceFilesNameTmp = antennaFilesName4Port[0:portList[cellIndex]]
        elif(Deployment ==6):                        #super cell
            if(numOfTxPort == 1):                    #SISO
                antennaFilesNameTmp = antennaFilesNameSISO2Port[0:6]
                referenceFilesNameTmp = antennaFilesNameSISO2Port[0:6]
            else:                                    #MIMO
                antennaFilesNameTmp = antennaFilesNameMIMO2Port[0:numOfTxAntennasInLocalCell]
                referenceFilesNameTmp = antennaFilesNameMIMO2Port[0:numOfTxAntennasInLocalCell]
        elif(Deployment ==7):
            antennaFilesNameTmp = antennaFilesName3DMIMO16Port[0:numOfTxAntennasInLocalCell]
            referenceFilesNameTmp = ['AntennaGroup'+str(antennaGroupIdIni)+'_'+ name for name in antennaFilesName16Port[0:numOfTxAntennasInLocalCell]]
        else:
            logger.error('Deployment %d is not support'%Deployment)
            exit()
        for i in range(len(antennaFilesNameTmp)):
            antennaFilesNameTmp[i] += str(cellIndex)            
            antennaFilesName.append(antennaFilesNameTmp[i])
        for i in range(len(referenceFilesNameTmp)):
            referenceFilesNameTmp[i] += str(cellIndex)
            referenceFilesName.append(referenceFilesNameTmp[i])
    antennaCoefs = 0
    if(Deployment == 1):
        if((antennaBitmap & 1) != 0 and (antennaBitmap & 2) == 0):
            antennaCoefs = (2,4)
        elif((antennaBitmap & 1) == 0 and (antennaBitmap & 2) != 0):
            antennaCoefs = (1,3)
        elif((antennaBitmap & 1) != 0 and (antennaBitmap & 2) != 0):
            antennaCoefs = (1,2,3,4)
    elif(Deployment == 2):
        if((antennaBitmap & 1) != 0 and (antennaBitmap & 2) == 0):
            antennaCoefs = (2,4,6,8)
        elif((antennaBitmap & 1) == 0 and (antennaBitmap & 2) != 0):
            antennaCoefs = (1,3,5,7)
        elif((antennaBitmap & 1) != 0 and (antennaBitmap & 2) != 0):
            antennaCoefs = (1,2,3,4,5,6,7,8)
    elif(Deployment == 7):
        antennaCoefs = (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16)
    logger.debug('antennaFilesName is %s,referenceFilesName is %s,antennaCoefs is %s'\
                 %(antennaFilesName,referenceFilesName,antennaCoefs))
    return (antennaFilesName,referenceFilesName,antennaCoefs,bwList,portList,dsList,logNeedToCheck)

#parse case list to get case name,case path,log path...and take these arguments making a detailed test case list as below
#e.g.[[caseName,casePath,logDir,antnnaBitmap,...],[caseName,...],[caseName,...],....]
def Parse():
    global CaseListName,sctRoot,prologHandleCount,numOfTxAntennasInLocalCell,checkMD5,boardType,sanwichConf,antennaGroupIdIni,poolId,calibrationCase
    times = 0
    testcasePath = ParseCasePath(CaseListName)
    newCaseListName = genUmMap.createWholeCaseList(sctRoot, testcasePath, CaseListName, boardType, sanwichConf)
    try:
        tc_all_lst = open('%s/%s'%(testcasePath,newCaseListName),'r')
    except Exception,e:
        logger.error('Can not open this testcase %s,please check'%newCaseListName)
        exit()
    for line in tc_all_lst:
        calOn,noFFT,scfTime,scfFreq,noThread,allDsp,caseName,antennaBitmap,cpListBySubf,slave, maxPipe, mapAllowedPhtxLogIdMin, mapAllowedPhtxLogIdMax, mapAllowedRtmLogIdMin, mapAllowedRtmLogIdMax = ParseTc_all_lst(line)
        if(caseName != 0):
            caseType = ParseCaseDir(caseName)
            if (caseName == 'UM_MAP_013'):
                if antennaGroupIdIni == 0:
                    antennaGroupIdIni = getRandomAntennaGPId()
                poolId = 1
                logger.info('Antenna Group ID: %s,  poolId: %s' %(antennaGroupIdIni,poolId))

            casePath = '%s/testcases_tdd/%s/%s'%(sctRoot,caseType,caseName)
            if(os.path.exists(casePath) == False):
                logger.error('Can not find %s in directory testcases_tdd,please check'%caseName)
                continue
            GetNumOfTxAntennasInLocalCell(caseName, maxPipe)
            logDir = '%s/LOGS'%casePath
            if not os.path.exists(logDir):
                os.mkdir(logDir)
            if(int(antennaBitmap,16) < 0 or int(antennaBitmap,16) > 15):
                logger.error('Antenna bitmap of %s is out of range 0-15'%caseName)
                continue
            antennaFilesName = referenceFilesName = antennaCoefs = calFile = \
            bandWidthList = numOfTxPortList = downSampleList = 0
            checkAntennaFile = transmitMD5 = generateMD5 = 0
            result = logNeedToCheck = -1
            if(caseType != 'MAP' and caseType != 'DIA' and int(antennaBitmap,16) != 0):
                antennaFilesName,referenceFilesName,antennaCoefs,bandWidthList,numOfTxPortList,downSampleList,\
                logNeedToCheck = ParseScript(numOfTxAntennasInLocalCell,casePath,int(antennaBitmap,16))
                if(logNeedToCheck == -1 or logNeedToCheck == ''):
                    checkAntennaFile = 1
                if(calOn != 0): calFile = '%s/%s.%s'%(casePath,calFileName,calFileSuffix)
            if(allDsp == 'allDsp' and prologHandleCount > 1): times = prologHandleCount
            else: times = 1

            if(caseName.find('BM_') != -1):
                logNeedToCheck = -1
                checkAntennaFile = transmitMD5 = generateMD5 = 0
            for i in range(times):
                TestCases.append([caseName,casePath,logDir,antennaBitmap,bandWidthList,cpListBySubf,calOn,noFFT,scfTime,\
                    scfFreq,noThread,allDsp,antennaFilesName,referenceFilesName,antennaCoefs,calFile,result,\
                    checkAntennaFile,numOfTxPortList,downSampleList,transmitMD5,generateMD5,logNeedToCheck,slave,\
                    mapAllowedPhtxLogIdMin, mapAllowedPhtxLogIdMax, mapAllowedRtmLogIdMin, mapAllowedRtmLogIdMax])
                if calibrationCase:
                    retryTestCases.append(
                        [caseName, casePath, logDir, antennaBitmap, bandWidthList, cpListBySubf, 0, 0, scfTime, \
                         scfFreq, noThread, allDsp, antennaFilesName, referenceFilesName, antennaCoefs, calFile, result, \
                         checkAntennaFile, numOfTxPortList, downSampleList, transmitMD5, generateMD5, logNeedToCheck, slave, \
                         mapAllowedPhtxLogIdMin, mapAllowedPhtxLogIdMax, mapAllowedRtmLogIdMin, mapAllowedRtmLogIdMax])
    tc_all_lst.close()

#read log which generated after put and get to check if put/get is successful
def CheckSicftp(logDir,operation,File,suffix,logFileName):
    try:
        logFile = open(r'%s/%s'%(logDir,logFileName),'r')
    except Exception,e:
        logger.error(r'%s %s.%s failed: can not open %s/%s'%(operation,File,suffix,logDir,logFileName))
        return -1
    for line in logFile:
        noLineBreak = line.strip('\n')
        if(len(re.findall('successfully|received',noLineBreak)) != 0):
            logFile.close()
            return 1
    logger.warn(r'%s %s.%s failed: %s'%(operation,File,suffix,logFile))
    logFile.close()
    return -1

#use sicftpRTM.exe to put or get files to/from specific dsp and port
#check the result of put and get
def Sicftp(operation,filePath,File,suffix,fileNewName,fileNewSuffix,logDir,rtmControlNodeId,port):
    global sctRoot
    if not File:
        logger.error('file name is empty, sicftp could not %s it, please check'%operation)
        return -1
    if(fileNewName == ''): fileNewName = File
    if(fileNewSuffix == ''): fileNewSuffix = suffix
    logFileName = '%sRTMFile_%s.log'%(operation,fileNewName)
    if(operation == 'put'):
        cmd = r'%s/tools/sicftp-client/sicftpRTM.exe -c %s -T %d -p %s/%s.%s %s.%s > %s/%s'\
              %(sctRoot,rtmControlNodeId,port,filePath,File,suffix,fileNewName,fileNewSuffix,logDir,logFileName)
    else:
        cmd = r'%s/tools/sicftp-client/sicftpRTM.exe -c %s -T %d -s 4096 -g %s.%s %s.%s > %s/%s'\
              %(sctRoot,rtmControlNodeId,port,File,suffix,fileNewName,fileNewSuffix,logDir,logFileName)
    logger.debug(cmd)
    if(os.system(cmd)):
        logger.error('%s failed'%cmd)
        return -1
    if(operation == 'get'):
        try:
            os.rename('%s/%s.%s'%(os.getcwd(),File,suffix),'%s/%s.%s'%(logDir,fileNewName,fileNewSuffix))
        except Exception,e:
            print e
            pass
    if(CheckSicftp(logDir,operation,File,suffix,logFileName) == 1): return 1
    return -1

#estimate if common files existed in specific dsp and port already
def CommonFilesExistInRtm(rtmControlNodeId,port):
    global startRoot
    try:
        commonFileList = open('%s/%s'%(startRoot,commonFilesListName),'r')
    except Exception,e:
        logger.error('Can not open %s/%s,please check'%(startRoot,commonFilesListName))
        AbnormalExit()
    for line in commonFileList:
        noLineBreak = line.strip('\n')
        if not noLineBreak:
            continue
        logger.debug('get %s'%noLineBreak)
        if(Sicftp('get','',noLineBreak,rtmScriptSuffix,'','',startRoot,rtmControlNodeId,port) == -1):
            logger.warn('can not get %s from rtm'%noLineBreak)
            commonFileList.close()
            return -1
        else:
            logger.info('get %s successful'%noLineBreak)
            break
    commonFileList.close()
    return 1

#transmit common files such as adapt.rtm,globalParam.rtm to specific dsp and port
def TransmitCommonFiles(rtmControlNodeId,port):
    global udpLogDir,startRoot
    logger.info('Transmit common files to %s:%d'%(rtmControlNodeId,port))
    try:
        commonFileList = open('%s/%s'%(startRoot,commonFilesListName),'r')
    except Exception,e:
        logger.error('Can not open %s/%s,please check'%(startRoot,commonFilesListName))
        AbnormalExit()
    for line in commonFileList:
        noLineBreak = line.strip('\n')
        if not noLineBreak:
            continue
        logger.debug('put %s'%noLineBreak)
        if(Sicftp('put',commonFilesDir,noLineBreak,rtmScriptSuffix,'','',udpLogDir,rtmControlNodeId,port) == -1):
           commonFileList.close()
           AbnormalExit()
    commonFileList.close()

#allocate a avaliable dsp and port
def AllocHandle():
    logger.debug('allochandle')
    allocHandle = 0
    with condHandle:
        if(len(prologFreeHandle) == 0):
            condHandle.wait(10)
        else:
            allocHandle = prologFreeHandle.pop(0)
            prologWorkingHandle.append(allocHandle)
        condHandle.notify()
    return allocHandle

#get index of prologWorkingHandle according to targetSicad
def GetWorkingHandleIndex(targetSicad):
    logger.debug('targetSicad = %s'%targetSicad)
    result = -1
    count = 0
    with condHandle:
        if(len(prologWorkingHandle) == 0):
            condHandle.wait()
        else:
            for workingHandle in prologWorkingHandle:
                if(workingHandle[4] == targetSicad):
                    result = count
                    break
                count += 1
        condHandle.notify()
    if(result == -1):
        logger.error('handle index out of range')
    return result

#according to targetSicad,release the dsp and port correspondingly
def FreeHandle(targetSicad):
    logger.debug('targetSicad = %s'%targetSicad)
    workingHandleIndex = GetWorkingHandleIndex(targetSicad)
    if(workingHandleIndex == -1):
        AbnormalExit()
    with condHandle:
        if(len(prologWorkingHandle) == 0):
            condHandle.wait()
        else:
            logger.debug('prologfreehandle: %s'%prologFreeHandle)
            logger.debug('prologworkinghandle: %s'%prologWorkingHandle)
            for i in range(len(prologWorkingHandle)):
                if(workingHandleIndex == i):
                    handleToBeFree = prologWorkingHandle.pop(i)
                    handleToBeFree[6] = []
                    prologFreeHandle.append(handleToBeFree)
                    break
        condHandle.notify()
    return 

#release all dsps and ports 
def FreeAllHandle():
    with lockHandle:
        while(len(prologWorkingHandle)):
            handleToBeFree = prologWorkingHandle.pop(0)
            handleToBeFree[6] = 0
            prologFreeHandle.append(handleToBeFree)
	logger.debug(prologWorkingHandle)
	logger.debug(prologFreeHandle)
    return

#transmit Weightdata.bin and Calcoefdata.bin if it existed
def TransmitWeightFile(filePath,logDir,rtmControlNodeId,port,cellID=None):
    result = 0
    index = 0
    
    #if cellID:
    #    index = (cellID-1)&0x0f
        
    if index > 0:
        NewWeightFileName = '%s_%d'%(weightFileName,index)
        NewCalFileName = '%s_%d'%(calFileName,index)
    else:
        NewWeightFileName = ''
        NewCalFileName = ''
        
    if(os.path.exists('%s/%s.%s'%(filePath,weightFileName,weightFileSuffix)) ==  True):
        #logger.debug('transmit weight file start at %s'%time.asctime())
        if(Sicftp('put',filePath,weightFileName,weightFileSuffix,NewWeightFileName,'',logDir,rtmControlNodeId,port) == 1):
            result = 1
    if(os.path.exists('%s/%s.%s'%(filePath,calFileName,calFileSuffix)) == True):
        if(Sicftp('put',filePath,calFileName,calFileSuffix,NewCalFileName,'',logDir,rtmControlNodeId,port) == 1):
            result = 2
    return result

    
def TransmitScenarioFile(filePath,logDir,rtmControlNodeId,port):
    global boardType
    scenarioFileName = scenarioFileSuffix = ''
    refloadFileName = refloadFileSuffix = ''
    
    fileList = os.listdir(filePath)
    for f in fileList:
        if boardType.find('nyquist') != -1:
            if f.find('fsmr3Scenario') != -1:
                scenarioFileName = f.split('.')[0]
                scenarioFileSuffix = f.split('.')[1]
            if f.find('fsmr3RefLoad') != -1:
                refloadFileName = f.split('.')[0]
                refloadFileSuffix = f.split('.')[1]
        elif boardType.find('fsm4') != -1:
            if f.find('fsmr4Scenario') != -1:
                scenarioFileName = f.split('.')[0]
                scenarioFileSuffix = f.split('.')[1]
            if f.find('fsmr4RefLoad') != -1:
                refloadFileName = f.split('.')[0]
                refloadFileSuffix = f.split('.')[1]
    
    if not scenarioFileName or not scenarioFileSuffix or not refloadFileName or not refloadFileSuffix:
        return 0
        
    if(Sicftp('put',filePath,scenarioFileName,scenarioFileSuffix,'Scenario','',logDir,rtmControlNodeId,port) == 1):
        if(Sicftp('put',filePath,refloadFileName,refloadFileSuffix,'RefLoad','',logDir,rtmControlNodeId,port) == 1):
            return 1
    return -1
    

#send start message to RTM
def SendReq(dspId,targetSicad,weight,checkAntennaFile,isRemote,remoteDspId,slave,antennaGroupIdIni,poolId):
    global McuSocket,boardType,boardId,checkMD5,rtmControlCpuId,rtmCaptureCpuId,Deployment,multiRTM,leftRtmOfSanwich
    msgId       = '00002229'
    if(slave == 2): msgId = '00002228'
    parameter1  = '0000000%d'%leftRtmOfSanwich
    parameter2  = '00000000'
    parameter3  = '0000000%d'%slave
    parameter4  = '000000%s%s'%(rtmControlCpuId,rtmCaptureCpuId)
    parameter5  = '00000001'
    parameter6  = '%08x'%dspId
    parameter7  = '0000000%d'%Deployment
    parameter8  = '%02d000000'%int(boardId)
    if(weight != 0):
        parameter9  = '0000000%d'%weight
    else:
        parameter9  = '00000000'
    if(isRemote != 0):
        parameter10 = '0000000%d'%isRemote
    else:
        parameter10 ='00000000'
    parameter11 = '%08x'%remoteDspId
    parameter12 = '00000000'
    if checkMD5 and checkAntennaFile:
        parameter12 = '0000000%d'%checkMD5
    if(boardType == 'fsm4_adv'):          #for FSM_ADV
        parameter13 = '00000001'
    elif(boardType == 'fsm4_bas'):       #for FSM4_BAS
        parameter13 = '00000002'
    elif(boardType == 'fzm'):
        parameter13 = '00000003'
    elif(boardType == 'fsm4_Ehance'):       #for FSM4_Ehance
        parameter13 = '00000004'
    elif (boardType == 'nyquist_adv'):
        parameter13 = '00000005'
    else:                            #for Nyquist
        parameter13 = '00000000'
    parameter14 = '%08x'%int(targetSicad,16)
    parameter15 = '0000000%d'%int(antennaGroupIdIni)
    parameter16 = '%08x'%int(hex(poolId),16)
    parameterCount = '00000016'
    parameters = parameter1+parameter2+parameter3+parameter4+parameter5+parameter6+\
                 parameter7+parameter8+parameter9+parameter10+parameter11+parameter12+parameter13+parameter14+parameter15+parameter16
    #for i in range(0,13):
	#logger.debug('parameter%d = %s'%(i+1,parameters[8*i:8*i+8]))
    length = '%04x'%(6 * 4 + (int(parameterCount) * 4))
    system = '00'
    sender = '00'
    header = '7e04%s00010000'%length
    
    if multiRTM == 1:
        logLevel = '00020040'
    else:
        logLevel = '00000040'
        
    messageContent = header+msgId+targetSicad+sourceSicad+length+system+sender+logLevel+parameterCount+parameters
    message = binascii.unhexlify(messageContent)
    try:
        McuSocket.send(message)
    except Exception,e:
        logger.error(e)
        AbnormalExit()

def TransmitMD5File(rtmCaptureNodeId,port,caseLogDir,casePath,caseName):
    logger.debug('tranmit MD5 files')
    md5FileList = []
    antennaMD5File = 'antenna.md5'
    flag = result = 0
    refDir = '%s/REFERENCE'%casePath
    if(os.path.exists(refDir) == False):
        logger.error('no such folder %s, use antenna files to compare'%refDir)
        return -1
    fileList = os.listdir(refDir)
    for f in fileList:
        if(f == 'antenna.md5' or f == 'AntennaGroup'+str(antennaGroupIdIni)+'.md5'):
            flag = 1
            break
        else:
            if(f.find('.md5') != -1) and not re.match('^AntennaGroup',f):
                md5FileList.append(f)
                              
    if flag:
        if (f == 'antenna.md5'):
            result = Sicftp('put',refDir,'antenna','md5','','',caseLogDir,rtmCaptureNodeId,port)
        else:
            result = Sicftp('put',refDir,'AntennaGroup'+str(antennaGroupIdIni),'md5','antenna','md5',caseLogDir,rtmCaptureNodeId,port)            
    elif(flag == 0 and len(md5FileList) != 0):
	md5File = open('%s/antenna.md5'%refDir,'w')
	for f in md5FileList:
            try:
                md5_file = open('%s/%s'%(refDir,f),'r')
            except Exception,e:
                logger.error('can not open %s/%s, please check'%(refDir,f))
		continue
            for line in md5_file:
                print >> md5File,line,
            md5_file.close()		
        md5File.close()
        result = Sicftp('put',refDir,'antenna','md5','','',caseLogDir,rtmCaptureNodeId,port)
        if (antennaGroupIdIni in (1,2,3,4)):
            os.rename('%s/antenna.md5'%refDir,'%s/%s'%(refDir,'AntennaGroup'+str(antennaGroupIdIni)+'.md5'))
            for file in md5FileList:
                os.remove("%s/%s"%(refDir,file))
    if not result:
        logger.info('no md5 file exist, generate them later. use antenna files to compare this time')
    elif(result == -1):
        logger.error('transmit md5 file failed, use antenna files to compare')
    return result

    

    
def  GetAntennaFileNames(antennaFilesName, referenceFilesName, cellID, Deployment, numOfTxPort, pipe):
    global antennaGroupIdIni
    if(Deployment == 2 or (Deployment == 5 and pipe == 8)):      #2 port                                   #MIMO
        antennaFilesNameTmp = antennaFilesNameMIMO2Port[0:pipe]
        referenceFilesNameTmp = antennaFilesNameMIMO2Port[0:pipe]
    elif(Deployment == 3):                       #4 port
        antennaFilesNameTmp = antennaFilesNameMIMO2Port[0:pipe]
        referenceFilesNameTmp = antennaFilesName4Port[0:pipe]
    elif(Deployment == 5):                       #multi-cell
        antennaFilesNameTmp = antennaFilesNameMIMO2Port[0:numOfTxPort]
        referenceFilesNameTmp = antennaFilesName4Port[0:numOfTxPort]
    elif(Deployment ==6):                        #super cell
        if(numOfTxPort == 1):                    #SISO
            antennaFilesNameTmp = antennaFilesNameSISO2Port[0:6]
            referenceFilesNameTmp = antennaFilesNameSISO2Port[0:6]
        else:                                    #MIMO
            antennaFilesNameTmp = antennaFilesNameMIMO2Port[0:pipe]
            referenceFilesNameTmp = antennaFilesNameMIMO2Port[0:pipe]
    elif(Deployment ==7):
        antennaFilesNameTmp = antennaFilesName3DMIMO16Port[0:pipe]
        referenceFilesNameTmp =  ['AntennaGroup'+str(antennaGroupIdIni)+'_'+ name for name in antennaFilesName16Port[0:pipe]]		
    else:
        logger.error('Deployment %d is not support'%Deployment)
        return False
        
    for i in range(len(antennaFilesNameTmp)):
        if cellID == None:
            cellID = 1
        antennaFilesNameTmp[i] += str((cellID-1)&0x0f)            
        antennaFilesName.append(antennaFilesNameTmp[i])
        
    for i in range(len(referenceFilesNameTmp)):
        referenceFilesNameTmp[i] += str(0)
        referenceFilesName.append(referenceFilesNameTmp[i])
        
    return True
    
    
def GetAntennaCoefs(antennaBitmap, Deployment,pipe):
    antennaCoefs = 0
    if(Deployment == 1):
        if((antennaBitmap & 1) != 0 and (antennaBitmap & 2) == 0):
            antennaCoefs = (2,4)
        elif((antennaBitmap & 1) == 0 and (antennaBitmap & 2) != 0):
            antennaCoefs = (1,3)
        elif((antennaBitmap & 1) != 0 and (antennaBitmap & 2) != 0):
            antennaCoefs = (1,2,3,4)
    elif(Deployment == 2 or (Deployment == 5 and pipe == 8)):
        if((antennaBitmap & 1) != 0 and (antennaBitmap & 2) == 0):
            antennaCoefs = (2,4,6,8)
        elif((antennaBitmap & 1) == 0 and (antennaBitmap & 2) != 0):
            antennaCoefs = (1,3,5,7)
        elif((antennaBitmap & 1) != 0 and (antennaBitmap & 2) != 0):
            antennaCoefs = (1,2,3,4,5,6,7,8)
    elif(Deployment == 7):
        antennaCoefs = (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16)
            
    return antennaCoefs

    

    
    
def ParseCaseConfig(maxPipe,casePath,antennaBitmap):
    global Deployment
    logger.debug('numOfTxAntenna = %s, casePath = %s'%(maxPipe,casePath))
    
    bwList,portList,dsList,numOfTxPort,logNeedToCheck,cellID = ReadBwPortDs(casePath, True)
    if(bwList == -1 or portList == -1 or dsList == -1 or numOfTxPort == -1):
        return (-1,-1,-1,-1,-1,-1,-1,None)
        
    antennaFilesName = []
    referenceFilesName = []
    result = GetAntennaFileNames(antennaFilesName, referenceFilesName, cellID, Deployment, numOfTxPort, maxPipe)
    if result == False:
        exit()
    
    antennaCoefs = GetAntennaCoefs(antennaBitmap, Deployment,maxPipe)
    
    logger.debug('antennaFilesName is %s,referenceFilesName is %s,antennaCoefs is %s'\
                 %(antennaFilesName,referenceFilesName,antennaCoefs))
    return (antennaFilesName,referenceFilesName,antennaCoefs,bwList,portList,dsList,logNeedToCheck,cellID)
    
  
    
#def MultiCaseSort(multiCaseList):
#    multiCaseList.sort(key=lambda x:x[24] )
 
 
def ParseMultiListFile(multiListFile, multiCaseList):
    global antennaGroupIdIni,poolId
    try:
        multiList = open(multiListFile, 'r')
    except Exception,e:
        logger.error('Can not open this file %s,please check'%multiListFile)
        return False            
                
    for line in multiList:
        calOn,noFFT,scfTime,scfFreq,noThread,allDsp,caseName,antennaBitmap,cpListBySubf,slave, maxPipe, mapAllowedPhtxLogIdMin, mapAllowedPhtxLogIdMax, mapAllowedRtmLogIdMin, mapAllowedRtmLogIdMax = ParseTc_all_lst(line)
        if(caseName != 0):
            caseType = ParseCaseDir(caseName)
            if (caseName == 'UM_MAP_013'):
                if antennaGroupIdIni == 0:
                    antennaGroupIdIni = getRandomAntennaGPId()
                poolId = 1
                logger.info('Antenna Group ID: %s,  poolId: %s' %(antennaGroupIdIni,poolId))
				
            casePath = '%s/testcases_tdd/%s/%s'%(sctRoot,caseType,caseName)
            if(os.path.exists(casePath) == False):
                logger.error('Can not find %s in directory testcases_tdd,please cheak'%caseName)
                break

            logDir = '%s/LOGS'%casePath
            if not os.path.exists(logDir):
                os.mkdir(logDir)
            slave = 0
            
            if(int(antennaBitmap,16) < 0 or int(antennaBitmap,16) > 15):
                logger.error('Antenna bitmap of %s is out of range 0-15'%caseName)
                break
          
            antennaFilesName = referenceFilesName = antennaCoefs = calFile = \
            bandWidthList = numOfTxPortList = downSampleList = 0
            checkAntennaFile = transmitMD5 = generateMD5 = 0
            result = logNeedToCheck = -1
            
            if(caseType != 'MAP' and caseType != 'DIA' and int(antennaBitmap,16) != 0):
                antennaFilesName,referenceFilesName,antennaCoefs,bandWidthList,numOfTxPortList,downSampleList,\
                logNeedToCheck,cellID = ParseCaseConfig(maxPipe,casePath,int(antennaBitmap,16))
                if antennaFilesName == -1 or referenceFilesName == -1:
                    logger.error('Parse case params failed!')
                    exit()
                    
                if(logNeedToCheck == -1 or logNeedToCheck == ''):
                    checkAntennaFile = 1
                    
                if(calOn != 0): calFile = '%s/%s.%s'%(casePath,calFileName,calFileSuffix)

            if(caseName.find('BM') != -1):
                logNeedToCheck = -1
                checkAntennaFile = transmitMD5 = generateMD5 = 0            
           
            multiCaseList.append([caseName,casePath,logDir,antennaBitmap,bandWidthList,cpListBySubf,calOn,noFFT,scfTime,\
                              scfFreq,noThread,allDsp,antennaFilesName,referenceFilesName,antennaCoefs,calFile,result,\
                              checkAntennaFile,numOfTxPortList,downSampleList,transmitMD5,generateMD5,logNeedToCheck,slave,cellID,\
                              mapAllowedPhtxLogIdMin, mapAllowedPhtxLogIdMax, mapAllowedRtmLogIdMin, mapAllowedRtmLogIdMax])
        
    multiList.close()   


def getRTMScriptFileNames(targetSicadId, multiRtmFlg):
    scriptIndex = (int(targetSicadId,16) & 0x000f) - 2
    if scriptIndex > 0:
        remoteRtmScriptName = '%s_%d'%(rtmScriptName, scriptIndex)
    else:
        remoteRtmScriptName = ''
        
    localRtmScriptName = rtmScriptName
    
    if multiRtmFlg:
        localRtmScriptSuffix = '%s%s'%(rtmScriptSuffix, tmpFileStr)
        remoteRtmSuffix = rtmScriptSuffix
    else:
        localRtmScriptSuffix = rtmScriptSuffix
        remoteRtmSuffix = rtmScriptSuffix
        
    return (localRtmScriptName, localRtmScriptSuffix, remoteRtmScriptName, remoteRtmSuffix)
    

def SelectRTMProcess(subCaseIndex, length):
    if subCaseIndex < length/2:
        processIndex = subCaseIndex*2 
    elif subCaseIndex < length:
        processIndex = (subCaseIndex - length/2)*2 + 1
    else:
        logger.error('Sub Case Index %d out of range'%subCaseIndex)
        processIndex = 0
        
    return processIndex
    
    
def HandleMultiRTMProlog(handle,retry):
    global sanwichConf,antennaGroupIdIni,poolId
    caseName = handle[CASE_INFO_INDEX][CASE_NAME_INDEX]
    logger.info('Running %s on multiRTM'%caseName) 
    
    casePath = handle[CASE_INFO_INDEX][CASE_PATH_INDEX]
    caseLogDir = handle[CASE_INFO_INDEX][CASE_LOG_DIR_INDEX]
    checkAntennaFile = handle[CASE_INFO_INDEX][CHK_ANTENNA_FILE_INDEX]
          
    rtmControlNodeIdArr = handle[RTM_CTL_NODE_ID_INDEX]
    targetSicadArr = handle[TARGET_SICAD_INDEX]
    targetStatArr = handle[TARGET_STAT_INDEX]
    weight = []
    rtmCaptureNodeId = handle[RTM_CAPTRUE_NODE_ID_INDEX]
    slave = 0 
    
    multiListFile = '%s/tc_multi.lst'%casePath
    multiRtmFlg = os.path.exists(multiListFile)
    
    multiCaseList = []
    if multiRtmFlg:
        if sanwichConf and retry:
            try:
                os.remove('%s.tmp'%multiListFile)
            except Exception,e:
                pass
        genUmMap.setCellIDInScripts(sctRoot, multiListFile)
        ParseMultiListFile(multiListFile, multiCaseList)
        handle[CASE_INFO_INDEX][ANTENNA_FILE_NAME_INDEX] = []
        handle[CASE_INFO_INDEX].append(multiCaseList)
    else:
        multiCaseList.append(0)
        
    for subCaseIndex,subCase in enumerate(multiCaseList):
        multiRTMIndex = SelectRTMProcess(subCaseIndex, len(rtmControlNodeIdArr))
        if multiRTMIndex < len(rtmControlNodeIdArr):
            rtmControlNodeId = rtmControlNodeIdArr[multiRTMIndex]
            targetSicadId = targetSicadArr[multiRTMIndex]
        else:
            return 0
            
        if multiRtmFlg:
            handle[CASE_INFO_INDEX][ANTENNA_FILE_NAME_INDEX].extend(subCase[ANTENNA_FILE_NAME_INDEX])
            subCasePath = subCase[CASE_PATH_INDEX]
            subCaseLogDir = subCase[CASE_LOG_DIR_INDEX]
            cellID = subCase[CELL_ID_INDEX]
            logger.info('Case %s on %s'%(subCase[CASE_NAME_INDEX],targetSicadId)) 
        else:
            subCasePath = casePath
            subCaseLogDir = caseLogDir
            cellID = None
            
        result = TransmitWeightFile(subCasePath,subCaseLogDir,rtmControlNodeId,handle[PORT_INDEX],cellID)
        weight.insert(0,result)
        
        
        localRtmScriptName, localRtmScriptSuffix, remoteRtmScriptName, remoteRtmSuffix = getRTMScriptFileNames(targetSicadId, multiRtmFlg)
        
        if(Sicftp('put',subCasePath,localRtmScriptName,localRtmScriptSuffix,remoteRtmScriptName,remoteRtmSuffix,subCaseLogDir,rtmControlNodeId,handle[PORT_INDEX]) == -1):
            logger.error('transmit %s.%s of %s to Rtm failed'%(rtmScriptName,rtmScriptSuffix,caseName))
            FreeHandle(targetSicadArr)
            return 0
        if TransmitScenarioFile(casePath,caseLogDir,rtmControlNodeId,handle[0]) == -1:
            logger.error('transmit scenario file of %s to Rtm failed'%caseName)
            FreeHandle(targetSicadArr)
            return 0             
            
    if checkMD5 and checkAntennaFile:
        handle[CASE_INFO_INDEX][TRANSMIT_MD5_INDEX] = TransmitMD5File(rtmCaptureNodeId,handle[PORT_INDEX],caseLogDir,casePath,caseName)
        if not handle[CASE_INFO_INDEX][TRANSMIT_MD5_INDEX]:
            handle[CASE_INFO_INDEX][GENERATE_MD5_INDEX] = 1
            
    for subCaseIndex in range(len(multiCaseList)): 
        multiRTMIndex = SelectRTMProcess(subCaseIndex, len(targetSicadArr))
        if multiRTMIndex < len(targetSicadArr):
            targetSicadId = targetSicadArr[multiRTMIndex]
            targetStatArr[multiRTMIndex] = 'wait'
        else:
            return 0  
        
        SendReq(handle[DSP_ID_INDEX],targetSicadId,weight.pop(),checkAntennaFile,handle[IS_REMOTE_INDEX],handle[REMOTE_DSP_ID_INDEX],slave,antennaGroupIdIni,poolId)     
        
    return handle[CASE_INFO_INDEX]   
        
        
    
    
#allocate a avaliable dsp and port
#clean up all logs in log folder
#transmit Weightdata.bin,Calcoefdata.bin(if exists),script.rtm to allocated dsp and port
#send start message to allocated dsp and port
def HandleProlog(prologParameters,retry=False):
    global sanwichConf,antennaGroupIdIni,poolId
    logger.debug('testcase: %s'%prologParameters)
    caseName = prologParameters[0]
    needSpeacialHandle = False
    if sanwichConf and not retry and caseName.find('CE_DIA') != -1:
        needSpeacialHandle = True
        
    while True:
        handle = AllocHandle()
        if handle:
            if needSpeacialHandle:
                if handle[2][0].find('126') == -1:
                    with condHandle:
                        prologFreeHandle.append(handle)
                else:
                    break                   
            else:
                break
                
    handle[6] = prologParameters
    logger.debug('handle is %s'%handle)
    rtmControlNodeId = handle[2][0]
    if(len(handle[2]) == 2):
        localRtmControlNodeId = handle[2][1]
    else:
        localRtmControlNodeId = 0
    casePath = handle[6][1]
    caseLogDir = handle[6][2]
    checkAntennaFile = handle[6][17]
    slave = handle[6][23]
    fileList = os.listdir(caseLogDir)
    for f in fileList:
        try:
            os.remove('%s/%s'%(caseLogDir,f))
        except Exception,e:
            pass
            
    if(multiRTM == 1): 
        return HandleMultiRTMProlog(handle,retry)
    else:
        logger.info('Running %s on %s'%(caseName,rtmControlNodeId))
        result = TransmitWeightFile(casePath,caseLogDir,rtmControlNodeId,handle[0])
        if(Sicftp('put',casePath,rtmScriptName,rtmScriptSuffix,'','',caseLogDir,rtmControlNodeId,handle[0]) == -1):
            logger.error('transmit %s.%s of %s to Rtm failed'%(rtmScriptName,rtmScriptSuffix,caseName))
            FreeHandle(handle[4])
            return 0
        if TransmitScenarioFile(casePath,caseLogDir,rtmControlNodeId,handle[0]) == -1:
            logger.error('transmit scenario file of %s to Rtm failed'%caseName)
            FreeHandle(handle[4])
            return 0 
        if checkMD5 and checkAntennaFile:
            handle[6][20] = TransmitMD5File(handle[3],handle[0],caseLogDir,casePath,caseName)
            if not handle[6][20]:
                handle[6][21] = 1
        if(localRtmControlNodeId != 0 and caseName.find('MAP') == -1 and caseName.find('DIA') == -1 and slave != 0):
            if(Sicftp('put',casePath,rtmScriptName,rtmScriptSuffix,'','',caseLogDir,localRtmControlNodeId,handle[0]) == -1):
                logger.warn('transmit %s.%s of %s to localRtmController %s failed'%(rtmScriptName,rtmScriptSuffix,caseName,localRtmControlNodeId))
            else:
                if TransmitScenarioFile(casePath,caseLogDir,localRtmControlNodeId,handle[0]) == -1:
                    logger.warn('transmit scenario file of %s to localRtmController %s failed'%(caseName,localRtmControlNodeId))
                else: 
                    SendReq(handle[1],handle[4],result,checkAntennaFile,handle[7],handle[8],slave,antennaGroupIdIni,poolId)
                    result = 0
                    slave = slave + 1
                    localTargetSicad = '%s%s'%(localRtmControlNodeId,handle[4][4:])
                    SendReq(handle[1],localTargetSicad,result,checkAntennaFile,handle[7],handle[8],slave,antennaGroupIdIni,poolId)
        else:
            SendReq(handle[1],handle[4],result,checkAntennaFile,handle[7],handle[8],slave,antennaGroupIdIni,poolId)
            
        return handle[6]

#save UM_MAP_XXX and CE_DIA_XXX cases for reboot board
#if the cases more than two,always pop a old one
def SaveSession(testcaseParameters):
    if(len(re.findall('MAP|DIA',testcaseParameters[0])) != 0):
        if not sessionCases:
            sessionCases.append(testcaseParameters)
        else:
            if(testcaseParameters[0] != sessionCases[-1][0]):
                sessionCases.append(testcaseParameters)
    if(len(sessionCases) > 2):
        sessionCases.pop(0)

     
def FindList(index,allLists):
        for perList in allLists:
            if(index == int(perList[0])):
                return perList
        return None
       

def RtmDspMap(dspIndex, dspName, processList,rtmControlNodeIdArr,targetSicadArr,targetStatArr):
    global boardId
    
    if processList == None:
        return None
        
    for coreList in processList[1:]:
        coreId = coreList[0]
        for cpid in coreList[1:]:
            rtmControlNodeIdTmp = '%s%d%s'%(boardId,dspName,coreId)
            targetSicadTmp = '%s%s'%(rtmControlNodeIdTmp,cpid)
            rtmControlNodeIdArr.append(rtmControlNodeIdTmp)
            targetSicadArr.append(targetSicadTmp)
            targetStatArr.append(None)
        
    return 0

       
def HandleCoreAddr(dspIndexList,dspNameList,allDspProcessList,rtmControlNodeIdArr,targetSicadArr,targetStatArr):
    global boardType,dspNo
    if(boardType.find('fsm4') != -1 and len(dspNameList) >= 2):
        dspIndexList.pop(0)
        dspNameList.pop(0)
    for dspIndex in dspIndexList:
        if (boardType == 'nyquist_adv'):
            if (dspNameList[dspIndex] % 2 == 0):
                continue
        perDspProcessList = FindList(dspIndex, allDspProcessList)
        RtmDspMap(dspIndex, dspNameList[dspIndex], perDspProcessList,rtmControlNodeIdArr,targetSicadArr,targetStatArr)
    return 0
       
#put resource such as avaliable dsp,port,targetSicad etc. into list prologFreeHandle
#e.g.[[port,dsp,rtmControlNodeId,...],...]
def DealSicadEtc():
    global boardId,rtmCaptureCpuId,rtmControlCpuId,rtmControlCpid,syncSendPdsch,multiRTM,rtmCtlAllDspProcList,boardType
    port = 15002
    if(len(dspNo) == 1):
        rtmCaptureNodeId = '%s%d%s'%(boardId,dspNo[0],rtmCaptureCpuId)
        rtmControlNodeId = '%s%d%s'%(boardId,dspNo[0],rtmControlCpuId)
        targetSicad = '%s%s'%(rtmControlNodeId,rtmControlCpid)
        if multiRTM:
            rtmControlNodeIdArr = []
            targetSicadArr = []
            targetStatArr = []
            if (HandleCoreAddr([0],dspNo,rtmCtlAllDspProcList,rtmControlNodeIdArr,targetSicadArr,targetStatArr) == None):
                    logger.error('Wrong parameter for DSP NO,please check')
                    AbnormalExit()
                    
            prologFreeHandle.append([port,dspNo[0],rtmControlNodeIdArr,rtmCaptureNodeId,targetSicadArr,0,0,0,0,targetStatArr])
        else:
            prologFreeHandle.append([port,dspNo[0],[rtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,0,0])
    elif(len(dspNo) == 2):
        nu = dspNo[0]
        nu1 = dspNo[1]
        rtmCaptureNodeId = '%s%d%s'%(boardId,nu1,rtmCaptureCpuId)
        rtmControlNodeId = '%s%d%s'%(boardId,nu1,rtmControlCpuId)
        targetSicad = '%s%s'%(rtmControlNodeId,rtmControlCpid)
        if syncSendPdsch:
            localRtmControlNodeId = '%s%d%s'%(boardId,nu,rtmControlCpuId)
            prologFreeHandle.append([port,nu,[rtmControlNodeId,localRtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,1,nu1])
        elif multiRTM:
            rtmControlNodeIdArr = []
            targetSicadArr = []
            targetStatArr = []
            
            if (HandleCoreAddr([1,0],[nu,nu1],rtmCtlAllDspProcList,rtmControlNodeIdArr,targetSicadArr,targetStatArr) == None):
                logger.error('Wrong parameter for DSP NO,please check')
                AbnormalExit()
                
            prologFreeHandle.append([port,nu,rtmControlNodeIdArr,rtmCaptureNodeId,targetSicadArr,0,0,1,nu1,targetStatArr])
        else:
            prologFreeHandle.append([port,nu,[rtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,1,nu1])
    elif(len(dspNo) == 3):
        for nu in dspNo:
            if(boardType.find('fsm4') != -1):
                nu1 = nu
            else:
                nu1 = nu - 1
            rtmCaptureNodeId = '%s%d%s'%(boardId,nu1,rtmCaptureCpuId)
            rtmControlNodeId = '%s%d%s'%(boardId,nu1,rtmControlCpuId)
            targetSicad = '%s%s'%(rtmControlNodeId,rtmControlCpid)
            if syncSendPdsch and boardType.find('nyquist') != -1:
                localRtmControlNodeId = '%s%d%s'%(boardId,nu,rtmControlCpuId)
                prologFreeHandle.append([port,nu,[rtmControlNodeId,localRtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,1,nu1])
            elif multiRTM:
                rtmControlNodeIdArr = []
                targetSicadArr = []
                targetStatArr = []
                
                if (HandleCoreAddr([1,0],[nu,nu1],rtmCtlAllDspProcList,rtmControlNodeIdArr,targetSicadArr,targetStatArr) == None):
                    logger.error('Wrong parameter for DSP NO,please check')
                    AbnormalExit()
                
                if(boardType.find('fsm4') != -1):
                    prologFreeHandle.append([port,nu,rtmControlNodeIdArr,rtmCaptureNodeId,targetSicadArr,0,0,0,0,targetStatArr])
                else:
                    prologFreeHandle.append([port,nu,rtmControlNodeIdArr,rtmCaptureNodeId,targetSicadArr,0,0,1,nu1,targetStatArr])
            else:
                if(boardType.find('fsm4') != -1):
                    prologFreeHandle.append([port,nu,[rtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,0,0])
                else:
                    prologFreeHandle.append([port,nu,[rtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,1,nu1])
            port += 1
    elif(len(dspNo) == 4):
        if(boardType.find('fsm4') == -1):
            logger.error('%s not support 4 dsps parallel'%boardType)
            AbnormalExit()
        for i in range(len(dspNo)):
            nu = dspNo[i]
            if prologHandleCount == 2:
                if i == 1 or i == 3:
                    continue
                else:
                    nu1 = dspNo[i+1] 
            else:
                nu1 = nu
            rtmCaptureNodeId = '%s%d%s'%(boardId,nu1,rtmCaptureCpuId)
            rtmControlNodeId = '%s%d%s'%(boardId,nu1,rtmControlCpuId)
            targetSicad = '%s%s'%(rtmControlNodeId,rtmControlCpid)
            if syncSendPdsch and prologHandleCount == 2:
                localRtmControlNodeId = '%s%d%s'%(boardId,nu,rtmControlCpuId)
                prologFreeHandle.append([port,nu,[rtmControlNodeId,localRtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,1,nu1])
            elif multiRTM:
                rtmControlNodeIdArr = []
                targetSicadArr = []
                targetStatArr = []
                
                if (HandleCoreAddr([1,0],[nu,nu1],rtmCtlAllDspProcList,rtmControlNodeIdArr,targetSicadArr,targetStatArr) == None):
                    logger.error('Wrong parameter for DSP NO,please check')
                    AbnormalExit()
                
                if(prologHandleCount == 4):
                    prologFreeHandle.append([port,nu,rtmControlNodeIdArr,rtmCaptureNodeId,targetSicadArr,0,0,0,0,targetStatArr])
                else:
                    prologFreeHandle.append([port,nu,rtmControlNodeIdArr,rtmCaptureNodeId,targetSicadArr,0,0,1,nu1,targetStatArr])
            else:
                if(prologHandleCount == 4):
                    prologFreeHandle.append([port,nu,[rtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,0,0])
                else:
                    prologFreeHandle.append([port,nu,[rtmControlNodeId],rtmCaptureNodeId,targetSicad,0,0,1,nu1])
            port += 1
    else:
        logger.error('Wrong parameter for DSP NO,please check')
        AbnormalExit()
    logger.debug('rtmCaptureNodeId = %s, rtmControlNodeId = %s,targetSicad = %s'\
                          %(rtmCaptureNodeId,rtmControlNodeId,targetSicad))

#get messages from queueProlog and operate correspondingly
def Prolog():
    global prologHandleCount
    while True:
        prologMessage = queueProlog.get()
        logger.debug('%s'%(prologMessage,))
        if(prologMessage[0] == REBOOT_REQ):               #stop actions until get message REBOOT_RESP
            prologMessageBox = []
            prologMessage = queueProlog.get()
            while(prologMessage[0] != REBOOT_RESP):
                prologMessageBox.append(prologMessage)
                prologMessage = queueProlog.get()
            with lockQueueProlog:
                for prologMessage in prologMessageBox:
                    queueProlog.put(prologMessage)
            continue
        if(prologMessage[0] == PROLOG_INIT_REQ):          #transmit common files if them not existed in RTM
            DealSicadEtc()
            for handle in prologFreeHandle:
                transferNodeIdList = list(set(handle[2]))
                for destControlNodeId in transferNodeIdList:
                    if(CommonFilesExistInRtm(destControlNodeId,handle[0]) == -1):
                        TransmitCommonFiles(destControlNodeId,handle[0])
            with lockQueueMain:
                queueMain.put((PROLOG_INIT_RESP,))
        elif(prologMessage[0] == LOAD_COMMON_FILE_REQ):   #transmit common files to RTM no matter if them existed or not
            for handle in prologFreeHandle:
                transferNodeIdList = list(set(handle[2]))
                for destControlNodeId in transferNodeIdList:
                    TransmitCommonFiles(destControlNodeId,handle[0])
            with lockQueueMain:
                queueMain.put((LOAD_COMMON_FILE_RESP,))
        elif(prologMessage[0] == TEST_REQ):               #put TEST_ACK into queueMain and TEST_REQ into queuePeroration after send start message to RTM
            if(len(prologMessage) != 2):
                logger.error('no testcase passed when %s'%(prologMessage,))
                continue
            if(prologMessage[1][11] == 'allDsp' and prologHandleCount > 1):
                while(len(prologFreeHandle) != prologHandleCount):
                    pass
            prologParameters = HandleProlog(prologMessage[1])
            if not prologParameters:
                logger.info('%s failed'%prologMessage[1][0])
            try:
                with lockQueueMain:
                    queueMain.put((TEST_ACK,prologParameters))
                with lockQueuePeroration:
                    queuePeroration.put((TEST_REQ,prologParameters))
            except Exception,e:
                logger.error(e)
            if powerBreakPort:
                SaveSession(prologMessage[1])
        elif(prologMessage[0] == EXIT_REQ):               #quit the loop and end the current thread
            break
        else:
            logger.error('unexpected message %s'%(prologMessage,))             
            AbnormalExit()

#extract the message recieved from RTM
#TCP header(8 bytes),msgHeader:(reserveId(2 bytes),respId(2 bytes),sourceSicad(4 bytes),targetSicad(4 bytes),msgSize(2 bytes),flag(2 bytes)),msgBody(4 bytes)
def ExtractFromResp(message,targetSicadGroup,resultGroup):
    global sourceSicad,respCount
    returnValue = targetSicad = -1
    bytesCount = len(message)
    length = '0014'
    header = '7e04%s00010000'%length
    respId = '222a'
    lenOfSourceSicad = len(sourceSicad)
    nu = bytesCount / 28
    respCount += nu
    for i in range(nu):
        payload = binascii.hexlify(message[28*i:28*(i+1)])
        result = re.findall('%s[\d]{4}%s[\w]{%d}([\w]{%d})%s[\d]{4}([a-f0-9]{8})'\
                        %(header,respId,lenOfSourceSicad,lenOfSourceSicad,length),payload)
        if(len(result) != 0):
            targetSicad = result[0][0].upper()
            returnValue = result[0][1]
            logger.debug('RTM response recieved from %s, payload is %s'%(targetSicad,payload))
        else:
            logger.error('unexpected message recieved from RTM:%s'%payload)
            return (targetSicadGroup,resultGroup)
        if(returnValue == '00000000'): returnValue = 0
        targetSicadGroup.append(targetSicad)
        resultGroup.append(returnValue)
    return (targetSicadGroup,resultGroup)

#set the readTimeout of socket
#wait to recieve message comes from RTM
#if timeout,reboot board(if powerBreakPort) or return [[],[]]
def ReceiveResp():
    global McuSocket
    readTimeout = 400
    reboot = 0
    message = ''
    resultGroup = []
    targetSicadGroup = []
    canRead,canWrite,abnormal = select.select([McuSocket],[],[],readTimeout)
    if canRead:
        try:
            message = McuSocket.recv(28)
            if not message:
                logger.warn('recieve empty message from board')
                reboot = 1
        except Exception,e:
            logger.error('connection abort,start reboot board')
            reboot = 1
    else:
        logger.warn('timeout,waiting for response from board')
        reboot = 1
    if reboot:
        if powerBreakPort:
            with lockQueueMain:
                queueMain.put((REBOOT_REQ,))
            with lockQueueProlog:
                queueProlog.put((REBOOT_REQ,))
            with lockQueuePeroration:
                queuePeroration.put((REBOOT_REQ,))
            with lockQueueCompare:
                queueCompare.put((REBOOT_REQ,))
            with lockQueueReboot:
                queueReboot.put((REBOOT_REQ,))
            FreeAllHandle()
            return (targetSicadGroup,resultGroup)
        else:
            logger.info('did not use argument -P in command line,SCT won\'t reboot automatically')
            AbnormalExit()
    logger.debug('length of recieved message is %d'%len(message))
    return ExtractFromResp(message,targetSicadGroup,resultGroup)

#get antenna files from specific dsp and port
def GetAntennaFile(rtmCaptureNodeId,port,destDir,antennaFilesName):
    logger.debug('rtmCaptureNodeId = %s, port = %d, destDir = %s,\
                antennaFilesName = %s'%(rtmCaptureNodeId,port,destDir,antennaFilesName))
    for antennaFile in antennaFilesName:
        if(Sicftp('get','',antennaFile,'iq','','',destDir,rtmCaptureNodeId,port) == -1):
            logger.error('get antenna file %s from %s:%d failed'%(antennaFile,rtmCaptureNodeId,port))
            return -1

def GetHBFile(rtmControlNodeId,port,destDir,hbFileNames, nIndex, mapAllowedPhtxLogIdMin, mapAllowedPhtxLogIdMax, mapAllowedRtmLogIdMin, mapAllowedRtmLogIdMax):
    ret = 0
    logger.debug('rtmControlNodeId = %s, port = %d, destDir = %s,\
                hbFileName = %s'%(rtmControlNodeId,port,destDir,hbFileNames))
    occurPhytxLogCount = {}
    occurRtmLogCount = {}
    for hbFile in hbFileNames:
        hbFileNew = '%s_%d'%(hbFile, nIndex)
        if(Sicftp('get','',hbFile,'bin',hbFileNew,'bin',destDir,rtmControlNodeId,port) == -1):
            logger.error('get hb file %s from %s:%d failed'%(hbFile,rtmControlNodeId,port))
            ret = -1
            continue
        
        HbDecodeOutfilePath = '%s/tools/HistoryBuffer'%sctRoot;
        if(os.path.exists(r'%s'%(HbDecodeOutfilePath)) == False):
            logger.error('no such dir HbDecodeOutfilePath: %s, please check'%(HbDecodeOutfilePath))
            return -1
        HbViewerPath = '%s/tools/HistoryBuffer/HbViewer.exe'%sctRoot;
        if(os.path.exists(r'%s'%(HbViewerPath)) == False):
            logger.error('no such file HbViewerPath: %s, please check'%(HbViewerPath))
            return -1
        msgDecode = ''
        csvFile = '%s/PhyTxLog.csv'%HbDecodeOutfilePath
        if(boardType == 'fsm4_adv'):          #for FSM_ADV
            if(hbFile.find('histbufrtm') != -1):
                msgDecode = '%s/DlDspKeCpu%sTdd.out'%(HbDecodeOutfilePath,rtmControlNodeId[3])
                csvFile = '%s/RtmLog.csv'%HbDecodeOutfilePath
            elif(hbFile.find('histbufslow_core1') != -1 or hbFile.find('histbuffast_core1') != -1):
                msgDecode = '%s/DlDspKeCpu1Tdd.out'%HbDecodeOutfilePath
            elif(hbFile.find('histbufslow_core2') != -1 or hbFile.find('histbuffast_core2') != -1):
                msgDecode = '%s/DlDspKeCpu2Tdd.out'%HbDecodeOutfilePath
            elif(hbFile.find('histbufslow_core3') != -1 or hbFile.find('histbuffast_core3') != -1):
                msgDecode = '%s/DlDspKeCpu3Tdd.out'%HbDecodeOutfilePath
            elif(hbFile.find('histbufslow_core4') != -1 or hbFile.find('histbuffast_core4') != -1):
                msgDecode = '%s/DlDspKeCpu4Tdd.out'%HbDecodeOutfilePath
        elif(boardType == 'fsm4_bas'):        #for FSM4_BAS
            if(hbFile.find('histbufrtm') != -1):
                msgDecode = '%s/L1DspKeCpu%sTdd.out'%(HbDecodeOutfilePath,rtmControlNodeId[3])
                csvFile = '%s/RtmLog.csv'%HbDecodeOutfilePath
            elif(hbFile.find('histbufslow_core1') != -1 or hbFile.find('histbuffast_core1') != -1):
                msgDecode = '%s/L1DspKeCpu1Tdd.out'%HbDecodeOutfilePath
            elif(hbFile.find('histbufslow_core2') != -1 or hbFile.find('histbuffast_core2') != -1):
                msgDecode = '%s/L1DspKeCpu2Tdd.out'%HbDecodeOutfilePath
        elif (boardType.find('nyquist') != -1):
            if(hbFile.find('histbufrtm') != -1):
                msgDecode = '%s/Dl8DspNyMtCpu%s.out'%(HbDecodeOutfilePath,rtmControlNodeId[3])
                csvFile = '%s/RtmLog.csv'%HbDecodeOutfilePath
            elif(hbFile.find('histbufslow_core1') != -1 or hbFile.find('histbuffast_core1') != -1):
                msgDecode = '%s/Dl8DspNyCpu1.out'%HbDecodeOutfilePath
            elif(hbFile.find('histbufslow_core4') != -1 or hbFile.find('histbuffast_core4') != -1):
                msgDecode = '%s/Dl8DspNyCpu4.out'%HbDecodeOutfilePath
        if(os.path.exists(r'%s'%(msgDecode)) == False):
            logger.error('no such file msgDecode: %s, please check'%(msgDecode))
            return -1
        if(os.path.exists(r'%s'%(csvFile)) == False):
            logger.error('no such csv file: %s, please check'%(csvFile))
            return -1
        hbTxtFile = '%s/%s.txt'%(destDir, hbFileNew)
        cmd = r'%s -s -b %s/%s.bin -csv %s -o %s > %s'\
              %(HbViewerPath, destDir, hbFileNew, csvFile, msgDecode, hbTxtFile)
        if(os.system(cmd)):
            logger.error('%s failed'%cmd)
            ret = -1
            continue
        # do check log if need
        
        try:
            log = open(hbTxtFile,'r')
        except Exception,e:
            logger.error(e)
            ret = -1
            continue
        
        for line in log:
            if(hbFile.find('histbufrtm') != -1):
                for keyRtm in mapAllowedRtmLogIdMin.keys():
                    findlog = r'PHY TX %s'%(keyRtm)
                    if (line.find(findlog) != -1):
                        if (occurRtmLogCount.has_key(keyRtm)):
                            occurRtmLogCount[keyRtm] = occurRtmLogCount[keyRtm] + 1
                        else:
                            occurRtmLogCount[keyRtm] = 1
            else:
                for keyPhytx in mapAllowedPhtxLogIdMin.keys():
                    findlog = r'PHY TX %s'%(keyPhytx)
                    if (line.find(findlog) != -1):
                        if (occurPhytxLogCount.has_key(keyPhytx)):
                            occurPhytxLogCount[keyPhytx] = occurPhytxLogCount[keyPhytx] + 1
                        else:
                            occurPhytxLogCount[keyPhytx] = 1
            
        log.close()	    				
    for keyPhytx in mapAllowedPhtxLogIdMin.keys():
        if (occurPhytxLogCount.has_key(keyPhytx)):
            if (int(occurPhytxLogCount[keyPhytx]) < int(mapAllowedPhtxLogIdMin[keyPhytx])):
                logger.error('PHY TX %s log occur times is %s,less then %s'%(keyPhytx, occurPhytxLogCount[keyPhytx], mapAllowedPhtxLogIdMin[keyPhytx]))
                ret = -1
            if (mapAllowedPhtxLogIdMax.has_key(keyPhytx)):
                if (occurPhytxLogCount[keyPhytx] > mapAllowedPhtxLogIdMax[keyPhytx]):
                    logger.error('PHY TX %s log occur times is %s,more then %s'%(keyPhytx, occurPhytxLogCount[keyPhytx], mapAllowedPhtxLogIdMax[keyPhytx]))
                    ret = -1
        else:
            if (int(mapAllowedPhtxLogIdMin[keyPhytx]) > 0):
                logger.error('PHY TX %s log occur times is 0,less then %s'%(keyPhytx, mapAllowedPhtxLogIdMax[keyPhytx]))
                ret = -1
    for keyRtm in mapAllowedRtmLogIdMin.keys():
        if (occurRtmLogCount.has_key(keyRtm)):
            if (int(occurRtmLogCount[keyRtm]) < int(mapAllowedRtmLogIdMin[keyRtm])):
                logger.error('RTM %s log occur times is %s,less then %s'%(keyRtm, occurRtmLogCount[keyRtm], mapAllowedRtmLogIdMin[keyRtm]))
                ret = -1
            if (mapAllowedRtmLogIdMax.has_key(keyRtm)):
                if (int(occurRtmLogCount[keyRtm]) > int(mapAllowedRtmLogIdMax[keyRtm])):
                    logger.error('RTM %s log occur times is %s,more then %s'%(keyRtm, occurRtmLogCount[keyRtm], mapAllowedRtmLogIdMax[keyRtm]))
                    ret = -1
        else:
            if (int(mapAllowedRtmLogIdMin[keyRtm]) > 0):
                logger.error('RTM %s log occur times is 0,less then %s'%(keyRtm, mapAllowedRtmLogIdMin[keyRtm]))
                ret = -1
    return ret

def CompareUdpLog(CellId, mapAllowedPhtxLogIdMin, mapAllowedPhtxLogIdMax, mapAllowedRtmLogIdMin, mapAllowedRtmLogIdMax):
    ret = 1
    occurPhytxLogCount = {}
    occurRtmLogCount = {}
    
    # do check log if need
    try:
        log = open(udpLog,'r')
    except Exception,e:
        logger.error(e)
        ret = 0
        logger.error('%s can not find'%(udpLog))
        return ret

    for line in log:
        for keyRtm in mapAllowedRtmLogIdMin.keys():
            findlog = r'PHY TX %s:'%(keyRtm)
            if (line.find(findlog) != -1):
                if (Deployment != 5 or (Deployment == 5 and line.find(r'0x%x'%(CellId)) != -1)):
                    if (occurRtmLogCount.has_key(keyRtm)):
                        occurRtmLogCount[keyRtm] = occurRtmLogCount[keyRtm] + 1
                    else:
                        occurRtmLogCount[keyRtm] = 1

        for keyPhytx in mapAllowedPhtxLogIdMin.keys():
            findlog = r'PHY TX %s:'%(keyPhytx)
            if (line.find(findlog) != -1):
                if (Deployment != 5 or (Deployment == 5 and line.find(r'0x%x'%(CellId)) != -1)):
                    if (occurPhytxLogCount.has_key(keyPhytx)):
                        occurPhytxLogCount[keyPhytx] = occurPhytxLogCount[keyPhytx] + 1
                    else:
                        occurPhytxLogCount[keyPhytx] = 1
            
    log.close()	    				
    for keyPhytx in mapAllowedPhtxLogIdMin.keys():
        if (occurPhytxLogCount.has_key(keyPhytx)):
            if (int(occurPhytxLogCount[keyPhytx]) < int(mapAllowedPhtxLogIdMin[keyPhytx])):
                logger.error('PHY TX %s log occur times is %s,less then %s'%(keyPhytx, occurPhytxLogCount[keyPhytx], mapAllowedPhtxLogIdMin[keyPhytx]))
                ret = 0
            if (mapAllowedPhtxLogIdMax.has_key(keyPhytx)):
                if (int(occurPhytxLogCount[keyPhytx]) > int(mapAllowedPhtxLogIdMax[keyPhytx])):
                    logger.error('PHY TX %s log occur times is %s,more then %s'%(keyPhytx, occurPhytxLogCount[keyPhytx], mapAllowedPhtxLogIdMax[keyPhytx]))
                    ret = 0
        else:
            if (int(mapAllowedPhtxLogIdMin[keyPhytx]) > 0):
                logger.error('PHY TX %s log occur times is 0,less then %s'%(keyPhytx, mapAllowedPhtxLogIdMax[keyPhytx]))
                ret = 0
    for keyRtm in mapAllowedRtmLogIdMin.keys():
        if (occurRtmLogCount.has_key(keyRtm)):
            if (int(occurRtmLogCount[keyRtm]) < int(mapAllowedRtmLogIdMin[keyRtm])):
                logger.error('RTM %s log occur times is %s,less then %s'%(keyRtm, occurRtmLogCount[keyRtm], mapAllowedRtmLogIdMin[keyRtm]))
                ret = 0
            if (mapAllowedRtmLogIdMax.has_key(keyRtm)):
                if (int(occurRtmLogCount[keyRtm]) > int(mapAllowedRtmLogIdMax[keyRtm])):
                    logger.error('RTM %s log occur times is %s,more then %s'%(keyRtm, occurRtmLogCount[keyRtm], mapAllowedRtmLogIdMax[keyRtm]))
                    ret = 0
        else:
            if (int(mapAllowedRtmLogIdMin[keyRtm]) > 0):
                logger.error('RTM %s log occur times is 0,less then %s'%(keyRtm, mapAllowedRtmLogIdMin[keyRtm]))
                ret = 0
    return ret
                    
def hasMultiCase(caseInfo):
    if (len(caseInfo) >= 29):
        return True
    else:
        return False      
            
            
def SearchWorkingHandleIndex(targetSicad,retVal):
    logger.debug('targetSicad = %s'%targetSicad)
    handleIndex = 0
    targetSicadIndex = 0
    hit = False
 
    with lockHandle:
        for workingHandle in prologWorkingHandle:
            targetSicadArr = workingHandle[TARGET_SICAD_INDEX]
            if targetSicad in targetSicadArr:
                targetSicadIndex = targetSicadArr.index(targetSicad)
                targetStatArr = workingHandle[TARGET_STAT_INDEX];
                if targetStatArr:
                    targetStatArr[targetSicadIndex] = retVal
                    if (retVal != 0):
                        logger.error('response %s of testcase on %s dspGourp %d index %d'%(retVal, targetSicad, handleIndex,targetSicadIndex))
                hit = True
                break
            handleIndex += 1
                
    if(hit == False):
        logger.error('handle index out of range')
        return (None,None)
    else:
        return (handleIndex,targetSicadIndex)
            

def multiCaseListLen(testCaseInfo):
    return len(testCaseInfo[MULTI_CASE_LIST_INDEX])
            
def CheckWorkingHandleStat(workHandleIndex,targetSicadNum):
    result = False
    retTargetStat = 0
    correctResult = 0
    waitStatus = 'wait'

    if (workHandleIndex == None or targetSicadNum == None):
        return (result,None,None) 
    
    with lockHandle:
        if(len(prologWorkingHandle)):
            workingHandle = prologWorkingHandle[workHandleIndex]
            testCaseInfo = workingHandle[CASE_INFO_INDEX]
            if hasMultiCase(testCaseInfo):
                multiRtmFlag = True
            else:
                multiRtmFlag = False
            targetStatArr = workingHandle[TARGET_STAT_INDEX] 
            
            if targetStatArr:
                if multiRtmFlag:   
                    if waitStatus not in targetStatArr:
                        result = True
                        if targetStatArr.count(correctResult) != multiCaseListLen(testCaseInfo):
                            retTargetStat = -1
                        else:
                            retTargetStat = 0
                    else:
                        result = False
                        
                else:
                    result = True
                    retTargetStat = targetStatArr[targetSicadNum]
    
    if result:
        return (result,retTargetStat,workingHandle[TARGET_SICAD_INDEX])
    else:
        return (result,None,None)


            
def ReceiveManage():
    targetSicadGroup = []
    resultGroup = []
    targetFinish = False

    while(True):    
        targetRecvOnce ,resultOnce = ReceiveResp()
            
        if targetRecvOnce:
            for i in range(len(targetRecvOnce)):
                workHandleIndex,targetSicadNum = SearchWorkingHandleIndex(targetRecvOnce[i],resultOnce[i])
                result,targetStat,targetSicadArr = CheckWorkingHandleStat(workHandleIndex, targetSicadNum)

                if result :
                    targetSicadGroup.append(targetSicadArr)
                    resultGroup.append(targetStat)
                    targetFinish = True
            if targetFinish:
                return targetSicadGroup,resultGroup
        else:
            return [],[] 
            
            
#wait to recieve messages comes from RTM
#get dsp number and port number according to targetSicad
#get antenna files from specific dsp and port
def HandlePeroration(perorationParameters):
    global prologHandleCount,checkMD5,caseNeedToCheckLog
    perorationParametersGroup = []
    skipCompare = result = 0
    
    if(multiRTM == 1):
        targetSicadGroup,resultGroup = ReceiveManage()
    else:
        targetSicadGroup,resultGroup = ReceiveResp()
    if targetSicadGroup:
        for i in range(len(targetSicadGroup)):
            nu = GetWorkingHandleIndex(targetSicadGroup[i])
            if(nu != -1):
                perorationParameters = prologWorkingHandle[nu][6]
                if perorationParameters:
                    logger.debug('recieve: targetSicad =  %s,case: %s,result = %s'%(targetSicadGroup[i],perorationParameters[0],resultGroup[i]))
                    if(perorationParameters[22] != -1 and perorationParameters[22] != ''):
                        skipCompare = 1
                    if(skipCompare == 0 and resultGroup[i] != 0):
                        logger.error('response %s of testcase %s on %s'%(resultGroup[i],perorationParameters[0],targetSicadGroup[i]))
                        if checkMD5 and perorationParameters[17]:
                            logger.error('MD5 failed, get antenna files and use it to compare')
                            result = GetAntennaFile(prologWorkingHandle[nu][3],prologWorkingHandle[nu][0],perorationParameters[2],perorationParameters[12])
                        else:
                            result = -1
                    else:
                        if(skipCompare == 0 and perorationParameters[21] == 0 and checkMD5):
                            perorationParameters[16] = 1
                        elif skipCompare:
                            caseNeedToCheckLog.append([perorationParameters[0],perorationParameters[22]])
                        elif(perorationParameters[17] == 0):
                            perorationParameters[16] = 1
                        else:
                            result = GetAntennaFile(prologWorkingHandle[nu][3],prologWorkingHandle[nu][0],perorationParameters[2],perorationParameters[12])
                    if(result == -1):
                        logger.error('%s failed'%perorationParameters[0])
                        perorationParameters = 0
                else:
                    logger.error('no testcase on %s is running'%targetSicadGroup[i])
                perorationParametersGroup.append(perorationParameters)
                FreeHandle(targetSicadGroup[i])
            else:
                perorationParametersGroup.append(0)
                FreeAllHandle()
                logger.error('get Working Handle Index failed!')
                time.sleep(3)
    else:
        perorationParametersGroup.append(0)
        FreeAllHandle()
        logger.error('get targetSicadGroup failed!')
	time.sleep(3)
    return (perorationParametersGroup, len(targetSicadGroup))
        
#get messages from queuePeroration and operate correspondingly
def Peroration():
    global prologHandleCount,respCount
    recvRespSum = 0
    while True:
        perorationMessageBox = []
        if(prologHandleCount > 1 and recvRespSum >= len(TestCases)):
            time.sleep(3)
            logger.debug('reach the last case')
            perorationMessage = queuePeroration.get()
            while(not queuePeroration.empty() and perorationMessage[0] != 'EXIT_REQ'):
                perorationMessage = queuePeroration.get()
            perorationMessage = (EXIT_REQ,)
        elif(prologHandleCount > 1):
            perorationMessageBox = []
            perorationMessage = queuePeroration.get()
            perorationMessageBox.append(perorationMessage)
            while not queuePeroration.empty():
                perorationMessageTmp = queuePeroration.get()
                perorationMessageBox.append(perorationMessageTmp)
            for i in range(len(perorationMessageBox)):
                if(perorationMessageBox[i][0] == 'REBOOT_REQ'):
                    perorationMessage = (REBOOT_REQ,)
                    perorationMessageBox.pop(i)
                    break
            if(perorationMessage[0] != REBOOT_REQ):
                perorationMessageBox.pop(0)
            with lockQueuePeroration:
                for i in range(len(perorationMessageBox)):
                    queuePeroration.put(perorationMessageBox[i])
        elif(prologHandleCount == 1):
            perorationMessage = queuePeroration.get()
        #logger.info('%s'%(perorationMessage,))
        if(perorationMessage[0] == TEST_REQ):                      #put TEST_RESP into queueMain after recieve message and get antenna files from RTM
            if(perorationMessage[1] == 0):
                with lockQueueMain:
                    queueMain.put((TEST_RESP,perorationMessage[1]))
                continue
            perorationParametersGroup, receiveCnt = HandlePeroration(perorationMessage[1])
            recvRespSum += receiveCnt
            for i in range(len(perorationParametersGroup)):
                with lockQueueMain:
                    queueMain.put((TEST_RESP,perorationParametersGroup[i]))
        elif(perorationMessage[0] == REBOOT_REQ):                  #stop actions until get message REBOOT_RESP
            perorationMessageBox = []
            perorationMessage = queuePeroration.get()
            while(perorationMessage[0] != REBOOT_RESP):
                perorationMessageBox.append(perorationMessage)
                perorationMessage = queuePeroration.get()
            with lockQueuePeroration:
                for perorationMessage in perorationMessageBox:
                    queuePeroration.put(perorationMessage)
            continue
        elif(perorationMessage[0] == EXIT_REQ):                    #quit the loop and end the current thread
            logger.debug('%s'%(perorationMessage,))
            break
        else:
            logger.error('unexpected message %s'%(perorationMessage,))
            AbnormalExit()

#compare frequece domain data and read the log to estimate if comparision is successful
def IqCompareFreq(bandWidth,downSample,cpSequence,compareParameters,antennaFileName,antennaFilePath,antennaFreqRef,antennaRefPath,swap,calCoefIndex):
    global limitRelEvmSq,limitAbsEvmSq,freqCompareScript,freqCompareFormat
    logger.debug('%s: frequence comparing %s'%(compareParameters[0],antennaFileName))
    if(os.path.exists(r'%s/%s'%(antennaFilePath,antennaFileName)) == False):
        logger.error('no such file: %s/%s of %s, please check'%(antennaFilePath,antennaFileName,compareParameters[0]))
        with lockResult:
            queueResult.put(0,block=False)
        return 0
    if(os.path.exists(r'%s/%s'%(antennaRefPath,antennaFreqRef)) == False):
        logger.error('no such file: %s/%s of %s, please check'%(antennaRefPath,antennaFreqRef,compareParameters[0]))
        with lockResult:
            queueResult.put(0,block=False)
        return 0
    runInCI = os.getenv('JOB_NAME')
    if (runInCI != None):
        shellPrefix = 'python '
    else:
        shellPrefix = ''
    cmd = '%s%s %s/%s %s/%s -b %d -r %4.4f -e %d -f %16f'%(shellPrefix,freqCompareScript,antennaFilePath,antennaFileName,antennaRefPath,\
            antennaFreqRef,bandWidth,limitRelEvmSq,limitAbsEvmSq,compareParameters[9])
    if(compareParameters[15] != 0):
        cmd += ' -n %d -F %s'%(calCoefIndex,compareParameters[15])
    if(cpSequence != ''):
        cmd += ' -p %s'%cpSequence
    if downSample:
        cmd += ' -d'
    if(swap != ''):
        cmd += ' -s'
    if(freqCompareFormat != ''):
        cmd += ' -o'
    logger.debug(cmd)
    os.system(cmd)
    logFile = '%s/iqcompareFreqResult_%s.log'%(antennaFilePath,antennaFileName.split('.')[0])
    try:
       log = open(logFile,'r')
    except Exception,e:
       logger.error('can not open %s, please check'%logFile)
       with lockResult:
           queueResult.put(0,block=False)
       return 0
    for line in log:
       noLineBreak = line.strip('\n')
       if(len(re.findall('No errors found',noLineBreak)) != 0):
           with lockResult:
               queueResult.put(1,block=False)
           log.close()
           return 1
    log.close()
    with lockResult:
        queueResult.put(0,block=False)
    logger.error('IqCompareFreq: %s of %s fail'%(antennaFileName,compareParameters[0]))
    return 0

#compare time domain data
#read the log to estimate if comparision is successful(if bandWidth not equal to 15)
def IqCompareTime(bandWidth,cpSequence,compareParameters,antennaFileName,antennaFilePath,antennaTimeRef,antennaRefPath,swap):
    global limitRelEvmSq,limitAbsEvmSq,timeCompareScript,timeCompareFormat
    logger.debug('%s: time comparing %s'%(compareParameters[0],antennaFileName))
    noFft = compareParameters[7]
    flag = 0
    if(os.path.exists(r'%s/%s'%(antennaFilePath,antennaFileName)) == False):
        logger.error('no such file: %s/%s of %s, please check'%(antennaFilePath,antennaFileName,compareParameters[0]))
        with lockResult:
            queueResult.put(0,block=False)
        return 0
    if(os.path.exists(r'%s/%s'%(antennaRefPath,antennaTimeRef)) == False):
        logger.error('no such file: %s/%s of %s, please check'%(antennaRefPath,antennaTimeRef,compareParameters[0]))
        with lockResult:
            queueResult.put(0,block=False)
        return 0
    logFile = '%s/iqcompareTimeResult_%s.log'%(antennaFilePath,antennaFileName.split('.')[0])
    cmd = '%s %s/%s %s/%s -B %d -f %d -X'%(timeCompareScript,antennaFilePath,antennaFileName,antennaRefPath,\
                                             antennaTimeRef,bandWidth,compareParameters[8])
    if(cpSequence == 'extCp'):
        cmd += ' -p'
    if(swap != ''):
        cmd += ' -s'
    if(timeCompareFormat != ''):
        cmd += ' -Q'
    logger.debug(cmd)
    try:
        os.system(cmd)
    except Exception,e:
        logger.error(e)
        logger.error('IqCompareTime: %s VS %s of %s failed'%(antennaFileName, antennaTimeRef, compareParameters[0]))
        with lockResult:
            queueResult.put(0,block=False)
        return 0
    if noFft:
        try:
            log = open(logFile,'r')
        except Exception,e:
            logger.error('can not open %s, please check'%logFile)
            with lockResult:
                queueResult.put(0,block=False)
            return 0
        for line in log:
            noLineBreak = line.strip('\n')
            numOfMismatchSymbol = re.findall('.*deviation > max_allowed_deviation.*\s+(\d+).*',noLineBreak)
            if(len(numOfMismatchSymbol) != 0):
                for i in range(len(numOfMismatchSymbol)):
                    if(numOfMismatchSymbol[i] != 0 and numOfMismatchSymbol[i] != '0'):
                        log.close()
                        logger.error('IqCompareTime: %s VS %s of %s failed'%(antennaFileName, antennaTimeRef, compareParameters[0]))
                        with lockResult:
                            queueResult.put(0,block=False)
                        return 0
        log.close()
    with lockResult:
	queueResult.put(1,block=False)
	return 1

#read udplog and check if there is any problem which need to reboot board occurred when compare failed
#reboot board if these kinds of problem occurred(if powerBreakPort) or quit current SCT test after report
def IfTerminateNormally(caseName):
    global udpLog,udpAction
    if(udpAction != 'stAcl'): return 0
    try:
        log = open(udpLog,'r')
    except Exception,e:
        logger.error('can not open file %s, please check'%udpLog)
        return 0
    try:
        for line in log:
            noLineBreak = line.strip('\n')
            if(len(re.findall(\
                'FATAL DSPHWAPI ERROR|No Ack message from RTM received|can not allocate QmPacket from free queueFATAL \
                DSPHWAPI ERROR|No Ack message from RTM received|can not allocate QmPacket from free queue',noLineBreak)) != 0):
                if powerBreakPort:
                    logger.warn('%sReboot board by %s'%(line,caseName))
                    with lockQueueMain:
                        queueMain.put((REBOOT_REQ,))
                    with lockQueueProlog:
                        queueProlog.put((REBOOT_REQ,))
                    with lockQueuePeroration:
                        queuePeroration.put((REBOOT_REQ,))
                    with lockQueueCompare:
                        queueCompare.put((REBOOT_REQ,))
                    with lockQueueReboot:
                        queueReboot.put((REBOOT_REQ,))
                else:
                    logger.error('find critical error in udp log,SCT test will be terminated immediately')
                    AbnormalExit()
                log.close()
                return 0
        log.close()
    except Exception,e:
        logger.error(e)
    return 0

    
        
def CompareMultiCaseAntennaFile(compareParameters,threadGroup):
    global Deployment
    calCoefIndex = ''
    fail = 0
    
    multiCaseList = compareParameters[MULTI_CASE_LIST_INDEX] 
    for subCase in multiCaseList:
        antennaCnt = subCase[NUM_OF_PORT_LIST_INDEX][0] 
        if(Deployment == 5 and antennaCnt == 2 and len(subCase[ANTENNA_FILE_NAME_INDEX]) == 8):
            antennaCnt *= 4
        antennaIndex = 0
        
        while(antennaIndex < antennaCnt):
            try:
                antennaFileName = '%s.iq'%subCase[ANTENNA_FILE_NAME_INDEX][antennaIndex]
                antennaFilePath = compareParameters[CASE_LOG_DIR_INDEX]
                antennaTimeRef = '%s.ref'%subCase[REFERENCE_FILE_NAME_INDEX][antennaIndex]
                antennaFreqRef = '%s_freq.ref'%subCase[REFERENCE_FILE_NAME_INDEX][antennaIndex]
                antennaRefPath = '%s/REFERENCE'%subCase[CASE_PATH_INDEX]
            except Exception,e:
                logger.error('%s'%e)
                antennaIndex += 1
                fail = 1
                continue
                
            if(subCase[CAL_FILE_INDEX] != 0):
                try:
                    calCoefIndex = subCase[ANTENNA_COEFS_INDEX][antennaIndex]
                except Exception,e:
                    logger.error('calibration case i=%d, subCase[ANTENNA_COEFS_INDEX]=%s'%(i, subCase[ANTENNA_COEFS_INDEX][antennaIndex]))
                    antennaIndex += 1
                    fail = 1
                    continue
                    
            if(subCase[NO_THREAD_INDEX] == 0 and subCase[BAND_WIDTH_LIST_INDEX][0] != 15):
                if(subCase[NO_FFT_INDEX] != 0):
                    tmp = threading.Thread(target=IqCompareTime,args=(subCase[BAND_WIDTH_LIST_INDEX][0],subCase[CP_LIST_BY_SUBF_INDEX][0],subCase,\
                        antennaFileName,antennaFilePath,antennaTimeRef,antennaRefPath,''))
                    tmp.start()
                    threadGroup.append(tmp)
                else:
                    tmp = threading.Thread(target=IqCompareFreq,args=(subCase[BAND_WIDTH_LIST_INDEX][0],subCase[DOWN_SAMPLE_LIST_INDEX][0],\
                        subCase[CP_LIST_BY_SUBF_INDEX][0],subCase,antennaFileName,antennaFilePath,antennaFreqRef,antennaRefPath,'',calCoefIndex))
                    tmp.start()
                    threadGroup.append(tmp)
            else:
                if(IqCompareTime(subCase[BAND_WIDTH_LIST_INDEX][0],subCase[CP_LIST_BY_SUBF_INDEX][0],subCase,antennaFileName,antennaFilePath,antennaTimeRef,antennaRefPath,'') == 0):
                    fail = 1
                if not subCase[NO_FFT_INDEX]:
                    if(IqCompareFreq(subCase[BAND_WIDTH_LIST_INDEX][0],subCase[DOWN_SAMPLE_LIST_INDEX][0],subCase[CP_LIST_BY_SUBF_INDEX][0],\
                        subCase,antennaFileName,antennaFilePath,antennaFreqRef,antennaRefPath,'',calCoefIndex) == 0):
                        fail = 1
            antennaIndex += 1
            
    return fail
    
#create threads to compare antenna files(if not nothreads and bandWidth not equal to 15)
#check the result of comparision
def CompareAntennaFile(compareParameters):
    global Deployment,multiRTM
    if not compareParameters: return 0
    if(os.path.exists(compareParameters[1]) == False):
        logger.error('no such testcase %s,please check'%compareParameters[0])
        return 0
    if(compareParameters[17] == 0 or compareParameters[16] == 1):
        return 1
    calCoefIndex = ''
    threadGroup = []
    fail = antennaIndex = i = 0
    with lockResult:
        queueResult.queue.clear()
        
    if (multiRTM == 1 and hasMultiCase(compareParameters)):
        fail = CompareMultiCaseAntennaFile(compareParameters,threadGroup)       
    else:
        for cellIndex in range(len(compareParameters[4])):
            antennaIndex += compareParameters[18][cellIndex]
            if(Deployment == 2):
                antennaIndex = antennaIndex * 4
            elif(Deployment == 6):
                antennaIndex = antennaIndex * 6
            elif(Deployment == 7):
                antennaIndex = antennaIndex * 8
            while(i < antennaIndex):
                try:
                    antennaFileName = '%s.iq'%compareParameters[12][i]
                    antennaFilePath = compareParameters[2]
                    antennaTimeRef = '%s.ref'%compareParameters[13][i]
                    antennaFreqRef = '%s_freq.ref'%compareParameters[13][i]
                    antennaRefPath = '%s/REFERENCE'%compareParameters[1]
                except Exception,e:
                    logger.error('number of antenna/ref files should be %d, did you use wrong file UM_MAP_XXX or wrong value with argument -D ?'%antennaIndex)
                    i += 1
                    fail = 1
                    continue
                if(compareParameters[15] != 0):
                    try:
                        calCoefIndex = compareParameters[14][i]
                    except Exception,e:
                        logger.error('compareParameters[14] is %s, i=%d?' % (compareParameters[14], i))
                        i += 1
                        fail = 1
                        continue
                if(compareParameters[10] == 0 and compareParameters[4][cellIndex] != 15):
                    if(compareParameters[7] != 0):
                        tmp = threading.Thread(target=IqCompareTime,args=(compareParameters[4][cellIndex],compareParameters[5][cellIndex],\
                            compareParameters,antennaFileName,antennaFilePath,antennaTimeRef,antennaRefPath,''))
                        tmp.start()
                        threadGroup.append(tmp)
                    else:
                        tmp = threading.Thread(target=IqCompareFreq,args=(compareParameters[4][cellIndex],compareParameters[19][cellIndex],\
                            compareParameters[5][cellIndex],compareParameters,antennaFileName,antennaFilePath,antennaFreqRef,antennaRefPath,'',calCoefIndex))
                        tmp.start()
                        threadGroup.append(tmp)
                else:
                    if(IqCompareTime(compareParameters[4][cellIndex],compareParameters[5][cellIndex],compareParameters,antennaFileName,antennaFilePath,antennaTimeRef,antennaRefPath,'') == 0):
                        fail = 1
                    if not compareParameters[7]:
                        if(IqCompareFreq(compareParameters[4][cellIndex],compareParameters[19][cellIndex],compareParameters[5][cellIndex],\
                            compareParameters,antennaFileName,antennaFilePath,antennaFreqRef,antennaRefPath,'',calCoefIndex) == 0):
                            fail = 1
                i += 1
    for thread in threadGroup:
        thread.join(timeout=200)
	if thread.is_alive(): fail = 1
    while not queueResult.empty():
        if(queueResult.get() != 1):
            fail = 1
            break
    if(fail == 1):
        compareParameters[16] = 0
        IfTerminateNormally(compareParameters[0])
    else:
        compareParameters[16] = 1
    return compareParameters[16]

def CheckUdpLog(compareParameters):
    global Deployment,multiRTM,gCheckUdpLog
    if not compareParameters: return 0
    if(os.path.exists(compareParameters[1]) == False):
        logger.error('no such testcase %s,please check'%compareParameters[0])
        return 0
   
    fail = 0 
    if (multiRTM == 1 and hasMultiCase(compareParameters)):
        multiCaseList = compareParameters[MULTI_CASE_LIST_INDEX] 
        for subCase in multiCaseList:
            #check udp log
            if(gCheckUdpLog):
                result = CompareUdpLog(subCase[CELL_ID_INDEX], subCase[25], subCase[26], subCase[27] ,subCase[28])
                if(result == 0):
                    logger.error('CASE:%s subCase:%s CellId:%d check udp log failed'%(compareParameters[0],subCase[0],subCase[CELL_ID_INDEX]))
                    fail = 1
                    break
    else:
        #check udp log
        if(gCheckUdpLog):
            result = CompareUdpLog(0, compareParameters[24], compareParameters[25], compareParameters[26] ,compareParameters[27])
            if(result == 0):
                logger.error('%s check udp log failed'%compareParameters[0])
                fail = 1
                    
    if(fail == 1):
        compareParameters[16] = 0
    else:
        compareParameters[16] = 1
    return compareParameters[16] 
  
def GenerateMultiCaseMD5File(compareParameters):
    logger.info('generate multiRTM md5 file')
    antFileDir = compareParameters[CASE_LOG_DIR_INDEX]
    
    multiCaseList = compareParameters[MULTI_CASE_LIST_INDEX] 
    for subCase in multiCaseList:
        subCaseRefDir = '%s/REFERENCE'%subCase[CASE_PATH_INDEX]
        if(os.path.exists(subCaseRefDir) == False):
            return False
            
        antennaFileNameList = subCase[ANTENNA_FILE_NAME_INDEX]
        for antennaFileName in antennaFileNameList:
            antennaFileName = '%s.iq'%antennaFileName
            md5File = '%s/%s.md5'%(subCaseRefDir,antennaFileName)
            cmd = 'md5.exe %s/%s'%(antFileDir,antennaFileName)
            
            try:
                os.system(cmd)
            except Exception,e:
                logger.error('generate md5 file %s failed'%md5File)
                return False
                
            try:
                md5Txt = open('md5.txt','r')
            except Exception,e:
                logger.error('can not open abc.txt, generate md5 file %s failed'%md5File)
                return
                
            md5_file = open(md5File,'w')
            print >> md5_file,md5Txt.readline().strip('\n') + ' *%s'%antennaFileName
            md5_file.close()
            md5Txt.close()
            
    return True
    
def GenerateMD5File(compareParameters):
    if not compareParameters:
        return
    if(compareParameters[16] != 1):
        return
    logger.info('generate md5 file')
        
    antFileDir = compareParameters[2]
    refDir = '%s/REFERENCE'%compareParameters[1]
    if(os.path.exists(refDir) == False):
        return
    for i in range(len(compareParameters[12])):
        antennaFileName = '%s.iq'%compareParameters[12][i]
        md5File = '%s/%s.md5'%(refDir,antennaFileName)
        cmd = 'md5.exe %s/%s'%(antFileDir,antennaFileName)
        try:
            os.system(cmd)
        except Exception,e:
            logger.error('generate md5 file %s failed'%md5File)
            return
        try:
            md5Txt = open('md5.txt','r')
        except Exception,e:
            logger.error('can not open abc.txt, generate md5 file %s failed'%md5File)
            return
        md5_file = open(md5File,'w')
        print >> md5_file,md5Txt.readline().strip('\n') + ' *%s'%antennaFileName
        md5_file.close()
        md5Txt.close()

#get messages from queueCompare and operate correspondingly    
def Compare():
    while True:
        compareMessage = queueCompare.get()
        logger.debug('%s'%(compareMessage,))
        if(compareMessage[0] == COMPARE_REQ):                        #put COMPARE_RESP into queueMain after compare antenna files
            compareParameters = compareMessage[1]
            result = generateMD5 = skipCompare = 0
            if compareParameters:
                generateMD5 = compareParameters[21]
                if(compareParameters[22] != -1 and compareParameters[22] != ''):
                    skipCompare = 1
                if(compareParameters[17] == 0 and skipCompare == 0):
                    if (compareParameters[16] == 1):
                        result = 1
                    else:
                        result = 0
                elif(skipCompare == 1):
                    pass
                else:
                    result = CompareAntennaFile(compareMessage[1])
                    if not result:
                        logger.info('%s failed'%compareParameters[0])
                if(gCheckUdpLog):
                    result = CheckUdpLog(compareMessage[1])
            if result:
                for i in range(len(TestCases)):
                    if(TestCases[i][0] == compareParameters[0]):
                        TestCases[i][16] = 1
            if generateMD5:
                GenerateMD5File(compareParameters)
            with lockQueueMain:
                queueMain.put((COMPARE_RESP,result))
        elif(compareMessage[0] == EXIT_REQ):                        #quit the loop and end the current thread
            break
        elif(compareMessage[0] == REBOOT_REQ):                      #stop actions until get message REBOOT_RESP
            compareMessageBox = []
            compareMessage = queueCompare.get()
            while(compareMessage[0] != REBOOT_RESP):
                compareMessageBox.append(compareMessage)
                compareMessage = queueCompare.get()
            with lockQueueCompare:
                for compareMessage in compareMessageBox:
                    queueCompare.put(compareMessage)
            continue
        else:
            logger.error('unexpected message %s'%(compareMessage,))
            AbnormalExit()

#check if reboot successful or not
def CheckReboot():
    global rebootDir
    no = 0
    for i in range(3,9):
        string = 'sicftpRTM.exe -c 12%d3 -p glo_def.h\n'%i                
        while True:
            p = subprocess.Popen(string,shell=True,cwd='%s/../sicftp-client'%rebootDir,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            if(p.wait() == 0):
                logger.info('DSP %d reboot successful'%i)
                break
            no += 1
            if(no > 40):
                logger.info('Sicftp time out')
                return -1                                
    logger.info('Hard-reboot successful')
    return 1      

def ReadConfig():
    try:
        tempf = open('%s/../Auto SCT Test/rebootconfig.txt'%startRoot,'r')
    except Exception,e:
        logger.error('can not open %s/../Auto SCT Test/rebootconfig.txt, please check'%startRoot)
        return (-1,-1,-1)
    myIp = ''
    pbIp = ''
    pbPort = 0
    names,aliases,ips = socket.gethostbyname_ex(socket.gethostname())
    for ip in ips:
        if not re.match('^192',ip):
            myIp = ip
            logger.debug('get my ip: %s'%myIp)
    for line in tempf:
        line = line.strip('\n')
        ipConfig = line.split('/')
        if(cmp(myIp,ipConfig[0]) == 0):
            pbPort = int(ipConfig[1])
            pbIp = ipConfig[2]
            tempf.close()
            logger.debug('pbIp: %s , pbPort: %d'%(pbIp,pbPort))
            return (myIp,pbIp,pbPort)
    logger.error('please update your rebootconfig.txt file\n')
    tempf.close()
    return (-1,-1,-1)

#use rebootBoard.exe to reboot board according to file rebootconfig.txt 
def RebootBoard():
    global rebootApp
    logger.info('reboot board')
    pcIp,pbIp,pbPort = ReadConfig()
    if(pcIp == -1 or pbIp == -1 or pbPort == -1):
        return -1
    cmd = '%s -o power_off -p %s:%d:%s'%(rebootApp,pbIp,pbPort,pcIp)
    if(os.system(cmd) != 0):
        time.sleep(2)
        if(os.system(cmd) != 0):
            logger.error('BTS power off failed')
            return -1
    time.sleep(3)
    if(os.system('%s -o power_on -p %s:%d:%s'%(rebootApp,pbIp,pbPort,pcIp)) != 0):
        logger.error('BTS power on failed')
        return -1
    if(CheckReboot() != 1):
        return -1
    return 1

#restore session cases UM_MAP_XXX and CE_DIA_XXX
def RestoreSession():
    global McuSocket,boardId,dspNo,rtmControlCpuId,prologHandleCount,rtmCtlAllDspProcList
    rtmControlNodeIdGroup = []
    targetSicadArr = []
    targetStatArr = []
    port = 15002
    logger.info('restore session')
    McuSocket.close()
    try:
        McuSocket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        McuSocket.connect((McuAddr,McuPort))
    except Exception,e:
        logger.error('Can not connect to BTS in function RestoreSession')
        AbnormalExit()
    logger.debug('connect BTS successful in function RestoreSession')
    if(len(dspNo) == 1):
        rtmControlNodeIdGroup.append('%s%d%s'%(boardId,dspNo[1]-1,rtmControlCpuId))
    elif(len(dspNo) == 2):
        if multiRTM == 1:
            if (HandleCoreAddr([1,0],dspNo,rtmCtlAllDspProcList,rtmControlNodeIdGroup,targetSicadArr,targetStatArr) == None):
                logger.error('Wrong parameter for DSP NO,please check')
                AbnormalExit()
        else:
            rtmControlNodeIdGroup.append('%s%d%s'%(boardId,dspNo[1]-1,rtmControlCpuId))
    else:
        for nu in dspNo:
            if multiRTM == 1:
                if (HandleCoreAddr([1,0],[nu,nu-1],rtmCtlAllDspProcList,rtmControlNodeIdGroup,targetSicadArr,targetStatArr) == None):
                    logger.error('Wrong parameter for DSP NO,please check')
                    AbnormalExit()
            else:
                rtmControlNodeIdGroup.append('%s%d%s'%(boardId,nu-1,rtmControlCpuId))
                
    transferNodeIdList = list(set(rtmControlNodeIdGroup))
    for rtmControlNodeId in transferNodeIdList:
        TransmitCommonFiles(rtmControlNodeId,port)
        port += 1
    if(len(prologWorkingHandle) != 0):
        FreeAllHandle()
        with lockQueueMain:
            queueMain.put((TEST_RESP,0))
    if(prologHandleCount > 1):
        for i in range(prologHandleCount-1):
            sessionCases.insert(0,sessionCases[0])
            sessionCases.insert(-1,sessionCases[-1])
        logger.debug('session cases are: %s'%sessionCases)
    for i in range(len(sessionCases)):
        logger.info('Restore %s'%sessionCases[i][0])
        testcaseParameters = HandleProlog(sessionCases[i])
        if testcaseParameters:
            testcaseParametersGroup, receiveCnt = HandlePeroration(testcaseParameters)
            if testcaseParametersGroup:
                for i in range(len(testcaseParametersGroup)):
                    if(CompareAntennaFile(testcaseParametersGroup[i]) != 1):
                        logger.error('restore %s fail,SCT test will be terminated immediately'%sessionCases[i][0])
                        AbnormalExit()
                    if(gCheckUdpLog):
                        CheckUdpLog(testcaseParametersGroup[i])
            else: return 0
        else: return 0
    return 1

#get messages from queueReboot and operate correspondingly 
def IfReboot():
    no = 0
    while True:
        message = queueReboot.get()
        if(no > 2):
            logger.info('reboot over two times,SCT test will be terminated because reboot too many times')
            AbnormalExit()
        if(message[0] == REBOOT_REQ):                       #put REBOOT_RESP into queueMain,queueProlog,queuePeroration,queueCompare after restore successful
            if(RebootBoard() == -1):
                logger.info('try to reboot board one more time')
                if(RebootBoard() == -1):
                    logger.error('SCT test will be terminated because fail reboot twice, please check')
                    AbnormalExit()
            if not RestoreSession():
                logger.error('restore fail,SCT test will be terminated immediately')
                AbnormalExit()
            with lockQueueMain:
                queueMain.put((REBOOT_RESP,))
            with lockQueueProlog:
                queueProlog.put((REBOOT_RESP,))
            with lockQueuePeroration:
                queuePeroration.put((REBOOT_RESP,))
            with lockQueueCompare:
                queueCompare.put((REBOOT_RESP,))
            no += 1
        elif(message[0] == EXIT_REQ):                     #quit the loop and end the current thread
            break
        else:
            logger.error('unexpected message %s'%(message,))
            AbnormalExit()

#wait specific message from specific queue
def WaitFor(queue,messageID):
    while True:
        message = queue.get()
        if(message[0] == messageID):
            logger.debug('get message %s'%messageID)
            return

#put TEST_REQ into queueProlog and return current index of TestCases
def TestAck(i):
    global prologHandleCount,TestCases
    if(i >= len(TestCases)):
        return i
    with lockQueueProlog:
        queueProlog.put((TEST_REQ,TestCases[i]))
    i += 1
    logger.debug('TestAck: i = %d'%i)
    return i

#put EXIT_REQ into specific queue and wait specific thread ending
def ThreadExit(queue,lock,threadName):
    with lock:
        queue.put((EXIT_REQ,))
    threadName.join()

#retry failed cases
def Retry():
    global retryCount
    k = 0
    for i in range(len(TestCases)):
        if(len(re.findall('MAP|DIA',TestCases[i][0])) != 0 or TestCases[i][16] != 1):
            if(len(retryTestCases) != 0 and TestCases[i][0] == retryTestCases[-1][0]):
                continue
            if(len(re.findall('MAP|DIA',TestCases[i][0])) != 0):
                k += 1
            retryTestCases.append(TestCases[i])
        logger.info('case: %s , result: %d'%(TestCases[i][0],TestCases[i][16]))
    if(k == len(retryTestCases)): return
    while(retryTestCases[-1][0].find('MAP') != -1 or retryTestCases[-1][0].find('DIA') != -1):
        retryTestCases.pop(-1)
    logger.debug('retryTestCases: %s'%retryTestCases)
    time.sleep(5)
    FreeAllHandle()
    with condHandle:
        while(len(prologFreeHandle) > 1):
            prologFreeHandle.pop(0)
        condHandle.notify()
    time.sleep(5)
    for case in retryTestCases:
        t = retryCount
        while(t > 0):
            logger.info('Retry %s'%case[0])
            if len(case) == 29:
                case.pop(28)
            testcaseParameters = HandleProlog(case,True)
            if testcaseParameters:
                testcaseParametersGroup, receiveCnt = HandlePeroration(testcaseParameters)
                for i in range(len(testcaseParametersGroup)):
                    if(CompareAntennaFile(testcaseParametersGroup[i]) == 1):
                        if(len(testcaseParametersGroup[i]) > 21 and testcaseParametersGroup[i][21] == 1):
                            GenerateMD5File(testcaseParametersGroup[i])
                        for j in range(len(TestCases)):
                            if(TestCases[j][0] == case[0]):
                                TestCases[j][16] = 1
                                t = 0
                                break
                    else: t -= 1
                    if(gCheckUdpLog):
                        CheckUdpLog(testcaseParametersGroup[i])
            else: t -= 1


def StartLogServer():
    global udpServer,logServerAddr,logServerPort,udpLog,newLogServer,flagToEndUdp
    logger.debug('startlogserver')
    if(newLogServer != '0'):
        try:
            UdpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            UdpSocket.bind((logServerAddr,logServerPort))
            f = open(udpLog,'w')
        except Exception,e:
            logger.error(e)
            return -1
        log = ''
        #while(UdpSocket.recv(log,4096)):
        try:
            while flagToEndUdp:
                udpCanRead,udpCanWrite,udpAbnormal = select.select([UdpSocket],[],[],5)
                if udpCanRead:
                    log = UdpSocket.recv(4096)
                    log = re.sub('\0','',log)
                    f.write(log)
        except Exception,e:
            logger.error(e)
    else:
        cmd = "start cmd.exe /c %s %s %d ascii '-f %s'"%(udpServer,logServerAddr,logServerPort,udpLog)
        try:
            os.system(cmd)
        except Exception,e:
            logger.error('%s failed'%cmd)
            return -1
        logger.debug('%s successful'%cmd)

def EndLogServer():
    global newLogServer,sctRoot,flagToEndUdp
    if(newLogServer == '0'):
        cmd = 'start %s %s/tools'%(udpServerClose,sctRoot)
        try:
            os.system(cmd)
        except Exception,e:
            logger.error('can not end udp log server')
            return
        time.sleep(5)
    else:
        flagToEndUdp = 0
        logger.debug('end udp log server')
    return

#get messages from queueMain and operate correspondingly
def RunTestcases(t_prolog,t_peroration,t_compare,t_reboot):
    global TestCases,udpAction,retryCount
    if(udpAction == 'stAcl'):
        t_udp = threading.Thread(target=StartLogServer)
        t_udp.start()
        time.sleep(1)
    i = j = k = 0
    compareRespCount = len(TestCases)
    i = TestAck(i)
    while True:
        mainMessage = queueMain.get()
        logger.debug('%s'%(mainMessage,))
        if(mainMessage[0] == TEST_ACK):                         #put TEST_REQ into queueProlog
            i = TestAck(i)
        elif(mainMessage[0] == TEST_RESP):                      #put COMPARE_REQ into queueCompare
            with lockQueueCompare:
                queueCompare.put((COMPARE_REQ,mainMessage[1]))
            k += 1
            if(k >= compareRespCount):
                ThreadExit(queueProlog,lockQueueProlog,t_prolog)
                ThreadExit(queuePeroration,lockQueuePeroration,t_peroration)
                if(powerBreakPort):
                    ThreadExit(queueReboot,lockQueueReboot,t_reboot)
        elif(mainMessage[0] == COMPARE_RESP):                   #put EXIT_REQ into queueCompare if all cases have been compared
            #TestCases[j][16] = mainMessage[1]
            j += 1
            if(j >= compareRespCount):
                ThreadExit(queueCompare,lockQueueCompare,t_compare)
                break
        elif(mainMessage[0] == REBOOT_REQ):                     #stop actions until get message REBOOT_RESP
            mainMessageBox = []
            mainMessage = queueMain.get()
            while(mainMessage[0] != REBOOT_RESP):
                mainMessageBox.append(mainMessage)
                mainMessage = queueMain.get()
            with lockQueueMain:
                for mainMessage in mainMessageBox:
                    queueMain.put(mainMessage)
            continue
        else:
            logger.error('unexpected message %s'%(mainMessage,))
    if(retryCount != 0):
        Retry()

    if(udpAction == 'stAcl'):
        EndLogServer()

#read file "config.ini" and return featureId 
def SnatchFeatureId(casePath):
    featureId = 'Common'
    if(os.path.exists('%s/config.ini'%casePath) == True):
        conf = ConfigParser.ConfigParser()
        conf.read('%s/config.ini'%casePath)
        featureId = conf.get('Common','FeatureId')
    return featureId

#read specification.txt if it existed and return description
def SnatchDescription(casePath):
    description = ''
    if(os.path.exists('%s/specification.txt'%casePath) == False):
        return description
    try:
        specFile = open('%s/specification.txt'%casePath,'r')
    except Exception,e:
        logger.warn('can not open file: %s/specification.txt'%casePath)
        return description
    for line in specFile:
        noLineBreak = line.strip('\n')
        description += noLineBreak
    specFile.close()
    return description

#count the test result
def GenerateResult():
    successCaseCount = 0
    reportFormat = 0
    failTestCases = []
    successTestCases = []
    resultList = []
    deleteSameCaseList = []
    if(prologHandleCount > 1):
        for i in range(len(TestCases)):
            if(len(deleteSameCaseList) == 0 or TestCases[i][0] != TestCases[i-1][0]):
                deleteSameCaseList.append(TestCases[i])
    else:
        deleteSameCaseList = TestCases
    for i in range(len(deleteSameCaseList)):
        if(deleteSameCaseList[i][16] == 1):
            successCaseCount += 1
            reportFormat = passFormat
            successTestCases.append([deleteSameCaseList[i][0],deleteSameCaseList[i][1]])
        else:
            reportFormat = failFormat
            failTestCases.append([deleteSameCaseList[i][0],deleteSameCaseList[i][2]])
        featureId = SnatchFeatureId(deleteSameCaseList[i][1])
        description = SnatchDescription(deleteSameCaseList[i][1])
        resultList.append(reportFormat%(deleteSameCaseList[i][0],featureId,description))
    return (successCaseCount,failTestCases,successTestCases,resultList,deleteSameCaseList)

def OutputCiReport(caseCount,successCaseCount,resultList):
    global udpLogDir,CiLogNameFormat
    try:
        ciLogFile = open('%s/%s'%(udpLogDir,CiLogNameFormat),'w')
    except Exception,e:
        logger.error('can not open %s/%s'%(udpLogDir,CiLogNameFormat))
        return -1
    failCaseCount = caseCount - successCaseCount
    percentage = '%d'%(successCaseCount * 100 / caseCount) + r'%'
    print >> ciLogFile,'<TABLE>'
    print >> ciLogFile,'<TR><TH>Total</TH><TH>Pass</TH><TH>Fail</TH><TH>Percentage</TH></TR>'
    print >> ciLogFile,'<TR><TD>%d</TD><TD>%d</TD><TD>%d</TD><TD>%s</TD></TR>'%(caseCount,successCaseCount,failCaseCount,percentage)
    print >> ciLogFile,'</TABLE>'
    print >> ciLogFile,'<TABLE>'
    print >> ciLogFile,'<TR><TH>Case</TH><TH>Feature ID</TH><TH>Result</TH><TH>Description</TH></TR>'
    for i in range(len(resultList)):
        print >> ciLogFile,resultList[i].strip('\n')
    print >> ciLogFile,'</TABLE>'
    ciLogFile.close()

'''
def OutputXmlReport(caseCount,successCaseCount,failTestCases,successTestCases):
    global CaseListName,CiXmlLogName,udpLogDir
    try:
        ciXmlLog = open('%s/%s'%(udpLogDir,CiXmlLogName),'w')
    except Exception,e:
        logger.error('can not open %s/%s'%(udpLogDir,CiXmlLogName))
        return -1
    failCaseCount = caseCount - successCaseCount
    percentage = '%d'%(successCaseCount * 100 / caseCount) + r'%'
    doc = minidom.Document()
    pTestResult = doc.createElement('TestResult')
    doc.appendChild(pTestResult)
    pList = doc.createElement('list')
    pList.appendChild(doc.createTextNode('%s'%CaseListName[:-4]))
    pTestResult.appendChild(pList)
    pTotal = doc.createElement('total')
    pTotal.appendChild(doc.createTextNode('%d'%caseCount))
    pTestResult.appendChild(pTotal)
    pPass = doc.createElement('pass')
    pPass.appendChild(doc.createTextNode('%d'%successCaseCount))
    pTestResult.appendChild(pPass)
    pFail = doc.createElement('fail')
    pFail.appendChild(doc.createTextNode('%d'%failCaseCount))
    pTestResult.appendChild(pFail)
    pPercentage = doc.createElement('percentage')
    pPercentage.appendChild(doc.createTextNode('%s'%percentage))
    pTestResult.appendChild(pPercentage)
    if failTestCases:
        pFailCases = doc.createElement('failCases')
        pTestResult.appendChild(pFailCases)
        for case in failTestCases:
            pCase = doc.createElement('case')
            pFailCases.appendChild(pCase)
            pName = doc.createElement('name')
            pName.appendChild(doc.createTextNode('%s'%case[0]))
            pCase.appendChild(pName)
            pFeatureId = doc.createElement('featureId')
            featureId = SnatchFeatureId(case[1])
            pFeatureId.appendChild(doc.createTextNode('%s'%featureId))
            pCase.appendChild(pFeatureId)
            pDescription = doc.createElement('description')
            description = SnatchDescription('%s'%(case[1][:-5]))
            pDescription.appendChild(doc.createTextNode('%s'%description))
            pCase.appendChild(pDescription)
    if successTestCases:
        pSuccessCases = doc.createElement('successCases')
        pTestResult.appendChild(pSuccessCases)
        for case in successTestCases:
            pCase = doc.createElement('case')
            pSuccessCases.appendChild(pCase)
            pName = doc.createElement('name')
            pName.appendChild(doc.createTextNode('%s'%case[0]))
            pCase.appendChild(pName)
            pFeatureId = doc.createElement('featureId')
            featureId = SnatchFeatureId(case[1])
            pFeatureId.appendChild(doc.createTextNode('%s'%featureId))
            pCase.appendChild(pFeatureId)
            pDescription = doc.createElement('description')
            description = SnatchDescription('%s'%(case[1]))
            pDescription.appendChild(doc.createTextNode('%s'%description))
            pCase.appendChild(pDescription)
    ciXmlLog.write(doc.toprettyxml(indent=" "))
    ciXmlLog.close()
'''

def OutputXmlReport(caseCount,successCaseCount,failTestCases,successTestCases):
    global CaseListName,CiXmlLogName,udpLogDir,boardType
    try:
        ciXmlLog = open('%s/%s'%(udpLogDir,CiXmlLogName),'w')
    except Exception,e:
        logger.error('can not open %s/%s'%(udpLogDir,CiXmlLogName))
        return -1
    failCaseCount = caseCount - successCaseCount
    percentage = '%d'%(successCaseCount * 100 / caseCount) + r'%'
    print >> ciXmlLog,'<TestResult>'
    print >> ciXmlLog,'\t<list>%s_%s</list>'%(CaseListName[:-4],boardType)
    print >> ciXmlLog,'\t<total>%d</total>'%caseCount
    print >> ciXmlLog,'\t<pass>%d</pass>'%successCaseCount
    print >> ciXmlLog,'\t<fail>%d</fail>'%failCaseCount
    print >> ciXmlLog,'\t<percentage>%s</percentage>'%percentage
    if failTestCases:
        print >> ciXmlLog,'\t<failCases>'
        for case in failTestCases:
            print >> ciXmlLog,'\t\t<case>'
            print >> ciXmlLog,'\t\t\t<name>%s</name>'%case[0]
            print >> ciXmlLog,'\t\t\t<featureId>%s</featureId>'%(SnatchFeatureId(case[1]))
            print >> ciXmlLog,'\t\t\t<result>Failed</result>'
            print >> ciXmlLog,'\t\t\t<description>%s</description>'%(SnatchDescription(case[1][:-5]))
            print >> ciXmlLog,'\t\t</case>'
        print >> ciXmlLog,'\t</failCases>'
    if successTestCases:
        print >> ciXmlLog,'\t<successCases>'
        for case in successTestCases:
            print >> ciXmlLog,'\t\t<case>'
            print >> ciXmlLog,'\t\t\t<name>%s</name>'%case[0]
            print >> ciXmlLog,'\t\t\t<featureId>%s</featureId>'%(SnatchFeatureId(case[1]))
            print >> ciXmlLog,'\t\t\t<result>Passed</result>'
            print >> ciXmlLog,'\t\t\t<description>%s</description>'%(SnatchDescription(case[1]))
            print >> ciXmlLog,'\t\t</case>'
        print >> ciXmlLog,'\t</successCases>'
    print >> ciXmlLog,'</TestResult>'
    ciXmlLog.close()

#report the test result and output failed cases and write ciReport
def Report():
    global udpLogDir,udpLog,CaseListName,udpAction
    successCaseCount = i = 0
    successCaseCount,failTestCases,successTestCases,resultList,deleteSameCaseList = GenerateResult()
    caseCount = len(deleteSameCaseList)
    logger.info('ALL: %d\tSUCCESS: %d'%(caseCount,successCaseCount))
    if(failTestCases):
        allowedFailNumber = int(caseCount * 0.05) + 1 
        for failCase in failTestCases:
            logger.info('%s fail'%failCase[0])
            if(caseCount > 3 and udpAction == 'stAcl' and i <= allowedFailNumber):
                try:
                    failCaseLogDir = '%s/%s'%(udpLogDir,failCase[0])
                    if os.path.exists(failCaseLogDir):
                        shutil.rmtree(failCaseLogDir)
                    shutil.copytree(failCase[1],failCaseLogDir)
                    fileList = os.listdir(failCaseLogDir)
                    for f in fileList:
                        if(f.find('iqcompare') == -1 and f.find('UDP_51000') == -1):
                            os.remove('%s/%s'%(failCaseLogDir,f))
                except Exception,e:
                    logger.error(e)
                i += 1
    OutputCiReport(caseCount,successCaseCount,resultList)
    OutputXmlReport(caseCount,successCaseCount,failTestCases,successTestCases)
    if(udpAction == 'stAcl' and udpLog.find('/0_LOGS/') != -1):
        try:
            shutil.copyfile(udpLog,'%s/UDP_51000_tc_all_%s.log'%(udpLogDir,CaseListName))
        except Exception,e:
            logger.error(e)
            return


def findCaseByName(caseName,allTestCaseList):
    findCase = []
    findSubCaseNameList = []
    hit = False
    for case in allTestCaseList:
        if hasMultiCase(case):
            result = [x for x in case[MULTI_CASE_LIST_INDEX] if type(x) == list and caseName == x[CASE_NAME_INDEX]]
            if result:
                findCase = case
                findSubCaseNameList = [x[CASE_NAME_INDEX] for x in case[MULTI_CASE_LIST_INDEX] if type(x) == list]
                hit = True 
                break
        else:
            if caseName == case[CASE_NAME_INDEX]:
                findCase = case
                hit = True
                break
    
    return (hit,findCase,findSubCaseNameList)
        
    
    
def WriteSingleMultiCaseLog(logFile):
    global TestCases
    subCaseNameList = []
    endTimes = 0
    
    try:
        log = open(logFile,'r')
    except Exception,e:
        logger.error('can not open %s, please check'%logFile)
        return False
    
    findStart = True
    line = log.readline()
    while line:
        if findStart:
            readCaseName = re.findall('INF/SCT\s+([A-Za-z0-9_]{10}):\s+Start TC',line)
            if readCaseName:
                hit,case,subCaseNameList = findCaseByName(readCaseName[0],TestCases)
                if hit:
                    findStart = False
                    endTimes = 0
                    
                    try:
                        singleCaseLog = open('%s/UDP_51000_tc_all.log'%case[CASE_LOG_DIR_INDEX],'w') 
                    except Exception,e:
                        logger.error('can not open %s/UDP_51000_tc_all.log'%case[CASE_LOG_DIR_INDEX])
                        return False
                        
                    singleCaseLog.write(line)
        else:
            singleCaseLog.write(line)
            
            if (len(subCaseNameList)):
                for subCaseName in subCaseNameList:
                    if (line.find('INF/SCT %s: End TC'%subCaseName) != -1):
                        endTimes += 1
                        break
                
                if (endTimes == len(subCaseNameList)):
                    singleCaseLog.close()
                    findStart = True
            else:            
                if (line.find('INF/SCT %s: End TC'%readCaseName[0]) != -1):
                    singleCaseLog.close()
                    findStart = True
                
        line = log.readline()
    
    if findStart == False:
        singleCaseLog.close()
    log.close()
    return True
    
    
def WriteSingleCaseLog(logFile):
    try:
        log = open(logFile,'r')
    except Exception,e:
        logger.error('can not open %s, please check'%logFile)
        return 1
    line = log.readline()
    while line:
        result = re.findall('INF/SCT\s+([A-Za-z0-9_]{10}):\s+Start TC',line)
        if result:
            for case in TestCases:
                if(case[0] == result[0]): break
            singleCaseLog = open('%s/UDP_51000_tc_all.log'%case[2],'w')
            while(line and line.find('INF/SCT %s: End TC'%result[0]) == -1):
                singleCaseLog.write(line)
                line = log.readline()
            singleCaseLog.write(line)
            singleCaseLog.close()
        line = log.readline()
    log.close()
    return 0
	    
	
def SplitUdpLog():
    global udpLog,udpLogDir,dspNo,TestCases,multiRTM
    if(udpLog.find('/0_LOGS/') != -1):
        fileList = os.listdir(udpLogDir)
        for f in fileList:
            if(os.path.isdir('%s/%s'%(udpLogDir,f)) == True):
                shutil.rmtree('%s/%s'%(udpLogDir,f))
            elif(os.path.isfile('%s/%s'%(udpLogDir,f)) == True and f.find('put') != -1):
                os.remove('%s/%s'%(udpLogDir,f))
    if(len(dspNo) == 3):
        try:
            log = open(udpLog,'r')
        except Exception,e:
            logger.error('can not open %s, please check'%udpLog)
            return 1
        log4DspList = ['','','']
        for i in range(0,3):
            log4DspList[i] = open('%s/UDP_51000_tc_all_dsp%d.log'%(udpLogDir,dspNo[i]),'w')
        for line in log:
            if(line == '\n' or line == ''): continue
            if(line.find('FSP-12%d'%dspNo[0]) != -1 or line.find('FSP-12%d'%(dspNo[0]-1)) != -1):
                log4DspList[0].write(line)
            elif(line.find('FSP-12%d'%dspNo[1]) != -1 or line.find('FSP-12%d'%(dspNo[1]-1)) != -1):
                log4DspList[1].write(line)
            elif(line.find('FSP-12%d'%dspNo[2]) != -1 or line.find('FSP-12%d'%(dspNo[2]-1)) != -1):
                log4DspList[2].write(line)
        log.close()
        for i in range(0,3):
            log4DspList[i].close()
            logFile = '%s/UDP_51000_tc_all_dsp%d.log'%(udpLogDir,dspNo[i])
            if multiRTM == 1:
                if WriteSingleMultiCaseLog(logFile) == False:
                    return 1
            else:
                if WriteSingleCaseLog(logFile):
                    return 1
    else:
        if multiRTM == 1:
            return WriteSingleMultiCaseLog(udpLog)
        else:
            return WriteSingleCaseLog(udpLog)
    return 0
	
def CheckError():
    global udpAction,udpLogDir
    if(udpAction != 'stAcl'): return
    errorLog = []
    i = 0
    if SplitUdpLog():
        return
    while(i < len(caseNeedToCheckLog)):
        for k in range(len(TestCases)):
            if(caseNeedToCheckLog[i][0] == TestCases[k][0]):
                try:
                    log = open('%s/UDP_51000_tc_all.log'%TestCases[k][2],'r')
                except Exception,e:
                    logger.error(e)
                    return
                for line in log:
                    if(line.find(caseNeedToCheckLog[i][1]) != -1):
                        logger.info('%s: find log %s in %s'%(caseNeedToCheckLog[i][0],caseNeedToCheckLog[i][1],line.strip('\n')))
                        TestCases[k][16] = 1
                        break
                log.close()
                if(TestCases[k][16] == 1):
                    caseNeedToCheckLog.pop(i)
                    i -= 1
                    break
        i += 1    
    for case in TestCases:
        if(case[0].find('MAP') != -1 or case[0].find('DIA') != -1):
            if(udpLogDir.find('/0_LOGS') == -1):
                continue
        try:
            log = open('%s/UDP_51000_tc_all.log'%case[2],'r')
        except Exception,e:
            logger.error(e)
            return
        for line in log:
            line = line.strip('\n')
            if((line.find('ERR/') != -1 or line.find('WRN/') != -1) and line.find('PHY TX') != -1):
                errorLog.append('%s: %s'%(case[0],line))
            elif((line.find('RTM/') != -1 or line.find('SCT/') != -1) and line.find('ERR/') != -1):
                errorLog.append('%s: %s'%(case[0],line))
            elif(line.find('FATAL') != -1 or line.find('Crash') != -1):
                errorLog.append('%s: %s'%(case[0],line))
        log.close()
    for i in range(len(caseNeedToCheckLog)):
        logger.error('can not find log %s in udplog, %s failed'%(caseNeedToCheckLog[i][1],caseNeedToCheckLog[i][0]))
    for i in range(len(errorLog)):
        logger.error('find error %s'%errorLog[i])
    return

def printMesg():
    global udpAction, udpLogDir
    for case in TestCases:
        messages = 'message'
        if case[0].find('MAP') != -1 or case[0].find('DIA') != -1:
            if udpLogDir.find('/0_LOGS') == -1:
                continue
        try:
             f_mesg = open('%s/message.log' % case[2], 'w')
        except Exception, e:
            logger.error(e)
            return
        try:
            with open('%s/UDP_51000_tc_all.log' % case[2], 'r') as log:
                for line in log:
                    line = line.strip('\n')
                    if line.find('SCT <<<') != -1:
                        f_mesg.write(line)
        except Exception, e:
            logger.error(e)
            return
        f_mesg.close()

def main():
    global TestCases,reloadCommonFiles,powerBreakPort
    startTime = time.time()
    logger.debug('start at %s'%time.asctime())
    GetOptions(sys.argv[1:])
    init()
    Parse()
    if not TestCases:
        logger.info('no TC in %s, please check'%caseListName)
        exit()
    t_prolog = threading.Thread(target=Prolog)
    t_peroration = threading.Thread(target=Peroration)
    t_compare = threading.Thread(target=Compare)
    t_reboot = threading.Thread(target=IfReboot)
    t_prolog.setDaemon(True); t_peroration.setDaemon(True); t_compare.setDaemon(True);t_reboot.setDaemon(True)
    t_prolog.start(); t_peroration.start(); t_compare.start()
    if powerBreakPort: t_reboot.start()
    queueProlog.put((PROLOG_INIT_REQ,))
    WaitFor(queueMain,PROLOG_INIT_RESP)
    if reloadCommonFiles:
        queueProlog.put((LOAD_COMMON_FILE_REQ,))
        WaitFor(queueMain,LOAD_COMMON_FILE_RESP)
        reloadCommonFiles = 0
    RunTestcases(t_prolog,t_peroration,t_compare,t_reboot)
    printMesg()
#    CheckError()
    Report()
    diffTime = time.time() - startTime
    logger.debug('end at %s'%time.asctime())
    logger.info('All cases cost time %d seconds'%diffTime) 

if __name__ == '__main__':
    main()
