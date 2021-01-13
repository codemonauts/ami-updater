# ami-updater

Little Lambda script to update all your  LaunchConfigurations after building a new AMI


## IAM Policy
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "ec2:CreateLaunchTemplateVersion",
            "Resource": "arn:aws:ec2:eu-central-1:ACCOUNT-ID:launch-template/*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeImages",
                "ec2:CreateLaunchTemplate",
                "ec2:GetLaunchTemplateData",
                "ec2:DescribeLaunchTemplates",
                "ec2:DescribeLaunchTemplateVersions"
            ],
            "Resource": "*"
        }
    ]
}
```
