from js import document
import generator # src/generator.py


START_TAG = "START"

SELECT_DELIMITER_LEFT = "<<"
SELECT_DELIMITER_RIGHT = ">>"

def generate_once(event=None):
    gen = generator.load_generator("data/hello_world.json")
    text = f"{SELECT_DELIMITER_LEFT}{START_TAG}{SELECT_DELIMITER_RIGHT}"
    result = generator.generate(text, gen)

    output_div = document.querySelector("#output")
    output_div.innerText = result

# Hook up the button after the page loads
btn = document.querySelector("#generate-btn")
btn.addEventListener("click", generate_once)