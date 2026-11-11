"""Run with: python -m unittest discover -s tests -v"""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.modules = []
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.close()
        for module in self.modules:
            module.engine.dispose()
            sys.modules.pop(module.__name__, None)
        self.temp.cleanup()

    def load(self, name):
        key = name.replace('-', '_') + '_test_application'
        url = f"sqlite:///{self.temp.name}/{name}.db"
        spec = importlib.util.spec_from_file_location(key, ROOT / name / 'app/main.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        with patch.dict(os.environ, {'DATABASE_URL': url}):
            spec.loader.exec_module(module)
        module.Base.metadata.create_all(module.engine)
        self.modules.append(module)
        client = TestClient(module.app)
        self.clients.append(client)
        return module, client

    def test_book_persistence_validation_and_unknown_id(self):
        _, client = self.load('book-service')
        response = client.post('/books', json={'title':'Test Book','author':'Author','price':'450.00'})
        self.assertEqual(response.status_code, 201)
        created = response.json()
        self.assertEqual(client.get(f"/books/{created['id']}").json(), created)
        self.assertEqual(len(client.get('/books').json()), 1)
        self.assertEqual(client.post('/books', json={'title':' ','author':'A','price':'0'}).status_code, 422)
        self.assertEqual(client.get('/books/999999').status_code, 404)

    def test_order_calls_book_api_and_stores_exact_total(self):
        book, book_client = self.load('book-service')
        order, order_client = self.load('order-service')
        created = book_client.post('/books', json={'title':'Exact Money','author':'A','price':'0.10'}).json()
        # Route the real lookup through an in-process Book API client.
        with patch.object(order.httpx, 'Client', return_value=TestClient(book.app)):
            response = order_client.post('/orders', json={'book_id':created['id'],'quantity':3})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['total_price'], '0.30')
        saved = order_client.get(f"/orders/{response.json()['id']}")
        self.assertEqual(saved.json()['total_price'], '0.30')

    def test_failures_do_not_write_orders(self):
        order, client = self.load('order-service')
        for status in (404, 503):
            with patch.object(order, 'fetch_book_price', side_effect=HTTPException(status_code=status, detail='test')):
                self.assertEqual(client.post('/orders', json={'book_id':1,'quantity':2}).status_code, status)
        self.assertEqual(client.post('/orders', json={'book_id':1,'quantity':0}).status_code, 422)
        with Session(order.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(order.Order)), 0)

    def test_dependency_timeout_maps_to_503(self):
        order, client = self.load('order-service')
        with patch.object(order.httpx.Client, 'get', side_effect=order.httpx.ReadTimeout('timeout')):
            response = client.post('/orders', json={'book_id':1,'quantity':1})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['detail'], 'Book service unavailable')


if __name__ == '__main__':
    unittest.main()
