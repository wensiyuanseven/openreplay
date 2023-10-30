import asyncio
from asyncio import Queue

from decouple import config
from confluent_kafka import Consumer
from datetime import datetime
import requests
import json


from time import time
QUICKWIT_PORT = config('QUICKWIT_PORT', default=7280, cast=int)
max_retry=3

async def _quickwit_ingest(index, data_list, retry=0):
    try:
        res = requests.post(f'http://localhost:{QUICKWIT_PORT}/api/v1/{index}/ingest', data=__jsonify_data(data_list, index))
    except requests.exceptions.ConnectionError as e:
        retry += 1
        assert retry <= max_retry, f'[ENDPOINT CONNECTION FAIL] Failed to connect to endpoint http://localhost:{QUICKWIT_PORT}/api/v1/{index}/ingest\n{e}\n'
        await asyncio.sleep(3*retry)
        print(f"[ENDPOINT ERROR] Failed to connect to endpoint http://localhost:{QUICKWIT_PORT}/api/v1/{index}/ingest, retrying in {3*retry} seconds..\n")
        return await _quickwit_ingest(index, data_list, retry=retry)
    return res

def __jsonify_data(data_list, msg_type):
    res = list()
    i = 0
    for data in data_list:
        if msg_type == 'fetchevent':
            try:
                _tmp = data['request']
                if _tmp != '':
                    data['request'] = json.loads(_tmp)
                else:
                    data['request'] = {}
                _tmp = data['response']
                if _tmp != '':
                    data['response'] = json.loads(_tmp)
                    if data['response']['body'][:1] == '{' or data['response']['body'][:2] == '[{':
                        data['response']['body'] = json.loads(data['response']['body'])
                else:
                    data['response'] = {}
            except Exception as e:
                print(f'Error {e}\tWhile decoding fetchevent\nEvent: {data}\n')
        elif msg_type == 'graphql':
            try:
                _tmp = data['variables']
                if _tmp != '':
                    data['variables'] = json.loads(_tmp)
                else:
                    data['variables'] = {}
                _tmp = data['response']
                if _tmp != '':
                    data['response'] = json.loads(_tmp)
                else:
                    data['response'] = {}
            except Exception as e:
                print(f'Error {e}\tWhile decoding graphql\nEvent: {data}\n')
        i += 1
        res.append(json.dumps(data))
    return '\n'.join(res)

def message_type(message):
    if 'loaded' in message.keys():
        return 'pageevent'
    elif 'variables' in message.keys():
        return 'graphql'
    elif 'status' in message.keys():
        return 'fetchevent'
    else:
        return 'default'


class KafkaFilter():

    def __init__(self, uid):
        self.uid = uid
        kafka_sources = config('KAFKA_SERVER')
        topic = config('QUICKWIT_TOPIC')

        self.fetchevent_maxsize = config('fetch_maxsize', default=100, cast=int)
        self.graphql_maxsize = config('graphql_maxsize', default=100, cast=int)
        self.pageevent_maxsize = config('pageevent_maxsize', default=100, cast=int)

        self.consumer = Consumer({
            "security.protocol": "SSL",
            "bootstrap.servers": kafka_sources,
            "group.id": config("group_id"),
            "auto.offset.reset": "earliest",
            #value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            "enable.auto.commit": False
        })
        self.consumer.subscribe([topic])
        self.queues = {'fetchevent': Queue(self.fetchevent_maxsize),
                'graphql': Queue(self.graphql_maxsize),
                'pageevent': Queue(self.pageevent_maxsize)
                }

    async def add_to_queue(self, message):
        # TODO: Fix this method
        associated_queue = message_type(message)
        if associated_queue == 'default':
            return
        await self.queues[associated_queue].put(message)

    async def flush_to_quickwit(self):
        # TODO: Fix this method
        one_queue_full = any([q.full() for q in self.queues.values()])
        if not one_queue_full:
            return
        for queue_name, _queue in self.queues.items():
            _list = list()
            unix_timestamp = int(datetime.now().timestamp())
            while not _queue.empty():
                msg = await _queue.get()
                value = dict(msg)
                value['insertion_timestamp'] = unix_timestamp
                if queue_name == 'fetchevent' and 'message_id' not in value.keys():
                    value['message_id'] = 0
                _list.append(value)
            if len(_list) > 0:
                await _quickwit_ingest(queue_name, _list)
        # self.consumer.commit() ## TODO: Find when to run commit


    async def process_messages(self):
        _tmp_previous = None
        repeated = False
        while True:
            msg = self.consumer.poll(1.0)
            if msg is None:
                await asyncio.sleep(0.1)
                continue
            value = json.loads(msg.value().decode('utf-8'))
            messages = [value]
                                                
            if _tmp_previous is None:
                _tmp_previous = messages
                if isinstance(messages, list):
                    for message in messages:
                        await self.add_to_queue(message)
                else:
                    await self.add_to_queue(messages)
                                                
            elif _tmp_previous != messages:
                if isinstance(messages, list):
                    for message in messages:
                        await self.add_to_queue(message)
                else:
                    await self.add_to_queue(messages)
                _tmp_previous = messages
                repeated = False
            elif not repeated:
                repeated = True

    async def upload_messages(self):
        while True:
            await self.flush_to_quickwit()
            await asyncio.sleep(1)

    async def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.process_messages())
        loop.create_task(self.upload_messages())
        return

    def __repr__(self):
        return f"Class object KafkaConsumer id #{self.uid}"


if __name__ == '__main__':
    layer = KafkaFilter(uid=0)
    asyncio.run(layer.run())
