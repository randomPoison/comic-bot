from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from typing import Union, List, Optional
import argparse
import json
import random
import requests
import shutil
import os
import unicodedata


COMICS_DIR = "static/comics"
"""Directory where comics are published."""


CHARACTERS = {
    "arbo": "A robot with a beard, dressed in a blue vest, smoking a cigarette.",
    "blah64": "A futuristic fighter pilot in an orange jumpsuit and helmet.",
    "cheerycherries": "A pair of cartoon cherries with connected stems, grinning happily.",
    "drewzar": "A small, simple grey robot with teal eyes.",
    "dusya": "A smiling rainbow waving a trans pride flag.",
    "geckomuerto": "An anthropomorphic lizard wearing a business suit and smoking a cigarette.",
    "hayt": "A tall, lanky red robot",
    "laura": "An anime schoolgirl with short yellow hair, wearing a white school uniform.",
    "malk": "A mushroom with a long grey moustache and wearing a wizard hat.",
    "metacentricheight": "A sub sandwich wearing a ski mask.",
    "missingno": "An ominous floating rectangle with a pixellated distortion effect.",
    "muta_work": "A cat wearing a black hoodie with a cat face on it.",
    "philza": "A rockstar with sunglasses and long blonde hair, holding a black and white guitar.",
    "randompoison": "A normal dog floating in the air.",
    "shadypkg": "A tall, buff, shirtless man with a cardboard box on his head.",
    "skalnik": "A ham with a human face on it.",
    "vilmibm": "A blue woman with blue hair, wearing blue shutter glasses.",
    "zsunsetdan": "A sun with a smiling baby face.",
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


def generate_panel(client: OpenAI, p: int, dialog_lines: List[str], speakers: List[str], location: str, max_tries: int = 3):
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

    # Try to generate the image with retry logic for content policy violations
    image_url = None
    for attempt in range(1, max_tries + 1):
        try:
            print(f"Attempting to generate panel {p} (attempt {attempt}/{max_tries})")

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
            break  # Success, exit the retry loop

        except Exception as e:
            print(f"Panel {p} generation failed on attempt {attempt}/{max_tries}: {e}")

            if attempt == max_tries:
                print(f"Failed to generate panel {p} after {max_tries} attempts. Giving up.")
                raise  # Re-raise the exception after all attempts are exhausted

    # Download the panel.
    if image_url:
        response = requests.get(image_url)
        file_name = f"panel_{p}.png"
        with open(file_name, "wb") as file:
            file.write(response.content)

        print(f"Saved file to {file_name}")
    else:
        raise RuntimeError(f"Failed to generate panel {p}: no image URL obtained")


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


def construct_comic(dialog_lines, rotate_panels=None, panel_shifts=None):
    """
    Constructs the final comic from the generated panels and parsed chat logs.

    Args:
        dialog_lines: List of dialog lines for the comic
        rotate_panels: List of panel numbers (1-based) to rotate 90 degrees clockwise
        panel_shifts: List of tuples (panel_id, offset) for shifting crop positions
    """
    if rotate_panels is None:
        rotate_panels = []
    if panel_shifts is None:
        panel_shifts = []

    # Combine the 3 panels into a single image.
    # -----------------------------------------

    # Load images for each panel.
    panels = [Image.open('panel_1.png'), Image.open('panel_2.png'), Image.open('panel_3.png')]

    # Create a dictionary for quick lookup of panel shifts
    shift_dict = {panel_id: offset for panel_id, offset in panel_shifts}

    # Crop the images to 1024x1024 pixels if they are portrait (1024x1792).
    default_crop_box = (0, 200, 1024, 200 + 1024)
    for index, panel in enumerate(panels):
        if panel.size == (1024, 1792):
            panel_id = index + 1  # Convert to 1-based panel ID

            # Check if this panel has a shift offset and apply it if so.
            if panel_id in shift_dict:
                shift_offset = shift_dict[panel_id]

                y_start = 200 + shift_offset
                y_end = y_start + 1024

                # Clamp the crop box to stay within image bounds
                y_start = max(0, min(y_start, 1792 - 1024))
                y_end = y_start + 1024

                crop_box = (0, y_start, 1024, y_end)
            else:
                crop_box = default_crop_box

            panels[index] = panel.crop(crop_box)

    # Rotate specified panels 90 degrees clockwise (after cropping).
    for panel_number in rotate_panels:
        panel_index = panel_number - 1  # Convert to 0-based index
        panels[panel_index] = panels[panel_index].rotate(-90, expand=True)

    # Define the dimensions of the comic.
    panel_width = 1024
    padding = 25

    # Calculate the width and height of the final image
    total_width = panel_width * 3 + padding * 4
    total_height = panel_width + padding * 2

    # Create a new blank image with a white background.
    comic = Image.new('RGB', (total_width, total_height), (255, 255, 255))

    # Paste the images into the new image with the appropriate padding
    for index, panel in enumerate(panels):
        offset = panel_width * index + padding * (index + 1)
        comic.paste(panel, (offset, padding))

    # Add lines of dialog to the comic.
    # ---------------------------------

    # Setup comic for having text drawn into it.
    regular_font = ImageFont.truetype("FiraCode-Bold.ttf", 38)
    emoji_font = ImageFont.truetype("NotoEmoji.ttf", 38)
    draw = ImageDraw.Draw(comic)

    # Iterate over the panels and add the dialog.
    for i in range(3):
        first_line = dialog_lines[2 * i]
        second_line = dialog_lines[2 * i + 1]

        # Wrap lines of dialog within a max width.
        first_line_wrapped = wrap_mixed_text(first_line, regular_font, emoji_font, 900, draw)
        second_line_wrapped = wrap_mixed_text(second_line, regular_font, emoji_font, 900, draw)

        # Calculate anchors for the text boxes.
        left_edge = i * panel_width + padding * (i + 1)
        right_edge = left_edge + panel_width

        # Draw the first text box (left-aligned).
        first_line_position = (left_edge, padding)
        _, first_text_height = draw_mixed_text_box(
            draw, first_line_wrapped, regular_font, emoji_font, first_line_position, padding=10
        )

        # Draw the second text box (right-aligned).
        text_width, _ = get_mixed_multiline_text_bbox(second_line_wrapped, regular_font, emoji_font, draw)
        second_line_position = (
            right_edge - text_width, first_line_position[1] + first_text_height + padding)
        draw_mixed_text_box(
            draw, second_line_wrapped, regular_font, emoji_font, second_line_position, padding=10)

    # Downscale the image by half and save it to disk.
    comic = comic.resize((total_width // 2, total_height // 2))
    comic.save('comic_strip.png')


def draw_mixed_text_box(draw, text_lines, regular_font, emoji_font, position, padding=0):
    """
    Draws text with mixed fonts on an image with a background rectangle.

    :param draw: ImageDraw object.
    :param text_lines: List of text lines to draw.
    :param regular_font: The regular font to use.
    :param emoji_font: The emoji font to use.
    :param position: Tuple (x, y) for the top-left position.
    :param padding: Padding inside the rectangle.
    :return: width and height of the drawn text box (including padding)
    """
    # Calculate the text bounding box.
    text_width, text_height = get_mixed_multiline_text_bbox(text_lines, regular_font, emoji_font, draw)

    # Adjust rectangle for padding.
    rect_start = (position[0] - padding, position[1] - padding)
    rect_end = (position[0] + text_width + padding,
                position[1] + text_height + padding)

    # Draw the text box and text.
    draw.rectangle([rect_start, rect_end], fill=(255, 255, 255))
    draw_mixed_multiline_text(draw, text_lines, regular_font, emoji_font, position, fill=(0, 0, 0))

    # Return the size of the text box including padding.
    total_width = text_width + 2 * padding
    total_height = text_height + 2 * padding
    return total_width, total_height


def is_emoji(char):
    """
    Check if a character is an emoji.
    """
    # Check for emoji characters using Unicode categories
    return (
        unicodedata.category(char) == 'So' or  # Other symbols (most emoji)
        char in ['\u2764', '\u2665', '\u2763']  # Common heart symbols
        or '\U0001F600' <= char <= '\U0001F64F'  # Emoticons
        or '\U0001F300' <= char <= '\U0001F5FF'  # Misc symbols
        or '\U0001F680' <= char <= '\U0001F6FF'  # Transport symbols
        or '\U0001F1E0' <= char <= '\U0001F1FF'  # Regional indicators (flags)
        or '\U00002600' <= char <= '\U000026FF'  # Misc symbols
        or '\U00002700' <= char <= '\U000027BF'  # Dingbats
    )


def split_text_by_font(text):
    """
    Split text into segments that need different fonts (regular text vs emoji).
    Returns a list of tuples: (text_segment, is_emoji)
    """
    segments = []
    current_segment = ""
    current_is_emoji = None

    for char in text:
        char_is_emoji = is_emoji(char)

        if current_is_emoji is None:
            current_is_emoji = char_is_emoji
            current_segment = char
        elif current_is_emoji == char_is_emoji:
            current_segment += char
        else:
            # Font type changed, save current segment and start new one
            if current_segment:
                segments.append((current_segment, current_is_emoji))
            current_segment = char
            current_is_emoji = char_is_emoji

    # Add the last segment
    if current_segment:
        segments.append((current_segment, current_is_emoji))

    return segments


def get_mixed_text_bbox(text, regular_font, emoji_font, draw):
    """
    Calculate the bounding box for text that may contain emoji.
    """
    segments = split_text_by_font(text)
    total_width = 0
    max_height = 0

    for segment_text, is_emoji in segments:
        font = emoji_font if is_emoji else regular_font
        bbox = draw.textbbox((0, 0), segment_text, font=font)
        segment_width = bbox[2] - bbox[0]
        segment_height = bbox[3] - bbox[1]

        total_width += segment_width
        max_height = max(max_height, segment_height)

    return total_width, max_height


def draw_mixed_text(draw, text, regular_font, emoji_font, position, fill=(0, 0, 0)):
    """
    Draw text with mixed fonts (regular text + emoji).
    Returns the total width drawn.
    """
    segments = split_text_by_font(text)
    x, y = position
    total_width = 0

    for segment_text, is_emoji in segments:
        font = emoji_font if is_emoji else regular_font

        # Draw the segment
        draw.text((x + total_width, y), segment_text, font=font, fill=fill)

        # Calculate width for positioning next segment
        bbox = draw.textbbox((0, 0), segment_text, font=font)
        segment_width = bbox[2] - bbox[0]
        total_width += segment_width

    return total_width


def wrap_mixed_text(text, regular_font, emoji_font, max_width, draw):
    """
    Wrap text that may contain emoji to fit within a specified width.
    """
    words = text.split(' ')
    wrapped_lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (word + " " if current_line else word + " ")
        text_width, _ = get_mixed_text_bbox(test_line, regular_font, emoji_font, draw)

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                wrapped_lines.append(current_line.strip())
            current_line = word + " "

    if current_line:
        wrapped_lines.append(current_line.strip())

    return wrapped_lines


def draw_mixed_multiline_text(draw, lines, regular_font, emoji_font, position, fill=(0, 0, 0)):
    """
    Draw multiple lines of text with mixed fonts.
    Returns the total width and height.
    """
    x, y = position
    max_width = 0
    # Use the larger font size for line spacing
    line_height = max(regular_font.size, emoji_font.size) + 5  # Add some extra spacing

    for i, line in enumerate(lines):
        line_y = y + i * line_height
        line_width = draw_mixed_text(draw, line, regular_font, emoji_font, (x, line_y), fill)
        max_width = max(max_width, line_width)

    total_height = len(lines) * line_height
    return max_width, total_height


def get_mixed_multiline_text_bbox(lines, regular_font, emoji_font, draw):
    """
    Calculate bounding box for multiple lines of mixed text.
    """
    max_width = 0
    # Use the larger font size for line spacing
    line_height = max(regular_font.size, emoji_font.size) + 5  # Add some extra spacing

    for line in lines:
        line_width, _ = get_mixed_text_bbox(line, regular_font, emoji_font, draw)
        max_width = max(max_width, line_width)

    total_height = len(lines) * line_height
    return max_width, total_height


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


def load_script():
    """Load the script content from script.txt file."""
    try:
        with open("script.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError("script.txt file not found. Please create this file with the chat log content.")


def main():
    parser = argparse.ArgumentParser(description='Generates AI slop.')

    parser.add_argument(
        '-p', '--panel',
        type=int,
        nargs='+',
        choices=[1, 2, 3],
        help='Panel number(s) to generate. Can specify multiple panels. Defaults to generating all three if not specified.'
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

    parser.add_argument(
        '-c', '--construct-only',
        action='store_true',
        help='Skip panel generation and only run the comic construction step using existing panel files.'
    )

    parser.add_argument(
        '-r', '--rotate',
        type=int,
        nargs='+',
        choices=[1, 2, 3],
        help='Panel number(s) to rotate 90 degrees clockwise. Can only be used with --construct-only.'
    )

    parser.add_argument(
        '-s', '--shift',
        type=int,
        nargs=2,
        action='append',
        metavar=('PANEL', 'OFFSET'),
        help='Shift a panel\'s crop position. First number is panel ID (1-3), second is offset in pixels. Positive values shift up, negative shift down. Can be used multiple times.'
    )

    parser.add_argument(
        '-m', '--max-tries',
        type=int,
        default=5,
        help='Maximum number of attempts to generate each panel before giving up. Defaults to 3.'
    )

    args = parser.parse_args()

    # Validate shift arguments
    if args.shift:
        for panel_id, offset in args.shift:
            if panel_id not in [1, 2, 3]:
                parser.error(f"Panel ID must be 1, 2, or 3, got {panel_id}")

    if args.publish:
        publish_comic()
        return

    # Process the raw chat logs into a list of lines of dialog, stripping off
    # the time prefix from each line (assume the time format is always `hh:mm AM/PM `).
    script_content = load_script()
    lines = script_content.strip().split("\n")
    assert len(lines) == 6, "script.txt must contain exactly 6 lines of dialog."
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

    if not args.construct_only:
        panels_to_generate = args.panel if args.panel else [1, 2, 3]
        for panel_id in panels_to_generate:
            generate_panel(client, panel_id, dialog_lines, speakers, location, args.max_tries)

    construct_comic(dialog_lines, rotate_panels=args.rotate, panel_shifts=args.shift)


if __name__ == "__main__":
    main()
