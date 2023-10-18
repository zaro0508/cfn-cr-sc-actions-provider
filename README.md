# cfn-cr-sc-actions-provider
This template and associated Lambda function and custom resource add support to AWS CloudFormation for the [AWS Service Catalog Service Actions][1]
resource type.

# Custom Resource
We create this custom resource to automate service catalog action functionality.  This custom
resource is implemented with a lambda to allow creation, update, and deletion of SC actions
resources using cloudformation. It also provides the functionality to create, update and delete
SC action associations to SC products.

Due to a few AWS issues we have decided to implement a bastardized custom resource.
This bastard will only create and remove SC actions. Updates will be a noop.

The idea to work around the AWS issue is to use the following workflow:

1. Initially add all SC actions (stop/start/restart) to all SC product versions
2. Before a sceptre update make the CI remove all SC actions from all product versions
3. Let sceptre update all CFN templates, this includes updating products and it this
step will also re-add all SC actions to all SC product versions.

## AWS Issues

### Product Duplication

The cloudformation AWS::ServiceCatalog::CloudFormationProduct Property
ProvisioningArtifactParameters is not working correctly. It duplicates the entire
list of products on an update. This only happens after a service catalog action is
associated with one of the Product version (i.e. ProvisioningArtifactIds). This is
bad because you can wind up with a ton of product versions that do not match what's
in the cloudformation template. We are wondering if this is a know issue at AWS or
if are doing something wrong here?

For example:
1. start with two items in ProvisioningArtifactParameters list
2. associate an action to the product(s)
3. make a change to any CloudFormationProduct parameters (i.e. Owner)
4. redeploy product template

__NOTE__: two additional versions are deployed. now we wind up with 4 versions of the
product in AWS even though there are still only two version in the CFN template

### Changing ProvisioningArtifact ID
Attempt workaround to disassociate actions from product versions
update the product template, then re-associate with product versions again
failed to work because CloudFormationProduct always create new
ProvisioningArtifact IDs even though the product versions never changed.

Result:
Updates to product templates create a new ProductArtifactVersion ID which means that
new product versions get the actions however previously provisioned products will
lose the actions because it is associated with the old ProductArtifactVersion ID.

Example:
1. SC restart action associated with prod ver1 (pa-1234)
2. disassociate restart action from prod ver1 (pa-1234)
3. Add prod ver2

Prod ver 1 gets a new ProvisioningArtifact ID (pa-45678)
Prod ver 2 gets a new ProvisioningArtifact ID (pa-90909)

4. associate action to product ver1 & ver2

Now the SC restart actionm is associated with ver1 (pa-45678) & ver2 (pa-90909).
SC restart was removed from prod ver1 (pa-1234) in step #2 and step #4 never
put it back. This results causes any products provisioned with old ver1 (pa-1234)
to lose the SC action.

## Development

### Contributions
Contributions are welcome.

### Setup Development Environment

