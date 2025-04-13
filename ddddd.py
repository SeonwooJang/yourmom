import discord
from discord.ext import tasks
import requests
from bs4 import BeautifulSoup
import asyncio
import datetime

DISCORD_TOKEN = 'MTM2MDI1Njg0NzAwODc2MzkxNA.GSA-jH.vVHyd4zuva4dPt7soyjNl8EYVEAw_YPThb_cLY'
CHANNEL_ID = 1360253634675347749
TICKER = '178320'

intents = discord.Intents.default()
intents.message_content = True

def get_stock_info():
    try:
        url = f"https://finance.naver.com/item/main.nhn?code={TICKER}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        price_tag = soup.select_one('p.no_today span.blind')
        volume_tag = soup.select_one('table.no_info td span.blind')

        price = int(price_tag.text.replace(',', '')) if price_tag else None
        volume = int(volume_tag.text.replace(',', '')) if volume_tag else None

        return price, volume
    except Exception as e:
        print(f"[ERROR] 주가/거래량 가져오기 실패: {e}")
        return None, None

def get_czech_news():
    try:
        search_url = "https://search.naver.com/search.naver"
        params = {'where': 'news', 'query': '체코 원전', 'sort': '1'}  # 최신순 정렬
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(search_url, params=params, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        news_items = soup.select("a.news_tit")[:2]  # 상위 2개 뉴스
        if not news_items:
            return "🔍 관련 뉴스 없음"

        result = ""
        for item in news_items:
            title = item.get('title')
            link = item.get('href')
            result += f"• [{title}]({link})\n"
        return result
    except Exception as e:
        print(f"[ERROR] 체코 뉴스 가져오기 실패: {e}")
        return "⚠️ 체코 뉴스 로딩 실패"

class SeojeonBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.last_price = None

    async def on_ready(self):
        print(f"[✅] 디스코드 봇 로그인됨: {self.user}")
        self.send_price.start()
        self.send_daily_report.start()

    @tasks.loop(minutes=10)
    async def send_price(self):
        now = datetime.datetime.now()
        if now.hour < 9 or (now.hour == 15 and now.minute > 30) or now.hour > 15:
            print("[INFO] 장 외 시간, 전송 생략")
            return

        price, _ = get_stock_info()
        print(f"[DEBUG] 현재 주가: {price}")
        if price is None:
            return

        if self.last_price is None:
            self.last_price = price
            return

        if price != self.last_price:
            diff = price - self.last_price
            emoji = "▲" if diff > 0 else "▼"
            msg = f"속보! 서전기전 현재가: {price:,}원 ({emoji}{abs(diff):,}원 변동)"
            channel = self.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(msg)
            else:
                print("[ERROR] 채널 접근 실패")
            self.last_price = price

    @tasks.loop(time=datetime.time(hour=15, minute=40))
    async def send_daily_report(self):
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            print("[ERROR] 채널 접근 실패 (리포트)")
            return

        price, volume = get_stock_info()
        news = get_czech_news()

        if price is None or volume is None:
            await channel.send("⚠️ 오늘 리포트 데이터를 불러오지 못했어 형...")
            return

        trend = "기관 매집 추정" if volume >= 50000 else "작전세력 의심"

        report = (
            f"📊 **서전기전 데일리 리포트** 📊\n"
            f"- 종가: {price:,}원\n"
            f"- 거래량: {volume:,}주\n"
            f"- 세력 분석: {trend}\n"
            f"- 🌍 체코 뉴스 요약:\n{news}\n"
            f"- 💬 오늘의 한줄: 형, 오늘도 잘 버텼다. 우린 결국 도착할 거야 🚀"
        )
        await channel.send(report)

    async def on_message(self, message):
        if message.author == self.user:
            return

        if self.user.mentioned_in(message) or "복덕아" in message.content:
            await message.channel.send("작동 중입니다 형! 🔧 언제든 불러줘!")

if __name__ == "__main__":
    bot = SeojeonBot()
    bot.run(DISCORD_TOKEN)
