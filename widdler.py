#!/usr/bin/env python
import argparse
import sys
import os
import src.config as c
from src.Cromwell import Cromwell
from src.Validator import Validator
import logging
import getpass
import json
import zipfile


def is_valid(path):
    """
    Integrates with ArgParse to validate a file path.
    :param path: Path to a file.
    :return: The path if it exists, otherwise raises an error.
    """
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(("{} is not a valid file path.\n".format(path)))
    else:
        return path


def is_valid_zip(path):
    """
    Integrates with argparse to validate a file path and verify that the file is a zip file.
    :param path: Path to a file.
    :return: The path if it exists and is a zip file, otherwise raises an error.
    """
    is_valid(path)
    if not zipfile.is_zipfile(path):
        raise argparse.ArgumentTypeError("{} is not a valid zip file.\n".format(path))
    else:
        return path


def call_run(args):
    """
    Optionally validates inputs and starts a workflow on the Cromwell execution engine if validation passes. Validator
    returns an empty list if valid, otherwise, a list of errors discovered.
    :param args: run subparser arguments.
    :return: JSON response with Cromwell workflow ID.
    """
    validator = Validator(wdl=args.wdl, json=args.json)
    if args.validate:
        result = validator.validate_json()
        if len(result) != 0:
            print("{} input file contains the following errors:\n{}".format(args.json, "\n".join(result)))
            sys.exit(-1)
    cromwell = Cromwell(host=args.server)
    return cromwell.jstart_workflow(wdl_file=args.wdl, json_file=args.json, dependencies=args.dependencies)


def call_query(args):
    """
    Get various types of data on a particular workflow ID.
    :param args:  query subparser arguments.
    :return: A list of json responses based on queries selected by the user.
    """
    cromwell = Cromwell(host=args.server)
    responses = []
    if args.status:
        status = cromwell.query_status(args.workflow_id)
        responses.append(status)
    if args.metadata:
        metadata = cromwell.query_metadata(args.workflow_id)
        responses.append(metadata)
    if args.logs:
        logs = cromwell.query_logs(args.workflow_id)
        responses.append(logs)
    return responses


def call_abort(args):
    """
    Abort a workflow with a given workflow id.
    :param args: abort subparser args.
    :return: JSON containing abort response.
    """
    cromwell = Cromwell(host=args.server)
    return cromwell.stop_workflow(args.workflow_id)

parser = argparse.ArgumentParser(
    description='Description: A tool for executing and monitoring WDLs to Cromwell instances.',
    usage='widdler.py <run | query | abort> [<args>]',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

sub = parser.add_subparsers()

run = sub.add_parser(name='run',
                     description='Submit a WDL & JSON for execution on a Cromwell VM.',
                     usage='widdler.py run <wdl file> <json file> [<args>]',
                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

run.add_argument('wdl', action='store', type=is_valid, help='Path to the WDL to be executed.')
run.add_argument('json', action='store', type=is_valid, help='Path the json inputs file.')
run.add_argument('-v', '--validate', action='store_true', default=False,
                 help='Validate WDL inputs in json file.')
run.add_argument('-d', '--dependencies', action='store', default=None, type=is_valid_zip,
                 help='A zip file containing one or more WDL files that the main WDL imports.')
run.add_argument('-S', '--server', action='store', required=True, type=str, choices=c.servers,
                 help='Choose a cromwell server from {}'.format(c.servers))
run.set_defaults(func=call_run)

query = sub.add_parser(name='query',
                       description='Query cromwell for information on the submitted workflow.',
                       usage='widdler.py query <workflow id> [<args>]',
                       formatter_class=argparse.ArgumentDefaultsHelpFormatter)
query.add_argument('workflow_id', action='store', help='workflow id for workflow execution of interest.')
query.add_argument('-s', '--status', action='store_true', default=False, help='Print status for workflow to stdout')
query.add_argument('-m', '--metadata', action='store_true', default=False, help='Print metadata for workflow to stdout')
query.add_argument('-l', '--logs', action='store_true', default=False, help='Print logs for workflow to stdout')
query.add_argument('-S', '--server', action='store', required=True, type=str, choices=c.servers,
                   help='Choose a cromwell server from {}'.format(c.servers))
query.set_defaults(func=call_query)

validate = sub.add_parser(name='validate',
                          description='Validate (but do not run) a json for a specific WDL file.',
                          usage='widdler.py validate <wdl_file> <json_file>',
                          formatter_class=argparse.ArgumentDefaultsHelpFormatter)

validate.add_argument('wdl', action='store', type=is_valid, help='Path to the WDL to be executed.')
validate.add_argument('json', action='store', type=is_valid, help='Path the json inputs file.')


abort = sub.add_parser(name='abort',
                       description='Abort a submitted workflow.',
                       usage='widdler.py abort <workflow id>',
                       formatter_class=argparse.ArgumentDefaultsHelpFormatter)
abort.add_argument('workflow_id', action='store', help='workflow id of workflow to abort.')
abort.add_argument('-S', '--server', action='store', required=True, type=str, choices=c.servers,
                   help='Choose a cromwell server from {}'.format(c.servers))
abort.set_defaults(func=call_abort)

args = parser.parse_args()


def main():
    logger = logging.getLogger('widdler')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(os.path.join(c.log_dir, 'widdler.log'))
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # create formatter and add it to the handlers
    user = getpass.getuser()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info("\n-------------New Widdler Execution by {}-------------".format(user))
    logger.info("Parameters chosen: {}".format(vars(args)))
    result = args.func(args)
    logger.info("Result: {}".format(result))
    print(json.dumps(result, indent=4))
    logger.info("\n-------------End Widdler Execution by {}-------------".format(user))

if __name__ == "__main__":
    sys.exit(main())