Install the following applications:
* [AWS CLI](https://github.com/aws/aws-cli)
* [AWS SAM CLI](https://github.com/aws/aws-sam-cli)
* [pre-commit](https://github.com/pre-commit/pre-commit)
* [pipenv](https://github.com/pypa/pipenv)

### Install Requirements

Run `pipenv install --dev` to install both production and development
requirements, and `pipenv shell` to activate the virtual environment. For more
information see the [pipenv docs](https://pipenv.pypa.io/en/latest/).

After activating the virtual environment, run `pre-commit install` to install
the [pre-commit](https://pre-commit.com/) git hook.

### Update Requirements

First, make any needed updates to the base requirements in `Pipfile`, then use
`pipenv` to regenerate both `Pipfile.lock` and `requirements.txt`.

```shell script
$ pipenv update --dev
```

We use `pipenv` to control versions in testing, but `sam` relies on
`requirements.txt` directly for building the lambda artifact, so we dynamically
generate `requirements.txt` from `Pipfile.lock` before building the artifact.
The file must be created in the `CodeUri` directory specified in
`template.yaml`.

```shell script
$ pipenv requirements > sc-actions-provider/requirements.txt
```

Additionally, `pre-commit` manages its own requirements.

```shell script
$ pre-commit autoupdate
```

### Create a local build

Use a Lambda-like docker container to build the Lambda artifact

```shell script
$ sam build --use-container
```

### Run unit tests

Tests are defined in the `tests` folder in this project, and dependencies are
managed with `pipenv`. Install the development dependencies and run the tests
using `coverage`.

```shell script
$ pipenv run coverage run -m pytest tests/ -svv
```

Automated testing will upload coverage results to [Coveralls](coveralls.io).

### Run integration tests

Running integration tests
[requires docker](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/sam-cli-command-reference-sam-local-start-api.html)

```shell script
$ sam local invoke CreateFunction --event events/create.json
```

## Deployment

### Build

```shell script
sam build
```

## Deploy Lambda to S3
This requires the correct permissions to upload to bucket
`bootstrap-awss3cloudformationbucket-19qromfd235z9` and
`essentials-awss3lambdaartifactsbucket-x29ftznj6pqw`

```shell script
sam package --template-file .aws-sam/build/template.yaml \
  --s3-bucket essentials-awss3lambdaartifactsbucket-x29ftznj6pqw \
  --output-template-file .aws-sam/build/cfn-cr-sc-actions-provider.yaml

aws s3 cp .aws-sam/build/cfn-cr-sc-actions-provider.yaml s3://bootstrap-awss3cloudformationbucket-19qromfd235z9/cfn-cr-sc-actions-provider/master/
```

## Install Lambda into AWS
Create the following [sceptre](https://github.com/Sceptre/sceptre) file

config/prod/cfn-cr-sc-actions-provider.yaml
```yaml
template_path: "remote/cfn-cr-sc-actions-provider.yaml"
stack_name: "cfn-cr-sc-actions-provider"
stack_tags:
  Department: "Platform"
  Project: "Infrastructure"
  OwnerEmail: "it@sagebase.org"
hooks:
  before_launch:
    - !cmd "curl https://s3.amazonaws.com/bootstrap-awss3cloudformationbucket-19qromfd235z9/cfn-cr-sc-actions-provider/master/cfn-cr-sc-actions-provider.yaml --create-dirs -o templates/remote/cfn-cr-sc-actions-provider.yaml"
```

Install the lambda using sceptre:
```shell script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/cfn-cr-sc-actions-provider.yaml
```

# Usage
This shows how to use the custom resource provider to create a SC service action and
associate the action to a SC product.  The provider contains two custom
resources, one to create the SC action and one to associate the action to a product.

## Creating SC Actions and Asssociation
Create the sceptre file

config/prod/sc-restart-instance-action.yaml:
```yaml
template_path: sc-action.yaml
stack_name: sc-restart-instance-action
stack_tags:
  Department: "Platform"
  Project: "Infrastructure"
  OwnerEmail: "joe.smith@sagebase.org"
parameters:
  # Action params
  Name: "RestartEC2Instance"
  SsmDocName: "AWS-RestartEC2Instance"
  SsmDocVersion: "1"
  AssumeRole: "arn:aws:iam::563295687221:role/SCEC2LaunchRole"
  # Assocation params
  ProductId: "prod-oxldqdwxwxtlg"              # the SC product ID
```

Create the AWS cloudformation template

template/sc-action.yaml:
```yaml
Description: Service Catalog Service Action
AWSTemplateFormatVersion: 2010-09-09
Parameters:
  SsmDocName:
    Type: String
    Description: The name of the SSM document providing the action
    AllowedValues:
      - AWS-StopEC2Instance
      - AWS-StartEC2Instance
      - AWS-RestartEC2Instance
    Default: "AWS-RestartEC2Instance"
  SsmDocVersion:
    Type: String
    Description: The SSM document version
    Default: "1"
  Name:
    Type: String
    Description: The SC action name
  AssumeRole:
    Type: String
    Description: The IAM role that SC actions will use
  ProductId:
    Type: String
    Description: The SC product Id
Resources:
  # Create the SC action
  EC2InstanceAction:
    Type: Custom::ScActionsProvider
    Properties:
     ServiceToken: !ImportValue
      'Fn::Sub': '${AWS::Region}-cfn-cr-sc-actions-provider-CreateFunctionArn'
     SsmDocName: !Ref SsmDocName
     SsmDocVersion: !Ref SsmDocVersion
     Name: !Ref Name
     AssumeRole: !Ref AssumeRole
  # Associate the SC action to a SC product
  AssociateProductAction:
    Type: Custom::ScActionsProvider
    Properties:
      ServiceToken: !ImportValue
        'Fn::Sub': '${AWS::Region}-cfn-cr-sc-actions-provider-AssociateFunctionArn'
      ServiceActionId: !Ref EC2InstanceAction
      ProductId: !Ref ProductId
Outputs:
  EC2InstanceActionId:
    Value: !Ref EC2InstanceAction
    Export:
      Name: !Sub '${AWS::Region}-${AWS::StackName}-EC2InstanceActionId'
```

Deploy the SC action:
```shell script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/sc-restart-instance-action.yaml
```

# Why a separate Lambda file

The code to handle creation updating and deletion of the OIDC Identity Provider
couldn't fit into the [4096 characters][2] allowed for embedded code without
heavily obfuscating the code.

[1]: https://docs.aws.amazon.com/servicecatalog/latest/adminguide/using-service-actions.html
[2]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-lambda-function-code.html#cfn-lambda-function-code-zipfile
