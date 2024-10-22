from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import requests


CHARACTER_DESCRIPTIONS = {
    "geckomuerto": "An anthropomorphic lizard wearing a business suit and smoking a cigarette.",
    "shadypkg": "A tall, buff, shirtless man with a cardboard box on his head.",
    "philza": "A rockstar with sunglasses and long blonde hair, holding a black and white guitar.",
}


def generate_panels(dialog_lines, speakers):
    """
    Generates 3 comic panels based on 6 IRC logs.
    """

    client = OpenAI()

    # Generate the 3 panels.
    for i in range(3):
        p = i + 1

        # First prompt: Generate concise speaker description and panel layout.
        # --------------------------------------------------------------------

        # Determine our speakers for this panel.
        panel_speakers = [speakers[2 * i], speakers[2 * i + 1]]
        speakers_prompt = f"""
        - **{panel_speakers[0]}**: {CHARACTER_DESCRIPTIONS[panel_speakers[0]]}

        - **{panel_speakers[1]}**: {CHARACTER_DESCRIPTIONS[panel_speakers[1]]}
        """

        system = f"""
        You will be given the description of two characters. Write a short
        description of a scene with the two characters. The characters should be
        explicitly placed on the left and right side of the image, with the
        first character on the left and the second character on the right.

        If the same character is listed twice, they are the only speaker. Simply
        describe that character alone in that case.

        Keep the generated description short and to the point. Avoid using
        superfluous descriptors, and keep character descriptions as close to
        their original descrption. Do not mention the characters' names, only
        reference them by their visual descriptions.

        example input:

        ```
        - **alice**: A talking toaster with a cartoon face on her side.

        - **bob**: A cat wearing a cat t-shirt.
        ```

        example output:

        ```
        On the left stands a large cartoon toaster with a large, expressive
        face on her side. To her right sits a large black cat wearing a t-shirt
        that depicts a cat. The two are engaged in a casual conversation.
        ```
        """

        # TODO: Handle potential failure here.
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": speakers_prompt,
                },
            ]
        )

        combined_description = completion.choices[0].message.content
        print(f"\nPanel {p} character descriptions:")
        print(combined_description)

        # Second prompt: Use dialog to generate location and character actions.
        # ---------------------------------------------------------------------

        dialog = "\n".join([dialog_lines[2 * i], dialog_lines[2 * i + 1]])

        system = """
        You will be given two lines of IRC chat dialog and the description of a
        scene containing one or two characters. The initial description of the
        characters will be simple, just describing their appearances and their
        positions in the frame.

        Using the two lines of chat as a starting point, rewrite the scene
        description to add an appropriate location and have the characters
        performing some action.

        Keep the generated description simple and concise, in the same style as
        the initial description. Keep it mostly the same, amending it only with
        a brief description of the location and what the characters are doing.
        """

        prompt = f"""
        # Initial Scene

        {combined_description}

        # Dialog

        {dialog}
        """
        print(f"\nPanel {p} dialog prompt:", prompt)

        # TODO: Handle potential failure here.
        completion = client.chat.completions.create(
            model="gpt-4o",
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

        expanded_description = completion.choices[0].message.content

        # Draw the panel.
        # ---------------

        print(f"\nFinal panel {p} prompt:\n{expanded_description}")

        # TODO: Handle potential failure here.
        response = client.images.generate(
            model="dall-e-3",
            prompt=expanded_description,
            size="1024x1024",
            quality="standard",
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


def main():
    chat_script = """
    4:06 PM <geckomuerto> gonna hafta make pasta for weeks so i can start collecting jars for paper pulp
    4:07 PM <geckomuerto> processed four jars today
    4:18 PM <philza> what do these things have to do with each other
    4:18 PM <geckomuerto> sauce jars are used to hold paper and water to stir into pulp slurry! the slurry is then used to make new paper
    4:19 PM <philza> love shady changing outfits in every panel. ai is so goooood
    4:19 PM <philza> geckomuerto: i see, i thought you needed the jars but they were full of pasta rofl
    """

    # Process the raw chat logs into a list of lines of dialog, stripping off
    # the time prefix from each line (assume the time format is always `hh:mm AM/PM `).
    lines = chat_script.strip().split("\n")
    dialog_lines = [line.strip().split(' ', 2)[2] for line in lines]

    # Extract the speakers for each line.
    speakers = [line.split('>')[0][1:] for line in dialog_lines]

    generate_panels(dialog_lines, speakers)
    construct_comic(dialog_lines)


if __name__ == "__main__":
    main()
