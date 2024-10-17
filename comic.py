from openai import OpenAI
client = OpenAI()

system = """
You are a writer for a comic. This comic takes 6 lines of IRC chat and turns
them into a 3 panel comic with 2 lines of dialog in each panel (either from
different people or from the same person). Your job is to write a script for the
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
Generate a script for a 3 panel comic based on the following IRC logs:

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

script = completion.choices[0].message.content
print("Script:")
print(script)

prompt = f"""
From the following script for a 3 panel comic, write a description of the first
panel. Include a description of the setting, each character's appearance, their
expressions, and their actions. Specify clearly which character each piece of
dialog is coming from.

{script}
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

panel1_script = completion.choices[0].message.content
print("\nPanel 1 Script:")
print(panel1_script)

prompt = f"""
Generate a single panel of a comic using the following script:

{panel1_script}
"""

response = client.images.generate(
    model="dall-e-3",
    prompt=prompt,
    size="1024x1024",
    quality="standard",
    n=1,
)

image_url = response.data[0].url
print("\nPanel 1 URL:")
print(image_url)
