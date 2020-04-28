# cfn-sc-actions-provider
This template and associated Lambda function and custom resource add support to AWS CloudFormation for the [AWS Service Catalog Service Actions][1]
resource type.

# Custom Resource
We create this custom resource to automate service catalog action functionality.  This custom
resource is implemented with a lambda to allow creation, update, and deletion of SC actions
resources using cloudformation. It also provides the functionality to create, update and delete
SC action associations to SC products.

## Development

### Contributions
Contributions are welcome.

### Requirements
Run `pipenv install --dev` to install both production and development
requirements, and `pipenv shell` to activate the virtual environment. For more
information see the [pipenv docs](https://pipenv.pypa.io/en/latest/).

After activating the virtual environment, run `pre-commit install` to install
the [pre-commit](https://pre-commit.com/) git hook.

### Create a local build

```shell script
$ sam build --use-container
```

### Run locally

```shell script
$ sam local invoke CreateFunction --event events/create.json
```

### Run unit tests
Tests are defined in the `tests` folder in this project. Use PIP to install the
[pytest](https://docs.pytest.org/en/latest/) and run unit tests.

```shell script
$ python -m pytest tests/ -v
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

aws s3 cp .aws-sam/build/template.yaml s3://bootstrap-awss3cloudformationbucket-19qromfd235z9/cfn-cr-sc-actions-provider/master/
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
```bash script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/cfn-sc-actions-provider.yaml
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
  ProvisioningArtifactId: "pa-ejemsqmj4uewa"   # the SC product's version ID
```

Create the AWS cloudformation template

sc-action.yaml:
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
  ProvisioningArtifactId:
    Type: String
    Description: The SC product's version Id
Resources:
  # Create the SC action
  EC2InstanceAction:
    Type: Custom::ScActionsProvider
    Properties:
     ServiceToken: !ImportValue
      'Fn::Sub': '${AWS::Region}-cfn-sc-actions-provider-CreateFunctionArn'
     SsmDocName: !Ref SsmDocName
     SsmDocVersion: !Ref SsmDocVersion
     Name: !Ref Name
     AssumeRole: !Ref AssumeRole
  # Associate the SC action to a SC product
  AssociateProductAction:
    Type: Custom::ScActionsProvider
    Properties:
      ServiceToken: !ImportValue
        'Fn::Sub': '${AWS::Region}-cfn-sc-actions-provider-AssociateFunctionArn'
      ServiceActionId: !Ref EC2InstanceAction
      ProductId: !Ref ProductId
      ProvisioningArtifactId: !Ref ProvisioningArtifactId
Outputs:
  EC2InstanceActionId:
    Value: !Ref EC2InstanceAction
    Export:
      Name: !Sub '${AWS::Region}-${AWS::StackName}-EC2InstanceActionId'
```

Deploy the SC action:
```bash script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/sc-restart-instance-action.yaml
```

# Why a separate Lambda file

The code to handle creation updating and deletion of the OIDC Identity Provider
couldn't fit into the [4096 characters][2] allowed for embedded code without
heavily obfuscating the code.

[1]: https://docs.aws.amazon.com/servicecatalog/latest/adminguide/using-service-actions.html
[2]: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-lambda-function-code.html#cfn-lambda-function-code-zipfile
