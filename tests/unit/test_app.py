from botocore.stub import Stubber

# Needed to import a module with hyphens in the name.
# This mimics an import of the form:
#   from sc-actions-provider import app
import importlib
app = importlib.import_module('sc-actions-provider.app')


mock_event = {
    'StackId': 'arn:aws:cloudformation:test-region:test-account:stack/test/uuid',
    'ResourceProperties': {
        'Name': 'test-name',
        'SsmDocName': 'test-ssm-doc',
        'SsmDocVersion': 'test-ssm-doc-version',
        'AssumeRole': 'test-role-name',
    },
    'OldResourceProperties': {},
    'PhysicalResourceId': 'test-physical-id',
}


mock_response = {
    'ServiceActionDetail': {
        'ServiceActionSummary': {
            'Id': 'test-physical-id'
        }
    }
}


def test_create():
    with Stubber(app.sc) as stub:
        stub.add_response('create_service_action', mock_response)
        test_id = app.create(mock_event, {})
        assert test_id == 'test-physical-id'
        stub.assert_no_pending_responses()


def test_delete():
    with Stubber(app.sc) as stub:
        stub.add_response('delete_service_action', {})
        app.delete(mock_event, {})
        stub.assert_no_pending_responses()


def test_update():
    with Stubber(app.sc) as stub:
        stub.add_response('update_service_action', mock_response)
        test_id = app.update(mock_event, {})
        assert test_id == 'test-physical-id'
        stub.assert_no_pending_responses()
