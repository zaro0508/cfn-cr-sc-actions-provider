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
```shell script
sceptre --var "profile=my-profile" --var "region=us-east-1" launch prod/cfn-cr-sc-actions-provider.yaml
```
