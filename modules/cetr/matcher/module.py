import nextcord
from nextcord.ext import commands

from pie import utils, logger, i18n
import pie.database.config

from .database import History

_ = i18n.Translator(__file__).translate
bot_log = logger.Bot.logger()
config = pie.database.config.Config.get()

# TODO: translations etc.


class NotMatchedError(Exception):
    pass


class Matches:
    def __init__():
        self.parner_LUT = {}
        self.DM_channels = {}

        self.init_from_db()

    def init_from_db(self):
        for match in Match.getall():
            add([match.user_id1, match.user_id2])

    def active(self, user_id):
        return user_id in self.partner_LUT

    async def send(self, message):
        author_id = message.author.id
        if author_id not in self.partner_LUT:
            raise NotMatchedError()

        partners = self.partner_LUT[author_id]
        targets = [self.DM_channels[partner] for partner in partners]

        files = []
        for attachment in message.attachments:
            files.append(await attachment.to_file())

        for target in targets:
            await target.send(message.content, files=files)

    def add(ids):
        for user_id in ids:
            self.partner_LUT[user_id] = [uid for uid in ids if uid != user_id]
            if user_id not in self.DM_channels:
                user = await self.bot.fetch_user(user_id)
                self.DM_channels[user_id] = await user.create_dm()

    def remove(ids):
        for user_id in ids:
            self.partner_LUT.pop(user_id)
            self.DM_channels.pop(user_id)


class Matcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # TODO: Make queue a class, allow adding and stuff (db)
        self.queues = {"Main": []}
        self.matches = Matches()

    def find_chatter(self, user_id):
        for match in self.matches.keys():
            for index in (0, 1):
                if user_id == match[index]:
                    return match, index

        return None, 0

    async def match(self, ctx, queue):
        for partner_id in queue:
            history = History.get(ctx.author.id, partner_id)
            if history is not None and (history.u1_blocked or history.u2_blocked):
                continue

            partner = await self.bot.fetch_user(partner_id)
            partner_dm = await partner.create_dm()
            last_matched = history.last_matched
            History.update(history)
            self.matches[(ctx.author.id, partner_id)] = (
                await ctx.author.create_dm(),
                partner_dm,
            )
            if history is None:
                History.add(ctx.author.id, partner_id)
                return partner_dm, None
            return partner_dm, last_matched

        return None, None

    @commands.dm_only()
    @commands.group(name="matcher")
    async def matcher(self, ctx):
        """Matcher"""
        await utils.discord.send_help(ctx)

    @matcher.command(name="match")
    async def matcher_match(self, ctx, *, queue: str = "Main"):
        if queue not in self.queues:
            await ctx.reply("What queue?")
            return

        if ctx.author.id in self.queues[queue]:
            await ctx.reply("Bruh, you're already queued")
            return

        match, last_matched = await self.match(ctx, self.queues[queue])
        if not match:
            self.queues[queue].append(ctx.author.id)
            await ctx.reply("Queuing you up")
            return

        message = "You are now matched!"
        if last_matched:
            message += f'\nLast matched with this person: {last_matched.strftime("%Y-%m-%d %H:%M")}'
        await ctx.reply(message)
        await match.send(message)

    @matcher.command(name="quit")
    async def matcher_quit(self, ctx):
        active_chat, _ = self.find_chatter(ctx.author.id)
        if not active_chat:
            await ctx.send("What? You're not matched atm.")
            return
        dms = self.matches[active_chat]
        for index in (0, 1):
            await dms[index].send("Connection closed")
        self.matches.pop(active_chat, None)

    @matcher.command(name="block")
    async def matcher_block(self, ctx):
        active_chat, index = self.find_chatter(ctx.author.id)
        if not active_chat:
            await ctx.send("What? You're not matched atm.")

        history = History.get(active_chat[0], active_chat[1])
        partner_id = active_chat[(index + 1) % 2]
        for num in (1, 2):
            if history.getattr(f"user_id{num}") == partner_id:
                history.setattr(f"u{num}_blocked", True)

        await ctx.send("User blocked.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if not isinstance(message.channel, nextcord.DMChannel):
            return
        if message.content.startswith(config.prefix):
            return

        if self.matches.active(message.author.id):
            self.matches.send(message)
            await message.add_reaction("✅")
        else:
            await message.add_reaction("❓")


def setup(bot) -> None:
    bot.add_cog(Matcher(bot))
