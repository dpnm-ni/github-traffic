import argparse
import configparser
import datetime
import errno
import json
import logging
import os

import dateutil.parser
import requests

logfmt = logging.Formatter("%(message)s")

log = logging.Logger("github")
ch = logging.StreamHandler()
ch.setFormatter(logfmt)
log.setLevel(logging.INFO)
log.addHandler(ch)

config = configparser.ConfigParser()

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def save(date, dirname, data):
    mkdir_p(dirname)
    fname = os.path.join(dirname, "%s.json" % date.isoformat())
    with open(fname, "w") as fp:
        json.dump(data, fp)


def save_month(date, dataname, dirname, data):
    log.info("%s by month" % dataname)
    mkdir_p(dirname)
    # Data for the last two weeks could contain information for two months

    data = data[dataname]
    # Remove the most recent day because it's today
    data = sorted(data, key=lambda x: x["timestamp"])
    data = data[:-1]

    months = set()
    for d in data:
        date = dateutil.parser.parse(d["timestamp"])
        months.add(date.strftime("%Y-%m"))

    for m in list(months):
        log.debug(m)
        fname = os.path.join(dirname, "%s.json" % (m,))
        try:
            this_month = json.load(open(fname, "r"))
        except FileNotFoundError:
            this_month = []

        data_for_this_month = set([d["timestamp"] for d in this_month])

        for d in data:
            date = dateutil.parser.parse(d["timestamp"])
            month = date.strftime("%Y-%m")
            if month == m and d["timestamp"] not in data_for_this_month:
                this_month.append(d)

        json.dump(this_month, open(fname, "w"))


def query(url):
    token = config["github"]["token"]
    url = os.path.join("https://api.github.com/", url)
    r = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"}, params={"access_token": token})
    r.raise_for_status()
    return r.json()


def referrers(repository):
    log.info("Referrers")
    owner = config["github"]["owner"]
    return query("repos/{}/{}/traffic/popular/referrers".format(owner, repository))


def paths(repository):
    log.info("Popular paths")
    owner = config["github"]["owner"]
    return query("repos/{}/{}/traffic/popular/paths".format(owner, repository))


def views(repository):
    log.info("Page views")
    owner = config["github"]["owner"]
    return query("repos/{}/{}/traffic/views".format(owner, repository))


def clones(repository):
    log.info("Clones")
    owner = config["github"]["owner"]
    return query("repos/{}/{}/traffic/clones".format(owner, repository))


def main():
    parser = argparse.ArgumentParser(description="Download access information about a GitHub repository")
    parser.add_argument("-c", metavar="config", help="config file location", required=True)
    parser.add_argument("-o", metavar="output", help="directory to write results to", required=True)

    args = parser.parse_args()

    config.read(args.c)
    log.info("Getting information for repository %s" % config["github"]["repository"])

    today = datetime.date.today()

    repositories = config["github"]["repository"].split(",")
    for repository in repositories:
        log.info("Fetching statistics from repo: %s" % repository)
        save(today, os.path.join(args.o, repository, "referrers"), referrers(repository))
        save(today, os.path.join(args.o, repository, "paths"), paths(repository))
        v = views(repository)
        save(today, os.path.join(args.o, repository, "views"), v)
        c = clones(repository)
        save(today, os.path.join(args.o, repository, "clones"), c)

    # For views + clones, split by month, fill in type_month.json, making sure not to duplicate
    #save_month(today, "views", os.path.join(args.o, "views"), v)
    #save_month(today, "clones", os.path.join(args.o, "clones"), c)

if __name__ == "__main__":
    main()
