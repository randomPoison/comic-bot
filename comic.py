from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from typing import Union, List, Optional
import argparse
import json
import random
import requests
import shutil
import os

# Define a constant for the comics directory path.
COMICS_DIR = "static/comics"

SCRIPT = """
4:47 PM <missingno> eating a banh mi in GGP watching the ppl play baseball…what is this feeling I remember having? omg I’m happy ; u ;
4:48 PM <missingno> randomPoison: did u say 6:30 for your place?
4:49 PM <randomPoison> invite says 6pm, but feel free to show up whenever
4:49 PM <skalnik> but the lore says randomPoison hates france, loves spain
4:50 PM <randomPoison> i dont even hate france }:|
4:50 PM <randomPoison> i just had more fun in spain
"""


CHARACTERS = {
    "blah64": "A futuristic fighter pilot in an orange jumpsuit and helmet.",
    "drewzar": "A small, simple grey robot with teal eyes.",
    "geckomuerto": "An anthropomorphic lizard wearing a business suit and smoking a cigarette.",
    "hayt": "A tall, lanky red robot",
    "malk": "A mushroom with a long grey moustache and wearing a wizard hat.",
    "metacentricheight": "A sub sandwich wearing a ski mask.",
    "missingno": "An ominous floating rectangle with a pixellated distortion effect.",
    "muta_work": "A cat wearing a black hoodie with a cat face on it.",
    "philza": "A rockstar with sunglasses and long blonde hair, holding a black and white guitar.",
    "randompoison": "A normal cat floating in the air.",
    "shadypkg": "A tall, buff, shirtless man with a cardboard box on his head.",
    "skalnik": "A ham with a human face on it.",
}


LOCATIONS = {
    "beach": "A sandy beach.",
    "clouds": "High in the sky amongst the clouds",
    "diner": "A greasy spoon diner with pies and coffee.",
    "forest": "A dense forest full of large deciduous trees.",
    "mountain": "The top of a snowy mountain.",
    "office": "A crowded office full of paper and computer monitors.",
    "pizzeria": "A pizza restaurant with a wood fired oven in the background.",
    "playground": "A playground with rowdy children playing in the background.",
    "rooftop": "The rooftop of a tall brick building.",
    "whales": "Under the sea near a pod of whales.",
}


def generate_panel(client: OpenAI, p: int, dialog_lines: List[str], speakers: List[str], location: List[str]):
    i = p - 1

    location_description = LOCATIONS[location]

    panel_speakers = [speakers[2 * i], speakers[2 * i + 1]]
    panel_dialog = [dialog_lines[2 * i], dialog_lines[2 * i + 1]]

    # Generate character descriptions for our speaker(s).
    # ---------------------------------------------------

    # Create a mapping of unique speakers to their dialogs.
    speaker_dialog_map = {}
    for speaker, dialog in zip(panel_speakers, panel_dialog):
        if speaker in speaker_dialog_map:
            speaker_dialog_map[speaker].append(dialog)
        else:
            speaker_dialog_map[speaker] = [dialog]

    # Loop over unique speakers and their dialogs, generating a list of
    # speaker descriptions (their actions and expressions in the panel).
    speaker_descriptions = []
    for speaker, dialogs in speaker_dialog_map.items():
        # Combine the speaker's dialogs into one string.
        combined_dialog = "\n".join(dialogs)

        system = """
        You will be given one or two lines of dialog for a character in a
        panel of a comic. Based on the dialog, briefly describe what the
        character is doing in the panel. Describe both their facial
        expression and their body language. Keep the descriptions concise
        and limit it to a couple of short sentences.

        Example prompt:
        ```
        <alice>: Today has been great, i'm having such a good time!
        <alice>: And this cake is great!
        ```

        Example output:
        ```
        Alice holds a slice of cake on a paper plate. She smiles brightly, a
        large grin spreading across her face.
        ```
        """

        speaker_action = send_prompts(
            client, combined_dialog, system=system)

        speaker_appearance = f"{speaker} is {CHARACTERS[speaker]}"
        speaker_description = speaker_appearance + "\n" + speaker_action
        speaker_descriptions.append(speaker_description)

    verbose_descriptions = "\n\n".join(speaker_descriptions)

    # Remove character names from panel description.
    # ----------------------------------------------

    system = """
    You will be given a few sentences describing a scene with one or two
    characters in it, stating their appearances, expressions, and actions.

    Rewrite the scene to remove the character names and only refer to the
    characters by description.
    """

    simplified_descriptions = send_prompts(
        client, verbose_descriptions, system=system)

    # Append location information.
    final_description = f"""
    {simplified_descriptions}
    
    They stand in {location_description}
    """

    # Draw the panel.
    # ---------------

    print(f"Final panel {p} prompt:", final_description)

    # TODO: Handle potential failure here.
    response = client.images.generate(
        model="dall-e-3",
        prompt=final_description,
        size="1024x1792",
        quality="hd",
        style="vivid",
        n=1,
    )

    image_url = response.data[0].url
    print(f"\nPanel {p} URL: {image_url}")

    # Download the panel.
    response = requests.get(image_url)
    file_name = f"panel_{p}.png"
    with open(file_name, "wb") as file:
        file.write(response.content)

    print(f"Saved file to {file_name}")


