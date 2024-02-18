import aiohttp, asyncio
import haversine as hs
from haversine import Unit


def distance(loc1, loc2):
    return hs.haversine(loc1,loc2,unit=Unit.METERS)

async def fetch(session, address_tuple):
    address, comune = address_tuple
    url = f'https://srvcarto2svil.regione.liguria.it/geoservices/REST/geocoder/proxy/pelias_geocode/v1/search/?text={address}'
    async with session.get(url) as response:
        resp = await response.json()
        region = resp['features'][0]['properties']['region']
        if region == comune:
            coords = resp['features'][0]['geometry']['coordinates']
        else:
            coords = []
        return coords


async def fetch_all(addresses, loop):
    async with aiohttp.ClientSession(loop=loop) as session:
        results = await asyncio.gather(*[fetch(session, address) for address in addresses], return_exceptions=True)
        return results


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    addresses = [('Borgo degli Incrociati 7', 'Genova'), ('Via Argonne, 5, 16145 Genova GE', 'Genova')]
    htmls = loop.run_until_complete(fetch_all(addresses, loop))
    print(htmls)