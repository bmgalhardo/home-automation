from typing import List
import logging
import requests
import os
import redis
import datetime

logging.basicConfig(level=logging.INFO)


def total_read(entry: dict):
    return entry['C'] + entry['V'] + entry['P']


class EDPConnect:
    USERNAME = os.getenv('USERNAME')
    PASSWORD = os.getenv('PASSWORD')
    ADDRESS = os.getenv('ADDRESS')
    r = redis.Redis(host='redis')
    HEADERS = {}

    @classmethod
    def set_headers(cls, token) -> None:
        cls.HEADERS = {"Authorization": f"Bearer {token}"}

    @classmethod
    def get_token(cls) -> None:

        response = requests.post(f"{cls.ADDRESS}/auth/auth/signin",
                                 json={
                                     "username": cls.USERNAME,
                                     "password": cls.PASSWORD,
                                 }, verify=False)

        try:
            token = response.json()['Body']['Result']['token']
        except KeyError:
            raise Exception("token not set")

        # store in cache
        cls.r.set('edp_token', token)
        cls.set_headers(token)
        logging.info('new token cached')

    @classmethod
    def authenticate(cls, invalid=False):
        """ authenticate DeepGrid API using token

        """
        if invalid:
            cls.get_token()
        else:
            cache_token = None
            try:
                cache_token = cls.r.get('edp_token').decode()
            except ConnectionError:
                logging.error("can't connect to redis, token will not be cached")

            if cache_token is None:
                cls.get_token()
            else:
                token = cache_token
                cls.set_headers(token)

        return cls

    @classmethod
    def post_response(cls, endpoint, data):
        """ general way to query API endpoint"""

        result = requests.post(endpoint, json=data, headers=cls.HEADERS, verify=False)

        if result.status_code == 401:
            logging.info('authenticating')
            cls.authenticate(True)

            result = cls.post_response(endpoint, data)
        elif result.status_code != 200:
            raise Exception('Error requesting data')

        return result

    @classmethod
    def get_monthly_active_power(cls, contract) -> int:
        now = datetime.datetime.now()
        data = {
            "cpe": contract,
            "request_type": "1",
            "start_date": now.strftime("%Y-%m-01 00:00:00"),
            "end_date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "wait": True,
            "formatted": True
        }

        response = cls.post_response(f"{cls.ADDRESS}/reading/data-usage/edm/get",
                                     data=data)

        try:
            active_power = response.json()['Body']['Result'][0]['Readings']['active']
        except (KeyError, TypeError):
            active_power = []

        month_end_read = total_read(active_power[0])
        month_start_read = total_read(active_power[-1])

        return month_end_read - month_start_read

    @classmethod
    def get_contracts(cls) -> List[dict]:
        data = {"nif": f"PT{cls.USERNAME}"}
        response = cls.post_response(f"{cls.ADDRESS}/masterdata/contract/pocket-get-contracts-by-nif",
                                     data=data)
        data = response.json()['Body']['Result']['data']
        contracts = [{'contract': d['cpe'], 'street_name': d['street_name']} for d in data]
        return contracts