def send_prompts(
    client: OpenAI,
    messages: Union[str, List[str]],
    system: Optional[str] = None,
    model: str = "gpt-4o",
) -> str:
    """
    Sends prompts to an OpenAI chat completion API and returns the response.

    Args:
        client (OpenAI): The OpenAI client instance.
        messages (Union[str, List[str]]): A string or a list of strings representing user messages.
        system (Optional[str], optional): Optional system message to include at the beginning. Defaults to None.
        model (str, optional): The model name to use for generating the completion. Defaults to "gpt-4o".

    Returns:
        str: The response content from the OpenAI API.

    Raises:
        TypeError: If 'messages' is not a string or a list of strings.
        ValueError: If 'messages' is a list but contains non-string items.
    """
    prompts = []

    # Include the system message if provided.
    if system:
        prompts.append({"role": "system", "content": system})

    # Normalize messages to a list of strings.
    if isinstance(messages, str):
        messages = [messages]
    elif isinstance(messages, list):
        if not all(isinstance(m, str) for m in messages):
            raise ValueError("all items in 'messages' list must be strings.")
    else:
        raise TypeError("'messages' must be a string or a list of strings.")

    # Add user messages to prompts.
    prompts.extend({"role": "user", "content": m} for m in messages)

    # Debug: print the prompts.
    print("Sending prompts:", json.dumps(prompts, indent=4))

    # Send the prompts to OpenAI API.
    completion = client.chat.completions.create(
        model=model,
        messages=prompts
    )

    # Extract and return the response content.
    response = completion.choices[0].message.content
    print("Response:", response)

    return response


