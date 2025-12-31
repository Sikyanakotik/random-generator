from js import document, fetch
from pyodide.ffi import create_proxy
import json
import random
import copy
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

async def load_generator(path):
    # Fetch JSON over HTTP
    resp = await fetch(path)
    text = await resp.text()
    generator_json = json.loads(text)

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
        raise Exception(f'Unmatched {SELECT_DELIMITER_LEFT} delimiter.\ntext = {text}')
    if (not SDL_found) and (SDR_found):
        raise Exception(f'Unmatched {SELECT_DELIMITER_RIGHT} delimiter.\ntext = {text}')
    if (VDL_found) and (not VDR_found):
        raise Exception(f'Unmatched {VARIABLE_DELIMITER_LEFT} delimiter.\ntext = {text}')
    if (not VDL_found) and (VDR_found):
        raise Exception(f'Unmatched {VARIABLE_DELIMITER_RIGHT} delimiter.\ntext = {text}')

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
        raise Exception(f"Do not put delimiters inside tags. Use switch tags instead.\ntag_text = {tag_text}")

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

def generate(text, gen):
    generator = copy.deepcopy(gen)
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
                    if "default" in generator["tags"][tag]:
                        key = "default"
                    else:
                        return (f'ERROR: Invalid key {key} into tag {tag}.\nText: {text}')
                tag_replacement = generator["tags"][tag][key]

            case _:
                raise NotImplementedError()
        text = f"{next_tag["before_text"]}{tag_replacement}{next_tag["after_text"]}"

    if iterations_remaining == 0:
        return ('ERROR: Maximum iterations for generator reached. Check generation JSON for loops.\n'
                + f'Text: {text}')


#async def generate_once(event=None):
#    generator_path = document.querySelector("#generator-select").value
#    gen = await load_generator(generator_path)
#    text = f"{SELECT_DELIMITER_LEFT}{START_TAG}{SELECT_DELIMITER_RIGHT}"
#    result = generate(text, gen)
#
#    output_div = document.querySelector("#output")
#    output_div.innerText = result

async def generate_web(event=None):
    generator_path = document.querySelector("#generator-select").value
    generation_count = int(document.querySelector("#gencount-select").value)
    generator = await load_generator(generator_path)
    output = ""

    for _ in range(generation_count):
        text = f"{SELECT_DELIMITER_LEFT}{START_TAG}{SELECT_DELIMITER_RIGHT}"
        result = generate(text, generator)
        output += f"\n{result}"
    output = output[1:] # Remove the initial '\n'.

    output_div = document.querySelector("#output")
    output_div.innerText = output


# Hook up page elements after the page loads
generate_web_proxy = create_proxy(generate_web)
btn = document.querySelector("#generate-btn")
btn.addEventListener("click", generate_web_proxy)