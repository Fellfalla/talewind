from mcp.server.fastmcp import FastMCP

# aliases
ItemT = str
OwnerT = str
InventoryID = OwnerT


class Inventory:
    def __init__(self, owner: OwnerT):
        assert isinstance(owner, OwnerT), "Owner must be a string"
        assert owner != "", "Owner must be a non-empty string"

        self.items: list[ItemT] = []
        self.owner: OwnerT = ""


# stick to simple list as number of inventories are not expected to be large
_inventories: list[Inventory] = []

mcp = FastMCP("inventory")


@mcp.tool(name="create_inventory")
async def create_inventory(owner: OwnerT) -> str:
    """
    Create a new inventory with the given identifier.

    Args:
        owner (str): The owner of the inventory. Must be a non-empty string.
    """
    if owner in _inventories:
        return f"Inventory for {owner} already exists."

    try:
        _inventories.append(Inventory(owner=owner))
    except AssertionError as e:
        return f"Error creating inventory: {e}"

    return f"Empty inventory created for {owner}."


@mcp.resource("inventory://")
async def list_inventories() -> list[InventoryID]:
    """
    List all available inventories.
    """
    return list(map(lambda x: x.owner, _inventories))


@mcp.resource("inventory://{owner}/items")
async def list_items(owner: OwnerT) -> list[InventoryID]:
    """
    List all items in the inventory.

    Args:
        owner (str): The owner of the inventory. Must be a non-empty string.

    """
    if owner not in _inventories:
        return f"Inventory for {owner} does not exist."

    return _inventories[owner].items


async def serve():
    """
    Start the server.
    """
    await mcp.run_stdio_async()


if __name__ == "__main__":
    import asyncio

    # Start the server
    asyncio.run(serve())
