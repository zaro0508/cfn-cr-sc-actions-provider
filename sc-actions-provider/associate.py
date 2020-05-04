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
    provisioning_artifact_ids = event['ResourceProperties']['ProvisioningArtifactIds'].split("|")
    return aws_account_id, service_action_id, product_id, provisioning_artifact_ids

def create_service_action_associations(service_action_id, product_id, provisioning_artifact_ids):
    '''
    Create a list of service action associations for batch execution
    '''
    service_action_assocations = []
    for provisioning_artifact_id in provisioning_artifact_ids:
        service_action_assocation = {
            'ServiceActionId': service_action_id,
            'ProductId': product_id,
            'ProvisioningArtifactId': provisioning_artifact_id
        }
        service_action_assocations.append(service_action_assocation)

    return service_action_assocations

def associate_actions(aws_account_id, service_action_id, product_id, provisioning_artifact_ids):
    '''
    associate SC service actions with a product version
    '''

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

def disassociate_actions(aws_account_id, service_action_id, product_id, provisioning_artifact_ids):
    '''
    disassociate SC service actions from a product version
    '''
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

def update_action_associations(event):
    '''
    Update SC service action associations

    Adding a Product version (i.e. ProvisioningArtifactVersion) is an update event and
    associating an action to a product depends on the ProvisioningArtifactVersion(s)

    Adding a ProvisioningArtifactVersion works because CFN will create a new
    ProvisioningArtifactVersion ID and pass it to the association custom resource.
    The custom resource then associates the action with the new
    ProvisioningArtifactVersion(s)

    Removing a ProvisioningArtifactVersion does not work because AWS does not allow
    deleting a ProvisioningArtifactVersion when there is an action associated with it.
    The action would need to be disassociated from the ProvisioningArtifactVersion(s) before
    the ProvisioningArtifactVersion can be removed.  This would only work if the dependency
    is reversed (i.e. Provisioning versions depends on association)
    '''

    properties = event['ResourceProperties']
    service_action_id = properties['ServiceActionId']
    product_id = properties['ProductId']
    provisioning_artifact_ids = properties['ProvisioningArtifactIds'].split("|")
    old_properties = event['OldResourceProperties']
    old_provisioning_artifact_ids = old_properties['ProvisioningArtifactIds'].split("|")

    # We only associate new ProvisioningArtifactVersion(s)
    new_provisioning_artifact_ids = []
    if len(provisioning_artifact_ids) > len(old_provisioning_artifact_ids):
        for curr_provisioning_artifact_id in provisioning_artifact_ids:
            if curr_provisioning_artifact_id not in old_provisioning_artifact_ids:
                new_provisioning_artifact_ids.append(curr_provisioning_artifact_id)

        service_action_associations = create_service_action_associations(
            service_action_id,
            product_id,
            new_provisioning_artifact_ids)
        logger.debug(
            "Associate action " + service_action_id +
            " with product " + product_id + ", provisioning_artifact_ids: " +
            str(new_provisioning_artifact_ids))
        response = sc.batch_associate_service_action_with_provisioning_artifact(
            ServiceActionAssociations=service_action_associations
        )

    return event['PhysicalResourceId']

@helper.create
def create(event, context):
    logger.debug("Received event: " + json.dumps(event, sort_keys=False))
    return associate_actions(*get_parameters(event))

@helper.update
def update(event, context):
    logger.debug("Received event: " + json.dumps(event, sort_keys=False))
    return update_action_associations(event)


@helper.delete
def delete(event, context):
    logger.debug("Received event: " + json.dumps(event, sort_keys=False))
    disassociate_actions(*get_parameters(event))

def lambda_handler(event, context):
    helper(event, context)
