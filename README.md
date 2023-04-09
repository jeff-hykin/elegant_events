# What is this?

A simple event manager that works between processes

# How do I use this?

`pip install elegant_events`

file1.py

```python
from elegant_events import Server

# will spinup a server in the background if one isn't already running
server1 = Server("localhost", 7070)

# 
# listener examples:
# 

# attach a listener that triggers every time
@server1.whenever("found_an_event")
def when_event_found(timestamp, data):
    print(f'''data = {data}''')

# attach a listener that will only trigger on the next occurance
@server1.once("found_an_event")
def when_event_found(timestamp, data):
    print(f'''data = {data}''')

# 
# send data example
# 
server1.tell(path="found_an_event", data="Hello from same process")


# 
# receive events examples:
# 

# manually check (e.g. the cooperative multitasking approach)
sleep(10) # (run the file2.py while this file is sleeping)
server1.check()
# because `.tell()` was called twice, when_event_found() will be triggered twice right here

# auto check (very efficiently wait for events from other processes)
# e.g. DONT do:
#     while True: server1.check()
server1.listen_forever() # 
```


file2.py

```python
from elegant_events import Server

# will spinup a server in the background if one isn't already running
server1 = Server("localhost", 7070)

# "data" can be anything that works with json.dumps()
server1.tell(path="found_an_event", data={"Hello from different process!": True})
```

# API


```python
from elegant_events import Server

# will spinup a server in the background if one isn't already running
server1 = Server("localhost", 7070)

# temp stop listening for an event
server1.stop_keeping_track_of("found_an_event")
# resume listening for an event
server1.keep_track_of("found_an_event")

# attach a listener that triggers every time
@server1.whenever("found_an_event", catch_and_print_errors=False)
def when_event_found(timestamp, data):
    pass

# attach a listener that will only trigger on the next occurance
@server1.once("found_an_event", catch_and_print_errors=False)
def when_event_found(timestamp, data):
    print(f'''data = {data}''')
    
```