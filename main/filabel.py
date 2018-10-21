import requests
import configparser
import click
import sys
import fnmatch

class StartApp:

    def __init__(self):
        self.token = ""
        self.labels = list()
        self.state = ""
        self.base = ""
        self.delete_old = True
        self.reposlugs = list()

    def load_config(self, conf_file_name):
        config = configparser.ConfigParser()
        try:
            with open(conf_file_name) as file:
                config.read_file(file)
            self.token = config['github']['token']
        except TypeError:
            return None
        except FileNotFoundError:
            return None

    def load_labels(self, conf_file_name):
        config = configparser.ConfigParser()
        try:
            with open(conf_file_name) as file:
                config.read_file(file)
            for label in config['labels']:
                labels = config['labels'][label].split('\n')
                for l in labels:
                    if l != "":
                        self.labels.append((l, label))
        except TypeError:
            return None
        except FileNotFoundError:
            return None

    def token_auth(self, req):
        req.headers['Authorization'] = f'token {self.token}'
        return req

    def send_requests(self):
        session = requests.Session()
        session.headers = {'User-Agent': 'Python'}
        session.auth = self.token_auth
        for repo in self.reposlugs:
            r = session.get('https://api.github.com/repos/' + repo + "/pulls")
            r.raise_for_status()
            pulls = r.json()
            for pull in pulls:
                print(pull['url'])
            print(r.json())
            print(r.status_code)

    def send_get_request(self, url):
        session = requests.Session()
        session.headers = {'User-Agent': 'Python'}
        session.auth = self.token_auth

        r = session.get(url)
        # r.raise_for_status()
        return r

    def send_post_request(self, url, data):
        session = requests.Session()
        session.headers = {'User-Agent': 'Python'}
        session.auth = self.token_auth

        r = session.post(url, data=data)
        r.raise_for_status()
        return r

    def validation(self, state, delete_old, base, config_auth, config_labels, reposlugs):
        if not state in ['open', 'closed', 'all']:
            pass
        else:
            self.state = state
        self.delete_old = delete_old
        self.base = base
        self.load_config(config_auth)
        if config_auth is None:
            print("Auth configuration not supplied!", file=sys.stderr)
            exit(1)
        elif self.token is None:
            print("Auth configuration not usable!", file=sys.stderr)
            exit(1)
        self.load_labels(config_labels)
        if config_labels is None:
            print("Labels configuration not supplied!", file=sys.stderr)
            exit(1)
        elif self.labels is None:
            print("Labels configuration not usable!", file=sys.stderr)
            exit(1)
        for repo in reposlugs:
            string = repo.split("/")
            if string[0] == "" or string[1] == "":
                print("Reposlug " + repo + " not valid!", file=sys.stderr)
                exit(1)
            self.reposlugs.append(repo)

    def label_pull_request(self, pull, repo, current_labels, temp_files):
        commit = pull['head']['sha']
        r = self.send_get_request('https://api.github.com/repos/' + repo + "/commits/" + commit)
        r_files = r.json()
        # Ensuring files
        for f in r_files['files']:
            # print((f['filename'], f['status']))
            # Comparing files with config file with labels
            for lab in self.labels:
                if fnmatch.fnmatch(f['filename'], lab[0]):
                    if not current_labels.__contains__(lab[1]):
                        current_labels.append(lab[1])
                    temp_files.append((lab[1], f['status']))

    def print_repo_ok(self, repo):
        repo_out = "REPO"
        repo_out = click.style(repo_out, bold=True)
        status = "OK"
        status = click.style(status, fg='green', bold=True)
        print("{} ".format(repo_out) + repo + " - {}".format(status))

    def print_pr_ok(self, pull):
        pr_out = "PR"
        pr_out = click.style(pr_out, bold=True)
        status = "OK"
        status = click.style(status, fg='green', bold=True)
        print("  {} ".format(pr_out) + pull['url'] + " - {}".format(status))

    def print_repo_fail(self, repo):
        repo_out = "REPO"
        repo_out = click.style(repo_out, bold=True)
        fail_out = "FAIL"
        fail_out = click.style(fail_out, bold=True, fg='red')
        print("{} ".format(repo_out) + repo + " - {}".format(fail_out))

    def print_pr_fail(self, pull):
        pr_out = "PR"
        pr_out = click.style(pr_out, bold=True)
        fail_out = "FAIL"
        fail_out = click.style(fail_out, bold=True, fg='red')
        print("  {} ".format(pr_out) + pull['url'] + " - {}".format(fail_out))

    def print_label(self, file):
        if file[1] == "added":
            string = "+ " + file[0]
            string = click.style(string, fg='green')
            print("    {}".format(string))
        elif file[1] == "modified":
            print("    = " + file[0])
        else:
            string = "- " + file[0]
            string = click.style(string, fg='red')
            print("    {}".format(string))

    def verify_repo(self, repo):
        # Test if repo exists
        r = self.send_get_request('https://api.github.com/repos/' + repo)
        if r.status_code == 200:
            self.print_repo_ok(repo)
            # Gets list of pull requests
            r = self.send_get_request('https://api.github.com/repos/' + repo + "/pulls")
            if r.json() != "[]":
                pulls = r.json()
                for pull in pulls:
                    # Ensure right state
                    if pull['state'] == self.state:
                        current_labels = list()
                        for l in pull['labels']:
                            current_labels.append(l['name'])
                        temp_files = list()
                        # If delete-old is set
                        if self.delete_old:
                            for l in self.labels:
                                if current_labels.__contains__(l[1]):
                                    current_labels.remove(l[1])
                        else:
                            # If the branch is set
                            if self.base is not None:
                                if pull['head']['ref'] == self.base:
                                    self.label_pull_request(pull, repo, current_labels, temp_files)
                                else:
                                    self.print_pr_fail(pull)
                                    return
                            else: # more branches - a branch is not set
                                self.label_pull_request(pull, repo, current_labels, temp_files)

                        string = str(current_labels)
                        string = string.replace("\'", "\"")
                        r = self.send_post_request('https://api.github.com/repos/' + repo + "/issues/" + str(pull['number']), "{\"labels\":" + string + "}")
                        if r.status_code == 200:
                            self.print_pr_ok(pull)
                            for file in temp_files:
                                self.print_label(file)
                        else:
                            self.print_pr_fail(pull)
        else:
            self.print_repo_fail(repo)

    def solve_repo(self, repo):
        self.verify_repo(repo)

    def solve_repos(self):
        for repo in self.reposlugs:
            self.solve_repo(repo)

@click.command()
@click.option('-s', '--state', default='open', metavar='[open|closed|all]', help='Filter pulls by state.  [default: open]')
@click.option('-d/-D', '--delete-old/--no-delete-old', default='True', metavar='', help='Delete labels that do not match anymore. [default: True]')
@click.option('-b', '--base', metavar='BRANCH', help='Filter pulls by base (PR target) branch name.')
@click.option('-a', '--config-auth', metavar='FILENAME', help='File with authorization configuration.')
@click.option('-l', '--config-labels', metavar='FILENAME', help='File with labels configuration.')
@click.argument('reposlugs', metavar='[REPOSLUGS]...', nargs=-1, required=True)
def command_line(state, delete_old, base, config_auth, config_labels, reposlugs):
    """CLI tool for filename-pattern-based labeling of GitHub PRs"""
    start = StartApp()
    start.validation(state, delete_old, base, config_auth, config_labels, reposlugs)
    start.solve_repos()
    # print(state)
    # print(delete_old)
    # print(base)
    # print(config_auth)
    # print(config_labels)
    # print(reposlugs)

if __name__ == "__main__":
    command_line()
