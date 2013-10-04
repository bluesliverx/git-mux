import os, subprocess, time, traceback, sys

from lib import ui, config

REQUIRED_LAYOUT_EXPLANATION = '''
This app is designed to be used with the following folder layout:

$GMUX_ROOT/bin   -- all the code for the app; where $MAIN_MODULE resides.
$GMUX_ROOT/repos -- all the repos that we'll work with.
$GMUX_ROOT/etc   -- config files.
'''

INSTALLATION_INSTRUCTIONS = '''
Installation instructions:

1. Make a folder named "$APP_NAME" in any convenient location. The folder
   should have the capacity to store git repos. The fully qualified
   path to this folder becomes $GMUX_ROOT. The path should be writable by
   your non-root user.
2. In a shell, cd to $GMUX_ROOT
2.   git clone $CODE_HOME_REPO bin
3.   sudo python bin/setup.py
4. Answer the prompts.
'''

def report_step(step):
    ui.printc('\n%s...' % step, ui.PARAM_COLOR)

def complain(problem):
    ui.eprintc(problem, ui.ERROR_COLOR)
    return 1 # return an exit code that implies an error

_non_root_user = None
def get_non_root_user():
    global _non_root_user
    if _non_root_user is None:
        if os.getegid() == 0:
            report_step('Finding non-root user')
            _non_root_user = do_or_die('stat -c %%U %s' % config.GMUX_ROOT, explanation='Need to be able to figure out non-root user.').strip()
            if _non_root_user == 'root':
                die('%s is owned by root. Needs to be owned by ordinary user.' % config.GMUX_ROOT)
        else:
            import getpass
            _non_root_user = getpass.getuser()
    return _non_root_user

_installer = None
def get_installer():
    global _installer
    if _installer is None:
        exit_code, stdout, stderr = do('which yum')
        if exit_code:
            do_or_die('which apt-get')
            _installer = 'apt-get'
        else:
            _installer = 'yum'
    return _installer

def die(msg):
    complain(msg)
    sys.exit(1)

def do(cmd, as_user=None):
    if as_user:
        if os.getegid() == 0:
            cmd = 'runuser -l %s %s' % (as_user, cmd)
    print(cmd)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr

def do_or_die(cmd, as_user=None, explanation=None):
    x = as_user
    exit_code, stdout, stderr = do(cmd, as_user=x)
    if exit_code:
        if not stderr:
            stderr = stdout
        if explanation:
            stderr = explanation.strip() + '\n\n' + stderr
        die(stderr)
    return stdout

def setup_folder_layout(audit_only=False):
    report_step('folder layout')
    if not config.BIN_FOLDER.endswith('/bin'):
        msg = '%s is not a valid location for $GMUX_ROOT/bin.\n' % config.BIN_FOLDER + \
            REQUIRED_LAYOUT_EXPLANATION + INSTALLATION_INSTRUCTIONS
        msg = msg.replace('$APP_NAME', config.APP_NAME)
        msg = msg.replace('$BIN_FOLDER', config.BIN_FOLDER)
        msg = msg.replace('$CODE_HOME_REPO', config.CODE_HOME_REPO)
        msg = msg.replace('$MAIN_MODULE', config.MAIN_MODULE)
        msg = msg.strip()
        if audit_only:
            return complain(msg)
        die(msg)
    else:
        print('layout is correct')
    return 0

def setup_app_cloned(audit_only=False):
    report_step('app is git clone')
    if not os.path.isdir(os.path.join(config.BIN_FOLDER, '.git')):
        msg = '''
%s has not been installed with a git clone command. This will prevent it
from updating itself.
''' % config.APP_TITLE + config.INSTALLATION_INSTRUCTIONS
        if audit_only:
            return complain(msg)
        die(msg)
    else:
        print('%s was cloned correctly' % config.APP_TITLE)
    return 0

def setup_git(audit_only=False):
    report_step('git')
    exit_code, stdout, stderr = do('git --version', as_user=get_non_root_user())
    if exit_code:
        if audit_only:
            return complain('git is not installed')
        print('installing git.')
        do_or_die('%s -y install git' % get_installer(), 'Need git to be installed.')
        print('Try setup again, now that git is installed.')
        sys.exit(1)
    else:
        print('git is installed')
    return 0

def setup_git_python(audit_only=False):
    report_step('gitpython')
    try:
        import git as gitpython
        print('gitpython is installed.')
    except:
        if audit_only:
            return complain('gitpython is not installed')
        print('installing gitpython')
        do_or_die('easy_install gitpython', explanation='Need gitpython to be installed.')
    return 0

def setup_git_flow(audit_only=False):
    report_step('git-flow')
    exit_code, stdout, stderr = do('which git-flow')
    if exit_code:
        if audit_only:
            return complain('git-flow is not installed')
        print('installing git-flow')
        installer = get_installer()
        pkg = 'gitflow'
        if installer == 'apt-get':
            pkg = 'git-flow'
        do_or_die('%s -y install %s' % (installer, pkg), explanation='Need git-flow to be installed.')
    else:
        print('git-flow is installed')
    return 0

def setup_data():
    data_path = os.path.join(config.GMUX_ROOT, 'git-mux-data')
    git = None
    if not os.path.isdir(data_path):
        os.makedirs(
        git = gitpython.Git(data_path)
    else:

        os.path.join(data_path, '.git')):

def run(audit_only=False, nonroot_only=False):
    # Only run this as root. This is a backup check; it's also enforced
    # in gitmux.setup().
    if not audit_only and not nonroot_only:
        if os.getegid() != 0:
            die('Must run setup as root user.')
    exit_code = 0
    # Make sure we know who is the non-root user that's temporarily running
    # with elevated privileges, so we can run other commands as that user.
    get_non_root_user()
    try:
        exit_code += setup_git(audit_only)
        if not exit_code:
            exit_code += setup_git_python(audit_only)
            exit_code += setup_git_flow(audit_only)
        exit_code += setup_folder_layout(audit_only)
        exit_code += setup_app_cloned(audit_only)
        if not audit_only:
            # We need to do the rest of the setup as the unprivileged user
            # instead of as root. The easiest way to do this is to launch
            # another copy of ourselves using the linux runuser utility...

        operation = 'Setup'
        if audit_only:
            operation = 'Setup audit'
        outcome = 'succeeded'
        if exit_code:
            outcome = 'failed'
        print('\n%s %s.\n' % (operation, outcome))
        return exit_code
    except KeyboardInterrupt:
        ui.eprintc('\nSetup interrupted.\n', WARNING_COLOR)
        pass
    except SystemExit:
        pass
    except:
        traceback.print_exc()

if __name__ == '__main__':
    show_help = False
    audit = False
    nonroot = False
    if len(sys.argv) > 2:
        show_help = True
    else:
        if len(sys.argv) > 1:
            arg = sys.argv[1].lower()
            if arg.find('?') or arg.startswith('-') or arg.startswith('h'):
                show_help = True
            elif arg.find('audit') > -1:
                audit = True
            elif arg.find('non') > -1 and arg.find('root') > -1:
                nonroot = True
    if show_help:
        print('''
sudo python setup.py   -- run setup
python setup.py audit  -- verify that setup is correct
''')
        sys.exit(0)
    else:
        sys.exit(run(audit_only=audit, nonroot_only=nonroot))