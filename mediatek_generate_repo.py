#!/usr/bin/env python

import os
from git import *
from distutils import dir_util
import shutil
import sys
import getopt

ERRORCOLORRED = '\33[31m'
WARNCOLORYELLOW = '\33[33m'
MESSAGECOLORGREEN = '\33[32m'
COLOREND = '\33[0m'

INTERNAL_REPO_SERVER = '/home/shubhraprakash/localaospgitserver'

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

def readManifestGroup(file, firstLine):
    line = firstLine
    if not line:
        return line
    v = line.find('/>')
    if v != -1:
        return line
    s = line.find('<')
    e = line.find(' ', s)
    k = line[s + 1 : e]
    k.lstrip()
    keyword = '/' + k
    while 1:
        l = file.readline()
        if not l:
            ERROR("Bad line detected")
            raise SystemExit()
        line = line + l
        v = l.find(keyword)
        if v != -1:
            return line

def getEntryValue(line, entry):
    value = ""
    v = line.find(entry)
    if v is -1:
        return value
    s = line.find('="', v)
    if s is -1:
        return value
    e = line.find('"', s + 2)
    if e is -1:
        return value
    value = line[s + 2 : e]
    return value

class parseManifest:
    def __init__(self, manifestPath, manifestAosp, destAosp, trackedAosp, verbose = False):
        self.projectLines = []
        self.names = []
        self.paths = []
        self.lineNum = 1;
        self.numProjects = 0;
        self.verbose = verbose
        self.newRepo = []
        # self.skip = []
        # self.groups = []
        # self.cloneDepth = []
        self.manifestAosp = manifestAosp
        self.destAosp = destAosp
        self.trackedAosp = trackedAosp
        self.readFileAndParse(manifestPath)

    def readFileAndParse(self, manifestPath):
        with open(manifestPath) as file:
            line = file.readline()
            while line:
                if line.find("include name") != -1 or line.find("project") != -1:
                    line = readManifestGroup(file, line)
                    self.processManifestLine(line)
                line = file.readline()

    def processManifestLine(self, line):
        v = line.find('include name')
        if v != -1:
            self.parseIncludeGroup(line)
            return
        v = line.find('project')
        if v != -1:
              self.parseProjectGroup(line)
              return
        print('No rule to parse ' + line)

    def parseIncludeGroup(self, line):
        name = getEntryValue(line, 'name')
        if not name:
            ERROR("Bad include line detected")
            raise SystemExit()
        if self.verbose:
            MESSAGE('recur on manifest: ' + name)
        self.readFileAndParse(name)

    def parseProjectGroup(self, line):
        name = getEntryValue(line, 'name')
        if not name:
            ERROR("No name detected")
            raise SystemExit()
        path = getEntryValue(line, 'path')
        if not path:
            path = name
        projectPath = os.path.join(self.manifestAosp, path)
        # if the dir is absent/vacant then there is noting to do
        if not os.path.exists(projectPath) or os.listdir(projectPath) == '':
            WARN('dir ' + projectPath + ' is absent/vacant')
            return
        if self.verbose:
            MESSAGE('name: ' + name + ' path: ' + path + ' detected in project')
            MESSAGE('project line: ' + line)
        # cloneDepth = getEntryValue(line, 'clone-depth')
        # group = getEntryValue(line, 'groups')
        # self.cloneDepth.insert(self.numProjects, cloneDepth)
        # self.groups.insert(self.numProjects, group)
        self.names.insert(self.numProjects, name)
        self.paths.insert(self.numProjects, path)
        self.projectLines.insert(self.numProjects, line)
        self.newRepo.insert(self.numProjects, False)
        # self.skip.insert(self.numProjects, False)
        self.numProjects = self.numProjects + 1

    def setProjectRepos(self):
        repos = []
        for i in range(0, self.numProjects):
            # change project name to be aosp/...
            name = self.names[i]
            path = self.paths[i]
            if -1 != name.find('alps'):
                temp = 'aosp/' + name[5:len(name)]
            else:
                temp = 'aosp/' + name
            name = temp
            self.names[i] = name
            repos.insert(i, GitRepo(path, self.destAosp, self.verbose))
            internalRepo = GitRepo(name, INTERNAL_REPO_SERVER)
            dest = os.path.join(self.destAosp, path)
            if os.path.exists(dest):
                continue
            if internalRepo.gitExists():
                continue
            internalRepo.setupGit()
            try:
                # create new dir
                # copy from the original code first
                trackedPath = os.path.join(self.trackedAosp, path)
                if os.path.exists(trackedPath):
                    try:
                        shutil.copytree(trackedPath, dest)
                    except:
                        pass
                    # fix file symlinks
                    repos[i].resetHead()
                else:
                    repos[i].cloneGit(internalRepo._getRepoDir())
                    self.newRepo[i] = True
                print ('copy ' + self.manifestAosp + '/' + path + ' to ' + self.destAosp)
                copy(path, self.manifestAosp, self.destAosp, self.verbose)

                repos[i].commitChanges()
                repos[i].addRemote(internalRepo._getRepoDir())
                if self.verbose:
                    print '\n'
            except:
                ERROR('Deleting ' + dest)
                os.system('rm -rf ' + dest)
                internalRepo.deleteRepo()
                raise SystemExit()

