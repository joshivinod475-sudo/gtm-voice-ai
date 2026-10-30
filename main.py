"""GTM workflow for an AI voice assistant: Apollo -> score -> Claude -> Saleshandy.

  python main.py demo              try it with sample data, no keys needed
  python main.py run               real leads, saves a CSV, sends nothing
  python main.py run --live        real leads, also adds them to Saleshandy
  python main.py sequences         list your Saleshandy sequences
  python main.py fields            list your Saleshandy prospect field IDs
"""
import argparse
import json
import os
import sys

import yaml
from dotenv import load_dotenv

from gtm import pipeline
from gtm.saleshandy import Saleshandy


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["demo", "run", "sequences", "fields"])
    parser.add_argument("--live", action="store_true", help="actually push leads to Saleshandy")
    parser.add_argument("--limit", type=int, default=25, help="max people to enrich (Apollo credits)")
    parser.add_argument("--config", default="config/icp.yaml")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if args.command == "demo":
        pipeline.demo(config)
    elif args.command == "run":
        pipeline.run(config, live=args.live, limit=args.limit)
    else:
        client = Saleshandy(os.environ["SALESHANDY_API_KEY"])
        data = client.sequences() if args.command == "sequences" else client.fields()
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    sys.exit(main())
