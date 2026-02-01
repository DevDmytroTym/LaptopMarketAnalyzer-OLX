import asyncio
import logging
import sys
import os
from aiogram import Bot
from tg_bot import dp, notify_users_new_deals
from analysis_engine import find_hot_deals
from scraper import run_scraper
from config_manager import ConfigManager
from LaptopBase import LaptopBase


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'), 
        logging.StreamHandler(sys.stdout)                 
    ]
)

async def scheduled_scraping(laptops: LaptopBase, config: ConfigManager, bot: Bot):
    """Фонова задача для регулярного сканування."""
    logging.info("Планувальник завдань запущено.")

    while True:
        try:
            interval = config.data.get('check_interval', 30)
            
            logging.info("Початок автоматичного сканування...")
            
            success = await asyncio.to_thread(run_scraper)

            if success:
                logging.info("Скрапінг успішний. Аналізуємо дані...")
                await asyncio.to_thread(find_hot_deals)
                
                laptops.update()
                
                await notify_users_new_deals(bot, config, laptops)
            else:
                logging.warning("Скрапінг завершився невдачею або не знайшов оголошень.")

        except Exception as e:
            logging.error(f"Критична помилка в планувальнику: {e}", exc_info=True)
            await asyncio.sleep(60) 
            continue

        logging.info(f" Спимо {interval} хвилин до наступного пошуку.")
        await asyncio.sleep(interval * 60)



async def main():
    try:
        config = ConfigManager()

        os.makedirs('data', exist_ok=True)
        
        token = config.data.get('token')
        if not token:
            logging.critical("ТОКЕН НЕ ЗНАЙДЕНО! Перевірте config.json")
            return

        bot = Bot(token=token)
        laptops = LaptopBase("data/hot_deals.csv")
        
        app_data = {"laptops": laptops, "config": config}

        asyncio.create_task(scheduled_scraping(laptops, config, bot))

        logging.info(f"Система запущена! Бот { (await bot.get_me()).username } чекає на команди...")

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, **app_data)

    except Exception as e:
        logging.critical(f"Фатальна помилка при старті: {e}", exc_info=True)
    finally:
        if 'bot' in locals():
            await bot.session.close()
        logging.info("Бот зупинений.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Роботу завершено вручну (Ctrl+C)")