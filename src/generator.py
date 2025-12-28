import argparse
import json
import os
import random
from enum import Enum

START_TAG = "START"

SELECT_DELIMITER_LEFT = "<<"
SELECT_DELIMITER_RIGHT = ">>"
SELECT_SWITCH_DELIMITER = '|'
VARIABLE_DELIMITER_LEFT = "[["
VARIABLE_DELIMITER_RIGHT = "]]"
VARIABLE_SET_DELIMITER = '='
DELIMITER_LENGTH = 2

MAX_GENERATOR_ITERATIONS = 50

class TagType (Enum):
    RANDOM = 1
    SWITCH = 2
    VAR_SET = 3
    VAR_GET = 4
    NONE = 0

def load_generator(path):
    with open(path) as generator_file:
        generator_json = json.load(generator_file)
    #print(generator)
    generator = generator_json["generator"]

    if "variables" not in generator:
        generator["variables"] = {}

    if START_TAG not in generator["tags"]:
        raise json.JSONDecodeError(f"{START_TAG} tag not found in generator file.")
    
    return generator

def find_next_tag(text: str) -> dict:
    first_SDL_index = text.find(SELECT_DELIMITER_LEFT)
    SDL_found = (first_SDL_index > -1)
    first_SDR_index = text.find(SELECT_DELIMITER_RIGHT)
    SDR_found = (first_SDR_index > -1)
    first_VDL_index = text.find(VARIABLE_DELIMITER_LEFT)
    VDL_found = (first_VDL_index > -1)
    first_VDR_index = text.find(VARIABLE_DELIMITER_RIGHT)
    VDR_found = (first_VDR_index > -1)

    # Catch unmatched delimiters
    if (SDL_found) and (not SDR_found):
        raise Exception(f'Unmatched {SELECT_DELIMITER_LEFT} delimiter.')
    if (not SDL_found) and (SDR_found):
        raise Exception(f'Unmatched {SELECT_DELIMITER_RIGHT} delimiter.')
    if (VDL_found) and (not VDR_found):
        raise Exception(f'Unmatched {VARIABLE_DELIMITER_LEFT} delimiter.')
    if (not VDL_found) and (VDR_found):
        raise Exception(f'Unmatched {VARIABLE_DELIMITER_RIGHT} delimiter.')

    # If there are no tags, return TagType.NONE. (We're done!)
    if not (SDL_found or VDL_found):
        return {'tag_type': TagType.NONE}
    
    # Now we know at least one of SDL or VDL is in the text and has a matching closure.
    # Determine which, or which is leftmost, then isolate the tag.
    is_select_tag = (SDL_found and ((not VDL_found) or (first_SDL_index < first_VDL_index)))
    if is_select_tag:
        tag_open_index = first_SDL_index
        tag_close_index = first_SDR_index + DELIMITER_LENGTH
    else:
        tag_open_index = first_VDL_index
        tag_close_index = first_VDR_index + DELIMITER_LENGTH
    before_text, after_text = (text[:tag_open_index], text[(tag_close_index):])
    tag_text = text[(tag_open_index + DELIMITER_LENGTH):(tag_close_index - DELIMITER_LENGTH)]

    if ((SELECT_DELIMITER_LEFT in tag_text) 
        or (SELECT_DELIMITER_RIGHT in tag_text)
        or (VARIABLE_DELIMITER_LEFT in tag_text) 
        or (VARIABLE_DELIMITER_RIGHT in tag_text)):
        raise Exception("Do not put delimiters inside tags. Use switch tags instead.")

    if is_select_tag:
        if SELECT_SWITCH_DELIMITER in tag_text:
            tag_type = TagType.SWITCH
        else:
            tag_type = TagType.RANDOM
    else:
        if VARIABLE_SET_DELIMITER in tag_text:
            tag_type = TagType.VAR_SET
        else:
            tag_type = TagType.VAR_GET

    return {"tag_type": tag_type, "before_text": before_text, "tag_text": tag_text, "after_text": after_text}

def generate(text, generator):
    iterations_remaining = MAX_GENERATOR_ITERATIONS

    while iterations_remaining > 0:
        iterations_remaining -= 1
        next_tag = find_next_tag(text)
        if next_tag["tag_type"] == TagType.NONE: #... then we're done!
            return text
        
        tag_text = next_tag["tag_text"].strip()
        match next_tag["tag_type"]:
            case TagType.RANDOM:
                if tag_text not in generator["tags"]:
                    return (f'ERROR: Tag {tag_text} not found.\nText: {text}')
                values = list(generator["tags"][tag_text].values())
                tag_replacement = random.choice(values)

            case TagType.VAR_SET:
                tag_replacement = ''
                variable, value = tuple(tag_text.split(VARIABLE_SET_DELIMITER, maxsplit=1))
                variable = variable.strip()
                value = value.strip()
                value = value.strip("'\"")
                generator["variables"][variable] = value

            case TagType.VAR_GET:
                if tag_text not in generator["variables"]:
                    return (f'ERROR: Variable {tag_text} used before setting.\nText: {text}')
                tag_replacement = generator["variables"][tag_text]

            case TagType.SWITCH:
                tag, variable = tuple(tag_text.split(SELECT_SWITCH_DELIMITER, maxsplit=1))
                tag = tag.strip()
                variable = variable.strip()

                if tag not in generator["tags"]:
                    return (f'ERROR: Tag {tag_text} not found.\nText: {text}')
                if variable not in generator["variables"]:
                    return (f'ERROR: Variable {tag_text} used before setting.\nText: {text}')
                
                key = generator["variables"][variable]
                if key not in generator["tags"][tag]:
                    return (f'ERROR: Invalid key {key} into tag {tag}.\nText: {text}')
                tag_replacement = generator["tags"][tag][key]

            case _:
                raise NotImplementedError()
        text = f"{next_tag["before_text"]}{tag_replacement}{next_tag["after_text"]}"

    if iterations_remaining == 0:
        return ('ERROR: Maximum iterations for generator reached. Check generation JSON for loops.\n'
                + f'Text: {text}')

def main ():
    parser = argparse.ArgumentParser(description="Random name generator using JSON generator files")
    parser.add_argument("generator_file", type=str, help="The JSON file defining the generator")
    parser.add_argument("--number", '-n', type=int, default=1, help="The number of generations to return")
    args = parser.parse_args()

    generator = load_generator(args.generator_file)
    
    for _ in range(args.number):
        print(generate(f'{SELECT_DELIMITER_LEFT}{START_TAG}{SELECT_DELIMITER_RIGHT}', generator))

if __name__ == "__main__":
#    try:
        main()
#    except Exception(e):
#        print(e)