# 1. start a server process
# 2. dump event data to a server
# 3. listen to event data from a server collaboratively (polling)
# 4. listen to event data from a server synchonously 

from random import random
import json
import time
import traceback
import asyncio

from websockets.sync.client import connect   # pip install websockets
import json_fix                              # pip install json-fix

this_file = __file__ # seems dumb but will break in interpreter if not assigned to a var

class Server:
    def __init__(self, address, port, debugging=False):
        self.address     = address
        self.port        = port
        self.connections = dict()
        self.id          = f"{random()}"
        self.tracking    = []
        self.url_base    = f"ws://{self.address}:{self.port}"
        self.callbacks   = {}
        self.debugging   = debugging
        try:
            with connect(f"{self.url_base}/builtin/ping") as websocket:
                message = websocket.recv()
                if message != "pong":
                    raise Exception(f'''Ping-pong with {self.url_base} failed, received: {repr(message)}''')
        except Exception as error:
            debugging and traceback.print_exc()
            debugging and print(f"starting server, {error}")
            import subprocess
            _process = subprocess.Popen(
                [
                    sys.executable,
                    this_file,
                    address,
                    f"{port}",
                ],
                **(dict(stdout=sys.stdout) if self.debugging else dict(stdout=subprocess.PIPE)),
                # stderr=subprocess.STDOUT,
            )
    
    def _builtin_tell(self, path, data):
        path = "builtin/"+path
        if not self.connections.get(path, None):
            self.connections[path] = connect(f"{self.url_base}/{path}")
        self.connections[path].send(json.dumps(data))
        return self.connections[path]
    
    def tell(self, path, data):
        path = "custom/"+path
        if not self.connections.get(path, None):
            self.connections[path] = connect(f"{self.url_base}/{path}")
        self.connections[path].send(json.dumps(data))
        return self.connections[path]
    
    def keep_track_of(self, path):
        if path not in self.tracking:
            self._builtin_tell("keep_track_of", dict(
                id=self.id,
                path=path,
            ))
            self.tracking.append(path)
    
    def stop_keeping_track_of(self, path):
        if path in self.tracking:
            self._builtin_tell("stop_keeping_track_of", dict(
                id=self.id,
                path=path,
            ))
            if path in self.tracking:
                self.tracking.remove(path)
    
    def check(self, path=None, paths=None):
        if path != None:
            paths = [ path ]
        response = self._builtin_tell("check", dict(
            id=self.id,
            paths=paths,
        )).recv()
        backlog = json.loads(response)
        self._process_backlog(backlog)
    
    def _process_backlog(self, backlog):
        chonological_backlog = []
        for each_path, events in backlog.items():
             for timestamp, data in events:
                chonological_backlog.append((timestamp, each_path, data))
        chonological_backlog.sort()
        for timestamp, each_path, data in chonological_backlog:
            data = json.loads(data)
            self.trigger(each_path, timestamp, data)
    
    def trigger(self, path, timestamp, data):
        new_callbacks_list = []
        for error_will_stop_main, runs_once, each_callback in self.callbacks.get(path, []):
            if error_will_stop_main:
                each_callback(timestamp, data)
            else:
                try:
                    each_callback(timestamp, data)
                except Exception as error:
                    # print the full stack trace, but keep going
                    traceback.print_exc()
            if not runs_once:
                new_callbacks_list.append((error_will_stop_main, runs_once, each_callback))
        # new list doesn't have any run_once functions
        self.callbacks[path] = new_callbacks_list
            
    def whenever(self, path, error_will_stop_main=False):
        self.keep_track_of(path)
        runs_once = False
        def function_getter(function_being_wrapped):
            self.callbacks[path] = self.callbacks.get(path, [])
            self.callbacks[path].append((error_will_stop_main, runs_once, function_being_wrapped))
        return function_getter
    
    def once(self, path, error_will_stop_main=False):
        self.keep_track_of(path)
        runs_once = True
        def function_getter(function_being_wrapped):
            self.callbacks[path] = self.callbacks.get(path, [])
            self.callbacks[path].append((error_will_stop_main, runs_once, function_being_wrapped))
        return function_getter
        
    def listen_forever(self):
        """
        a much more efficient and responsive alternative to while True: server.check()
        """
        with connect(f"{self.url_base}/builtin/listen") as connection:
            connection.send(json.dumps(dict(id=self.id)))
            while True:
                response = connection.recv()
                backlog = json.loads(response)
                self._process_backlog(backlog)
            
            
            
        

def start_server(address, port):
    import asyncio
    import argparse 
    import base64

    from websockets import serve # pip install websockets
    
    listeners = {}
    trackers = {}
    backlog = {}
    
    # 
    # socket setup
    # 
    async def socket_response(websocket):
        async for message in websocket:
            if websocket.path == "/builtin" or websocket.path.startswith("/builtin/"):
                if websocket.path == "/builtin/ping":
                    print("sending pong")
                    await websocket.send("pong")
                elif websocket.path == "/builtin/keep_track_of":
                    content = json.loads(message)
                    the_id = content["id"]
                    the_path = content["path"]
                    backlog[the_id] = backlog.get(the_id, {})
                    backlog[the_id][the_path] = backlog[the_id].get(the_path, [])
                    trackers[the_path] = trackers.get(the_path, [])
                    if the_id not in trackers[the_path]:
                        trackers[the_path].append(the_id)
                elif websocket.path == "/builtin/stop_keeping_track_of":
                    content = json.loads(message)
                    the_id = content["id"]
                    the_path = content["path"]
                    backlog[the_id] = backlog.get(the_id, {})
                    if the_path in backlog[the_id]:
                        del backlog[the_id][the_path]
                    
                    if the_id not in trackers[the_path]:
                        trackers[the_path].append(the_id)
                    trackers[the_path] = trackers.get(the_path, [])
                    if the_id in trackers[the_path]:
                        trackers[the_path].remove(the_id)
                elif websocket.path == "/builtin/check":
                    content         = json.loads(message)
                    the_id          = content["id"]
                    backlog[the_id] = backlog.get(the_id, {})
                    the_paths       = content.get("paths", None)
                    if the_paths == None:
                        await websocket.send(json.dumps(backlog[the_id]))
                        # clear out the backlog
                        for each_value in backlog[the_id].values():
                            each_value.clear()
                    else:
                        return_message = {}
                        for each_path in the_paths:
                            return_message[each_path] = backlog[the_id].get(each_path,[])
                            backlog[the_id].get(each_path,[]).clear()
                        await websocket.send(json.dumps(return_message))
                elif websocket.path == "/builtin/listen":
                    content         = json.loads(message)
                    the_id          = content["id"]
                    listeners[the_id] = websocket # even if it already had a socket, only use the latest one
                else:
                    print(f"warning, unknown attempt to call a builtin: {websocket.path}")
            elif websocket.path.startswith("/custom/"):
                the_path = websocket.path[len("/custom/"):]
                packet = (time.time(), message)
                for each_id in trackers.get(the_path, []):
                    backlog[each_id][the_path].append(packet)
                    if each_id in listeners:
                        # respond on the other socket
                        await listeners[each_id].send(json.dumps(backlog[each_id]))
                        # clear out the backlog if there was one
                        for each_value in backlog[each_id].values():
                            each_value.clear()
                            
                        
    # 
    # start servers
    # 
    async def main():
        async with serve(socket_response, address, port):
            await asyncio.Future()  # run forever

    asyncio.run(main())

if __name__ == '__main__':
    import sys
    start_server(address=sys.argv[1], port=sys.argv[2])