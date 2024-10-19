from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import requests


def generate_panels(chat_script):
    """
    Generates 3 comic panels based on 6 IRC logs.
    """

    client = OpenAI()

    # Generate the full script for the comic from the initial chat logs.

    system = """
    You are a writer for a simple web comic. You will be given 6 lines of IRC chat
    that you will turn into a 3 panel comic with 2 lines of dialog in each panel
    (either from different people or from the same person). Write a script for the
    comic based on the logs, describing the following details about the comic:

    * The location the comic is set. Describe any details about the location that
    are relevant for the comic such as specific object that need to be in the
    scene.
    * Any specific clothing or visual modifiers for the characters, e.g. if the
    comic is set in a kitchen one character may be wearing an apron.
    * The emotional expressions and actions of each of the characters in each panel.
    The characters should act and emote properly based on the context of the
    conversion and their lines of dialog.
    * The dialog for each character in each panel. Dialogue should be the exact text
    of the original IRC log.
    """

    prompt = chat_script

    # TODO: Handle potential failure here.
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )

    full_script = completion.choices[0].message.content
    print("\nScript:")
    print(full_script)

    # Generate the 3 panels.
    panel_urls = []
    for p in range(1, 4):
        # Generate the script for the panel.

        system = f"""
        You will be given the script of a simple 3 panel web comic. From that script
        extract the script for panel {p}. Include a description of the setting, each
        character's appearance, their expressions, and their actions. Specify clearly
        which character each piece of dialog is coming from.
        """

        prompt = full_script

        # TODO: Handle potential failure here.
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
        )

        panel_script = completion.choices[0].message.content
        print(f"\nPanel {p} Script:")
        print(panel_script)

        # Generate a description of the panel from its script.

        system = """
        You will be given the script of a single panel of 3 panel comic. From that
        script generate a visual description of the panel. Include a brief description
        of the setting, each character's physical appearance, their emotion, and their
        actions. Put the first speaking character on the left side of the panel and the
        second speaking character on the right side. Explicitly note which side of the
        panel each character is on.
        """

        prompt = panel_script

        # TODO: Handle potential failure here.
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
        )

        panel_description = completion.choices[0].message.content
        print("\nPanel Description:")
        print(panel_description)

        # Draw the panel.

        prompt = f"""
        Draw an image in the style of a 1950s golden age comic from the following description:

        {panel_description}
        """

        # TODO: Handle potential failure here.
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        print(f"\nPanel {p} URL:")
        print(image_url)

        panel_urls.append(image_url)

    # Download the panels.
    for index, url in enumerate(panel_urls):
        p = index + 1
        response = requests.get(url)

        # Save the image to a file
        file_name = f"panel_{p}.png"
        with open(file_name, "wb") as file:
            file.write(response.content)

        print(f"Saved file to {file_name}")


def construct_comic(chat_script):
    """
    Constructs the final comic from the generated panels and parsed chat logs.
    """

    # Combine the 3 panels into a single image.
    # -----------------------------------------

    # Load images for each panel.
    panel_1 = Image.open('panel_1.png')
    panel_2 = Image.open('panel_2.png')
    panel_3 = Image.open('panel_3.png')

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

    # Process the raw chat logs into a list of lines of dialog, stripping off
    # the time prefix from each line (assume the time format is always `hh:mm AM/PM `).
    lines = chat_script.strip().split("\n")
    dialog_lines = [line.strip().split(' ', 2)[2] for line in lines]

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


def main():
    chat_script = """
    11:26 AM <philza> Muta_work: imo the line never makes you happy
    11:26 AM <@Muta_work> it's a bad line
    11:26 AM <@Muta_work> I refer to it as the bad line
    11:26 AM <@Muta_work> no good comes from this line
    11:26 AM <@Muta_work> also, i have like, six different lines, and they are all going down
    11:27 AM <skalnik> is down good or bad
    """

    # generate_panels(chat_script)
    construct_comic(chat_script)


if __name__ == "__main__":
    main()