class GitRepo:
    def __init__(self, path, aospPath, verbose = False):
        self.path = path
        self.aospPath = aospPath
        self.verbose = verbose

    def resetHead(self):
        repoPath = os.path.join(self.aospPath, self.path)
        repo = Repo(repoPath)
        repo.git.reset('--hard', 'HEAD')

    def deleteRepo(self):
        repoPath = os.path.join(self.aospPath, self.path)
        repoPath = repoPath + '.git'
        ERROR('Deleting ' + repoPath)
        os.system('rm -rf ' + repoPath)

    def addRemote(self, remotePath):
        try:
            repoPath = os.path.join(self.aospPath, self.path)
            repo = Repo(repoPath)
            # writer = repo.config_writer()
            # writer.set_value('user', 'name', 'Shubhraprakash Das')
            # writer.set_value('user', 'email', 'shubhraprakash.das@oculus.com')
            repo.git.remote('add', 'fbgit', remotePath)
            repo.git.checkout('-b', 'android-8.1.0_r7_mtk')
            shallow = repoPath + '/.git/shallow'
            if os.path.exists(shallow):
                repo.git.checkout('--orphan', 'android-8.1.0_r7_mtk_orphan')
                repo.git.commit('--allow-empty', m = 'Initial commit for shallow repo')
                repo.git.push("fbgit", "android-8.1.0_r7_mtk_orphan:android-8.1.0_r7_mtk")
            else:
                repo.git.push("fbgit", "android-8.1.0_r7_mtk:android-8.1.0_r7_mtk")
        except GitCommandError as e:
            ERROR(e.stderr)
            raise e


    def emptyDir(self, untrackedAosp):
        for files in os.listdir(untrackedAosp):
            filepath = os.path.join(untrackedAosp, files)
            if os.path.isfile(filepath):
                os.unlink(filepath)
            else:
                shutil.rmtree(filepath)

    def _getRepoDir(self):
        repoPath = os.path.join(self.aospPath, self.path)
        repoDir = repoPath + '.git'
        return repoDir

    def setupGit(self):
        repoDir = self._getRepoDir()
        if os.path.exists(repoDir):
            ERROR("Git repo exists already: " + repoDir)
            raise SystemExit()
        # need to create a new repository
        repo = Repo.init(repoDir, bare = True)
        if self.verbose:
            MESSAGE('Created bare repo: ' + repoDir)

    def gitExists(self):
        projectRepoDir = self._getRepoDir()
        if os.path.exists(projectRepoDir):
            return True
        return False

    def cloneGit(self, remotePath):
        projectDir = os.path.join(self.aospPath, self.path)
        repo = Repo.clone_from(remotePath, projectDir)
        if self.verbose:
            MESSAGE('Cloned repo: ' + remotePath + ' to ' + projectDir)

    def commitChanges(self):
        repoPath = os.path.join(self.aospPath, self.path)
        if self.verbose:
            MESSAGE('repo path ' + repoPath)
        repo = Repo(repoPath)
        writer = repo.config_writer()
        writer.set_value('user', 'name', 'Shubhraprakash Das')
        writer.set_value('user', 'email', 'shubhraprakash.das@oculus.com')
        status = repo.git.status()
        if self.verbose:
            MESSAGE('git status:' + status)
        if -1 != status.find('modified') or -1 != status.find('Untracked files'):
            try:
                repo.git.lfs('uninstall')
            except GitCommandError as e:
                # status 1 for lfs not present
                if e.status != 1:
                    ERROR(e.stderr)
                    raise e
            repo.git.add('.')
            status1 = repo.git.status()
            if status1 == status:
                WARN('Cannot commit changes in dir: ' + repoPath)
            else:
                repo.git.commit(m = 'Intial MTK code drop')
                status1 = repo.git.status()
                if -1 == status1.find('working tree clean'):
                    WARN('Could not commit some changes in dir: ' + repoPath)
                elif self.verbose:
                    MESSAGE('Committed changes to dir ' + repoPath)
        elif self.verbose:
            MESSAGE('No changes to dir ' + repoPath)

