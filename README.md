# ami-updater

Little Lambda script to update all your LaunchConfigurations after building a new AMI


## Required IAM Permissions
```
"Action": [
    "ec2:CreateLaunchTemplate",
    "ec2:CreateLaunchTemplateVersion",
    "ec2:DeleteLaunchTemplateVersions",
    "ec2:DeregisterImage",
    "ec2:DescribeImages",
    "ec2:DescribeLaunchTemplateVersions"
    "ec2:DescribeLaunchTemplates",
    "ec2:GetLaunchTemplateData",
    "ec2:ModifyLaunchTemplate"
]
```
