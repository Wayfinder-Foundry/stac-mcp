"""
Quick runner to call STACClient.estimate_data_size against Planetary Computer sentinel-2 example.
Placed in `debug/` for convenience.
"""
import asyncio

from stac_mcp.tools.client import STACClient


async def main():
    client = STACClient()
    # Sentinel-2 L2A collection and bbox/datetime used earlier in the session
    res = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: client.estimate_data_size(
            collections=["sentinel-2-l2a"],
            bbox=[-119.2, 34.23, -118.42, 35.23],
            datetime="2023-06-30T18:39:29.024000Z",
            limit=10,
        ),
    )
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
"""
Quick runner to call STACClient.estimate_data_size against Planetary Computer sentinel-2 example.
"""
import asyncio


async def main():
    client = STACClient()
    # Sentinel-2 L2A collection and bbox/datetime used earlier in the session
    res = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: client.estimate_data_size(
            collections=["sentinel-2-l2a"],
            bbox=[-119.2, 34.23, -118.42, 35.23],
            datetime="2023-06-30T18:39:29.024000Z",
            limit=10,
        ),
    )
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
