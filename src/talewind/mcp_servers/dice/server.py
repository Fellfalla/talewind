from mcp.server.fastmcp import FastMCP
import random

# NOTE: We may generalize this to "random_int", but we keep it dice so the AI is more likely to use it
mcp = FastMCP("dice")


@mcp.tool(name="roll_dice")
async def roll_dice(n_sides: int) -> int:
    """
    Roll a dice with the given number of sides.

    Args:
        n_sides (int): The number of sides on the dice. Must be a positive integer.

    Returns:
        int: The result of the dice roll.
    """
    if n_sides <= 0:
        return "Number of ssides must be a positive integer."

    return random.randint(1, n_sides)


async def serve():
    """
    Start the server.
    """
    await mcp.run_stdio_async()


if __name__ == "__main__":
    import asyncio

    # Start the server
    asyncio.run(serve())
