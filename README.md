# ami-updater

Little Lambda script to update all your EC2 launch configurations after building a new AMI.

## Description

The Lambda function searchs for all existing Launch Templates. If the Launch Template has a tag `ami-search-string`, all AMIs with the value of the tag will be considered as possible AMIs to use. Then it checks if there is a new AMI available (creation time) and creates a new default version with the new AMI.

After this, all versions withing the retension policy will be kept, all older versions and their AMIs and snapshots will be deleted.

### Search Tag

The template tag `ami-search-string` is used to find all possible AMIs by the defined name. You can use wildcards like `webserver_*`.

### Retension policy

In the Lambda function, you can add an environment variable called `KEEP_AMIS` to set the maximal versions to keep (including the new version created). The default value is 3.

## Installation by hand

### Role and policy

Create a role for the Lambda function and add the following policy. Please replace the `<REGION>` and `<ACCOUNTID>` with your values.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ec2:DeregisterImage",
            "Resource": "arn:aws:ec2:<REGION>::image/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeImages",
                "ec2:DescribeLaunchTemplates",
                "ec2:DescribeLaunchTemplateVersions"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:ModifyLaunchTemplate",
                "ec2:DeleteLaunchTemplateVersions",
                "ec2:CreateLaunchTemplateVersion"
            ],
            "Resource": "arn:aws:ec2:<REGION>:<ACCOUNTID>:launch-template/*"
        },
        {
            "Effect": "Allow",
            "Action": "ec2:DeleteSnapshot",
            "Resource": "arn:aws:ec2:*::snapshot/*"
        },
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:<REGION>:<ACCOUNTID>:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:<REGION>:<ACCOUNTID>:log-group:/aws/lambda/ami-updater:*"
            ]
        }
    ]
}
```

### Build package for Lambda

Run the following command to build a `package.zip` with the code for the Lambda function. 

```shell
make build
```

### Lambda function

You can create the Lambda function with the console. The following settings are recommended:

- Timeout wit 60 seconds or more (depends on the number of Launch templates to check).
- Runtime is Python 3.11 or newer.
- The handler is `main.lambda_handler`.
- Architecture can be `arm64` or `x86_64`.
- Add an environment variable `KEEP_AMIS` with the value of the number of AMIs to keep per Launch Template. Default is 3.

Or create a Lambda function with the AWS CLI. Replace the `<ARN>` with the ARN of the role created above:

```shell
aws lambda create-function \
    --function-name ami-updater \
    --runtime python3.11 \
    --zip-file fileb://package.zip \
    --handler main.lambda_handler \
    --timeout 60 \
    --publish \
    --architectures arm64 \
    --role <ARN>
```

You have now a Lambda function without a trigger. We suggest to use an EventBridge schedule rule or the EventBridge Scheduler.

## Installation by Terraform

You can use the `main.tf` to

- Create all roles.
- A log group.
- The Lambda function itself.
- A scheduler to invoke the Lambda function at a 12 hours rate.

If you know what you do, you can do:

```shell
make build
make plan
make deploy
```
