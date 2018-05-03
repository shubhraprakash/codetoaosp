#!/usr/bin/env python

from repomanifestparser import *
from repologger import *
import getopt
import sys
import os
import commands

def revPathDepth(path):
    if not path:
        return ''

    depth = 0
    for i in range(1,len(path)):
        if path[i] == '/':
            while (i < len(path) and path[i] == '/'):
        	    i = i + 1
            depth = depth + 1
    if path[len(path) - 1] != '/':
        depth = depth + 1
    temp = ''
    for i in range(0, depth):
        temp = temp + '../'
    return temp

def main(argv):
    git = ''
    verbose = False
    repoDir = ''
    usage = 'Usage: mediatek_push_fbgit.py -g <repogiturl>'
    try:
        options, args = getopt.getopt(argv, 'hg:r:', ["help", "git=", "repo="])
    except getopt.GetoptError:
        ERROR(usage)
        sys.exit(2)
    for opt, arg in options:
        if opt in ('-h', "-help"):
            MESSAGE(usage)
            sys.exit()
        elif opt in ('-g', "-git"):
            git = arg
        elif opt in ('-r', "-repo"):
            repoDir = arg
    if not git:
        ERROR('No git server specified')
        sys.exit()

    scriptFile = repoDir + '/fbuploadscript.sh'
    file = open(scriptFile, 'w')
    manifestPath = repoDir + '/.repo/manifests'
    parser = parseManifest(manifestPath, 'default.xml', repoDir, '', '', verbose)
    for i in range(0, parser.numProjects):
        remoteRepo = os.path.join(git, parser.names[i])
        command = 'git ls-remote --heads ' + remoteRepo + ' mtk-8.1.0'
        res = commands.getoutput(command)
        # ret = os.system(command)
        ret = 0
        if res.find('mtk-8.1.0') != -1:
            WARN('repo ' + remoteRepo + ' already has mtk-8.1.0')
        else:
            localgit = os.path.join(repoDir, parser.paths[i])
            repo = Repo(localgit)
            status = repo.git.branch()
            if status.find('mtk-8.1.0') == -1:
                repo.git.checkout('-b', 'mtk-8.1.0')
            res = repo.git.remote('-v')
            if  res.find('fbgit') == -1:
                repo.git.remote('add', 'fbgit', remoteRepo)
            shallowPath = localgit + '/.git/shallow'
            if os.path.exists(shallowPath):
                MESSAGE('Push shallow git ' + localgit + ' to ' + remoteRepo)
                status = repo.git.branch()
                if status.find('mtk-8.1.0_orphan') == -1:
                    repo.git.checkout('--orphan', 'mtk-8.1.0_orphan')
                repo.git.commit('--allow-empty', m = 'Initial commit for shallow repo')
                try:
                    ERROR('Push to ' + remoteRepo + ' failed')
                    repo.git.push('fbgit', 'mtk-8.1.0_orphan:mtk-8.1.0')
                except:
                    pass
            else:
                MESSAGE('Push git ' + localgit + ' to ' + remoteRepo)
                try:
                    repo.git.push('fbgit', 'mtk-8.1.0:mtk-8.1.0')
                except:
                    ERROR('Push to ' + remoteRepo + ' failed')
                    pass
	        # changeDir = 'cd ' + parser.paths[i]
	        # origDir = 'cd ' + revPathDepth(parser.paths[i])
	        # checkOut = 'git checkout -b mtk-8.1.0'
	        # addRem = 'git remote add fbgit ' + remoteRepo
	        # pushToRem = 'git push fbgit mtk-8.1.0:mtk-8.1.0'
	        # line = changeDir + ' && ' + checkOut + ' && ' + addRem + ' && ' + pushToRem + ' && ' + origDir + '\n'
	        # file.write(line)
	        # file.flush()
    file.close()

if __name__ == "__main__":
    main(sys.argv[1:])


