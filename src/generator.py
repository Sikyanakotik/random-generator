import argparse
import json
import os

def main ():
    parser = argparse.ArgumentParser(description="Random name generator using JSON generator files")
    parser.add_argument("generator_file", type=str, help="The JSON file defining the generator")
    parser.add_argument("--number", '-n', type=int, help="The number of generations to return")
    args = parser.parse_args()

    with open(args.generator_file) as generator_file:
        generator = json.load(generator_file)
    print(generator)
    

if __name__ == "__main__":
#    try:
        main()
#    except Exception(e):
#        print(e)