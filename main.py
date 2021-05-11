from bot import Bot, AssetPair, Asset, logger
from bot.data import Loader
from os import getenv
import asyncio
import datetime

import json
import time


import random
from dataclasses import dataclass


@dataclass
class Order:
    sent: bool = False
    
buy_price = 0
sell_price = 0
order = Order()
logger.add(f"file_{datetime.datetime.now().date()}.log")




async def currency_watch(asset, bot):

    loader = Loader(asset.symbol, bot).initialize_iterator()
    
    async for item in loader:
        
        data = item.get('data')
        asset.bid_p, asset.bid_q = float(data.get('bid')), float(data.get('bidSize'))
        asset.ask_p, asset.ask_q = float(data.get('ask')), float(data.get('askSize'))
        

async def buy(bot, asset, volume, client_id, post_only, reduce_only=False):
    
    response = await bot.buy(market=asset.symbol,
                  price=asset.ask_p + 0.111,
                  size=volume,
                  client_id=client_id,
                  post_only=post_only,
                  reduce_only=reduce_only,
                  type='limit')
    
    if not response.get('success'):
        await asyncio.sleep(30)
        logger.error(response)
        
    
    counter = 0    
    while True:
        if response.get('success'):
            if not response.get('result').get('filledSize') == volume:
                if response.get('result').get('remainingSize') == 0.0:
                    await asyncio.sleep(0.001)
                    counter += 1   
                    response = await bot.buy(market=asset.symbol,
                        price=asset.ask_p + 0.111,
                        size=volume,
                        client_id=client_id + counter,
                        post_only=post_only,
                        reduce_only=reduce_only,
                        type='limit')
                    
                else:
                    response = await bot.get_order_status_by_client_id(client_id + counter)
                    logger.info(response)
            else:
                if response.get('result').get('status') == 'closed':
                    return response
        
        await asyncio.sleep(0.05)
        
        
@logger.catch
async def sell(bot, asset, volume, client_id, post_only, reduce_only=False):
    
    response =  await bot.sell(market=asset.symbol,
                  price=asset.bid_p + 0.1,
                  size=volume,
                  reduce_only=reduce_only,
                  client_id=client_id,
                  post_only=post_only,
                  type='limit')
    
    if not response.get('success'):
        await asyncio.sleep(30)
        logger.error(response)
    
    counter = 0    
    while True:
        if response.get('success'):            
            if not response.get('result').get('filledSize') == volume:
                if response.get('result').get('remainingSize') == 0.0:
                    await asyncio.sleep(0.02)
                    counter += 1   
                    response = await bot.sell(market=asset.symbol,
                    price=asset.bid_p + 0.1,
                    size=volume,
                    reduce_only=reduce_only,
                    client_id=client_id + counter,
                    post_only=post_only,
                    type='limit')
                else:
                    response = await bot.get_order_status_by_client_id(client_id + counter)
            else:
                if response.get('result').get('status') == 'closed':
                    return response
                    
            await asyncio.sleep(0.05)
        
@logger.catch
async def check_opportunities(asset_pair, bot):
    
    # Giving some time to download data from stream
    await asyncio.sleep(3)
    
    
    while True:
        # Context switching during the analyze procedure
        await asyncio.sleep(0.001)
        basis = await asset_pair.get_basis()
        
        print(basis)
        
        if basis >= 0.11 and order.sent == False:
            logger.success(f'[ENTER] {basis}')
            order.sent = True
                    
            
            client_ids_ = [int(time.time() * 10000000), int(time.time() * 10000001)]
            
            logger.info(f'[ORDER]: buy {asset_pair.first_leg} sell {asset_pair.second_leg}')
            bought = await buy(bot=bot, asset=asset_pair.first_leg, volume=asset_pair.volume, client_id=client_ids_[0], post_only=True, reduce_only=False)
            sold = await sell(bot=bot, asset=asset_pair.second_leg, volume=asset_pair.volume, client_id=client_ids_[1], post_only=True, reduce_only=False)
            
            logger.info(f'[ORDERS] Done')
            
            
            with open('open.json', 'a+') as fobj:
                json.dump(bought, fobj, indent=4)
                json.dump(sold, fobj, indent=4)
            
            

            
        elif basis <= 0.03 and order.sent == True:
            
            logger.success(f'Profitable exit! {asset_pair.second_leg.ask_p}, {asset_pair.first_leg.bid_p}')
            
            client_ids = [int(time.time() * 10000000), int(time.time() * 10000001)]

            logger.info(f'[ORDER]: sell {asset_pair.first_leg} buy {asset_pair.second_leg}')

            bought = await buy(bot, asset_pair.second_leg, asset_pair.volume, client_ids[0], post_only=True, reduce_only=True)
            await asyncio.sleep(0.01)
            sold = await sell(bot, asset_pair.first_leg, asset_pair.volume, client_ids[1], post_only=True)
            
            order.sent = False
            
            
            
            with open('open.json', 'a+') as fobj:
                json.dump(bought, fobj, indent=4)
                json.dump(sold, fobj, indent=4)


async def main(asset_pair, first_leg, second_leg, bot):
    
    await asyncio.gather(
        asyncio.create_task(currency_watch(first_leg, bot)),
        asyncio.create_task(currency_watch(second_leg, bot)),
        asyncio.create_task(check_opportunities(asset_pair, bot))
        )


if __name__ == "__main__":
    
    pairs = [('MEDIA/USD', 'MEDIA-PERP'), ('BNB/USD', 'BNB-PERP'), ('DOT/USD', 'DOT-PERP')]
    
    bot = Bot(getenv('KEY'), getenv('SECRET'))

    first_leg = Asset(symbol='ETH/USD')
    second_leg = Asset(symbol='ETH-PERP')
    asset_pair = AssetPair(first_leg=first_leg, second_leg=second_leg)
    
    
    asyncio.run(main(asset_pair, asset_pair.first_leg, asset_pair.second_leg, bot))