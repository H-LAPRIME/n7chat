from __future__ import annotations

import asyncio

from scripts.index_documents import index_courses


async def main() -> None:
    count = await index_courses()
    print(f"Indexed {count} course chunks.")


if __name__ == "__main__":
    asyncio.run(main())
