import boto3
import json
import logging
import uuid

from crhelper import CfnResource

logger = logging.getLogger(__name__)
helper = CfnResource(
    json_logging=False, log_level='DEBUG', boto_level='CRITICAL')

try:
    sc = boto3.client("servicecatalog")
except Exception as e:
    helper.init_failure(e)

def get_parameters(event):
    aws_account_id = event['StackId'].split(':')[4]
    service_action_id = event['ResourceProperties']['ServiceActionId']
    product_id = event['ResourceProperties']['ProductId']
    return aws_account_id, service_action_id, product_id

def get_provisioning_artifact_ids(product_id):
    '''
    Get all product version IDs
    '''
    response = sc.list_provisioning_artifacts(
        ProductId=product_id
    )
    provisioning_artifact_details = response['ProvisioningArtifactDetails']
    provisioning_artifact_ids = []
    for provisioning_artifact_detail in provisioning_artifact_details:
        provisioning_artifact_ids.append(provisioning_artifact_detail['Id'])

    return provisioning_artifact_ids

def create_service_action_associations(service_action_id, product_id):
    '''
    Create a list of service action associations for batch execution
    '''
    provisioning_artifact_ids = get_provisioning_artifact_ids(product_id)
    service_action_assocations = []
    for provisioning_artifact_id in provisioning_artifact_ids:
        service_action_assocation = {
            'ServiceActionId': service_action_id,
            'ProductId': product_id,
            'ProvisioningArtifactId': provisioning_artifact_id
        }
        service_action_assocations.append(service_action_assocation)

    return service_action_assocations

def associate_actions(aws_account_id, service_action_id, product_id):
    '''
    associate SC service actions with a product version
    '''
    provisioning_artifact_ids = get_provisioning_artifact_ids(product_id)
    logger.debug(
        "Associate action " + service_action_id +
        " with product " + product_id + ", provisioning_artifact_ids: " +
        str(provisioning_artifact_ids))
    service_action_associations = create_service_action_associations(
        service_action_id,
        product_id,
        provisioning_artifact_ids)
    response = sc.batch_associate_service_action_with_provisioning_artifact(
        ServiceActionAssociations=service_action_associations
    )
    physical_resource_id = 'ass-{}'.format(str(uuid.uuid4()).replace('-', '')[0:13])
    return physical_resource_id

def disassociate_actions(aws_account_id, service_action_id, product_id):
    '''
    disassociate SC service actions from a product version
    '''
    provisioning_artifact_ids = get_provisioning_artifact_ids(product_id)
    logger.debug(
        "dis-associate action " + service_action_id +
        " with product " + product_id + ", provisioning_artifact_ids: " +
        str(provisioning_artifact_ids))
    associations = create_service_action_associations(
        service_action_id,
        product_id,
        provisioning_artifact_ids)
    response = sc.batch_disassociate_service_action_from_provisioning_artifact(
        ServiceActionAssociations=associations
    )


@helper.create
def create(event, context):
    logger.debug("Received event: " + json.dumps(event, sort_keys=False))
    return associate_actions(*get_parameters(event))

@helper.update
def update(event, context):
    logger.debug("Received event: " + json.dumps(event, sort_keys=False))
    return event['PhysicalResourceId']


@helper.delete
def delete(event, context):
    logger.debug("Received event: " + json.dumps(event, sort_keys=False))
    disassociate_actions(*get_parameters(event))

def lambda_handler(event, context):
    helper(event, context)
