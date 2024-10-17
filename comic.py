from openai import OpenAI
import requests

client = OpenAI()

# Generate the full script for the comic.

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

prompt = """
11:26 AM <philza> Muta_work: imo the line never makes you happy
11:26 AM <@Muta_work> it's a bad line
11:26 AM <@Muta_work> I refer to it as the bad line
11:26 AM <@Muta_work> no good comes from this line
11:26 AM <@Muta_work> also, i have like, six different lines, and they are all going down
11:27 AM <skalnik> is down good or bad
"""

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
