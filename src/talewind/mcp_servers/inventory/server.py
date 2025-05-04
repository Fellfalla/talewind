from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Context

# aliases
# TODO: use struct for item containing identifier and desciption/properties separately.
ItemT = str
OwnerT = str
InventoryID = OwnerT


class Inventory:
    def __init__(self, owner: OwnerT):
        assert isinstance(owner, OwnerT), "Owner must be a string"
        assert owner != "", "Owner must be a non-empty string"

        self.items: list[ItemT] = []
        self.owner: OwnerT = owner

    @property
    def identifier(self) -> InventoryID:
        return self.owner


# stick to simple list as number of inventories are not expected to be large
_inventories: list[Inventory] = []

mcp = FastMCP("inventory")


def get_inventory(inventory_id: InventoryID) -> Inventory:
    """
    Get the inventory for the given owner.

    Args:
        inventory_id (str): The owner of the inventory. Must be a non-empty string.

    Returns:
        Inventory: The inventory for the given owner.
    """
    for inventory in _inventories:
        if inventory.identifier == inventory_id:
            return inventory


@mcp.tool(name="create_inventory")
async def create_inventory(owner: OwnerT) -> str:
    """
    Create a new inventory with the given identifier.

    Args:
        owner (str): The owner of the inventory. Must be a non-empty string.
    """
    global _inventories
    if get_inventory(owner) is not None:
        return f"Inventory for {owner} already exists."

    try:
        _inventories.append(Inventory(owner=owner))
    except AssertionError as e:
        return f"Error creating inventory: {e}"

    return f"Empty inventory created for {owner}."


@mcp.resource("inventory://")
@mcp.tool("list_inventories")
async def list_inventories() -> list[InventoryID]:
    """
    List all available inventories.
    """
    return list(map(lambda x: x.identifier, _inventories))


# NOTE (@weber): if the arg name does not match the placeholder in resource, the mcp server will timeout during bootup
@mcp.resource("inventory://{inventory_id}/items")
@mcp.tool("list_items")
async def list_items(inventory_id: InventoryID) -> list[ItemT]:
    """
    List all items in the inventory.

    Args:
        inventory_id (str): The owner of the inventory. Must be a non-empty string.

    """
    inventory = get_inventory(inventory_id)
    if inventory is None:
        return f"Inventory for {inventory_id} does not exist."

    return inventory.items


@mcp.tool(name="add_item")
async def add_item(inventory_id: InventoryID, item: ItemT, ctx: Context) -> str:
    """
    Add an item to the inventory.

    Args:
        inventory_id (str): The owner of the inventory. Must be a non-empty string.
        item (str): The item to add. Must be a non-empty string.
    """
    global _inventories
    inventory = get_inventory(inventory_id)
    if inventory is None:
        ctx.error(f"Inventory for {inventory_id} does not exist.")
        return f"Inventory for {inventory_id} does not exist."

    # NOTE (@weber): Allow duplicate items
    inventory.items.append(item)
    return f"Item {item} added to inventory for {inventory_id}."


@mcp.tool(name="remove_item")
async def remove_item(inventory_id: InventoryID, item: ItemT) -> str:
    """
    Remove an item from the inventory.

    Args:
        inventory (str): The owner of the inventory. Must be a non-empty string.
        item (str): The item to remove. Must be a non-empty string.
    """
    global _inventories
    inventory = get_inventory(inventory_id)
    if inventory is None:
        return f"Inventory for {inventory_id} does not exist."

    if item not in inventory.items:
        return f"Item {item} not found in inventory for {inventory_id}."

    return f"Item {item} removed from inventory for {inventory_id}."


@mcp.tool(name="update_item")
async def update_item(inventory_id: InventoryID, item: ItemT, ctx: Context) -> str:
    """
    Update an item in the inventory.

    Args:
        inventory (str): The owner of the inventory. Must be a non-empty string.
        item (str): The item to update. Must be a non-empty string.
    """
    global _inventories
    inventory = get_inventory(inventory_id)
    if inventory is None:
        return f"Inventory for {inventory_id} does not exist."

    if item not in inventory.items:
        return f"Item {item} not found in inventory for {inventory_id}."

    # NOTE (@weber): This doesnt make any sense until we separate item identifier and description from each other
    inventory.items[inventory.items.index(item)] = item

    return f"Item {item} updated in inventory for {inventory_id}."


async def serve():
    """
    Start the server.
    """
    await mcp.run_stdio_async()


if __name__ == "__main__":
    import asyncio

    # Start the server
    asyncio.run(serve())
