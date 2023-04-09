from elegant_events import Server

# basic = Server("localhost", 7070, debugging=True)
basic = Server("localhost", 7070)

@basic.whenever("test_point")
def yo(*args):
    print(f'''args = {args}''')

basic.tell(path="test_point", data="howdy")
basic.check()