import os
from git import *
from distutils import dir_util
import shutil
import sys
from repologger import *

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
    def __init__(self, manifestPath, manifestFile, manifestAosp, destAosp, trackedAosp, verbose = False):
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
        self.manifestPath = manifestPath
    	self.readFileAndParse(manifestPath + '/' + manifestFile)

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
        self.readFileAndParse(self.manifestPath + '/' + name)

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
	        # create new dir
	        if os.path.exists(dest):
	            os.system('rm -rf ' + dest)
	        if not internalRepo.gitExists():
	            internalRepo.setupGit()
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

	        copy(path, self.manifestAosp, self.destAosp, self.verbose)
	        repos[i].commitChanges()
	        repos[i].addRemote(internalRepo._getRepoDir())
	        if self.verbose:
	            print '\n'

class GitRepo:
    def __init__(self, path, aospPath, verbose = False):
        self.path = path
        self.aospPath = aospPath
        self.verbose = verbose

    def resetHead(self):
        repoPath = os.path.join(self.aospPath, self.path)
        repo = Repo(repoPath)
        repo.git.reset('--hard', 'HEAD')

    def addRemote(self, remotePath):
        repoPath = os.path.join(self.aospPath, self.path)
        repo = Repo(repoPath)
        # writer = repo.config_writer()
        # writer.set_value('user', 'name', 'Shubhraprakash Das')
        # writer.set_value('user', 'email', 'shubhraprakash.das@oculus.com')
        repo.git.remote('add', 'fbgit', remotePath)
        # push to remote
        repo.git.checkout('-b', 'android-8.1.0_r7_mtk')
        try:
            repo.git.push("fbgit", "android-8.1.0_r7_mtk:android-8.1.0_r7_mtk")
        except GitCommandError as e:
            emsg = e.stderr
            if -1 != emsg.find('android-8.1.0_r7_mtk -> android-8.1.0_r7_mtk (fetch first)'):
            	# already pushed in prev run just skip
                WARN('git is already pushed: ' + repoPath)
            elif -1 != emsg.find('shallow update not allowed'):
            	WARN('shallow git ' + repoPath)
            	repo.git.checkout('--orphan', 'android-8.1.0_r7_mtk_orphan')
                repo.git.commit('--allow-empty', m = 'Initial commit for shallow repo')
                # repo.git.checkout('--unshallow', 'aosp')
                # push after unshallow
                try:
                    repo.git.push("fbgit", "android-8.1.0_r7_mtk_orphan:android-8.1.0_r7_mtk")
                except GitCommandError as e:
                    emsg = e.stderr
                    if -1 != emsg.find('android-8.1.0_r7_mtk_orphan -> android-8.1.0_r7_mtk (fetch first)'):
                        WARN('git is already pushed: ' + repoPath)
                    else:
                        ERROR(emsg)
                        raise SystemExit()
            else:
            	ERROR(emsg)
                raise SystemExit()
            # repo.git.fetch('--unshallow', 'aosp')

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