# copied from distutils/dir_util.py and made few modifications
def copy_tree(src, dst, preserve_mode=1, preserve_times=1,
              preserve_symlinks=0, update=0, verbose=1, dry_run=0):
    """Copy an entire directory tree 'src' to a new location 'dst'.

    Both 'src' and 'dst' must be directory names.  If 'src' is not a
    directory, raise DistutilsFileError.  If 'dst' does not exist, it is
    created with 'mkpath()'.  The end result of the copy is that every
    file in 'src' is copied to 'dst', and directories under 'src' are
    recursively copied to 'dst'.  Return the list of files that were
    copied or might have been copied, using their output name.  The
    return value is unaffected by 'update' or 'dry_run': it is simply
    the list of all files under 'src', with the names changed to be
    under 'dst'.

    'preserve_mode' and 'preserve_times' are the same as for
    'copy_file'; note that they only apply to regular files, not to
    directories.  If 'preserve_symlinks' is true, symlinks will be
    copied as symlinks (on platforms that support them!); otherwise
    (the default), the destination of the symlink will be copied.
    'update' and 'verbose' are the same as for 'copy_file'.
    """
    from distutils.file_util import copy_file

    if not dry_run and not os.path.isdir(src):
        raise DistutilsFileError, \
              "cannot copy tree '%s': not a directory" % src
    try:
        names = os.listdir(src)
    except os.error, (errno, errstr):
        if dry_run:
            names = []
        else:
            raise DistutilsFileError, \
                  "error listing files in '%s': %s" % (src, errstr)

    if not dry_run:
        dir_util.mkpath(dst, verbose=verbose)

    outputs = []

    for n in names:
        src_name = os.path.join(src, n)
        dst_name = os.path.join(dst, n)

        if preserve_symlinks and os.path.islink(src_name):
            link_dest = os.readlink(src_name)
            if os.path.exists(dst_name):
                if not os.path.islink(dst_name):
                    ERROR(src_name + " is a symlink and " + dst_name + " is not")
                    raise SystemExit()
                link_dest_dst = os.readlink(dst_name)
                if link_dest != link_dest_dst:
                    ERROR("symlink " + src_name + " != symlink " + dst_name)
                    raise SystemExit()
            if verbose >= 1:
                MESSAGE('linking ' + dst_name + ' -> ' + link_dest)
            if not dry_run:
                try:
                    os.symlink(link_dest, dst_name)
                except OSError as err:
                    if err.errno == 17:
                        if verbose >= 1:
                            WARN('Symlink overwrite skip: ' + link_dest + ':' + dst_name)
                    else:
                        ERROR("Link Copy Error: " + err + " link_dest -> dst_name")
                        raise SystemExit()

            outputs.append(dst_name)

        elif os.path.isdir(src_name):
            outputs.extend(
                copy_tree(src_name, dst_name, preserve_mode,
                          preserve_times, preserve_symlinks, update,
                          verbose=verbose, dry_run=dry_run))
        else:
            copy_file(src_name, dst_name, preserve_mode,
                      preserve_times, update, verbose=verbose,
                      dry_run=dry_run)
            outputs.append(dst_name)

    return outputs

def copy(path, src, dest, verbose = False):
    srcPath = os.path.join(src, path)
    destPath = os.path.join(dest, path)
    if not os.path.isdir(srcPath):
        ERROR("Dir " + srcPath + "does not exist")
        raise SystemExit()
    if verbose:
        MESSAGE('copy dir ' + srcPath + ' to ' + destPath)
    copy_tree(srcPath, destPath, preserve_symlinks = 1, verbose = 0)

def setupNewAospProject(aospDest, aospTracked):
    if os.path.exists(aospDest):
        print(WARNCOLORYELLOW + 'New aosp project Path exist already' + COLOREND)
        return
    os.makedirs(aospDest)
    MESSAGE('copying the aosp project from ' + aospTracked + ' to ' + aospDest)
    dir_util.copy_tree(aospTracked, aospDest, preserve_symlinks = 1, verbose = 0)

def addNewProjectToRepoList(projectPath, aospPath):
    projectList = os.path.join(aospPath, '.repo/project.list')
    f = open(projectList, "a+")
    temp = projectPath + '\n'
    f.write(temp)
    f.close()

def inManifest(path, mProjects, mNumProjects):
    for i in range(0, mNumProjects):
        p = getEntryValue(mNumProjects[i], 'path')
        if p and p == path:
            return True
    return False

