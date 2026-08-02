import pytest
import datetime
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor

from engine_core.model_results_repository import ModelResult, ModelResultRepository

# Mock connection and cursor for testing
class MockCursor:
    def __init__(self, fetchall_data=None, fetchone_data=None):
        self.fetchall_data = fetchall_data or []
        self.fetchone_data = fetchone_data
        self.queries = []
        self.params = []

    def execute(self, query, params=None):
        self.queries.append(query)
        self.params.append(params)

    def fetchall(self):
        return self.fetchall_data

    def fetchone(self):
        return self.fetchone_data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockConnection:
    def __init__(self, fetchall_data=None, fetchone_data=None):
        self.cursor_mock = MockCursor(fetchall_data, fetchone_data)
        self.committed = False
        self.closed = False

    def cursor(self, cursor_factory=None):
        return self.cursor_mock

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_model_result_from_row():
    row = {
        'symbol': 'POLYCAB',
        'model_id': 'RRG',
        'model_version': '1.0',
        'evaluation_date': datetime.date(2026, 8, 3),
        'status': 'SUCCESS',
        'score': Decimal('85.5'),
        'payload': {'quadrant': 'Leading'},
        'explain_node_id': '550e8400-e29b-41d4-a716-446655440000'
    }
    result = ModelResult.from_row(row)
    assert result.symbol == 'POLYCAB'
    assert result.model_id == 'RRG'
    assert result.model_version == '1.0'
    assert result.evaluation_date == datetime.date(2026, 8, 3)
    assert result.status == 'SUCCESS'
    assert result.score == Decimal('85.5')
    assert result.payload == {'quadrant': 'Leading'}
    assert result.explain_node_id == '550e8400-e29b-41d4-a716-446655440000'


def test_repository_save():
    conn = MockConnection()
    repo = ModelResultRepository(conn=conn)
    
    result = ModelResult(
        symbol='POLYCAB',
        model_id='CANSLIM',
        model_version='1.2',
        evaluation_date=datetime.date(2026, 8, 3),
        status='PASS',
        score=Decimal('82.0'),
        payload={'letters': {'C': 'PASS'}}
    )
    
    repo.save(result)
    
    assert conn.committed
    assert len(conn.cursor_mock.queries) == 1
    assert "INSERT INTO model_results" in conn.cursor_mock.queries[0]
    assert "ON CONFLICT (symbol, model_id, model_version, evaluation_date)" in conn.cursor_mock.queries[0]
    
    # Check that payload was JSON encoded
    params = conn.cursor_mock.params[0]
    assert params['symbol'] == 'POLYCAB'
    assert params['payload'] == '{"letters": {"C": "PASS"}}'


def test_repository_latest():
    # Setup mock returns
    row1 = {
        'symbol': 'POLYCAB', 'model_id': 'RRG', 'model_version': '1.0', 
        'evaluation_date': datetime.date(2026, 8, 3), 'status': None, 'score': None,
        'payload': None, 'explain_node_id': None
    }
    row2 = {
        'symbol': 'POLYCAB', 'model_id': 'CANSLIM', 'model_version': '1.2', 
        'evaluation_date': datetime.date(2026, 8, 3), 'status': 'PASS', 'score': Decimal('84'),
        'payload': None, 'explain_node_id': None
    }
    conn = MockConnection(fetchall_data=[row1, row2])
    repo = ModelResultRepository(conn=conn)
    
    results = repo.latest('POLYCAB')
    
    assert len(results) == 2
    assert results[0].model_id == 'RRG'
    assert results[1].model_id == 'CANSLIM'
    assert "DISTINCT ON (model_id)" in conn.cursor_mock.queries[0]


def test_repository_latest_for_model():
    row = {
        'symbol': 'POLYCAB', 'model_id': 'CANSLIM', 'model_version': '1.2', 
        'evaluation_date': datetime.date(2026, 8, 3), 'status': 'PASS', 'score': Decimal('84'),
        'payload': None, 'explain_node_id': None
    }
    conn = MockConnection(fetchone_data=row)
    repo = ModelResultRepository(conn=conn)
    
    result = repo.latest_for_model('POLYCAB', 'CANSLIM')
    
    assert result is not None
    assert result.model_id == 'CANSLIM'
    assert result.score == Decimal('84')
    assert "WHERE symbol = %s AND model_id = %s" in conn.cursor_mock.queries[0]
