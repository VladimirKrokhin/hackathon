import asyncio
import logging


from bootstrap import bootstrap
from app import bot, dp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)



if __name__ == "__main__":

    asyncio.run(bootstrap(bot, dp))
