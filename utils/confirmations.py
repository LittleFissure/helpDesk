from __future__ import annotations

"""Reusable confirmation view for destructive actions."""

import discord


class ConfirmActionView(discord.ui.View):
    """Simple yes/no confirmation view used before destructive actions."""

    def __init__(self, author_id: int, timeout: int = 60) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command user can confirm this action.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.confirmed = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


async def confirm_action(interaction: discord.Interaction, prompt: str) -> bool:
    """Ask the command user to confirm a destructive action."""
    view = ConfirmActionView(interaction.user.id)
    await interaction.response.send_message(prompt, ephemeral=True, view=view)
    await view.wait()
    return view.confirmed
