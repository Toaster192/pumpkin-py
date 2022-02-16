from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Iterable, Optional, Union

import disnake
from disnake.ext import commands

from pie import i18n

_ = i18n.Translator("pie").translate


class ScrollableEmbed(disnake.ui.View):
    """Class for making scrollable embeds easy.

    Args:
        ctx (:class:`disnake.ext.commands.Context`): The context for translational purposes.
        iterable (:class:`Iterable[disnake.Embed]`): Iterable which to build the ScrollableEmbed from.
        timeout (:class:'int'): Timeout (in seconds, default 300) from last interaction with the UI before no longer accepting input. If None then there is no timeout.
        delete_message (:class:'bool'): True - remove message after timeout. False - remove only View controls.
    """

    def __init__(
        self,
        ctx: commands.Context,
        iterable: Iterable[disnake.Embed],
        timeout: int = 300,
        delete_message: bool = False,
        locked: bool = False,
    ) -> ScrollableEmbed:
        super().__init__(timeout=timeout)
        self.pages = self._pages_from_iter(ctx, iterable)
        self.ctx = ctx
        self.pagenum = 0
        self.delete_message = delete_message
        self.locked = locked

        self.add_item(
            disnake.ui.Button(
                label="\u25c1",
                style=disnake.ButtonStyle.green,
                custom_id="left-button",
            )
        )

        if self.locked:
            self.lock_button = disnake.ui.Button(
                label="🔒",
                style=disnake.ButtonStyle.red,
                custom_id="lock-button",
            )
        else:
            self.lock_button = disnake.ui.Button(
                label="🔓",
                style=disnake.ButtonStyle.green,
                custom_id="lock-button",
            )
        self.add_item(self.lock_button)

        self.add_item(
            disnake.ui.Button(
                label="\u25b7",
                style=disnake.ButtonStyle.green,
                custom_id="right-button",
            )
        )

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} "
            f"page_count='{len(self.pages)}' pages='[{self.pages}]'>"
        )

    def _pages_from_iter(
        self, ctx: commands.Context, iterable: Iterable[disnake.Embed]
    ) -> list[disnake.Embed]:
        pages = []
        for idx, embed in enumerate(iterable):
            if not isinstance(embed, disnake.Embed):
                raise ValueError("Items in iterable must be of type disnake.Embed")
            embed.add_field(
                name=_(ctx, "Page"),
                value="{curr}/{total}".format(curr=idx + 1, total=len(iterable)),
                inline=False,
            )
            pages.append(embed)
        return pages

    def _toggle_lock(self) -> None:
        if self.locked:
            self.locked = False
            self.lock_button.label = "🔓"
            self.lock_button.style = disnake.ButtonStyle.green
        else:
            self.locked = True
            self.lock_button.label = "🔒"
            self.lock_button.style = disnake.ButtonStyle.red

    def __get_gtx(
        self,
        interaction: disnake.Interaction,
    ) -> i18n.TranslationContext:
        if self.ctx.guild is not None:
            gtx = i18n.TranslationContext(self.ctx.guild.id, interaction.user.id)
        else:
            # TranslationContext does not know how to use user without guild,
            # this will result in bot preference being used.
            gtx = i18n.TranslationContext(None, interaction.user.id)
        return gtx

    async def scroll(self):
        """Make embeds move.

        Sends the first page to the context.
        """
        ctx = self.ctx
        if self.pages == []:
            self.clear_items()
            await ctx.reply(_(ctx, "No results were found."))
            self.stop()
            return

        if len(self.pages) == 1:
            self.clear_items()
            await ctx.send(embed=self.pages[0])
            self.stop()
            return

        self.message = await ctx.send(embed=self.pages[0], view=self)

    async def interaction_check(self, interaction: disnake.Interaction) -> None:
        """Gets called when interaction with any of the Views buttons happens."""
        if interaction.data["custom_id"] not in [
            "lock-button",
            "left-button",
            "right-button",
        ]:
            # In case of unknown interaction (eg: decorated functions in child class)
            await super().interaction_check(interaction)
            return
        if interaction.data["custom_id"] == "lock-button":
            if interaction.user.id is self.ctx.author.id:
                self._toggle_lock()
                await interaction.response.edit_message(view=self)
                return
            else:
                gtx = self.__get_gtx(interaction)
                await interaction.response.send_message(
                    _(gtx, "Only command issuer can toggle the lock."), ephemeral=True
                )
                return
        elif interaction.user.id != self.ctx.author.id and self.locked:
            gtx = self.__get_gtx(interaction)
            await interaction.response.send_message(
                _(gtx, "Only command issuer can scroll."), ephemeral=True
            )
            return

        if interaction.data["custom_id"] == "left-button":
            self.pagenum -= 1
        else:
            self.pagenum += 1

        if self.pagenum < 0:
            self.pagenum = len(self.pages) - 1

        if self.pagenum >= len(self.pages):
            self.pagenum = 0

        await interaction.response.edit_message(embed=self.pages[self.pagenum])

    async def on_timeout(self) -> None:
        """Gets called when the view timeouts."""
        if not self.delete_message:
            self.clear_items()
            try:
                await self.message.edit(embed=self.pages[self.pagenum], view=None)
            except disnake.errors.NotFound:
                pass
        else:
            try:
                try:
                    await self.message.delete()
                except (
                    disnake.errors.HTTPException,
                    disnake.errors.Forbidden,
                ):
                    self.clear_items()
                    await self.message.edit(embed=self.pages[self.pagenum], view=None)
            except disnake.errors.NotFound:
                pass


