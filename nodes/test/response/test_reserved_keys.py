# =============================================================================
# MIT License
# Copyright (c) 2026 Aparavi Software AG
# =============================================================================

"""Node-behavior test: the response node rejects result keys it writes itself.

``result_types``, ``metadata``, ``name`` and ``path`` are filled in by the node, so a
configured ``laneName`` with one of those names would either crash the next write
(``result_types`` is a dict, not a list) or be overwritten in close().
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

NODES_SRC = Path(__file__).parent.parent.parent / 'src' / 'nodes'
while str(NODES_SRC) in sys.path:
    sys.path.remove(str(NODES_SRC))
sys.path.insert(0, str(NODES_SRC))

from response.IGlobal import IGlobal  # noqa: E402
from response.IInstance import IInstance  # noqa: E402

RESERVED = ['result_types', 'metadata', 'name', 'path']


class _Obj:
    def __init__(self):
        self.response = {}
        self.hasComponentId = False
        self.hasMetadata = True
        self.metadata = {'author': 'a'}
        self.hasName = True
        self.name = 'file.pdf'
        self.hasPath = True
        self.path = '/some/directory/file.pdf'


def _begin(config, logicalType='response_text'):
    iglobal = IGlobal.__new__(IGlobal)
    iglobal.glb = SimpleNamespace(connConfig=config, logicalType=logicalType)
    iglobal.beginGlobal()
    return iglobal


def _make_instance(iglobal):
    inst = IInstance()
    inst.instance = SimpleNamespace(currentObject=_Obj())
    inst.IGlobal = iglobal
    inst.open(None)
    return inst


@pytest.mark.parametrize('key', RESERVED)
def test_reserved_lane_name_is_rejected(key):
    with pytest.raises(ValueError, match=f'Result key "{key}" is reserved'):
        _begin({'laneName': key})


@pytest.mark.parametrize('key', RESERVED)
def test_reserved_name_in_lanes_list_is_rejected(key):
    with pytest.raises(ValueError, match=f'Result key "{key}" is reserved'):
        _begin({'lanes': [{'laneId': 'text', 'laneName': 'body'}, {'laneId': 'json', 'laneName': key}]}, 'response')


@pytest.mark.parametrize(
    'logicalType, write, lane',
    [
        ('response_text', lambda inst: inst.writeText('hello'), 'text'),
        ('response_json', lambda inst: inst.writeJson({'a': 1}), 'json'),
        ('response_table', lambda inst: inst.writeTable('| a |'), 'table'),
    ],
)
def test_custom_lane_name_is_kept(logicalType, write, lane):
    inst = _make_instance(_begin({'laneName': 'defdoc'}, logicalType))
    write(inst)
    inst.close()

    response = inst.instance.currentObject.response
    assert len(response['defdoc']) == 1
    assert response['result_types'] == {'defdoc': lane}
    assert response['name'] == 'file.pdf'
    assert response['path'] == '/some/directory'
    assert response['metadata'] == {'author': 'a'}


def test_lanes_list_maps_each_lane_to_its_key():
    inst = _make_instance(_begin({'lanes': [{'laneId': 'text', 'laneName': 'body'}]}, 'response'))
    inst.writeText('hello')
    inst.writeTable('| a |')
    inst.close()

    response = inst.instance.currentObject.response
    assert response['body'] == ['hello\n\n']
    assert response['table'] == ['| a |']
    assert response['result_types'] == {'body': 'text', 'table': 'table'}
