import asyncio

import pytest

from protogen.input_manager import InputManager
from protogen.commands import Command, InputEvent


@pytest.mark.asyncio
async def test_put_and_get():
    mgr = InputManager()
    cmd = Command(event=InputEvent.NEXT_EXPRESSION)
    await mgr.put(cmd)
    result = await mgr.get()
    assert result == cmd


@pytest.mark.asyncio
async def test_queue_ordering():
    mgr = InputManager()
    cmd1 = Command(event=InputEvent.SET_EXPRESSION, value="happy")
    cmd2 = Command(event=InputEvent.SET_EXPRESSION, value="sad")
    await mgr.put(cmd1)
    await mgr.put(cmd2)
    assert (await mgr.get()) == cmd1
    assert (await mgr.get()) == cmd2