class ConfirmView(disnake.ui.View):
    """Class for making confirmation embeds easy.
    The right way of getting response is first calling wait() on instance,
    then checking instance attribute `value`.

    Attributes:
        value: True if confirmed, False if declined, None if timed out
        ctx: Context of command
        message: Confirmation message

    Args:
        ctx: The context for translational and sending purposes.
        embed: Embed to send.
        timeout: Number of seconds before timeout. `None` if no timeout
        delete: Delete message after answering / timeout


    To use import this object and create new instance:
    .. code-block:: python
        :linenos:

        from pie.utils.objects import ConfirmView

        ...

        embed = utils.discord.create_embed(
            author=reminder_user,
            title=Confirm your action.",
        )
        view = ConfirmView(ctx, embed)

        value = await view.send()

        if value is None:
            await ctx.send(_(ctx, "Confirmation timed out."))
        elif value:
            await ctx.send(_(ctx, "Confirmed."))
        else:
            await ctx.send(_(ctx, "Aborted."))
    """

    def __init__(
        self,
        ctx: commands.Context,
        embed: disnake.Embed,
        timeout: Union[int, float, None] = 300,
        delete: bool = True,
    ):
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.ctx = ctx
        self.embed = embed
        self.delete = delete

    async def send(self):
        """Sends message to channel defined by command context.
        Returns:
            True if confirmed, False if declined, None if timed out
        """
        self.add_item(
            disnake.ui.Button(
                label=_(self.ctx, "Confirm"),
                style=disnake.ButtonStyle.green,
                custom_id="confirm-button",
            )
        )
        self.add_item(
            disnake.ui.Button(
                label=_(self.ctx, "Reject"),
                style=disnake.ButtonStyle.red,
                custom_id="reject-button",
            )
        )
        self.message = await self.ctx.reply(embed=self.embed, view=self)
        await self.wait()

        if not self.delete:
            self.clear_items()
            await self.message.edit(embed=self.embed, view=None)
        else:
            try:
                try:
                    await self.message.delete()
                except (
                    disnake.errors.HTTPException,
                    disnake.errors.Forbidden,
                ):
                    self.clear_items()
                    await self.message.edit(embed=self.embed, view=None)
            except disnake.errors.NotFound:
                pass
        return self.value

    async def interaction_check(self, interaction: disnake.Interaction) -> None:
        """Gets called when interaction with any of the Views buttons happens."""
        if interaction.user.id != self.ctx.author.id:
            return

        if interaction.data["custom_id"] == "confirm-button":
            self.value = True
        else:
            self.value = False
        self.stop()

    async def on_timeout(self) -> None:
        """Gets called when the view timeouts."""
        self.value = None
        self.stop()


class VotableEmbed(disnake.Embed, metaclass=ABCMeta):
    """
    Abrstract class extendindg Embed functionality
    so it can be used in ScollableVotingEmbed.

    Functions `vote_up`, `vote_neutral` and `vote_down`
    must be overriden. Init takes same arguments,
    as :class:`disnake.Embed`.

    Example of usage can be found in School.Review module.
    """

    def __init__(self, *args, **kwargs):
        super(VotableEmbed, self).__init__(*args, **kwargs)

    @abstractmethod
    async def vote_up(interaction: disnake.Interaction):
        """
        Callback when user votes UP. Must be overriden.
        """
        pass

    @abstractmethod
    async def vote_neutral(interaction: disnake.Interaction):
        """
        Callback when user votes NEUTRAL. Must be overriden.
        """
        pass

    @abstractmethod
    async def vote_down(interaction: disnake.Interaction):
        """
        Callback when user votes DOWNs. Must be overriden.
        """
        pass


class ScrollableVotingEmbed(ScrollableEmbed):
    """Class for making scrollable embeds with voting easy.

    Args:
        ctx (:class:`disnake.ext.commands.Context`): The context for translational purposes.
        iterable (:class:`Iterable[VotableEmbed]`): Iterable which to build the ScrollableVotingEmbed from.
        timeout (:class:'int'): Timeout (in seconds, default 300) from last interaction with the UI before no longer accepting input. If None then there is no timeout.
        delete_message (:class:'bool'): True - remove message after timeout. False - remove only View controls.
        locked: (:class:'bool'): True if only author can scroll, False otherwise
    """

    def __init__(self, *args, **kwagrs) -> ScrollableVotingEmbed:
        super().__init__(*args, **kwagrs)

        if len(self.pages) == 1:
            self.clear_items()

        self.add_item(
            disnake.ui.Button(
                label="👍",
                style=disnake.ButtonStyle.green,
                custom_id="vote_up",
                row=1,
            )
        )
        self.add_item(
            disnake.ui.Button(
                label="🤷‍",
                style=disnake.ButtonStyle.gray,
                custom_id="vote_neutral",
                row=1,
            )
        )
        self.add_item(
            disnake.ui.Button(
                label="👎",
                style=disnake.ButtonStyle.red,
                custom_id="vote_down",
                row=1,
            )
        )

    async def scroll(self):
        """Make embeds move. Overrides original function which
        was stopping View when there were only 1 page.

        Sends the first page to the context.
        """
        ctx = self.ctx
        if self.pages == []:
            self.clear_items()
            await ctx.reply(_(ctx, "No results were found."))
            self.stop()
            return

        self.message = await ctx.send(embed=self.pages[0], view=self)

    async def interaction_check(self, interaction: disnake.Interaction) -> None:
        """
        Gets called when interaction with any of the Views buttons happens.
        If custom ID is not recognized, it's passed to parent.
        """
        if interaction.data["custom_id"] == "vote_up":
            await self.pages[self.pagenum].vote_up(interaction)
        elif interaction.data["custom_id"] == "vote_neutral":
            await self.pages[self.pagenum].vote_neutral(interaction)
        elif interaction.data["custom_id"] == "vote_down":
            await self.pages[self.pagenum].vote_down(interaction)
        else:
            await super().interaction_check(interaction)