def generateManifestProjectList(parser):
    # add the new custom projects to the project list and manifest
    manifestFile = os.path.join(parser.destAosp, '.repo/manifest.xml')
    mNumProjects = 0
    numFooterLines = 0
    numHeaderLines = 0
    mHeader = []
    mFooter = []
    mProjects = []
    mProjectDict = {}
    with open(manifestFile) as file:
        line = file.readline()
        while line:
            if -1 != line.find('<project'):
                mProjects.insert(mNumProjects, readManifestGroup(file, line))
                path = getEntryValue(line, 'path')
                mProjectDict[path] = True
                mNumProjects = mNumProjects + 1
            else:
                if mNumProjects == 0:
                    mHeader.insert(numHeaderLines, line)
                    numHeaderLines = numHeaderLines + 1;
                else:
                    mFooter.insert(numFooterLines, line)
                    numFooterLines = numFooterLines + 1;
            line = file.readline()

    # overwrite the original manifest
    file = open(manifestFile, 'w')
    for i in range(0, numHeaderLines):
        file.write(mHeader[i])
    # write original projects
    for i in range(0, mNumProjects):
        file.write(mProjects[i])
    # write the new custom projects
    for i in range(0, parser.numProjects):
        path = parser.paths[i]
        if path not in mProjectDict:
            file.write(parser.projectLines[i])
            addNewProjectToRepoList(parser.paths[i], parser.destAosp)
    # write footer
    for i in range(0, numFooterLines):
        file.write(mFooter[i])
    file.close()

def generateManifestGit(parser):
    manifestGit = GitRepo('aosp/manifest', INTERNAL_REPO_SERVER)
    if not manifestGit.gitExists():
        manifestGit.setupGit()
    cloneManifest = GitRepo('manifest', parser.destAosp)
    cloneManifest.cloneGit(manifestGit._getRepoDir())
    mtkManifest = os.path.join(parser.destAosp, 'manifest/mtk-aosp-custom.xml')
    file = open(mtkManifest, 'w')
    file.write('<?xml version="1.0" encoding="utf-8"?>\n<manifest>\n')
    for i in range(0, parser.numProjects):
        if -1 != parser.projectLines[i].find('alps'):
            v = parser.projectLines[i].find('alps')
            line = (parser.projectLines[i])[0:v]
            line = line + 'aosp'
            line = line + (parser.projectLines[i])[v + 4 : len(parser.projectLines[i])]
            file.write(line)
        else:
            v = parser.projectLines[i].find('name="')
            line = (parser.projectLines[i])[0 : v] + 'name="aosp/'
            line = line + (parser.projectLines[i])[v + 6 : len(parser.projectLines[i])]
            # add path if path is missing
            if -1 == line.find('path="'):
                v = line.find('name="')
                e = line.find('"', v + 6)
                line2 = line[0 : e + 1]
                line2 = line2 + ' path="' + parser.paths[i] + '"'
                line2 = line2 + line[e + 1 : len(line)]
                line = line2
            file.write(line)
    file.write('</manifest>')
    file.close()

    defManifest = os.path.join(parser.destAosp, 'manifest/default.xml')
    file = open(defManifest, 'w')
    file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    file.write('<manifest>\n')
    file.write('  <remote name="origin"\n')
    file.write('    fetch="' + INTERNAL_REPO_SERVER + '/"\n')
    file.write('    pushurl="' + INTERNAL_REPO_SERVER + '/"/>\n')
    file.write('  <default remote="origin"\n')
    file.write('    revision="android-8.1.0_r7_mtk"\n')
    file.write('    sync-j="12"/>\n')
    file.write('  <include name="mtk-aosp-custom.xml"/>\n')
    file.write('</manifest>')
    file.close()

    cloneManifest.commitChanges()
    cloneManifest.addRemote(manifestGit._getRepoDir())

def main(argv):
    verbose = False
    manifest = ''
    aosp = ''
    dest = ''
    untrackedAosp = ''
    usage = 'Usage: mediatek_generate_repo.py -m <aosp_manifest> ' + \
            '-t <tracked_aosp_Folder> -u ' + \
            '<untracked_aosp_folder> -d <destination_folder>'
    try:
        options, args = getopt.getopt(argv, 'hm:t:u:d:v', ["help", "manifest=",
                                      "trackedaosp=", "untrackedaosp=", "destination=", "verbose"])
    except getopt.GetoptError:
        ERROR(usage)
        sys.exit(2)
    for opt, arg in options:
        if opt in ('-h', "-help"):
            MESSAGE(usage)
            sys.exit()
        elif opt in ("-m", "-manifest"):
            manifest = arg
        elif opt in ("-t", "-trackedaosp"):
            aosp = arg
        elif opt in ("-u", "-untrackedaosp"):
            untrackedAosp = arg
        elif opt in ("-d", "-destination"):
            dest = arg
        elif opt in ("-v", "-verbose"):
            verbose = True
    if not manifest or not aosp or not untrackedAosp or not dest:
        ERROR(usage)
        sys.exit(2)
    # first create the new project dir and copy the tracked folder
    # setupNewAospProject(dest, aosp)
    parser = parseManifest(manifest, untrackedAosp, dest, aosp, verbose)
    parser.setProjectRepos()
    generateManifestGit(parser)

if __name__ == "__main__":
    main(sys.argv[1:])

