import json

import schemas_ee
import logging
from chalicelib.utils import helper
from chalicelib.utils import pg_client
from chalicelib.utils import events_queue


def handle_frontend_signals(project_id: int, user_id: str, data: schemas_ee.SignalsSchema):
    insights_query = """INSERT INTO public.frontend_signals (project_id, user_id, timestamp, action, source, category, data) VALUES (%(project_id)s, %(user_id)s, %(timestamp)s, %(action)s, %(source)s, %(category)s, %(data)s)"""
    try:
        with pg_client.PostgresClient() as conn:
            query = conn.mogrify(insights_query, {'project_id': project_id, 'user_id': user_id, 'timestamp': data.timestamp, 'action': data.action, 'source': data.source,
                                      'category': data.category, 'data': json.dumps(data.data)})
            conn.execute(query)
            # res = helper.dict_to_camel_case(conn.fetchone())
        return {'data': 'insertion succeded'}
    except Exception as e:
        logging.info(f'Error while inserting: {e}')
        return {'errors': [e]}

def handle_frontend_signals_queued(project_id: int, user_id: str, data: schemas_ee.SignalsSchema):
    try:
        events_queue.global_queue.put((project_id, user_id, data))
        return {'data': 'insertion succeded'}
    except Exception as e:
        logging.info(f'Error while inserting: {e}')
        return {'errors': [e]}
