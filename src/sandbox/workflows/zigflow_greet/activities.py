from temporalio import activity


@activity.defn
async def shout_greet(name: str) -> str:
    return f"HELLO {name.upper()}"
