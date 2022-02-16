import datetime

from disnake.ext import commands

from pie import check, i18n, utils

_ = i18n.Translator("modules/base").translate


class BaseInfo(commands.Cog):
    """Basic bot information."""

    def __init__(self, bot):
        self.bot = bot

        self.boot = datetime.datetime.now().replace(microsecond=0)

    #

    @commands.slash_command()
    async def ping(self, inter):
        """Return latency information."""
        delay: str = "{:.2f}".format(self.bot.latency)
        await inter.response.send_message(
            _(inter, "Pong: **{delay}** 🏓").format(delay=delay)
        )

    @commands.slash_command()
    async def uptime(self, inter):
        """Return uptime information."""
        now = datetime.datetime.now().replace(microsecond=0)
        delta = now - self.boot

        embed = utils.discord.create_embed(
            author=inter.author, title=_(inter, "Uptime")
        )
        embed.add_field(
            name=_(inter, "Boot time"),
            value=utils.time.format_datetime(self.boot),
            inline=False,
        )
        embed.add_field(
            name=_(inter, "Run time"),
            value=str(delta),
            inline=False,
        )

        await inter.response.send_message(embed=embed)


def setup(bot) -> None:
    bot.add_cog(BaseInfo(bot))
