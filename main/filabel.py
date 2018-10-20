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
                self.labels.append(config['labels'][label])
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

    def send_request(self, url):
        session = requests.Session()
        session.headers = {'User-Agent': 'Python'}
        session.auth = self.token_auth

        r = session.get(url)
        r.raise_for_status()
        return r

    def validation(self, state, base, config_auth, config_labels, reposlugs):
        if not state in ['open', 'closed', 'all']:
            pass
        else:
            self.state = state
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
        # print(state)
        # print(base)
        # print(token)
        # for label in self.labels:
        #     print(label)
        # print(reposlugs)

    def verify_repo(self, repo):
        r = self.send_request('https://api.github.com/repos/' + repo)
        if r.status_code == 200:
            print("OK")
            r = self.send_request('https://api.github.com/repos/' + repo + "/pulls")
            if r.json() != "[]":
                data = r.json()
                for pull in data:
                    if pull['state'] == self.state:
                        if self.base != "":
                            pass
                        else:
                            pass
        else:
            print("FAIL")

    def solve_repo(self, repo):
        self.verify_repo(repo)

    def solve_repos(self):
        for repo in self.reposlugs:
            self.solve_repo(repo)

@click.command()
@click.option('-s', '--state', default='open', metavar='[open|closed|all]', help='Filter pulls by state.  [default: open]')
@click.option('-d/-D', '--delete-old/--no-delete-old', metavar='', help='Delete labels that do not match anymore. [default: True]')
@click.option('-b', '--base', metavar='BRANCH', help='Filter pulls by base (PR target) branch name.')
@click.option('-a', '--config-auth', metavar='FILENAME', help='File with authorization configuration.')
@click.option('-l', '--config-labels', metavar='FILENAME', help='File with labels configuration.')
@click.argument('reposlugs', metavar='[REPOSLUGS]...', nargs=-1, required=True)
def command_line(state, delete_old, base, config_auth, config_labels, reposlugs):
    """CLI tool for filename-pattern-based labeling of GitHub PRs"""
    start = StartApp()
    start.validation(state, base, config_auth, config_labels, reposlugs)
    start.solve_repos()
    # print(state)
    # print(delete_old)
    # print(base)
    # print(config_auth)
    # print(config_labels)
    # print(reposlugs)

if __name__ == "__main__":
    command_line()
