import discord

class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()

class VC_Dropdown(discord.ui.Select):
    def __init__(self, vcs: list[discord.VoiceChannel], custom_callback, placeholder):
        self.custom_callback = custom_callback

        options = [discord.SelectOption(label=c.name, value=c.id) for c in vcs]

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.custom_callback(interaction, self.values[0])

class VCView(discord.ui.View):
    def __init__(self, vcs: list[discord.VoiceChannel], custom_callback, placeholder):
        super().__init__()
    
        self.add_item(VC_Dropdown(vcs, custom_callback, placeholder))

class Sound_Dropdown(discord.ui.Select):
    def __init__(self, sounds: dict, custom_callback, placeholder):
        self.custom_callback = custom_callback

        options = [discord.SelectOption(label=sounds[s], value=s) for s in sounds]

        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        await self.custom_callback(interaction, self.values[0])

class SoundView(discord.ui.View):
    def __init__(self, sounds: dict, custom_callback, placeholder):
        super().__init__()

        self.add_item(Sound_Dropdown(sounds, custom_callback, placeholder))