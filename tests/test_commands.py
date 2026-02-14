from protogen.commands import Command, InputEvent


def test_command_creation():
    cmd = Command(event=InputEvent.SET_EXPRESSION, value="happy")
    assert cmd.event == InputEvent.SET_EXPRESSION
    assert cmd.value == "happy"


def test_command_without_value():
    cmd = Command(event=InputEvent.NEXT_EXPRESSION)
    assert cmd.value is None