def construct_comic(dialog_lines):
    """
    Constructs the final comic from the generated panels and parsed chat logs.
    """

    # Combine the 3 panels into a single image.
    # -----------------------------------------

    # Load images for each panel.
    panel_1 = Image.open('panel_1.png')
    panel_2 = Image.open('panel_2.png')
    panel_3 = Image.open('panel_3.png')

    # Crop the images to 1024x1024 pixels, starting at an offset from the top.
    crop_box = (0, 200, 1024, 200 + 1024)
    panel_1 = panel_1.crop(crop_box)
    panel_2 = panel_2.crop(crop_box)
    panel_3 = panel_3.crop(crop_box)

    # Define the dimensions of the comic.
    panel_width = 1024
    padding = 25

    # Calculate the width and height of the final image
    total_width = panel_width * 3 + padding * 4
    total_height = panel_width + padding * 2

    # Create a new blank image with a white background.
    comic = Image.new('RGB', (total_width, total_height), (255, 255, 255))

    # Paste the images into the new image with the appropriate padding
    for index, panel in enumerate([panel_1, panel_2, panel_3]):
        offset = panel_width * index + padding * (index + 1)
        comic.paste(panel, (offset, padding))

    # Add lines of dialog to the comic.
    # ---------------------------------

    # Setup comic for having text drawn into it.
    font = ImageFont.truetype("FiraCode-Bold.ttf", 38)
    draw = ImageDraw.Draw(comic)

    # Iterate over the panels and add the dialog.
    for i in range(3):
        first_line = dialog_lines[2 * i]
        second_line = dialog_lines[2 * i + 1]

        # Wrap lines of dialog within a max width.
        first_line = wrap_text(first_line, font, 900, draw)
        second_line = wrap_text(second_line, font, 900, draw)

        # Calculate anchors for the text boxes.
        left_edge = i * panel_width + padding * (i + 1)
        right_edge = left_edge + panel_width

        # Draw the first text box (left-aligned).
        first_line_position = (left_edge, padding)
        _, first_text_height = draw_text_box(
            draw, first_line, font, first_line_position, padding=10
        )

        # Draw the second text box (right-aligned).
        _, _, text_width, _ = draw.multiline_textbbox(
            (0, 0), second_line, font=font)
        second_line_position = (
            right_edge - text_width, first_line_position[1] + first_text_height + padding)
        draw_text_box(
            draw, second_line, font, second_line_position, padding=10)

    # Downscale the image by half and save it to disk.
    comic = comic.resize((total_width // 2, total_height // 2))
    comic.save('comic_strip.png')


def draw_text_box(draw, text, font, position, padding=0):
    """
    Draws text on an image with a background rectangle.

    :param draw: ImageDraw object.
    :param text: The text to draw (should be already wrapped).
    :param font: The font to use.
    :param position: Tuple (x, y) for the top-left position.
    :param padding: Padding inside the rectangle.
    :return: width and height of the drawn text box (including padding)
    """
    # Calculate the text bounding box.
    _, _, text_width, text_height = draw.multiline_textbbox(
        (0, 0), text, font=font)

    # Adjust rectangle for padding.
    rect_start = (position[0] - padding, position[1] - padding)
    rect_end = (position[0] + text_width + padding,
                position[1] + text_height + padding)

    # Draw the text box and text.
    draw.rectangle([rect_start, rect_end], fill=(255, 255, 255))
    draw.multiline_text(position, text, font=font, fill=(0, 0, 0))

    # Return the size of the text box including padding.
    total_width = text_width + 2 * padding
    total_height = text_height + 2 * padding
    return total_width, total_height


def wrap_text(text, font, max_width, draw):
    """
    Wrap text to fit within a specified width.

    :param text: The text to be wrapped.
    :param font: The font used to measure the text size.
    :param max_width: The maximum width allowed for each line.
    :param draw: The ImageDraw object used to measure text size.
    :return: A list of wrapped lines.
    """
    words = text.split(' ')
    wrapped_lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (word + " ")
        text_width = draw.textlength(test_line, font=font)

        if text_width <= max_width:
            current_line = test_line
        else:
            wrapped_lines.append(current_line.strip())
            current_line = word + " "

    if current_line:
        wrapped_lines.append(current_line.strip())

    return "\n".join(wrapped_lines)


def normalize_nick(nick: str) -> str:
    """
    Normalizes speaker nicknames to all lowercase, stripping moderator
    identifiers, and normalizing the nick used for people who've had multiple
    nicks.

    Returns: The normalized nickname.
    """

    # Normalize names to all lowercase.
    nick = nick.lower()

    # Strip @ off the front for mods.
    if nick.startswith("@"):
        nick = nick[1:]

    return nick


def publish_comic():
    """
    Copies the generated comic_strip.png into the static/comics directory
    and assigns it a unique name based on the number of existing comics.
    """
    # Assert that the comics directory exists.
    assert os.path.exists(COMICS_DIR), f"Comics dir ({COMICS_DIR}) does not exist"

    # Count existing comics to determine the new comic's name.
    existing_comics = [f for f in os.listdir(COMICS_DIR) if f.endswith('.png')]
    new_comic_id = len(existing_comics) + 1
    new_comic_name = f"comic-{new_comic_id:03}.png"

    # Copy the comic_strip.png to the static/comics directory.
    shutil.copy("comic_strip.png", os.path.join(COMICS_DIR, new_comic_name))
    print(f"Published comic as {new_comic_name}")


def main():
    parser = argparse.ArgumentParser(description='Generates AI slop.')

    parser.add_argument(
        '-p', '--panel',
        type=int,
        choices=[1, 2, 3],
        help='A single panel to generate. Defaults to generating all three if not specified.'
    )

    parser.add_argument(
        '-l', '--location',
        type=str,
        help='The location to use for the generated panel. Uses a random location if not specified.',
    )

    parser.add_argument(
        '--publish',
        action='store_true',
        help='Publish the generated comic_strip.png to the static/comics directory.'
    )

    args = parser.parse_args()

    if args.publish:
        publish_comic()
        return

    # Process the raw chat logs into a list of lines of dialog, stripping off
    # the time prefix from each line (assume the time format is always `hh:mm AM/PM `).
    lines = SCRIPT.strip().split("\n")
    assert len(lines) == 6, "SCRIPT must contain exactly 6 lines of dialog."
    dialog_lines = [line.strip().split(' ', 2)[2] for line in lines]

    # Extract the speakers for each line.
    speakers = [normalize_nick(line.split('>')[0][1:])
                for line in dialog_lines]

    client = OpenAI()

    if args.location:
        if not args.location in LOCATIONS:
            print(
                f"Invalid location: '{args.location}'. Must be one of: {', '.join(LOCATIONS.keys())}")
            exit(1)
        location = args.location
    else:
        # Decide a location for the comic.
        location = random.choice(list(LOCATIONS.keys()))
        print("Location:", location)

    if args.panel:
        generate_panel(client, args.panel, dialog_lines, speakers, location)
    else:
        # Generate all 3 panels.
        for p in range(1, 4):
            generate_panel(client, p, dialog_lines, speakers, location)

    construct_comic(dialog_lines)


if __name__ == "__main__":
    main()
