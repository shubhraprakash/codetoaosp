ERRORCOLORRED = '\33[31m'
WARNCOLORYELLOW = '\33[33m'
MESSAGECOLORGREEN = '\33[32m'
COLOREND = '\33[0m'

INTERNAL_REPO_SERVER = '/Users/shubhraprakash/localaospgitserver'

def printColorLog(line, color):
    print color + line + COLOREND

def MESSAGE(line):
    line = 'MSG: ' + line
    printColorLog(line, MESSAGECOLORGREEN)

def WARN(line):
    line = 'WARN: ' + line
    printColorLog(line, WARNCOLORYELLOW)

def ERROR(line):
    line = 'ERROR: ' + line
    printColorLog(line, ERRORCOLORRED)